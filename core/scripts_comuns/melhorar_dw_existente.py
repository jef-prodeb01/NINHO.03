#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Motor Fast-Track de Melhoria Pontual para DW Oracle Já Construído (Sem Alterar Carga)
Plataforma NINHO — Funcionalidades Rápidas (Quick Wins / Brownfield DW)

Quando o Engenheiro de Dados já construiu o DW (DIM_*, FATO_*, STG_*) e não vai
mexer na esteira de carga (ODI / Hop / Python), este utilitário lê o DDL existente
e gera apenas os ajustes cirúrgicos solicitados, sem exigir o fluxo completo do
INTAKE_DW.md e sem recriar tabelas (zero DROP/CREATE destrutivo):

Modos de Operação (--modo):
  1. comentarios (/gerar-comentarios):
     - Gera scripts SQL não-destrutivos de COMMENT ON TABLE (com grão explícito) e
       COMMENT ON COLUMN para todas as tabelas e colunas do DDL.
     - Gera o Dicionário de Dados interativo em HTML (11_dicionario_dados/dicionario_dados.html).
  2. indices (/gerar-indices):
     - Analisa os índices já existentes no DDL e gera apenas os índices faltantes:
       * Fatos: BITMAP INDEX (Estratégia A) ou B-TREE COMPRESS 1 (Estratégia B) em todas as FKs,
         com PARALLEL 4 NOLOGGING -> ALTER INDEX NOPARALLEL LOGGING + DBMS_STATS.
       * Dimensões: B-TREE INDEX na PK (se ausente), Lookup SCD2 composto (Chave Natural + Vigência)
         e colunas de filtro, garantindo zero Bitmap em Dimensões (prevenção de ORA-00060).
     - Gera a procedure PRC_PRE_CARGA_FATO e PRC_POS_CARGA_FATO (05_procedimentos_manutencao/).
  3. patch (/melhorar-dw-existente) ou tudo:
     - Executa o Raio-X completo do DDL existente (DIAGNOSTICO_MELHORIAS_DW_EXISTENTE.md).
     - Gera scripts não-destrutivos de evolução (ALTER TABLE ENABLE NOVALIDATE para PKs/FKs
       faltantes + MERGE idempotente do registro padrão -1 'NAO INFORMADO' adaptado às colunas
       NOT NULL e tamanhos de cada DIM_*).
     - Inclui Comentários, Dicionário HTML, Índices, PRC_POS_CARGA_FATO, Testes de Integridade
       (10_testes_integridade/) e Guia do Analista de BI com medidas DAX (08_datasets_bi/).

Uso:
    python core/scripts_comuns/melhorar_dw_existente.py --modo comentarios
    python core/scripts_comuns/melhorar_dw_existente.py --modo indices --estrategia A
    python core/scripts_comuns/melhorar_dw_existente.py --modo patch
    python core/scripts_comuns/melhorar_dw_existente.py --caminho entrega/planejador_dw/ddl/meu_dw.sql --modo tudo
"""

import sys
import re
import html
import argparse
from pathlib import Path
from datetime import datetime

# Configura encoding UTF-8 no Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

VERDE = "\033[92m"
AMARELO = "\033[93m"
VERMELHO = "\033[91m"
CIANO = "\033[96m"
AZUL = "\033[94m"
NEGRITO = "\033[1m"
RESET = "\033[0m"


def get_base_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent


# Importa o parser determinístico de DDL do módulo irmão
sys.path.insert(0, str(Path(__file__).resolve().parent))
from inspecionar_ddl_origem import parse_ddl_text, ler_texto_sql  # noqa: E402


# Dicionário semântico de prefixos corporativos para geração inteligente de comentários
PREFIXOS_SEMANTICOS = {
    "DIMENSION_KEY": "Chave primária substituta (Surrogate Key) da dimensão gerada via Sequence Oracle",
    "SK_": "Chave substituta técnica (Surrogate Key)",
    "DIM_": "Chave estrangeira dimensional (Foreign Key) que referencia a dimensão",
    "ID_": "Identificador numérico ou chave natural na origem de",
    "COD_": "Código identificador de negócio de",
    "NUM_": "Número ou código numérico de",
    "NOM_": "Nome completo ou razão social de",
    "DES_": "Descrição textual ou detalhamento de",
    "DSC_": "Descrição textual de",
    "TXT_": "Texto livre ou observação detalhada de",
    "SIG_": "Sigla ou abreviação oficial de",
    "SGL_": "Sigla de",
    "DTC_": "Data civil ou data-hora de referência de",
    "DTH_": "Data e hora exata (Timestamp) de",
    "DAT_": "Data de referência de",
    "DTA_": "Data de",
    "DT_": "Data de",
    "VAL_": "Valor monetário ou quantitativo de",
    "VLR_": "Valor financeiro apurado de",
    "QTD_": "Quantidade apurada ou contagem de",
    "QT_": "Quantidade de",
    "PER_": "Percentual ou taxa calculada de",
    "PRC_": "Percentual ou proporção de",
    "SIN_": "Sinalizador booleano (S/N) indicando status de",
    "FLG_": "Flag indicadora (S/N ou 1/0) de",
    "IND_": "Indicador categórico ou binário de",
    "STS_": "Status ou situação atual de",
    "SIT_": "Situação cadastral ou operacional de",
    "TIP_": "Tipo ou classificação de",
    "TPO_": "Tipo de",
    "SEQ_": "Sequencial numérico de",
    "ANO_": "Ano civil de referência de",
    "MES_": "Mês de referência de",
}

COLUNAS_PADRAO_CONHECIDAS = {
    "DIMENSION_KEY": "Surrogate Key técnica da dimensão (PK). Contém o registro sentinela -1 para 'NÃO INFORMADO'.",
    "DTC_EFETIVACAO": "Data de início de vigência da versão do registro (Slowly Changing Dimension Tipo 2).",
    "DTC_EXPIRACAO": "Data de fim de vigência do registro (SCD Tipo 2). Valor NULL indica o registro ativo/vigente.",
    "DTC_INICIO_VIGENCIA": "Data de início de vigência histórica do registro na dimensão (SCD Tipo 2).",
    "DTC_FIM_VIGENCIA": "Data de encerramento da vigência do registro (SCD Tipo 2). NULL representa versão atual.",
    "DES_ATUALIZAR": "Flag de controle de processamento SCD no ODI ('S' = atualizar, 'N' = inalterado).",
    "SIN_ATIVO": "Sinalizador de registro ativo na fonte ('S' = Ativo, 'N' = Inativo).",
    "FLG_ATUAL": "Indicador de versão corrente do registro dimensional ('S'/'1' = Vigente, 'N'/'0' = Histórico).",
    "DIM_TEMPO": "Chave estrangeira (FK) que referencia a dimensão calendário corporativa DIM_TEMPO(DIMENSION_KEY).",
    "DTC_COMPLETA": "Data civil completa (TRUNC(DATE)) utilizada como referência no calendário corporativo.",
}


def humanizar_identificador(texto: str) -> str:
    """Converte identificadores SNAKE_CASE para texto legível em português."""
    substituicoes = {
        "MUNICIPIO": "Município",
        "ORGAO": "Órgão",
        "UNIDADE": "Unidade Organizacional",
        "USUARIO": "Usuário",
        "SERVIDOR": "Servidor",
        "PROCESSO": "Processo",
        "CHAMADO": "Chamado",
        "CONTRATO": "Contrato",
        "FORNECEDOR": "Fornecedor",
        "ELEICAO": "Eleição",
        "ELEICOES": "Eleições",
        "VOTACAO": "Votação",
        "CANDIDATO": "Candidato",
        "PARTIDO": "Partido",
        "CARGO": "Cargo",
        "SITUACAO": "Situação",
        "HISTORICO": "Histórico",
        "CRIACAO": "Criação",
        "ATUALIZACAO": "Atualização",
        "CONCLUSAO": "Conclusão",
        "ABERTURA": "Abertura",
        "ENCERRAMENTO": "Encerramento",
        "EFETIVACAO": "Efetivação",
        "EXPIRACAO": "Expiração",
        "VIGENCIA": "Vigência",
        "ENDERECO": "Endereço",
        "TELEFONE": "Telefone",
        "INSCRICAO": "Inscrição",
        "MATRICULA": "Matrícula",
        "OPERACAO": "Operação",
        "TRANSACAO": "Transação",
        "PAGAMENTO": "Pagamento",
        "FATURAMENTO": "Faturamento",
        "LIQUIDACAO": "Liquidação",
        "EMPENHO": "Empenho",
        "DESPESA": "Despesa",
        "RECEITA": "Receita",
        "PERIODO": "Período",
        "REFERENCIA": "Referência",
        "QUANTIDADE": "Quantidade",
        "PERCENTUAL": "Percentual",
        "MEDIA": "Média",
        "NUMERO": "Número",
        "CODIGO": "Código",
        "DESCRICAO": "Descrição",
    }
    partes = [p for p in texto.upper().split("_") if p]
    palavras = []
    for p in partes:
        if p in substituicoes:
            palavras.append(substituicoes[p])
        elif len(p) <= 2 and p in ("DE", "DA", "DO", "EM", "NO", "NA", "UF", "ID", "SK", "FK", "PK", "BI", "DW"):
            palavras.append(p.lower() if p in ("DE", "DA", "DO", "EM", "NO", "NA") else p)
        else:
            palavras.append(p.capitalize())
    return " ".join(palavras) if palavras else texto


def classificar_tabela_dw(tab: dict) -> str:
    """Classifica uma tabela do DDL entre FATO, DIM, STG ou OUTRA."""
    nome = tab["nome_tabela"].upper()
    if nome.startswith(("FATO_", "FAT_", "FT_")):
        return "FATO"
    if nome.startswith(("DIM_", "DM_")):
        return "DIM"
    if nome.startswith(("STG_", "ODI_DIM_", "TMP_")):
        return "STG"

    cols = [c["nome_dw"].upper() for c in tab["colunas"]]
    if "DIMENSION_KEY" in cols or "DTC_EFETIVACAO" in cols or "DTC_EXPIRACAO" in cols:
        return "DIM"
    fks_dim = [c for c in cols if c.startswith(("DIM_", "SK_")) or c.endswith("_KEY")]
    metricas = [c for c in cols if c.startswith(("VAL_", "VLR_", "QTD_", "QT_"))]
    if len(fks_dim) >= 2 and len(metricas) >= 1:
        return "FATO"
    return "DIM"


def extrair_schema_e_projeto(tabelas: list, schema_cli: str = None, projeto_cli: str = None) -> tuple:
    """Infere o Schema Oracle e o Nome do Projeto a partir dos nomes das tabelas do DDL ou do INTAKE_DW.md."""
    schema_detectado = schema_cli
    projeto_detectado = projeto_cli

    if not schema_detectado:
        for t in tabelas:
            bruto = t.get("nome_completo_origem", "")
            if "." in bruto:
                cand = bruto.split(".")[0].strip('`"[]').upper()
                if cand and cand not in ("DBO", "PUBLIC"):
                    schema_detectado = cand
                    break

    if not projeto_detectado:
        for t in tabelas:
            nome = t["nome_tabela"].upper()
            m = re.match(r"^(?:DIM|FATO|FAT|STG|ODI_DIM)_([A-Z0-9]+)_", nome)
            if m and m.group(1) not in ("TEMPO", "CALENDARIO", "DATA"):
                projeto_detectado = m.group(1)
                break

    # Fallback para INTAKE_DW.md se preenchido
    base_dir = get_base_dir()
    intake_path = base_dir / "modulos" / "planejador_dw" / "INTAKE_DW.md"
    ts_dados = None
    ts_idx = None
    if intake_path.exists():
        txt = intake_path.read_text(encoding="utf-8", errors="ignore")
        if not projeto_detectado:
            m_p = re.search(r"\*\*Nome do Projeto:\*\*\s*`?(.*?)`?$", txt, re.MULTILINE)
            if m_p and m_p.group(1).strip() and not m_p.group(1).strip().startswith("[Ex:"):
                projeto_detectado = re.sub(r"[^A-Z0-9_]", "_", m_p.group(1).strip().upper())
        if not schema_detectado:
            m_s = re.search(r"\*\*Schema Alvo no Oracle:\*\*\s*`?(.*?)`?$", txt, re.MULTILINE)
            if m_s and m_s.group(1).strip() and not m_s.group(1).strip().startswith("[Ex:"):
                schema_detectado = m_s.group(1).strip().upper()
        m_td = re.search(r"\*\*Tablespace de Dados:\*\*\s*`?(.*?)`?$", txt, re.MULTILINE)
        if m_td and m_td.group(1).strip() and not m_td.group(1).strip().startswith("[Ex:"):
            ts_dados = m_td.group(1).strip().upper()
        m_ti = re.search(r"\*\*Tablespace de Índices:\*\*\s*`?(.*?)`?$", txt, re.MULTILINE)
        if m_ti and m_ti.group(1).strip() and not m_ti.group(1).strip().startswith("[Ex:"):
            ts_idx = m_ti.group(1).strip().upper()

    projeto_final = projeto_detectado or "DW_CORPORATIVO"
    schema_final = schema_detectado or f"{projeto_final}_OLAP"
    return schema_final, projeto_final, ts_dados, ts_idx


def gerar_comentario_tabela(tab: dict, categoria: str, projeto: str) -> str:
    """Retorna o comentário existente (garantindo declaração de grão) ou infere um novo comentário semântico."""
    existente = (tab.get("comentario_tabela") or "").strip()
    nome = tab["nome_tabela"].upper()
    sufixo = re.sub(r"^(DIM|FATO|FAT|STG|ODI_DIM)_([A-Z0-9]+_)?", "", nome)
    entidade_legivel = humanizar_identificador(sufixo or nome)

    if existente:
        if "uma linha representa" not in existente.lower():
            return f"{existente.rstrip('.')} — Uma linha representa um registro de {entidade_legivel}."
        return existente

    if categoria == "FATO":
        fks = [
            humanizar_identificador(re.sub(r"^(DIM|SK|ID)_", "", c["nome_dw"]))
            for c in tab["colunas"]
            if c["nome_dw"].startswith(("DIM_", "SK_"))
        ]
        contexto_fks = f" cruzado por {', '.join(fks[:4])}" if fks else ""
        return (
            f"Tabela Fato de {entidade_legivel} do projeto {projeto}. "
            f"Uma linha representa uma ocorrência/medição analítica de {entidade_legivel}{contexto_fks}."
        )
    if categoria == "DIM":
        if nome == "DIM_TEMPO":
            return (
                "Dimensão Calendário Corporativa conformada (DIM_TEMPO). "
                "Uma linha representa um dia civil único no calendário, incluindo o registro padrão -1 (NÃO INFORMADO)."
            )
        tem_scd2 = any(c["nome_dw"] in ("DTC_EFETIVACAO", "DTC_EXPIRACAO", "DTC_INICIO_VIGENCIA", "DTC_FIM_VIGENCIA") for c in tab["colunas"])
        tipo_scd = "com histórico de vigência SCD Tipo 2" if tem_scd2 else "conformada"
        return (
            f"Dimensão {entidade_legivel} ({tipo_scd}). "
            f"Uma linha representa uma versão cadastral de {entidade_legivel} (incluindo linha técnica -1 para Não Informado)."
        )
    if categoria == "STG":
        return (
            f"Tabela de Staging/Work ({nome}) utilizada na preparação de dados de {entidade_legivel}. "
            f"Uma linha representa um registro bruto extraído da fonte antes da carga dimensional."
        )
    return f"Tabela analítica {nome} ({entidade_legivel}). Uma linha representa um registro de {entidade_legivel}."


def gerar_comentario_coluna(col: dict, tab: dict, categoria: str) -> str:
    """Retorna o comentário existente da coluna ou infere uma descrição clara em português."""
    existente = (col.get("comentario") or "").strip()
    if existente:
        return existente

    nome_col = col["nome_dw"].upper()
    if nome_col in COLUNAS_PADRAO_CONHECIDAS:
        return COLUNAS_PADRAO_CONHECIDAS[nome_col]

    # Se for FK na Fato (ex: DIM_PROJETO_MUNICIPIO ou SK_MUNICIPIO)
    if categoria == "FATO" and (nome_col.startswith(("DIM_", "SK_")) or nome_col.endswith("_KEY")):
        alvo = humanizar_identificador(re.sub(r"^(DIM|SK)_", "", nome_col))
        return f"Chave estrangeira (FK) para a dimensão {nome_col} ({alvo}). Recebe -1 quando não informado na origem."

    for pref, desc_base in PREFIXOS_SEMANTICOS.items():
        if nome_col.startswith(pref) and nome_col != pref:
            resto = nome_col[len(pref):]
            legivel = humanizar_identificador(resto)
            if pref in ("VAL_", "VLR_", "QTD_", "QT_", "PER_", "PRC_") and categoria == "FATO":
                adit = "Não-Aditiva (Percentual/Taxa)" if pref in ("PER_", "PRC_") else "Aditiva (SUM)"
                return f"{desc_base} {legivel}. Métrica {adit} na tabela Fato."
            if pref in ("ID_", "COD_") and categoria == "DIM":
                return f"{desc_base} {legivel} (Chave Natural do sistema de origem)."
            return f"{desc_base} {legivel}."

    legivel_geral = humanizar_identificador(nome_col)
    if nome_col in tab.get("pks", []):
        return f"Chave primária identificadora de {legivel_geral}."
    return f"Atributo de negócio referente a {legivel_geral} ({col['tipo_oracle']})."


def identificar_fks_fato(tab: dict, nomes_dimensoes: set) -> list:
    """Retorna a lista de colunas de FK em uma tabela Fato (declaradas ou inferidas por convenção)."""
    fks_map = {}
    nomes_dims_up = {d.upper() for d in (nomes_dimensoes or set())}

    def _resolver_dim(radical: str) -> str | None:
        alvo_exato = f"DIM_{radical}"
        if alvo_exato in nomes_dims_up:
            return alvo_exato
        for d in sorted(nomes_dims_up):
            ent_d = re.sub(r"^(DIM|FATO|FAT)_", "", d)
            if ent_d == radical or ent_d.startswith(radical + "_") or radical.startswith(ent_d + "_"):
                return d
        return None

    for fk in tab.get("fks", []):
        ref_up = fk["tabela_ref"].upper()
        rad_ref = re.sub(r"^(TB|TAB|DIM)_", "", ref_up)
        fks_map[fk["coluna"].upper()] = _resolver_dim(rad_ref) or ref_up

    pks_up = [p.upper() for p in tab.get("pks", [])]
    first_col_up = tab["colunas"][0]["nome_dw"].upper() if tab.get("colunas") else ""

    for c in tab["colunas"]:
        cn = c["nome_dw"].upper()
        if cn in fks_map:
            continue
        if cn in pks_up and len(pks_up) == 1 and not cn.startswith("DIM_"):
            continue
        if cn.startswith("DIM_"):
            rad = cn[4:]
            fks_map[cn] = _resolver_dim(rad) or cn
        elif cn.startswith("SK_"):
            rad = cn[3:]
            fks_map[cn] = _resolver_dim(rad) or ("DIM_" + rad)
        elif cn.endswith("_KEY") and cn != "DIMENSION_KEY":
            rad = cn[:-4]
            fks_map[cn] = _resolver_dim(rad) or ("DIM_" + rad)
        elif cn.startswith(("ID_", "COD_", "SEQ_")) and cn != first_col_up and cn != "COD_EXECUCAO_CARGA":
            rad = re.sub(r"^(ID|COD|SEQ)_", "", cn)
            dim_match = _resolver_dim(rad)
            if dim_match:
                fks_map[cn] = dim_match

    return [{"coluna": k, "tabela_ref": v} for k, v in fks_map.items()]


def coluna_ja_indexada(tab: dict, col_alvo: str) -> bool:
    """Verifica se a coluna já é líder de algum índice ou PK única no DDL."""
    col_u = col_alvo.upper()
    if tab.get("pks") == [col_u]:
        return True
    for idx in tab.get("indices", []):
        cols = [c.upper() for c in idx.get("colunas", [])]
        if cols and cols[0] == col_u:
            return True
    return False


def gerar_valor_default_menos_um(col: dict) -> str:
    """Gera o literal SQL seguro para a linha técnica -1 respeitando tipo e tamanho máximo da coluna."""
    nome = col["nome_dw"].upper()
    tipo = col["tipo_oracle"].upper()

    if nome in ("DIMENSION_KEY",) or nome.startswith("SK_") or nome in col.get("_pks_tab", []):
        if "CHAR" in tipo:
            return "'-1'"
        return "-1"

    if nome == "DES_ATUALIZAR":
        return "'N'"
    if nome in ("SIN_ATIVO", "FLG_ATUAL", "IND_ATIVO"):
        return "'S'"
    if nome in ("DTC_EXPIRACAO", "DTC_FIM_VIGENCIA") and col.get("obrigatorio") != "NOT NULL":
        return "NULL"
    if "DATE" in tipo or "TIMESTAMP" in tipo or nome.startswith(("DTC_", "DTH_", "DAT_", "DT_")):
        return "TO_DATE('1900-01-01', 'YYYY-MM-DD')"
    if any(t in tipo for t in ("NUMBER", "INT", "DECIMAL", "FLOAT", "NUMERIC")):
        if nome.startswith(("ID_", "COD_", "NUM_", "SEQ_")):
            return "-1"
        return "0"

    # Tratamento de strings respeitando o limite de caracteres VARCHAR2(n) / CHAR(n)
    m_len = re.search(r"\((\d+)", tipo)
    tam_max = int(m_len.group(1)) if m_len else 255

    if tam_max == 1:
        return "'N'"
    if tam_max == 2:
        return "'NI'"
    if tam_max <= 5:
        return "'N/I'"
    if tam_max < 13:
        return "'NAO INFORMADO'"[:tam_max - 1] + "'"
    return "'NAO INFORMADO'"


def construir_script_comentarios(tabelas_cat: list, schema: str, titulo_camada: str) -> tuple:
    """Gera o script SQL de COMMENT ON TABLE e COMMENT ON COLUMN para um grupo de tabelas."""
    linhas = [
        "-- =============================================================================",
        f"-- PATCH FAST-TRACK: COMENTÁRIOS DE TABELAS E COLUNAS ({titulo_camada.upper()})",
        f"-- Schema Alvo: {schema} | Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "-- Nota: Script 100% não-destrutivo. Não altera estrutura nem esteira de carga.",
        "-- =============================================================================",
        "",
    ]
    qtd_tab = 0
    qtd_col = 0
    for tab, cat in tabelas_cat:
        nome_tab = tab["nome_tabela"].upper()
        comm_tab = gerar_comentario_tabela(tab, cat, schema).replace("'", "''")
        linhas.append(f"-- -----------------------------------------------------------------------------")
        linhas.append(f"-- Tabela: {schema}.{nome_tab} ({cat})")
        linhas.append(f"-- -----------------------------------------------------------------------------")
        linhas.append(f"COMMENT ON TABLE {schema}.{nome_tab} IS '{comm_tab}';")
        linhas.append("")
        qtd_tab += 1
        for col in tab["colunas"]:
            nome_col = col["nome_dw"].upper()
            comm_col = gerar_comentario_coluna(col, tab, cat).replace("'", "''")
            linhas.append(f"COMMENT ON COLUMN {schema}.{nome_tab}.{nome_col} IS '{comm_col}';")
            qtd_col += 1
        linhas.append("")
    return "\n".join(linhas), qtd_tab, qtd_col


def construir_dicionario_html(tabelas_classificadas: list, schema: str, projeto: str) -> str:
    """Gera o Dicionário de Dados interativo em HTML5 a partir das tabelas reais do DDL."""
    cards_html = []
    schema = html.escape(str(schema), quote=True)
    projeto = html.escape(str(projeto), quote=True)
    for tab, cat in tabelas_classificadas:
        nome_tab = html.escape(tab["nome_tabela"].upper(), quote=True)
        comm_tab = html.escape(gerar_comentario_tabela(tab, cat, projeto), quote=True)
        pks = set(tab.get("pks", []))
        fks_cols = {fk["coluna"].upper() for fk in tab.get("fks", [])}
        for c in tab["colunas"]:
            cn = c["nome_dw"].upper()
            if cat == "FATO" and (cn.startswith(("DIM_", "SK_")) or cn.endswith("_KEY")):
                fks_cols.add(cn)

        badge_cls = "badge-fato" if cat == "FATO" else "badge-dim"
        badge_txt = "Tabela Fato" if cat == "FATO" else ("Dimensão" if cat == "DIM" else "Staging / Apoio")
        pk_label = html.escape(", ".join(pks) if pks else "DIMENSION_KEY", quote=True)

        linhas_tr = []
        for col in tab["colunas"]:
            cn = col["nome_dw"].upper()
            cn_esc = html.escape(cn, quote=True)
            tipo = html.escape(str(col["tipo_oracle"]), quote=True)
            obr = html.escape(str(col["obrigatorio"]), quote=True)
            desc = html.escape(gerar_comentario_coluna(col, tab, cat), quote=True)

            if cn in pks:
                badge_col = '<span class="badge badge-pk">PK</span>'
                regra_col = "Chave Primária"
            elif cn in fks_cols:
                badge_col = '<span class="badge badge-fk">FK</span>'
                regra_col = '<span class="formula">NVL(LOOKUP, -1)</span>'
            elif cat == "FATO" and cn.startswith(("VAL_", "VLR_", "QTD_", "QT_", "PER_", "PRC_")):
                badge_col = '<span class="badge badge-metric">Métrica</span>'
                fn_agreg = "AVG" if cn.startswith(("PER_", "PRC_")) else "SUM"
                regra_col = f'<span class="formula">{fn_agreg}({cn_esc})</span>'
            else:
                badge_col = "-"
                if cn in ("DTC_EFETIVACAO", "DTC_INICIO_VIGENCIA"):
                    regra_col = "SCD2 Início Vigência"
                elif cn in ("DTC_EXPIRACAO", "DTC_FIM_VIGENCIA"):
                    regra_col = "SCD2 Fim Vigência (NULL = Atual)"
                elif cn.startswith(("ID_", "COD_")) and cat == "DIM":
                    regra_col = "Chave Natural"
                else:
                    regra_col = obr

            linhas_tr.append(
                f"                <tr>\n"
                f"                    <td class=\"col-name\">{cn_esc}</td>\n"
                f"                    <td class=\"col-type\">{tipo} ({obr})</td>\n"
                f"                    <td>{badge_col}</td>\n"
                f"                    <td>{desc}</td>\n"
                f"                    <td>{regra_col}</td>\n"
                f"                </tr>"
            )

        card = f"""    <div class="table-card" data-category="{cat}">
        <div class="table-header">
            <div>
                <span class="table-title">{schema}.{nome_tab}</span>
                <span class="badge {badge_cls}">{badge_txt}</span>
            </div>
            <span><strong>PK:</strong> {pk_label} | <strong>Colunas:</strong> {len(tab['colunas'])}</span>
        </div>
        <div class="table-desc">
            {comm_tab}
        </div>
        <table>
            <thead>
                <tr>
                    <th>Coluna</th>
                    <th>Tipo Oracle</th>
                    <th>Papel</th>
                    <th>Descrição de Negócio (COMMENT ON COLUMN)</th>
                    <th>Regra / Comportamento</th>
                </tr>
            </thead>
            <tbody>
{chr(10).join(linhas_tr)}
            </tbody>
        </table>
    </div>"""
        cards_html.append(card)

    data_hoje = datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dicionário de Dados — {projeto}</title>
    <style>
        :root {{
            --bg-color: #f8fafc;
            --card-bg: #ffffff;
            --border-color: #e2e8f0;
            --text-main: #1e293b;
            --text-muted: #64748b;
            --primary: #2563eb;
            --badge-pk: #dc2626;
            --badge-fk: #d97706;
            --badge-metric: #059669;
            --badge-dim: #7c3aed;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            margin: 0;
            padding: 24px;
            line-height: 1.5;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        header {{ margin-bottom: 24px; padding-bottom: 16px; border-bottom: 2px solid var(--border-color); }}
        h1 {{ font-size: 26px; margin: 0 0 8px 0; color: #0f172a; }}
        .meta-info {{ font-size: 14px; color: var(--text-muted); display: flex; gap: 20px; flex-wrap: wrap; }}
        .search-bar {{ display: flex; gap: 12px; margin-bottom: 24px; position: sticky; top: 12px; z-index: 100; background: var(--bg-color); padding: 8px 0; }}
        .search-input {{ flex: 1; padding: 12px 16px; font-size: 15px; border: 2px solid var(--border-color); border-radius: 8px; outline: none; background: #ffffff; }}
        .search-input:focus {{ border-color: var(--primary); }}
        .filter-btn {{ padding: 10px 16px; background: #ffffff; border: 1px solid var(--border-color); border-radius: 8px; cursor: pointer; font-weight: 500; color: var(--text-main); }}
        .filter-btn.active {{ background: var(--primary); color: #ffffff; border-color: var(--primary); }}
        .table-card {{ background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 12px; margin-bottom: 24px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
        .table-header {{ padding: 16px 20px; background: #f1f5f9; border-bottom: 1px solid var(--border-color); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }}
        .table-title {{ font-size: 18px; font-weight: 700; margin: 0; color: #0f172a; margin-right: 8px; }}
        .table-desc {{ padding: 12px 20px; background: #fafafa; font-size: 14px; color: var(--text-muted); border-bottom: 1px solid var(--border-color); }}
        .badge {{ display: inline-block; font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 12px; text-transform: uppercase; }}
        .badge-fato {{ background: #fee2e2; color: var(--badge-pk); }}
        .badge-dim {{ background: #ede9fe; color: var(--badge-dim); }}
        .badge-pk {{ background: #fee2e2; color: #b91c1c; }}
        .badge-fk {{ background: #fef3c7; color: #b45309; }}
        .badge-metric {{ background: #d1fae5; color: #047857; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 13px; text-align: left; }}
        th {{ background: #f8fafc; padding: 10px 16px; font-weight: 600; color: var(--text-muted); border-bottom: 1px solid var(--border-color); }}
        td {{ padding: 10px 16px; border-bottom: 1px solid var(--border-color); }}
        tr:last-child td {{ border-bottom: none; }}
        .col-name {{ font-family: monospace; font-weight: 600; color: #0f172a; }}
        .col-type {{ color: #475569; font-family: monospace; }}
        .formula {{ font-family: monospace; background: #f1f5f9; padding: 2px 6px; border-radius: 4px; font-size: 12px; }}
    </style>
</head>
<body>
<div class="container">
    <header>
        <h1>📖 Dicionário de Dados — {projeto}</h1>
        <div class="meta-info">
            <span><strong>Schema Oracle:</strong> {schema}</span>
            <span><strong>Data de Geração:</strong> {data_hoje}</span>
            <span><strong>Total de Tabelas:</strong> {len(tabelas_classificadas)}</span>
            <span><strong>Modo:</strong> Fast-Track (DW Existente)</span>
        </div>
    </header>
    <div class="search-bar">
        <input type="text" id="searchInput" class="search-input" placeholder="Buscar por tabela, coluna, tipo ou descrição de negócio...">
        <button class="filter-btn active" onclick="filterCategory('ALL', event)">Todas ({len(tabelas_classificadas)})</button>
        <button class="filter-btn" onclick="filterCategory('FATO', event)">Fatos</button>
        <button class="filter-btn" onclick="filterCategory('DIM', event)">Dimensões</button>
    </div>
{chr(10).join(cards_html)}
</div>
<script>
    document.getElementById('searchInput').addEventListener('input', function(e) {{
        const query = e.target.value.toLowerCase();
        document.querySelectorAll('.table-card').forEach(card => {{
            card.style.display = card.textContent.toLowerCase().includes(query) ? 'block' : 'none';
        }});
    }});
    function filterCategory(cat, ev) {{
        document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
        if (ev && ev.target) ev.target.classList.add('active');
        document.querySelectorAll('.table-card').forEach(card => {{
            card.style.display = (cat === 'ALL' || card.getAttribute('data-category') === cat) ? 'block' : 'none';
        }});
    }}
</script>
</body>
</html>
"""


def construir_scripts_indices(
    dims: list,
    fatos: list,
    schema: str,
    ts_idx: str = None,
    estrategia: str = "A",
) -> tuple:
    """Gera os scripts SQL de índices otimizados para Dimensões (B-Tree) e Fatos (Bitmap ou B-Tree)."""
    clausula_ts = f" TABLESPACE {ts_idx}" if ts_idx else ""
    nomes_dims = {d["nome_tabela"].upper() for d in dims}

    # 1. Script de Índices para Dimensões (SEMPRE B-TREE, NUNCA BITMAP)
    linhas_dim = [
        "-- =============================================================================",
        "-- PATCH FAST-TRACK: ÍNDICES DE PERFORMANCE E LOOKUP SCD2 (DIMENSÕES)",
        f"-- Schema Alvo: {schema} | Regra: Estritamente B-TREE em Dimensões (Zero Bitmap)",
        "-- =============================================================================",
        "",
    ]
    qtd_idx_dim = 0
    for d in dims:
        nt = d["nome_tabela"].upper()
        curto = nt[:18]
        linhas_dim.append(f"-- -----------------------------------------------------------------------------")
        linhas_dim.append(f"-- Dimensão: {schema}.{nt}")
        linhas_dim.append(f"-- -----------------------------------------------------------------------------")
        cols_d = [c["nome_dw"].upper() for c in d["colunas"]]

        # Identifica chave natural (ID_* ou COD_*) e colunas de vigência SCD2
        naturais = [
            c for c in cols_d
            if c.startswith(("ID_", "COD_", "NUM_CPF", "NUM_CNPJ", "MATRICULA"))
            and c != "DIMENSION_KEY"
        ]
        col_scd_fim = next((c for c in cols_d if c in ("DTC_EXPIRACAO", "DTC_FIM_VIGENCIA", "SIN_ATIVO", "FLG_ATUAL")), None)

        if naturais:
            nat_principal = naturais[0]
            if not coluna_ja_indexada(d, nat_principal):
                nome_idx = f"IDX_{curto}_LKP"[:30]
                if col_scd_fim:
                    linhas_dim.append(
                        f"-- Índice composto B-Tree de Lookup SCD2 (Chave Natural + Vigência)\n"
                        f"CREATE INDEX {schema}.{nome_idx} ON {schema}.{nt} ({nat_principal}, {col_scd_fim})"
                        f" COMPRESS 1{clausula_ts} PARALLEL 4 NOLOGGING;\n"
                        f"ALTER INDEX {schema}.{nome_idx} NOPARALLEL LOGGING;\n"
                    )
                else:
                    linhas_dim.append(
                        f"-- Índice B-Tree de Lookup por Chave Natural\n"
                        f"CREATE INDEX {schema}.{nome_idx} ON {schema}.{nt} ({nat_principal})"
                        f"{clausula_ts} PARALLEL 4 NOLOGGING;\n"
                        f"ALTER INDEX {schema}.{nome_idx} NOPARALLEL LOGGING;\n"
                    )
                qtd_idx_dim += 1

        # Colunas de filtro frequente (SIG_, STS_, TIP_)
        filtros = [c for c in cols_d if c.startswith(("SIG_", "STS_", "TIP_")) and not coluna_ja_indexada(d, c)]
        for idx_num, col_f in enumerate(filtros[:2], start=1):
            nome_idx_f = f"IDX_{curto}_FLT{idx_num}"[:30]
            linhas_dim.append(
                f"CREATE INDEX {schema}.{nome_idx_f} ON {schema}.{nt} ({col_f}){clausula_ts};\n"
            )
            qtd_idx_dim += 1

        if nt == "DIM_TEMPO" and "DTC_COMPLETA" in cols_d and not coluna_ja_indexada(d, "DTC_COMPLETA"):
            linhas_dim.append(
                f"CREATE UNIQUE INDEX {schema}.IDX_DIM_TEMPO_DTC ON {schema}.DIM_TEMPO (DTC_COMPLETA){clausula_ts};\n"
            )
            qtd_idx_dim += 1

        linhas_dim.append(
            f"BEGIN\n"
            f"    DBMS_STATS.GATHER_TABLE_STATS(ownname => '{schema}', tabname => '{nt}', cascade => TRUE, degree => 4);\n"
            f"END;\n/\n"
        )

    # 2. Script de Índices para Fatos (Estratégia A = BITMAP | Estratégia B = B-TREE COMPRESS 1)
    tipo_idx_str = "BITMAP INDEX (Estratégia A - Star Transformation)" if estrategia.upper() == "A" else "B-TREE COMPRESS 1 (Estratégia B - MERGE Concorrente)"
    linhas_fato = [
        "-- =============================================================================",
        f"-- PATCH FAST-TRACK: ÍNDICES DE CHAVES ESTRANGEIRAS E TUNING (FATOS)",
        f"-- Schema Alvo: {schema} | Modalidade: {tipo_idx_str}",
        "-- =============================================================================",
        "",
    ]
    qtd_idx_fato = 0
    for f in fatos:
        nt = f["nome_tabela"].upper()
        curto = nt[:16]
        linhas_fato.append(f"-- -----------------------------------------------------------------------------")
        linhas_fato.append(f"-- Fato: {schema}.{nt}")
        linhas_fato.append(f"-- -----------------------------------------------------------------------------")
        fks = identificar_fks_fato(f, nomes_dims)
        for seq_fk, fk_info in enumerate(fks, start=1):
            col_fk = fk_info["coluna"].upper()
            if coluna_ja_indexada(f, col_fk):
                linhas_fato.append(f"-- [OK] Coluna FK {col_fk} já possui índice no DDL original.")
                continue
            sufixo_col = re.sub(r"^(DIM|SK|ID)_", "", col_fk)[:8]
            if estrategia.upper() == "A":
                nome_idx = f"BIX_{curto}_{seq_fk}_{sufixo_col}"[:30].rstrip("_")
                linhas_fato.append(
                    f"CREATE BITMAP INDEX {schema}.{nome_idx} ON {schema}.{nt} ({col_fk})"
                    f"{clausula_ts} PARALLEL 4 NOLOGGING;\n"
                    f"ALTER INDEX {schema}.{nome_idx} NOPARALLEL LOGGING;\n"
                )
            else:
                nome_idx = f"IDX_{curto}_{seq_fk}_{sufixo_col}"[:30].rstrip("_")
                linhas_fato.append(
                    f"CREATE INDEX {schema}.{nome_idx} ON {schema}.{nt} ({col_fk})"
                    f" COMPRESS 1{clausula_ts} PARALLEL 4 NOLOGGING;\n"
                    f"ALTER INDEX {schema}.{nome_idx} NOPARALLEL LOGGING;\n"
                )
            qtd_idx_fato += 1

        linhas_fato.append(
            f"BEGIN\n"
            f"    DBMS_STATS.GATHER_TABLE_STATS(ownname => '{schema}', tabname => '{nt}', cascade => TRUE, degree => 4);\n"
            f"END;\n/\n"
        )

    return "\n".join(linhas_dim), "\n".join(linhas_fato), qtd_idx_dim, qtd_idx_fato


def construir_patches_ajustes_nao_destrutivos(dims: list, fatos: list, schema: str) -> tuple:
    """
    Gera scripts de evolução segura (sem DROP/CREATE):
      - MERGE idempotente da linha técnica -1 em todas as dimensões (respeitando todas as colunas NOT NULL)
      - ALTER TABLE ADD CONSTRAINT (PK e FK com ENABLE NOVALIDATE para não travar nem rejeitar legado)
    """
    nomes_dims = {d["nome_tabela"].upper(): d for d in dims}

    linhas_dim = [
        "-- =============================================================================",
        "-- PATCH FAST-TRACK NÃO-DESTRUTIVO: LINHA PADRÃO (-1) E CONSTRAINTS (DIMENSÕES)",
        f"-- Schema Alvo: {schema} | Seguro para execução em banco já populado",
        "-- =============================================================================",
        "",
    ]
    for d in dims:
        nt = d["nome_tabela"].upper()
        cols = d["colunas"]
        if not cols:
            continue
        pks = d.get("pks", [])
        col_pk = pks[0] if pks else ("DIMENSION_KEY" if any(c["nome_dw"] == "DIMENSION_KEY" for c in cols) else cols[0]["nome_dw"])

        linhas_dim.append(f"-- -----------------------------------------------------------------------------")
        linhas_dim.append(f"-- Dimensão: {schema}.{nt} (PK: {col_pk})")
        linhas_dim.append(f"-- -----------------------------------------------------------------------------")

        # Se PK não estava declarada no DDL, sugere ALTER TABLE ADD CONSTRAINT ENABLE NOVALIDATE
        if not pks:
            nome_pk = f"PK_{nt}"[:30]
            linhas_dim.append(
                f"-- Adiciona constraint de Primary Key (ENABLE NOVALIDATE preserva carga existente)\n"
                f"ALTER TABLE {schema}.{nt} ADD CONSTRAINT {nome_pk} PRIMARY KEY ({col_pk}) ENABLE NOVALIDATE;\n"
            )

        # MERGE idempotente para o registro padrão -1
        select_exprs = []
        insert_cols = []
        insert_vals = []
        for c in cols:
            c_copy = dict(c)
            c_copy["_pks_tab"] = [col_pk]
            cn = c["nome_dw"].upper()
            val_sql = gerar_valor_default_menos_um(c_copy)
            select_exprs.append(f"{val_sql} AS {cn}")
            insert_cols.append(f"T.{cn}")
            insert_vals.append(f"S.{cn}")

        val_pk = "-1" if "CHAR" not in cols[0]["tipo_oracle"].upper() else "'-1'"
        linhas_dim.append(f"-- Garante existência idempotente do registro sentinela -1 ('NAO INFORMADO')")
        linhas_dim.append(f"MERGE INTO {schema}.{nt} T")
        linhas_dim.append(f"USING (SELECT {', '.join(select_exprs)} FROM DUAL) S")
        linhas_dim.append(f"ON (T.{col_pk} = {val_pk})")
        linhas_dim.append(f"WHEN NOT MATCHED THEN")
        linhas_dim.append(f"    INSERT ({', '.join(insert_cols)})")
        linhas_dim.append(f"    VALUES ({', '.join(insert_vals)});")
        linhas_dim.append("")

    linhas_dim.append("COMMIT;\n")

    # Script de Constraints Não-Destrutivas nas Fatos (ENABLE NOVALIDATE)
    linhas_fato = [
        "-- =============================================================================",
        "-- PATCH FAST-TRACK NÃO-DESTRUTIVO: INTEGRIDADE REFERENCIAL E AJUSTES (FATOS)",
        f"-- Schema Alvo: {schema} | Cláusula ENABLE NOVALIDATE (não bloqueia dados históricos)",
        "-- =============================================================================",
        "",
    ]
    for f in fatos:
        nt = f["nome_tabela"].upper()
        curto = nt[:14]
        fks_ja_declaradas = {fk["coluna"].upper() for fk in f.get("fks", [])}
        fks_inferidas = identificar_fks_fato(f, set(nomes_dims.keys()))

        linhas_fato.append(f"-- -----------------------------------------------------------------------------")
        linhas_fato.append(f"-- Fato: {schema}.{nt}")
        linhas_fato.append(f"-- -----------------------------------------------------------------------------")
        adicionou = False
        for seq_fk, fk_info in enumerate(fks_inferidas, start=1):
            col_fk = fk_info["coluna"].upper()
            tab_ref = fk_info["tabela_ref"].upper()
            if col_fk in fks_ja_declaradas:
                linhas_fato.append(f"-- [OK] Constraint FK na coluna {col_fk} -> {tab_ref} já existe no DDL.")
                continue
            if tab_ref in nomes_dims:
                d_alvo = nomes_dims[tab_ref]
                pk_alvo = d_alvo["pks"][0] if d_alvo.get("pks") else "DIMENSION_KEY"
                nome_fk = f"FK_{curto}_{seq_fk}_{col_fk[:8]}"[:30].rstrip("_")
                linhas_fato.append(
                    f"ALTER TABLE {schema}.{nt} ADD CONSTRAINT {nome_fk}\n"
                    f"    FOREIGN KEY ({col_fk}) REFERENCES {schema}.{tab_ref} ({pk_alvo})\n"
                    f"    ENABLE NOVALIDATE;\n"
                )
                adicionou = True
            else:
                linhas_fato.append(
                    f"-- [INFO] Possível FK {col_fk} -> {tab_ref} (tabela alvo não presente neste DDL; descomente se existir no schema):\n"
                    f"-- ALTER TABLE {schema}.{nt} ADD CONSTRAINT FK_{curto}_{seq_fk} FOREIGN KEY ({col_fk}) REFERENCES {schema}.{tab_ref} (DIMENSION_KEY) ENABLE NOVALIDATE;\n"
                )
        if not adicionou and not fks_inferidas:
            linhas_fato.append(f"-- Nenhuma FK dimensional pendente detectada para {nt}.")
        linhas_fato.append("")

    return "\n".join(linhas_dim), "\n".join(linhas_fato)


def construir_testes_integridade(dims: list, fatos: list, schema: str, projeto: str) -> str:
    """Gera o script 13_testes_integridade.sql adaptado às tabelas reais do DDL existente."""
    nomes_dims = {d["nome_tabela"].upper(): d for d in dims}
    linhas = [
        "-- =============================================================================",
        f"-- SUÍTE DE TESTES DE INTEGRIDADE PARA DW EXISTente — PROJETO: {projeto}",
        f"-- Schema Alvo: {schema} | Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "-- =============================================================================",
        "",
        "SET SERVEROUTPUT ON;",
        "SET LINESIZE 200;",
        "SET PAGESIZE 100;",
        "",
    ]

    if dims:
        linhas.append("-- 1. Verificação da presença do registro sentinela -1 nas Dimensões")
        unions_m1 = []
        for d in dims:
            nt = d["nome_tabela"].upper()
            pk_d = d["pks"][0] if d.get("pks") else ("DIMENSION_KEY" if any(c["nome_dw"] == "DIMENSION_KEY" for c in d["colunas"]) else d["colunas"][0]["nome_dw"])
            unions_m1.append(f"SELECT '{nt}' AS TABELA_DIMENSAO, COUNT(*) AS QTD_REGISTRO_MENOS_1 FROM {schema}.{nt} WHERE {pk_d} = -1")
        linhas.append("\nUNION ALL\n".join(unions_m1) + ";\n")

    if fatos:
        linhas.append("-- 2. Verificação de FKs Nulas e Chaves Órfãs nas Tabelas Fato")
        for f in fatos:
            nt = f["nome_tabela"].upper()
            fks = identificar_fks_fato(f, set(nomes_dims.keys()))
            exprs_nulos = [f"SUM(CASE WHEN {fk['coluna']} IS NULL THEN 1 ELSE 0 END) AS NULOS_{fk['coluna'][:18]}" for fk in fks]
            if exprs_nulos:
                linhas.append(f"SELECT COUNT(*) AS TOTAL_{nt[:18]},\n       " + ",\n       ".join(exprs_nulos))
                linhas.append(f"FROM {schema}.{nt};\n")

            unions_orfas = []
            for fk in fks:
                col_fk = fk["coluna"].upper()
                tab_ref = fk["tabela_ref"].upper()
                if tab_ref in nomes_dims:
                    d_alvo = nomes_dims[tab_ref]
                    pk_alvo = d_alvo["pks"][0] if d_alvo.get("pks") else "DIMENSION_KEY"
                    unions_orfas.append(
                        f"SELECT '{nt} -> {tab_ref} ({col_fk})' AS RELACIONAMENTO, COUNT(*) AS QTD_ORFAS\n"
                        f"FROM {schema}.{nt} F\n"
                        f"LEFT JOIN {schema}.{tab_ref} D ON F.{col_fk} = D.{pk_alvo}\n"
                        f"WHERE D.{pk_alvo} IS NULL"
                    )
            if unions_orfas:
                linhas.append("\nUNION ALL\n".join(unions_orfas) + ";\n")

    todas_tabs = [d["nome_tabela"].upper() for d in dims] + [f["nome_tabela"].upper() for f in fatos]
    if todas_tabs:
        lista_in = ", ".join(f"'{t}'" for t in todas_tabs)
        linhas.append("-- 3. Auditoria de Índices UNUSABLE / INVALID e Cobertura de Comentários no Catálogo Oracle")
        linhas.append(
            f"SELECT TABLE_NAME, INDEX_NAME, INDEX_TYPE, STATUS\n"
            f"FROM ALL_INDEXES\n"
            f"WHERE OWNER = '{schema}'\n"
            f"  AND TABLE_NAME IN ({lista_in})\n"
            f"  AND STATUS <> 'VALID';\n"
        )
        linhas.append(
            f"SELECT TABLE_NAME, COUNT(*) AS COLUNAS_SEM_COMENTARIO\n"
            f"FROM ALL_COL_COMMENTS\n"
            f"WHERE OWNER = '{schema}'\n"
            f"  AND TABLE_NAME IN ({lista_in})\n"
            f"  AND COMMENTS IS NULL\n"
            f"GROUP BY TABLE_NAME;\n"
        )

    return "\n".join(linhas)


def construir_guia_bi_rapido(dims: list, fatos: list, schema: str, projeto: str) -> str:
    """Gera o Guia do Analista de BI (08_datasets_bi/) com diagrama Mermaid ER e medidas DAX extraídas do DDL."""
    nomes_dims = {d["nome_tabela"].upper(): d for d in dims}
    linhas_er = ["```mermaid", "erDiagram"]
    for f in fatos:
        nt_f = f["nome_tabela"].upper()
        for fk in identificar_fks_fato(f, set(nomes_dims.keys())):
            linhas_er.append(f'    {fk["tabela_ref"]} ||--o{{ {nt_f} : "{fk["coluna"]}"')
    linhas_er.append("```")

    medidas_dax = []
    for f in fatos:
        nt_f = f["nome_tabela"].upper()
        medidas_dax.append(
            f"### Tabela Fato: `{nt_f}`\n\n"
            f"```dax\n"
            f"Qtd Registros ({humanizar_identificador(nt_f)}) = COUNTROWS('{nt_f}')\n"
        )
        for c in f["colunas"]:
            cn = c["nome_dw"].upper()
            if cn.startswith(("VAL_", "VLR_", "QTD_", "QT_")):
                leg = humanizar_identificador(re.sub(r"^(VAL|VLR|QTD|QT)_", "", cn))
                medidas_dax.append(f"Total {leg} = SUM('{nt_f}'[{cn}])\n")
            elif cn.startswith(("PER_", "PRC_")):
                leg = humanizar_identificador(re.sub(r"^(PER|PRC)_", "", cn))
                medidas_dax.append(f"Média {leg} = AVERAGE('{nt_f}'[{cn}])\n")
        medidas_dax.append("```\n")

    linhas_cat = []
    for f in fatos:
        nt = f["nome_tabela"].upper()
        linhas_cat.append(f"| `{schema}.{nt}` | **Fato** | {gerar_comentario_tabela(f, 'FATO', projeto)} |")
    for d in dims:
        nt = d["nome_tabela"].upper()
        linhas_cat.append(f"| `{schema}.{nt}` | **Dimensão** | {gerar_comentario_tabela(d, 'DIM', projeto)} |")

    return f"""# Guia do Analista de BI (Fast-Track DW Existente) — {projeto}

> **Schema Oracle:** `{schema}` | **Data de Geração:** {datetime.now().strftime('%Y-%m-%d %H:%M')}  
> **Modo:** Melhoria Rápida sobre DW Existente (Sem alteração de carga)

---

## 1. Catálogo de Tabelas do Modelo Dimensional

| Objeto Oracle | Papel | Descrição e Granularidade |
| :--- | :--- | :--- |
{chr(10).join(linhas_cat)}

---

## 2. Diagrama de Relacionamentos (Star Schema no Power BI)

Configure todos os relacionamentos no Power BI em modo **Import**, cardinalidade **1 para Muitos (`1:*`)** e direção de filtro cruzado **Única (`Single`)**:

{chr(10).join(linhas_er)}

---

## 3. Medidas DAX Base Sugeridas

{chr(10).join(medidas_dax) if medidas_dax else "_Nenhuma coluna numérica de métrica explícita (`VAL_`, `QTD_`) detectada nas tabelas Fato._"}
"""


def construir_relatorio_diagnostico(
    tabelas_classificadas: list,
    schema: str,
    projeto: str,
    modo: str,
    arquivos_gerados: list,
) -> str:
    """Gera o relatório executivo DIAGNOSTICO_MELHORIAS_DW_EXISTENTE.md em 09_relatorio_estrategias/."""
    achados = []
    total_cols = 0
    cols_sem_comm_orig = 0
    tabs_sem_comm_orig = 0

    for tab, cat in tabelas_classificadas:
        nt = tab["nome_tabela"].upper()
        if not (tab.get("comentario_tabela") or "").strip():
            tabs_sem_comm_orig += 1
        sem_c = [c["nome_dw"] for c in tab["colunas"] if not (c.get("comentario") or "").strip()]
        total_cols += len(tab["colunas"])
        cols_sem_comm_orig += len(sem_c)

        itens_tab = []
        if not (tab.get("comentario_tabela") or "").strip() or sem_c:
            itens_tab.append(f"Documentação incompleta na origem ({len(sem_c)}/{len(tab['colunas'])} colunas sem `COMMENT ON COLUMN`).")
        if cat == "DIM" and not tab.get("pks"):
            itens_tab.append("Dimensão sem constraint `PRIMARY KEY` explícita no DDL.")
        if cat == "DIM" and not tab.get("indices"):
            itens_tab.append("Dimensão sem índice B-Tree de Lookup SCD2 / Chave Natural declarado no DDL.")
        if cat == "FATO":
            fks = identificar_fks_fato(tab, set())
            fks_sem_idx = [fk["coluna"] for fk in fks if not coluna_ja_indexada(tab, fk["coluna"])]
            if fks_sem_idx:
                itens_tab.append(f"{len(fks_sem_idx)} coluna(s) FK sem índice de performance no DDL: `{', '.join(fks_sem_idx)}`.")
        if not itens_tab:
            itens_tab.append("Estrutura física aderente; comentários e estatísticas consolidadas.")

        achados.append(f"### `{schema}.{nt}` ({cat})\n" + "\n".join(f"- {it}" for it in itens_tab))

    lista_arqs = "\n".join(f"- `{a}`" for a in arquivos_gerados)
    return f"""# Diagnóstico e Patch Fast-Track — DW Existente ({projeto})

> **Schema Alvo:** `{schema}` | **Modo Executado:** `{modo.upper()}` | **Data:** {datetime.now().strftime('%Y-%m-%d %H:%M')}  
> **Garantia de Segurança:** Todos os scripts gerados são **100% não-destrutivos** (zero `DROP TABLE`, zero alteração na esteira de carga ODI/Hop).

---

## 1. Resumo do Raio-X no DDL Recebido

- **Tabelas Inspecionadas:** `{len(tabelas_classificadas)}`
- **Total de Colunas Mapeadas:** `{total_cols}`
- **Tabelas sem `COMMENT ON TABLE` no DDL original:** `{tabs_sem_comm_orig}`
- **Colunas sem `COMMENT ON COLUMN` no DDL original:** `{cols_sem_comm_orig}`

---

## 2. Diagnóstico por Tabela

{chr(10).join(achados)}

---

## 3. Artefatos Não-Destrutivos Gerados em `saida/planejador_dw/`

{lista_arqs}
"""


def _obter_sk_dim(d: dict) -> str:
    pks = d.get("pks", [])
    if pks:
        return pks[0].upper()
    cols = d.get("colunas", [])
    for c in cols:
        cn = c["nome_dw"].upper()
        if cn == "DIMENSION_KEY" or cn.startswith("SK_"):
            return cn
    return cols[0]["nome_dw"].upper() if cols else "DIMENSION_KEY"


def _obter_nk_dim(d: dict) -> str:
    sk = _obter_sk_dim(d)
    for c in d.get("colunas", []):
        cn = c["nome_dw"].upper()
        if cn != sk and cn.startswith(("ID_", "COD_", "NUM_", "SIG_")):
            return cn
    for c in d.get("colunas", []):
        cn = c["nome_dw"].upper()
        if cn not in (sk, "VERSION", "DTC_INICIO", "DTC_EXPIRACAO", "FLG_ATUAL"):
            return cn
    return sk


def construir_script_linha_default(dims: list, schema: str) -> str:
    """Gera o script isolado 06_init_default_records.sql com MERGE idempotente da linha -1."""
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linhas = [
        "-- =============================================================================",
        f"-- NINHO MICRO-PROCESSO — REGISTRO PADRÃO (-1 / NÃO INFORMADO) NAS DIMENSÕES",
        f"-- Schema Alvo: {schema} | Data: {agora}",
        "-- Garantias  : 100% Idempotente (MERGE INTO ON DIMENSION_KEY = -1)",
        "-- =============================================================================",
        "",
    ]
    for d in dims:
        nt = d["nome_tabela"].upper()
        cols = d["colunas"]
        if not cols:
            continue
        col_pk = _obter_sk_dim(d)
        select_exprs = []
        insert_cols = []
        insert_vals = []
        for c in cols:
            c_copy = dict(c)
            c_copy["_pks_tab"] = [col_pk]
            cn = c["nome_dw"].upper()
            val_sql = gerar_valor_default_menos_um(c_copy)
            select_exprs.append(f"{val_sql} AS {cn}")
            insert_cols.append(f"T.{cn}")
            insert_vals.append(f"S.{cn}")

        val_pk = "-1" if "CHAR" not in cols[0]["tipo_oracle"].upper() else "'-1'"
        linhas.extend([
            f"-- Dimensão: {schema}.{nt} (PK: {col_pk})",
            f"MERGE INTO {schema}.{nt} T",
            f"USING (SELECT {', '.join(select_exprs)} FROM DUAL) S",
            f"ON (T.{col_pk} = {val_pk})",
            "WHEN NOT MATCHED THEN",
            f"    INSERT ({', '.join(insert_cols)})",
            f"    VALUES ({', '.join(insert_vals)});",
            "",
        ])
    linhas.append("COMMIT;\n")
    return "\n".join(linhas)


def construir_scripts_odi(
    dims: list,
    fatos: list,
    stgs: list,
    schema: str,
    projeto: str,
    estrategia: str,
    schema_stg: str | None = None,
) -> tuple:
    """
    Gera os 3 scripts SQL corporativos do ODI 12c a partir do DDL:
      1. 03_create_odi_dim_tables.sql (Tabelas auxiliares ODI_DIM_*)
      2. 03_selects_odi_dimensoes.sql (Consultas analíticas SCD2 com ROW_NUMBER + LEAD)
      3. 04_select_odi_fato.sql (Consulta da Fato com LEFT JOIN nas Dimensões e NVL -1)
    """
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    schema_s = (schema_stg or schema).upper()
    stg_map = {s["nome_tabela"].upper().replace("STG_", ""): s["nome_tabela"].upper() for s in stgs}

    linhas_odi_ddl = [
        "-- =============================================================================",
        f"-- TABELAS AUXILIARES DE PREPARAÇÃO SCD2 DO ODI (ODI_DIM_*) — PROJETO {projeto}",
        f"-- Schema Alvo: {schema} | Gerado em: {agora}",
        "-- =============================================================================",
        "",
    ]
    linhas_odi_sel_dim = [
        "-- =============================================================================",
        f"-- CONSULTAS ANALÍTICAS SQL PARA O ODI 12c (MAP_001_ODI_DIM_*) — PROJETO {projeto}",
        f"-- Schema Alvo: {schema} | Stage Origem: {schema_s} | Gerado em: {agora}",
        "-- Instrução  : Cole cada SELECT na propriedade Custom SQL do Dataset no ODI 12c.",
        "-- =============================================================================",
        "",
    ]

    cols_scd_controle = {
        "VERSION",
        "DTC_INICIO",
        "DTC_EFETIVACAO",
        "DTC_EXPIRACAO",
        "DTC_INICIO_VIGENCIA",
        "DTC_FIM_VIGENCIA",
        "FLG_ATUAL",
        "FLG_ATIVO",
        "SIN_ATIVO",
        "DES_ATUALIZAR",
    }

    for d in dims:
        tname = d["nome_tabela"].upper()
        if "TEMPO" in tname or "CALENDARIO" in tname:
            continue
        entidade = re.sub(r"^DIM_", "", tname)
        odi_table = f"ODI_{tname}"
        stg_origem = stg_map.get(entidade, f"STG_{entidade}")
        sk_col = _obter_sk_dim(d)
        nk_col = _obter_nk_dim(d)

        col_defs = []
        cols_negocio = []
        nomes_cols_dim = {c["nome_dw"].upper() for c in d["colunas"]}
        for c in d["colunas"]:
            cname = c["nome_dw"].upper()
            ctype = c["tipo_oracle"]
            col_defs.append(f"    {cname:<28} {ctype}")
            if cname not in (sk_col, nk_col) and cname not in cols_scd_controle:
                cols_negocio.append(cname)

        col_dt_idx = next(
            (c for c in ("DTC_EFETIVACAO", "DTC_INICIO", "DTC_INICIO_VIGENCIA") if c in nomes_cols_dim),
            None,
        )
        clausula_idx_cols = f"{nk_col}, {col_dt_idx} DESC" if col_dt_idx else nk_col

        linhas_odi_ddl.extend([
            f"-- Tabela Auxiliar ODI para {tname}",
            f"CREATE TABLE {schema}.{odi_table} (",
            ",\n".join(col_defs),
            ");",
            f"CREATE INDEX {schema}.IDX_{odi_table[:18]}_NK ON {schema}.{odi_table} ({clausula_idx_cols});",
            f"COMMENT ON TABLE {schema}.{odi_table} IS 'Tabela intermediária de stage analítico do ODI 12c para cálculo de versão e vigência SCD2 de {tname}.';",
            "",
        ])

        sel_cols = ",\n        ".join([f"S.{c}" for c in cols_negocio]) if cols_negocio else f"S.{nk_col}"
        outer_cols = ",\n    ".join([f"B.{c}" for c in cols_negocio]) if cols_negocio else f"B.{nk_col}"

        scd_outer_exprs = []
        if "VERSION" in nomes_cols_dim:
            scd_outer_exprs.append("    B.NR_VERSAO AS VERSION")
        if "SIN_ATIVO" in nomes_cols_dim:
            scd_outer_exprs.append("    CASE WHEN B.PROX_DTC_INICIO IS NULL THEN 'S' ELSE 'N' END AS SIN_ATIVO")
        if "FLG_ATIVO" in nomes_cols_dim:
            scd_outer_exprs.append("    CASE WHEN B.PROX_DTC_INICIO IS NULL THEN 'S' ELSE 'N' END AS FLG_ATIVO")
        if "FLG_ATUAL" in nomes_cols_dim:
            scd_outer_exprs.append("    CASE WHEN B.PROX_DTC_INICIO IS NULL THEN 'S' ELSE 'N' END AS FLG_ATUAL")
        col_dt_ini_sel = col_dt_idx or "DTC_EFETIVACAO"
        scd_outer_exprs.append(
            f"    CASE WHEN B.NR_VERSAO = 1 THEN TO_DATE('1900-01-01', 'YYYY-MM-DD') ELSE B.DTC_MOVIMENTO END AS {col_dt_ini_sel}"
        )
        col_dt_fim_sel = "DTC_FIM_VIGENCIA" if "DTC_FIM_VIGENCIA" in nomes_cols_dim else "DTC_EXPIRACAO"
        scd_outer_exprs.append(f"    B.PROX_DTC_INICIO AS {col_dt_fim_sel}")
        if "DES_ATUALIZAR" in nomes_cols_dim:
            scd_outer_exprs.append("    CASE WHEN B.PROX_DTC_INICIO IS NULL THEN 'S' ELSE 'N' END AS DES_ATUALIZAR")

        linhas_odi_sel_dim.extend([
            "-- -----------------------------------------------------------------------------",
            f"-- Dimensão Alvo: {schema}.{tname} (Tabela Auxiliar: {schema}.{odi_table})",
            f"-- Origem Stage : {schema_s}.{stg_origem} | Chave Natural (NK): {nk_col}",
            "-- -----------------------------------------------------------------------------",
            "WITH BASE_DEDUP AS (",
            "    SELECT",
            f"        S.{nk_col},",
            f"        {sel_cols},",
            "        SYSDATE AS DTC_MOVIMENTO,",
            f"        ROW_NUMBER() OVER (PARTITION BY S.{nk_col} ORDER BY S.{nk_col}) AS NR_VERSAO,",
            f"        LEAD(SYSDATE, 1) OVER (PARTITION BY S.{nk_col} ORDER BY S.{nk_col}) AS PROX_DTC_INICIO",
            f"    FROM {schema_s}.{stg_origem} S",
            f"    WHERE S.{nk_col} IS NOT NULL",
            ")",
            "SELECT",
            f"    B.{nk_col},",
            f"    {outer_cols},",
            ",\n".join(scd_outer_exprs),
            "FROM BASE_DEDUP B;",
            "",
        ])

    linhas_odi_fato = [
        "-- =============================================================================",
        f"-- CONSULTAS DE RESOLUÇÃO DE SKs PARA TABELAS FATO (MAP_FATO_*) — PROJETO {projeto}",
        f"-- Schema Alvo: {schema} | Stage Origem: {schema_s} | Estratégia: {estrategia.upper()} | Gerado em: {agora}",
        "-- =============================================================================",
        "",
    ]

    dims_by_name = {d["nome_tabela"].upper(): d for d in dims}
    nomes_dims_set = set(dims_by_name.keys())
    dim_by_key = {}
    for d in dims:
        ent = re.sub(r"^DIM_", "", d["nome_tabela"].upper())
        dim_by_key[ent] = d

    for f in fatos:
        fname = f["nome_tabela"].upper()
        ent_fato = re.sub(r"^(FATO_|FAT_)", "", fname)
        stg_fato = stg_map.get(ent_fato, f"STG_{ent_fato}")
        sk_fato = f["colunas"][0]["nome_dw"].upper() if f["colunas"] else f"SK_{ent_fato}"
        fks_f_map = {fk["coluna"].upper(): fk["tabela_ref"].upper() for fk in identificar_fks_fato(f, nomes_dims_set)}

        select_parts = []
        join_parts = []
        alias_idx = 1

        for c in f["colunas"]:
            cname = c["nome_dw"].upper()
            if cname == sk_fato and cname not in fks_f_map:
                continue
            if cname in fks_f_map or cname.startswith(("SK_", "DIM_")) or cname.endswith("_KEY"):
                dim_match = dims_by_name.get(fks_f_map.get(cname, ""))
                if not dim_match:
                    sufixo = re.sub(r"^(SK_|DIM_|ID_|COD_)", "", cname)
                    sufixo = re.sub(r"_KEY$", "", sufixo)
                    dim_match = dim_by_key.get(sufixo)
                    if not dim_match:
                        for k_ent, d_obj in dim_by_key.items():
                            if k_ent in sufixo or sufixo in k_ent:
                                dim_match = d_obj
                                break
                alias = f"D{alias_idx}"
                alias_idx += 1
                if dim_match:
                    d_name = dim_match["nome_tabela"].upper()
                    d_sk = _obter_sk_dim(dim_match)
                    d_nk = _obter_nk_dim(dim_match)
                    tem_scd2 = any(col["nome_dw"].upper() in ("DTC_EXPIRACAO", "DTC_FIM_VIGENCIA") for col in dim_match["colunas"])
                    col_exp = "DTC_FIM_VIGENCIA" if any(col["nome_dw"].upper() == "DTC_FIM_VIGENCIA" for col in dim_match["colunas"]) else "DTC_EXPIRACAO"
                    select_parts.append(f"    NVL({alias}.{d_sk}, -1) AS {cname}")
                    if tem_scd2:
                        join_parts.append(
                            f"LEFT JOIN {schema}.{d_name} {alias}\n"
                            f"    ON S.{d_nk} = {alias}.{d_nk}\n"
                            f"   AND {alias}.{col_exp} IS NULL"
                        )
                    else:
                        join_parts.append(
                            f"LEFT JOIN {schema}.{d_name} {alias}\n"
                            f"    ON S.{d_nk} = {alias}.{d_nk}"
                        )
                else:
                    select_parts.append(f"    NVL(S.{cname}, -1) AS {cname}")
            elif cname.startswith(("VLR_", "VAL_", "QTD_", "QTDE_", "NUM_")):
                select_parts.append(f"    NVL(S.{cname}, 0) AS {cname}")
            elif cname in ("DTC_CARGA", "DT_CARGA"):
                select_parts.append(f"    SYSDATE AS {cname}")
            else:
                select_parts.append(f"    S.{cname} AS {cname}")

        linhas_odi_fato.extend([
            "-- -----------------------------------------------------------------------------",
            f"-- Tabela Fato Alvo: {schema}.{fname} | Stage Origem: {schema_s}.{stg_fato}",
            "-- -----------------------------------------------------------------------------",
            "SELECT",
            ",\n".join(select_parts),
        ])
        if join_parts:
            linhas_odi_fato.append(f"FROM {schema_s}.{stg_fato} S")
            linhas_odi_fato.append("\n".join(join_parts) + ";")
        else:
            linhas_odi_fato.append(f"FROM {schema_s}.{stg_fato} S;")
        linhas_odi_fato.append("")

    return "\n".join(linhas_odi_ddl), "\n".join(linhas_odi_sel_dim), "\n".join(linhas_odi_fato)


def construir_guias_odi_modulares(
    dims: list, fatos: list, schema: str, projeto: str, estrategia: str
) -> dict:
    """Gera os guias modulares de construção no Canvas do ODI 12c (09_relatorio_estrategias/)."""
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    arquivos = {}

    resumo_linhas = [
        f"# 📘 Relatório de Estratégias e Orquestração ODI 12c — Projeto `{projeto}`",
        "",
        f"> **Schema Alvo:** `{schema}` | **Estratégia da Fato:** `Estratégia {estrategia.upper()}` | **Gerado em:** `{agora}`",
        "",
        "## 1. Visão Geral da Esteira no ODI 12c",
        "",
        "| Ordem | Objeto ODI | Tipo | Alvo Físico | IKM Recomendado |",
        "| :---: | :--- | :--- | :--- | :--- |",
    ]
    ordem = 1
    for d in dims:
        tname = d["nome_tabela"].upper()
        if "TEMPO" in tname or "CALENDARIO" in tname:
            continue
        ent = re.sub(r"^DIM_", "", tname)
        ent_low = ent.lower()
        resumo_linhas.append(f"| {ordem} | `TRT_TRUNC_ODI_DIM_{ent}` | Procedure | `{schema}.ODI_{tname}` | `TRUNCATE TABLE` |")
        ordem += 1
        resumo_linhas.append(f"| {ordem} | `MAP_001_ODI_DIM_{ent}` | Mapping (Custom SQL) | `{schema}.ODI_{tname}` | `IKM Oracle Insert` (`APPEND`) |")
        ordem += 1
        resumo_linhas.append(f"| {ordem} | `MAP_002_DIM_{ent}` | Mapping (SCD2) | `{schema}.{tname}` | `IKM Oracle Incremental Update (MERGE)` |")
        ordem += 1

        guia_dim = [
            f"# 🛠️ Guia de Construção no ODI 12c — Dimensão `{tname}`",
            "",
            f"> **Projeto:** `{projeto}` | **Schema:** `{schema}` | **Tabela Auxiliar:** `ODI_{tname}`",
            "",
            f"## Passo 1 — Procedure `TRT_TRUNC_ODI_DIM_{ent}`",
            "- **Target Technology:** `Oracle`",
            f"- **Comando:** `TRUNCATE TABLE {schema}.ODI_{tname}`",
            "",
            f"## Passo 2 — Mapping `MAP_001_ODI_DIM_{ent}` (Stage ➔ `ODI_{tname}`)",
            "- Crie um Dataset com **Custom SQL Override** colando a query correspondente de `03_selects_odi_dimensoes.sql`.",
            f"- Conecte ao datastore alvo `ODI_{tname}`.",
            "- **IKM:** `IKM Oracle Insert` com hint `/*+ APPEND */` e `FLOW_CONTROL = FALSE`.",
            "",
            f"## Passo 3 — Mapping `MAP_002_DIM_{ent}` (`ODI_{tname}` ➔ `{tname}`)",
            f"- **Chave de Integração (Update Key):** Chave Natural (`{_obter_nk_dim(d)}`) + `DTC_INICIO`.",
            f"- **Sequence da Surrogate Key (`{_obter_sk_dim(d)}`):** `:SEQ_{tname}.NEXTVAL` (Execute on Hint: **Target**).",
            "- **IKM:** `IKM Oracle Incremental Update (MERGE)` com `COMMIT_INTERVAL = 100000`.",
            "",
        ]
        arquivos[f"guia_estrategias_odi_dim_{ent_low}.md"] = "\n".join(guia_dim)

    for f in fatos:
        fname = f["nome_tabela"].upper()
        ent_f = re.sub(r"^(FATO_|FAT_)", "", fname)
        ent_f_low = ent_f.lower()
        ikm_fato = "IKM Oracle Insert (TRUNCATE + APPEND)" if estrategia.upper() == "A" else "IKM Oracle Incremental Update (MERGE)"
        resumo_linhas.append(f"| {ordem} | `MAP_{fname}` | Mapping (Fato) | `{schema}.{fname}` | `{ikm_fato}` |")
        ordem += 1

        guia_fato = [
            f"# 🛠️ Guia de Construção no ODI 12c — Tabela Fato `{fname}`",
            "",
            f"> **Projeto:** `{projeto}` | **Schema:** `{schema}` | **Estratégia:** `{estrategia.upper()}`",
            "",
            "## Passo 1 — Pré-Carga (`PRC_PRE_CARGA_FATO`)",
            f"- Na Estratégia A (Full/Janela), execute `BEGIN {schema}.PRC_PRE_CARGA_FATO('{fname}', 'S'); END;` antes do mapa para marcar os Bitmap Indexes como `UNUSABLE` e evitar contenção de DML.",
            "",
            f"## Passo 2 — Mapping `MAP_{fname}`",
            "- Utilize a consulta de `04_select_odi_fato.sql` ou construa os `LEFT JOIN` no Canvas garantindo `NVL(DIM.DIMENSION_KEY, -1)` em 100% das chaves estrangeiras.",
            f"- **Sequence da PK:** `:SEQ_{fname}.NEXTVAL` (Target).",
            f"- **IKM:** `{ikm_fato}` (`FLOW_CONTROL = FALSE`, `COMMIT_INTERVAL = 100000`).",
            "",
            "## Passo 3 — Pós-Carga (`PRC_POS_CARGA_FATO`)",
            f"- Execute `BEGIN {schema}.PRC_POS_CARGA_FATO('{fname}'); END;` ao término do pacote para reconstruir índices `UNUSABLE` com `NOLOGGING PARALLEL` e coletar estatísticas `DBMS_STATS`.",
            "",
        ]
        arquivos[f"guia_estrategias_odi_fato_{ent_f_low}.md"] = "\n".join(guia_fato)

    resumo_linhas.extend([
        "",
        "## 2. Guias Modulares Gerados",
        "",
    ])
    for k in sorted(arquivos.keys()):
        resumo_linhas.append(f"- [`{k}`]({k})")

    arquivos["RELATORIO_ESTRATEGIAS.md"] = "\n".join(resumo_linhas) + "\n"
    return arquivos


def executar_melhoria_rapida(
    caminho_ddl: Path,
    modo: str = "tudo",
    estrategia: str = "A",
    schema_cli: str = None,
    projeto_cli: str = None,
    ts_idx_cli: str = None,
) -> dict:
    base_dir = get_base_dir()
    saida_dw = base_dir / "saida" / "planejador_dw"

    if caminho_ddl.is_file():
        arquivos_sql = [caminho_ddl]
    elif caminho_ddl.is_dir():
        arquivos_sql = sorted([
            f for f in caminho_ddl.rglob("*")
            if f.is_file() and f.suffix.lower() in (".sql", ".txt", ".ddl") and f.name.lower() != "readme.md"
        ])
    else:
        arquivos_sql = []

    if not arquivos_sql:
        print(f"{VERMELHO}[ERRO] Nenhum arquivo DDL (.sql/.txt/.ddl) encontrado em: {caminho_ddl}{RESET}")
        print(f"{AMARELO}Dica: Deposite o DDL do seu DW já construído em 'entrega/planejador_dw/ddl/' ou informe '--caminho <arquivo.sql>'.{RESET}")
        return {"erros": 1, "arquivos_gerados": []}

    tabelas = []
    for arq in arquivos_sql:
        sql_txt = ler_texto_sql(arq)
        tabs_arq = parse_ddl_text(sql_txt, arq.name)
        tabelas.extend(tabs_arq)

    if not tabelas:
        print(f"{VERMELHO}[ERRO] Nenhuma instrução CREATE TABLE encontrada nos arquivos lidos ({len(arquivos_sql)} arquivo(s)).{RESET}")
        return {"erros": 1, "arquivos_gerados": []}

    schema, projeto, _ts_dados, ts_idx_intake = extrair_schema_e_projeto(tabelas, schema_cli, projeto_cli)
    ts_idx = ts_idx_cli or ts_idx_intake

    tabelas_classificadas = [(t, classificar_tabela_dw(t)) for t in tabelas]
    dims = [t for t, c in tabelas_classificadas if c == "DIM"]
    fatos = [t for t, c in tabelas_classificadas if c == "FATO"]
    stgs = [t for t, c in tabelas_classificadas if c not in ("DIM", "FATO")]

    print(f"\n{CIANO}{NEGRITO}{'=' * 72}{RESET}")
    print(f"{CIANO}{NEGRITO}  ⚡ NINHO MICRO-PROCESSO / FAST-TRACK DE DW ({modo.upper()}){RESET}")
    print(f"{CIANO}{NEGRITO}{'=' * 72}{RESET}")
    print(f"  • Projeto / Schema : {NEGRITO}{projeto}{RESET} ({schema})")
    print(f"  • Tabelas Lidas    : {len(tabelas)} ({len(dims)} Dimensão(ões), {len(fatos)} Fato(s), {len(stgs)} Staging/Outras)")
    print(f"  • Modo Selecionado : {NEGRITO}{modo.upper()}{RESET}\n")

    arquivos_gerados = []
    modo_norm = modo.lower().strip()

    gerar_comm = modo_norm in ("comentarios", "comentario", "patch", "melhorias", "tudo", "all")
    gerar_dic = modo_norm in ("dicionario", "comentarios", "comentario", "patch", "melhorias", "tudo", "all")
    gerar_idx = modo_norm in ("indices", "indice", "index", "patch", "melhorias", "tudo", "all")
    gerar_linha_def = modo_norm in ("linha-default", "patch", "melhorias", "ajustes", "tudo", "all")
    gerar_constraints = modo_norm in ("constraints", "patch", "melhorias", "ajustes", "tudo", "all")
    gerar_testes = modo_norm in ("testes", "patch", "melhorias", "ajustes", "tudo", "all")
    gerar_guia_bi = modo_norm in ("guia-bi", "patch", "melhorias", "ajustes", "tudo", "all")
    gerar_sel_odi = modo_norm in ("selects-odi", "odi")
    gerar_guia_odi = modo_norm in ("guia-odi", "odi")

    # 1. Comentários SQL (COMMENT ON TABLE / COLUMN)
    if gerar_comm:
        if dims:
            sql_comm_dim, qt_d, qc_d = construir_script_comentarios([(d, "DIM") for d in dims], schema, "Dimensões")
            p_comm_dim = saida_dw / "03_dimensoes" / "90_patch_comentarios_dimensoes.sql"
            p_comm_dim.parent.mkdir(parents=True, exist_ok=True)
            p_comm_dim.write_text(sql_comm_dim, encoding="utf-8")
            arquivos_gerados.append(str(p_comm_dim.relative_to(base_dir).as_posix()))
            print(f"  {VERDE}[OK]{RESET} Comentários de Dimensões ({qt_d} tabelas, {qc_d} colunas) -> {p_comm_dim.relative_to(base_dir)}")

        if fatos:
            sql_comm_fato, qt_f, qc_f = construir_script_comentarios([(f, "FATO") for f in fatos], schema, "Tabelas Fato")
            p_comm_fato = saida_dw / "04_fatos" / "90_patch_comentarios_fatos.sql"
            p_comm_fato.parent.mkdir(parents=True, exist_ok=True)
            p_comm_fato.write_text(sql_comm_fato, encoding="utf-8")
            arquivos_gerados.append(str(p_comm_fato.relative_to(base_dir).as_posix()))
            print(f"  {VERDE}[OK]{RESET} Comentários de Fatos ({qt_f} tabelas, {qc_f} colunas) -> {p_comm_fato.relative_to(base_dir)}")

        if stgs:
            sql_comm_stg, qt_s, qc_s = construir_script_comentarios([(s, "STG") for s in stgs], schema, "Staging / Apoio")
            p_comm_stg = saida_dw / "02_staging" / "90_patch_comentarios_staging.sql"
            p_comm_stg.parent.mkdir(parents=True, exist_ok=True)
            p_comm_stg.write_text(sql_comm_stg, encoding="utf-8")
            arquivos_gerados.append(str(p_comm_stg.relative_to(base_dir).as_posix()))
            print(f"  {VERDE}[OK]{RESET} Comentários de Staging ({qt_s} tabelas, {qc_s} colunas) -> {p_comm_stg.relative_to(base_dir)}")

    # 1.1 Dicionário de Dados HTML Interativo
    if gerar_dic:
        html_dic = construir_dicionario_html(tabelas_classificadas, schema, projeto)
        p_dic = saida_dw / "11_dicionario_dados" / "dicionario_dados.html"
        p_dic.parent.mkdir(parents=True, exist_ok=True)
        p_dic.write_text(html_dic, encoding="utf-8")
        arquivos_gerados.append(str(p_dic.relative_to(base_dir).as_posix()))
        print(f"  {VERDE}[OK]{RESET} Dicionário de Dados HTML interativo -> {p_dic.relative_to(base_dir)}")

    # 2. Índices e PRC_POS_CARGA_FATO
    if gerar_idx:
        sql_idx_dim, sql_idx_fato, q_id, q_if = construir_scripts_indices(dims, fatos, schema, ts_idx, estrategia)
        if dims:
            p_idx_dim = saida_dw / "03_dimensoes" / "91_patch_indices_dimensoes.sql"
            p_idx_dim.parent.mkdir(parents=True, exist_ok=True)
            p_idx_dim.write_text(sql_idx_dim, encoding="utf-8")
            arquivos_gerados.append(str(p_idx_dim.relative_to(base_dir).as_posix()))
            print(f"  {VERDE}[OK]{RESET} Índices B-Tree de Dimensões ({q_id} novos índices + DBMS_STATS) -> {p_idx_dim.relative_to(base_dir)}")

        if fatos:
            p_idx_fato = saida_dw / "04_fatos" / "91_patch_indices_fatos.sql"
            p_idx_fato.parent.mkdir(parents=True, exist_ok=True)
            p_idx_fato.write_text(sql_idx_fato, encoding="utf-8")
            arquivos_gerados.append(str(p_idx_fato.relative_to(base_dir).as_posix()))
            print(f"  {VERDE}[OK]{RESET} Índices de Fatos (Estratégia {estrategia.upper()}: {q_if} novos índices + DBMS_STATS) -> {p_idx_fato.relative_to(base_dir)}")

            tpl_prc = base_dir / "modulos" / "planejador_dw" / "templates" / "07_prc_pos_carga_fato.sql"
            if tpl_prc.exists():
                prc_txt = tpl_prc.read_text(encoding="utf-8", errors="ignore").replace("<SCHEMA_ALVO>", schema)
                p_prc = saida_dw / "05_procedimentos_manutencao" / "07_prc_pos_carga_fato.sql"
                p_prc.parent.mkdir(parents=True, exist_ok=True)
                p_prc.write_text(prc_txt, encoding="utf-8")
                arquivos_gerados.append(str(p_prc.relative_to(base_dir).as_posix()))
                print(f"  {VERDE}[OK]{RESET} Procedures PRC_PRE_CARGA_FATO e PRC_POS_CARGA_FATO -> {p_prc.relative_to(base_dir)}")

    # 3. Linha Default -1 isolada
    if gerar_linha_def and dims:
        sql_def = construir_script_linha_default(dims, schema)
        p_def = saida_dw / "03_dimensoes" / "06_init_default_records.sql"
        p_def.parent.mkdir(parents=True, exist_ok=True)
        p_def.write_text(sql_def, encoding="utf-8")
        arquivos_gerados.append(str(p_def.relative_to(base_dir).as_posix()))
        print(f"  {VERDE}[OK]{RESET} Script de Linha Padrão (-1 / Não Informado) -> {p_def.relative_to(base_dir)}")

    # 4. Constraints ENABLE NOVALIDATE e Ajustes Não-Destrutivos
    if gerar_constraints:
        sql_aj_dim, sql_aj_fato = construir_patches_ajustes_nao_destrutivos(dims, fatos, schema)
        if dims:
            p_aj_dim = saida_dw / "03_dimensoes" / "92_patch_ajustes_dimensoes.sql"
            p_aj_dim.parent.mkdir(parents=True, exist_ok=True)
            p_aj_dim.write_text(sql_aj_dim, encoding="utf-8")
            arquivos_gerados.append(str(p_aj_dim.relative_to(base_dir).as_posix()))
            print(f"  {VERDE}[OK]{RESET} Patch Não-Destrutivo de Dimensões (PKs + Linha -1) -> {p_aj_dim.relative_to(base_dir)}")

        if fatos:
            p_aj_fato = saida_dw / "04_fatos" / "92_patch_ajustes_fatos.sql"
            p_aj_fato.parent.mkdir(parents=True, exist_ok=True)
            p_aj_fato.write_text(sql_aj_fato, encoding="utf-8")
            arquivos_gerados.append(str(p_aj_fato.relative_to(base_dir).as_posix()))
            print(f"  {VERDE}[OK]{RESET} Patch Não-Destrutivo de Fatos (FKs ENABLE NOVALIDATE) -> {p_aj_fato.relative_to(base_dir)}")

    # 5. Testes de Integridade
    if gerar_testes:
        sql_testes = construir_testes_integridade(dims, fatos, schema, projeto)
        p_testes = saida_dw / "10_testes_integridade" / "13_testes_integridade.sql"
        p_testes.parent.mkdir(parents=True, exist_ok=True)
        p_testes.write_text(sql_testes, encoding="utf-8")
        arquivos_gerados.append(str(p_testes.relative_to(base_dir).as_posix()))
        print(f"  {VERDE}[OK]{RESET} Suíte de Testes de Integridade adaptada ao DW -> {p_testes.relative_to(base_dir)}")

    # 6. Guia do Analista de BI
    if gerar_guia_bi:
        md_bi = construir_guia_bi_rapido(dims, fatos, schema, projeto)
        p_bi = saida_dw / "08_datasets_bi" / f"GUIA_ANALISTA_BI_{projeto}.md"
        p_bi.parent.mkdir(parents=True, exist_ok=True)
        p_bi.write_text(md_bi, encoding="utf-8")
        arquivos_gerados.append(str(p_bi.relative_to(base_dir).as_posix()))
        print(f"  {VERDE}[OK]{RESET} Guia Rápido do Analista de BI (Star Schema + DAX) -> {p_bi.relative_to(base_dir)}")

    # 7. Micro-Processo ODI: Consultas SQL e Tabelas ODI_DIM_*
    if gerar_sel_odi:
        sql_odi_ddl, sql_odi_dim, sql_odi_fato = construir_scripts_odi(dims, fatos, stgs, schema, projeto, estrategia)
        if dims:
            p_odi_ddl = saida_dw / "03_dimensoes" / "03_create_odi_dim_tables.sql"
            p_odi_ddl.parent.mkdir(parents=True, exist_ok=True)
            p_odi_ddl.write_text(sql_odi_ddl, encoding="utf-8")
            arquivos_gerados.append(str(p_odi_ddl.relative_to(base_dir).as_posix()))
            print(f"  {VERDE}[OK]{RESET} Tabelas Auxiliares ODI (ODI_DIM_*) -> {p_odi_ddl.relative_to(base_dir)}")

            p_odi_sdim = saida_dw / "03_dimensoes" / "03_selects_odi_dimensoes.sql"
            p_odi_sdim.write_text(sql_odi_dim, encoding="utf-8")
            arquivos_gerados.append(str(p_odi_sdim.relative_to(base_dir).as_posix()))
            print(f"  {VERDE}[OK]{RESET} Consultas Analíticas SCD2 para ODI (ROW_NUMBER + LEAD) -> {p_odi_sdim.relative_to(base_dir)}")

        if fatos:
            p_odi_sfato = saida_dw / "04_fatos" / "04_select_odi_fato.sql"
            p_odi_sfato.parent.mkdir(parents=True, exist_ok=True)
            p_odi_sfato.write_text(sql_odi_fato, encoding="utf-8")
            arquivos_gerados.append(str(p_odi_sfato.relative_to(base_dir).as_posix()))
            print(f"  {VERDE}[OK]{RESET} Consulta de Resolução de SKs da Fato para ODI -> {p_odi_sfato.relative_to(base_dir)}")

    # 8. Micro-Processo ODI: Guias Modulares do Canvas ODI 12c
    if gerar_guia_odi:
        guias_odi = construir_guias_odi_modulares(dims, fatos, schema, projeto, estrategia)
        pasta_rel = saida_dw / "09_relatorio_estrategias"
        pasta_rel.mkdir(parents=True, exist_ok=True)
        for nome_arq, conteudo_md in guias_odi.items():
            p_g = pasta_rel / nome_arq
            p_g.write_text(conteudo_md, encoding="utf-8")
            arquivos_gerados.append(str(p_g.relative_to(base_dir).as_posix()))
            print(f"  {VERDE}[OK]{RESET} Guia Modular ODI 12c -> {p_g.relative_to(base_dir)}")

    # Sempre gera o diagnóstico resumido do Fast-Track em 09_relatorio_estrategias/
    rel_md = construir_relatorio_diagnostico(tabelas_classificadas, schema, projeto, modo_norm, arquivos_gerados)
    p_rel = saida_dw / "09_relatorio_estrategias" / "DIAGNOSTICO_MELHORIAS_DW_EXISTENTE.md"
    p_rel.parent.mkdir(parents=True, exist_ok=True)
    p_rel.write_text(rel_md, encoding="utf-8")
    arquivos_gerados.append(str(p_rel.relative_to(base_dir).as_posix()))
    print(f"  {VERDE}[OK]{RESET} Relatório Diagnóstico -> {p_rel.relative_to(base_dir)}")

    print(f"\n{VERDE}{NEGRITO}✅ Micro-processo '{modo_norm}' concluído com sucesso! {len(arquivos_gerados)} artefato(s) gerado(s) em 'saida/planejador_dw/'.{RESET}")
    print(f"{CIANO}🧭 O que você pode fazer agora:{RESET}")
    print("  • `/iniciar-semantica`  ➔ Gerar as 3 camadas de Views Semânticas + Catálogo META_* sobre este DW")
    print("  • `/gerar-mock-bi`      ➔ Gerar massa CSV sintética para testar dashboards no Power BI")
    print("  • `/validar-entrega`    ➔ Rodar o auditor de qualidade Fast-Track (`validar_entrega.py fast-track`)")
    print("  • `/onde-estou`         ➔ Consultar o status completo do workspace\n")
    return {"erros": 0, "arquivos_gerados": arquivos_gerados}


def main():
    parser = argparse.ArgumentParser(
        description="Motor de Micro-Processos e Melhoria Rápida (Fast-Track) para DW Oracle e ODI 12c"
    )
    parser.add_argument(
        "--caminho",
        "--ddl",
        dest="caminho",
        type=str,
        default="entrega/planejador_dw/ddl",
        help="Caminho do arquivo .sql ou pasta contendo os DDLs do DW (padrão: entrega/planejador_dw/ddl)",
    )
    parser.add_argument(
        "--modo",
        type=str,
        default="tudo",
        choices=[
            "comentarios",
            "dicionario",
            "indices",
            "linha-default",
            "constraints",
            "testes",
            "guia-bi",
            "selects-odi",
            "guia-odi",
            "odi",
            "patch",
            "tudo",
        ],
        help=(
            "Micro-processo a executar: 'comentarios', 'dicionario', 'indices', 'linha-default', "
            "'constraints', 'testes', 'guia-bi', 'selects-odi', 'guia-odi', 'odi', 'patch' ou 'tudo'"
        ),
    )
    parser.add_argument(
        "--estrategia",
        type=str,
        default="A",
        choices=["A", "B", "a", "b"],
        help="Estratégia de índices nas FKs da Fato: 'A' (BITMAP INDEX) ou 'B' (B-TREE COMPRESS 1)",
    )
    parser.add_argument("--schema", type=str, default=None, help="Nome do Schema Oracle alvo (opcional, inferido do DDL)")
    parser.add_argument("--projeto", type=str, default=None, help="Sigla do Projeto (opcional, inferido do DDL)")
    parser.add_argument("--tablespace-idx", type=str, default=None, help="Tablespace de Índices opcional")

    args = parser.parse_args()
    base_dir = get_base_dir()
    caminho_alvo = Path(args.caminho)
    if not caminho_alvo.is_absolute():
        caminho_alvo = base_dir / caminho_alvo

    res = executar_melhoria_rapida(
        caminho_ddl=caminho_alvo,
        modo=args.modo,
        estrategia=args.estrategia.upper(),
        schema_cli=args.schema,
        projeto_cli=args.projeto,
        ts_idx_cli=args.tablespace_idx,
    )
    sys.exit(1 if res["erros"] > 0 else 0)


if __name__ == "__main__":
    main()

