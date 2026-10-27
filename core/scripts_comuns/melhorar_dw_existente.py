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
import zipfile
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime

try:
    from gerador_artefatos_visuais import (
        gerar_mockup_painel_bi_svg,
        gerar_preview_painel_bi_html,
        gerar_diagrama_star_schema_svg,
        gerar_mapa_canvas_odi_svg,
        gerar_planilha_indicadores_xlsx,
        gerar_apresentacao_executiva,
        exportar_markdown_para_docx,
        exportar_markdown_para_pdf,
        ler_planilha_ods,
        ler_documento_docx,
        ler_documento_odt,
        avaliar_medidas_guia_bi_amostra,
    )
except ImportError:
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parent))
    from gerador_artefatos_visuais import (
        gerar_mockup_painel_bi_svg,
        gerar_preview_painel_bi_html,
        gerar_diagrama_star_schema_svg,
        gerar_mapa_canvas_odi_svg,
        gerar_planilha_indicadores_xlsx,
        gerar_apresentacao_executiva,
        exportar_markdown_para_docx,
        exportar_markdown_para_pdf,
        ler_planilha_ods,
        ler_documento_docx,
        ler_documento_odt,
        avaliar_medidas_guia_bi_amostra,
    )

_TEM_ARTEFATOS_VISUAIS = True

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
    if nome.startswith(("FATO_", "FAT_", "FT_")) or "_FATO_" in nome or "_FAT_" in nome:
        return "FATO"
    if nome.startswith(("DIM_", "DM_")) or "_DIM_" in nome or "_DM_" in nome:
        return "DIM"
    if nome.startswith(("STG_", "ODI_DIM_", "TMP_")) or "_STG_" in nome:
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
        candidatos_proj = {}
        for t in tabelas:
            nome = t["nome_tabela"].upper()
            m_mvw = re.match(r"^(?:MVW|VW)_([A-Z0-9]+)_(?:DIM|FATO|FAT|STG)_", nome)
            if m_mvw and m_mvw.group(1) not in ("TEMPO", "CALENDARIO", "DATA"):
                projeto_detectado = m_mvw.group(1)
                break
            m = re.match(r"^(?:DIM|FATO|FAT|STG|ODI_DIM)_([A-Z0-9]+)_", nome)
            if m and m.group(1) not in ("TEMPO", "CALENDARIO", "DATA"):
                tok = m.group(1)
                candidatos_proj[tok] = candidatos_proj.get(tok, 0) + 1

        if not projeto_detectado and candidatos_proj:
            # Só assume o token intermediário como sigla de projeto se ele se repetir em >= 2 tabelas
            tok_mais_freq, qtd_freq = max(candidatos_proj.items(), key=lambda x: x[1])
            if qtd_freq >= 2:
                projeto_detectado = tok_mais_freq

        if not projeto_detectado and schema_detectado:
            cand_schema = re.sub(
                r"^(?:DW_|OLAP_|STG_|STAGE_|USR_)|_(?:ORIGEM|OLAP|DW|STG|STAGE|DEV|HOM|PROD|BI|DM)$",
                "",
                schema_detectado.upper(),
            ).strip("_")
            if cand_schema and cand_schema not in ("DW", "ORIGEM", "OLAP", "STAGE", "STG", "CORPORATIVO"):
                projeto_detectado = cand_schema

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
    sufixo = re.sub(r"^(?:MVW_|VW_)?(?:[A-Z0-9]+_)?(?:DIM|DM|FATO|FAT|STG|ODI_DIM)_", "", nome)
    if projeto and sufixo.startswith(f"{projeto.upper()}_"):
        sufixo = sufixo[len(projeto) + 1 :]
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
            ent_d = re.sub(r"^(?:MVW_|VW_)?(?:[A-Z0-9]+_)?(?:DIM|DM|FATO|FAT)_", "", d)
            if (
                ent_d == radical
                or ent_d.startswith(radical + "_")
                or radical.startswith(ent_d + "_")
                or ent_d.endswith("_" + radical)
            ):
                return d
            if radical.startswith("TEMPO") and "TEMPO" in d:
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
        if cn == first_col_up and cn.startswith("SK_") and not _resolver_dim(cn[3:]):
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
                        f" COMPRESS 1{clausula_ts} PARALLEL 4 NOLOGGING;\n"
                        f"ALTER INDEX {schema}.{nome_idx} NOPARALLEL LOGGING;\n"
                    )
                qtd_idx_dim += 1

        # Colunas de filtro frequente (SIG_, STS_, TIP_)
        filtros = [c for c in cols_d if c.startswith(("SIG_", "STS_", "TIP_")) and not coluna_ja_indexada(d, c)]
        for idx_num, col_f in enumerate(filtros[:2], start=1):
            nome_idx_f = f"IDX_{curto}_FLT{idx_num}"[:30]
            linhas_dim.append(
                f"CREATE INDEX {schema}.{nome_idx_f} ON {schema}.{nt} ({col_f})"
                f" COMPRESS 1{clausula_ts} PARALLEL 4 NOLOGGING;\n"
                f"ALTER INDEX {schema}.{nome_idx_f} NOPARALLEL LOGGING;\n"
            )
            qtd_idx_dim += 1

        if nt == "DIM_TEMPO" and "DTC_COMPLETA" in cols_d and not coluna_ja_indexada(d, "DTC_COMPLETA"):
            linhas_dim.append(
                f"CREATE UNIQUE INDEX {schema}.IDX_DIM_TEMPO_DTC ON {schema}.DIM_TEMPO (DTC_COMPLETA)"
                f"{clausula_ts} PARALLEL 4 NOLOGGING;\n"
                f"ALTER INDEX {schema}.IDX_DIM_TEMPO_DTC NOPARALLEL LOGGING;\n"
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
        cols_fato_reais = {c["nome_dw"].upper() for c in f["colunas"]}
        linhas_fato.append(f"-- -----------------------------------------------------------------------------")
        linhas_fato.append(f"-- Fato: {schema}.{nt}")
        linhas_fato.append(f"-- -----------------------------------------------------------------------------")
        fks = identificar_fks_fato(f, nomes_dims)
        cols_fks_validas = []
        for seq_fk, fk_info in enumerate(fks, start=1):
            col_fk = fk_info["coluna"].upper()
            if col_fk not in cols_fato_reais:
                continue
            cols_fks_validas.append(col_fk)
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

        # Índice composto do Grão da Fato (Update Key do IKM MERGE / filtro composto de alta seletividade)
        # Estritamente restrito às colunas que existem fisicamente na tabela Fato (evita ORA-00904)
        degeneradas_grao = [
            c["nome_dw"].upper()
            for c in f["colunas"]
            if c["nome_dw"].upper().startswith(("COD_", "ID_", "NUM_"))
            and c["nome_dw"].upper() not in cols_fks_validas
            and not c["nome_dw"].upper().startswith(("SK_FATO", "SK_FAT", "ID_FATO", "ID_FAT"))
        ]
        cols_grao_composto = (cols_fks_validas + degeneradas_grao)[:4]
        if len(cols_grao_composto) >= 2:
            nome_idx_grao = f"IDX_{curto}_GRAO"[:30].rstrip("_")
            linhas_fato.append(
                f"-- Índice composto B-Tree sobre o Grão / Update Key da Fato (colunas validadas no DDL)\n"
                f"CREATE INDEX {schema}.{nome_idx_grao} ON {schema}.{nt} ({', '.join(cols_grao_composto)})"
                f" COMPRESS 1{clausula_ts} PARALLEL 4 NOLOGGING;\n"
                f"ALTER INDEX {schema}.{nome_idx_grao} NOPARALLEL LOGGING;\n"
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


def _col_letter_to_idx(col_ref: str) -> int:
    """Converte referência de coluna Excel (ex: 'A12' -> 0, 'G2' -> 6)."""
    letras = re.sub(r"[^A-Z]", "", col_ref.upper())
    idx = 0
    for ch in letras:
        idx = idx * 26 + (ord(ch) - ord("A") + 1)
    return max(0, idx - 1)


def carregar_indicadores_negocio_entrega(base_dir: Path = None) -> list:
    """
    Inspeciona automaticamente planilhas .xlsx em entrega/planejador_dw/ (usando apenas
    zipfile + xml.etree.ElementTree da stdlib) em busca de matrizes de Indicadores/Metas
    do cliente (ex: 'Indicadores - PRAES.xlsx').
    """
    if base_dir is None:
        base_dir = get_base_dir()
    pasta_dw = base_dir / "entrega" / "planejador_dw"
    if not pasta_dw.exists():
        return []

    planilhas = sorted(
        f for f in pasta_dw.rglob("*")
        if f.is_file() and f.suffix.lower() in (".xlsx", ".ods", ".docx", ".odt") and not f.name.startswith("~$")
    )
    indicadores = []
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

    for arq in planilhas:
        try:
            sheets_rows_list = []
            suf = arq.suffix.lower()
            if suf == ".ods":
                ods_rows = ler_planilha_ods(str(arq))
                if ods_rows:
                    sheets_rows_list.append(ods_rows)
            elif suf == ".docx" and ler_documento_docx is not None:
                doc_info = ler_documento_docx(str(arq))
                for tbl in doc_info.get("tabelas", []):
                    if tbl:
                        sheets_rows_list.append(tbl)
            elif suf == ".odt" and ler_documento_odt is not None:
                doc_info = ler_documento_odt(str(arq))
                for tbl in doc_info.get("tabelas", []):
                    if tbl:
                        sheets_rows_list.append(tbl)
            else:
                with zipfile.ZipFile(arq, "r") as zf:
                    shared = []
                    if "xl/sharedStrings.xml" in zf.namelist():
                        root_ss = ET.fromstring(zf.read("xl/sharedStrings.xml"))
                        for si in root_ss.findall(f".//{ns}si"):
                            shared.append("".join(t.text or "" for t in si.findall(f".//{ns}t")).strip())

                    sheets = sorted(n for n in zf.namelist() if n.startswith("xl/worksheets/sheet") and n.endswith(".xml"))
                    for sh in sheets:
                        root_sh = ET.fromstring(zf.read(sh))
                        rows_parsed = []
                        for row in root_sh.findall(f".//{ns}row"):
                            cells_map = {}
                            max_idx = -1
                            for c in row.findall(f"{ns}c"):
                                ref = c.attrib.get("r", "")
                                c_idx = _col_letter_to_idx(ref) if ref else (max_idx + 1)
                                max_idx = max(max_idx, c_idx)
                                t_attr = c.attrib.get("t", "")
                                v_el = c.find(f"{ns}v")
                                is_el = c.find(f"{ns}is")
                                val = ""
                                if t_attr == "s" and v_el is not None and v_el.text is not None:
                                    s_idx = int(v_el.text)
                                    val = shared[s_idx] if 0 <= s_idx < len(shared) else v_el.text
                                elif is_el is not None:
                                    val = "".join(t.text or "" for t in is_el.findall(f".//{ns}t"))
                                elif v_el is not None and v_el.text is not None:
                                    val = v_el.text
                                cells_map[c_idx] = val.strip()
                            if max_idx >= 0:
                                linha = [cells_map.get(i, "") for i in range(max_idx + 1)]
                                if any(linha):
                                    rows_parsed.append(linha)
                        if rows_parsed:
                            sheets_rows_list.append(rows_parsed)

            for rows_parsed in sheets_rows_list:
                if len(rows_parsed) < 2:
                    continue

                header = [h.strip().lower() for h in rows_parsed[0]]
                if not any(
                     any(k in h for k in ("indicador", "kpi", "métrica", "metrica"))
                    for h in header
                ):
                    continue

                def _achar_col(termos: tuple, default_idx: int = -1) -> int:
                    for idx_h, h_val in enumerate(header):
                        if any(t in h_val for t in termos):
                            return idx_h
                    return default_idx

                idx_ind = _achar_col(("indicador", "kpi", "métrica", "metrica"), 0)
                idx_desc = _achar_col(("descri", "objetivo", "defini"), 1)
                idx_form = _achar_col(("fórmula", "formula", "cálculo", "calculo", "regra"), 2)
                idx_unid = _achar_col(("unidade", "formato", "medida"), 3)
                idx_per = _achar_col(("periodicidade", "frequência", "frequencia", "período"), 4)
                idx_meta = _achar_col(("meta", "target", "alvo"), 5)
                idx_filt = _achar_col(("filtro", "segmenta", "dimens"), 6)

                for r in rows_parsed[1:]:
                    get_c = lambda i: r[i].strip() if 0 <= i < len(r) else ""
                    nome_ind = get_c(idx_ind)
                    if not nome_ind:
                        continue
                    meta_txt = get_c(idx_meta)
                    metas_num = []
                    if meta_txt and "não se aplica" not in meta_txt.lower():
                        for m_num in re.finditer(
                            r"(\d+(?:\.\d{3})+(?:,\d+)?|\d+(?:[\.,]\d+)?)\s*(%|bolsas\s+(?:de\s+|do\s+)?[^,\.;]+)?",
                            meta_txt,
                            flags=re.IGNORECASE,
                        ):
                            raw_n = m_num.group(1)
                            if re.match(r"^\d+(?:\.\d{3})+$", raw_n):
                                num_raw = raw_n.replace(".", "")
                            else:
                                num_raw = raw_n.replace(".", "").replace(",", ".") if "," in raw_n else raw_n
                            ctx_raw = (m_num.group(2) or "").strip()
                            metas_num.append({"valor": num_raw, "contexto": ctx_raw})

                    indicadores.append({
                        "arquivo_origem": arq.name,
                        "indicador": nome_ind,
                        "descricao": get_c(idx_desc),
                        "formula": get_c(idx_form),
                        "unidade": get_c(idx_unid),
                        "periodicidade": get_c(idx_per),
                        "meta": meta_txt or "Não se aplica",
                        "filtros": get_c(idx_filt),
                        "metas_numericas": metas_num,
                    })
        except Exception:
            continue

    return indicadores


def construir_guia_bi_rapido(
    dims: list,
    fatos: list,
    schema: str,
    projeto: str,
    base_dir: Path = None,
    dados_amostra: dict = None,
) -> str:
    """
    Gera o Guia Completo de Implementação no Power BI (08_datasets_bi/) em nível executivo e técnico,
    operando em ciclo de vida de 2 estágios:
      - Estágio 1 (VERSÃO PRÉVIA — PRÉ-CARGA): Gerado na modelagem inicial a partir do DDL, antes da
        carga e validação com amostra real.
      - Estágio 2 (VERSÃO OFICIAL — HOMOLOGADA PÓS-CARGA): Gerado após processar a carga das DIMs e Fatos
        e validar as medidas DAX contra uma amostra real (/validar-medidas-bi), substituindo eventuais
        fórmulas parcialmente corretas pelas versões corrigidas e anexando a Prova Real SQL x DAX.
    Cada medida DAX possui uma Ficha Técnica individual detalhando:
      - O que calcula (Definição Funcional)
      - Por que esta medida existe (Objetivo de Negócio no Painel)
      - Por que a fórmula DAX foi construída assim (Racional Técnico Detalhado)
      - Onde utilizar no Power BI & Formatação recomendada
    """
    homologado_pos_carga = bool(dados_amostra and dados_amostra.get("tem_amostra"))
    mapa_medidas_avaliadas = {
        m["nome"].strip(): m
        for m in (dados_amostra.get("medidas_avaliadas", []) if homologado_pos_carga else [])
        if m.get("nome")
    }

    def _render_ficha_medida(
        nome_med: str,
        o_que_calcula: str,
        por_que_existe: str,
        por_que_formula_assim: str,
        onde_usar_formato: str,
        expr_dax_padrao: str,
        comentario_dax: str = "",
    ) -> str:
        info_av = mapa_medidas_avaliadas.get(nome_med.strip())
        expr_final = expr_dax_padrao.strip()
        if homologado_pos_carga and info_av:
            if info_av.get("dax_corrigido"):
                expr_final = info_av["dax_corrigido"].strip()
                status_linha = (
                    f"- **🧪 Validação na Amostra Pós-Carga:** Valor apurado = **`{info_av.get('valor_formatado', '-')}`** "
                    f"(⚠️ *Medida ajustada automaticamente na Prova Real pós-carga para blindar `{ ' '.join(info_av.get('diagnosticos', [])) }`*)"
                )
            else:
                status_linha = (
                    f"- **🧪 Validação na Amostra Pós-Carga:** Valor apurado = **`{info_av.get('valor_formatado', '-')}`** "
                    f"(✅ *Fórmula 100% conciliada com o SQL da amostra pós-carga*)"
                )
        elif homologado_pos_carga:
            status_linha = "- **🧪 Validação na Amostra Pós-Carga:** ✅ *Estrutura validada no modelo estrela pós-carga*"
        else:
            status_linha = (
                "- **⏳ Status do Ciclo de Vida:** **Versão Prévia (Pré-Carga)** — "
                "*Fórmula projetada a partir do DDL; aguarda conciliação com amostra pós-carga via `/validar-medidas-bi`.*"
            )

        bloco_cod = []
        if comentario_dax:
            bloco_cod.append(f"// {comentario_dax}")
        if "\n" in expr_final:
            bloco_cod.append(f"{nome_med} = \n{expr_final}")
        else:
            bloco_cod.append(f"{nome_med} = {expr_final}")

        return (
            f"##### 📌 Medida: `[{nome_med}]`\n"
            f"- **O que calcula (Definição Funcional):** {o_que_calcula}\n"
            f"- **Por que esta medida existe (Objetivo de Negócio no Painel):** {por_que_existe}\n"
            f"- **Por que a fórmula DAX foi construída assim (Racional Técnico Detalhado):** {por_que_formula_assim}\n"
            f"- **Onde utilizar no Power BI & Formatação:** {onde_usar_formato}\n"
            f"{status_linha}\n\n"
            f"```dax\n"
            + "\n".join(bloco_cod)
            + "\n```\n"
        )

    nomes_dims = {d["nome_tabela"].upper(): d for d in dims}
    linhas_er = ["```mermaid", "erDiagram"]
    linhas_rel_matrix = []
    dim_tempo_nome = "DIM_TEMPO"
    dim_tempo_obj = None
    for d in dims:
        dn = d["nome_tabela"].upper()
        if "TEMPO" in dn or "CALENDARIO" in dn:
            dim_tempo_nome = dn
            dim_tempo_obj = d
            break

    pk_tempo = _obter_sk_dim(dim_tempo_obj) if dim_tempo_obj else "DIMENSION_KEY"

    tempo_count_por_fato = {}
    fks_por_fato = {}
    for f in fatos:
        nt_f = f["nome_tabela"].upper()
        fks_f = identificar_fks_fato(f, set(nomes_dims.keys()))
        fks_por_fato[nt_f] = fks_f
        for fk in fks_f:
            tab_r = fk["tabela_ref"].upper()
            col_fk = fk["coluna"].upper()
            d_obj = nomes_dims.get(tab_r)
            pk_dim = _obter_sk_dim(d_obj) if d_obj else "DIMENSION_KEY"
            is_tempo = "TEMPO" in tab_r or "CALENDARIO" in tab_r or "TEMPO" in col_fk
            if is_tempo:
                tempo_count_por_fato[nt_f] = tempo_count_por_fato.get(nt_f, 0) + 1
                ativo = tempo_count_por_fato[nt_f] == 1
                conector = "||--o{" if ativo else "||..o{"
                status_txt = "**Ativo** (Data Principal)" if ativo else "**Inativo** (Usar `USERELATIONSHIP`)"
            else:
                conector = "||--o{"
                status_txt = "**Ativo**"
            linhas_er.append(f'    {tab_r} {conector} {nt_f} : "{pk_dim} = {col_fk}"')
            linhas_rel_matrix.append(
                f"| `{tab_r}` | `{pk_dim}` | `{nt_f}` | `{col_fk}` | `1 : *` | **Única** (`Dim ➔ Fato`) | {status_txt} |"
            )
    linhas_er.append("```")

    # 1.3 Catálogo separado de Fatos e Dimensões
    linhas_cat_fatos = []
    for f in fatos:
        nt_f = f["nome_tabela"].upper()
        pk_f = _obter_sk_dim(f)
        fks_nomes = [fk["coluna"].upper() for fk in fks_por_fato.get(nt_f, [])]
        metricas_nomes = [
            c["nome_dw"].upper()
            for c in f["colunas"]
            if c["nome_dw"].upper().startswith(("VAL_", "VLR_", "QTD_", "QT_", "PER_", "PRC_", "IND_", "FLG_", "SIN_"))
        ]
        grao_txt = ", ".join(f"`{k}`" for k in fks_nomes[:5]) if fks_nomes else f"`{pk_f}`"
        met_txt = ", ".join(f"`{m}`" for m in metricas_nomes[:5]) if metricas_nomes else "`COUNT(*)`"
        linhas_cat_fatos.append(
            f"| `{schema}.{nt_f}` | `{pk_f}` | {grao_txt} | {met_txt} | {gerar_comentario_tabela(f, 'FATO', projeto)} |"
        )

    linhas_cat_dims = []
    dims_negocio = []
    for d in dims:
        nt_d = d["nome_tabela"].upper()
        pk_d = _obter_sk_dim(d)
        nk_d = _obter_nk_dim(d)
        is_tempo = nt_d == dim_tempo_nome or "TEMPO" in nt_d or "CALENDARIO" in nt_d
        if not is_tempo:
            dims_negocio.append(d)
        cols_desc = [
            c["nome_dw"].upper()
            for c in d["colunas"]
            if c["nome_dw"].upper().startswith(("DES_", "NOM_", "DSC_", "SIG_"))
        ]
        cols_scd = [
            c["nome_dw"].upper()
            for c in d["colunas"]
            if c["nome_dw"].upper() in ("DTC_EFETIVACAO", "DTC_INICIO", "DTC_EXPIRACAO", "DTC_FIM", "SIN_ATIVO", "FLG_ATIVO", "DES_ATUALIZAR")
        ]
        desc_txt = ", ".join(f"`{c}`" for c in cols_desc[:4]) if cols_desc else f"`{nk_d}`"
        scd_txt = ", ".join(f"`{c}`" for c in cols_scd) if cols_scd else "Dimensão Fixa / Calendário"
        linhas_cat_dims.append(
            f"| `{schema}.{nt_d}` | `{pk_d}` | `{nk_d}` | {desc_txt} | {scd_txt} |"
        )

    # 4 & 5 & 7: Medidas DAX, Slicers, Queries SQL e Nomes de Medidas para o Mockup
    indicadores_negocio = carregar_indicadores_negocio_entrega(base_dir)
    medidas_dax = []
    radar_rows = []
    sql_conferencia = []
    medidas_kpi_topo = []
    medidas_eficiencia = []
    medidas_qualidade = []

    slicers_rows = [
        f"| **Ano / Semestre / Mês** | `NUM_ANO`, `DES_SEMESTRE`, `DES_MES` | `{dim_tempo_nome}` | *Dropdown* / Botões Horizontais | **Global (Todas as Páginas)** — ordenar `DES_MES` por `NUM_MES`. |"
    ]

    for d in dims_negocio:
        nt_d = d["nome_tabela"].upper()
        nk_d = _obter_nk_dim(d)
        cols_desc = [
            c["nome_dw"].upper()
            for c in d["colunas"]
            if c["nome_dw"].upper().startswith(("DES_", "NOM_", "DSC_", "SIG_"))
        ]
        campos_slicer = ", ".join(f"`{c}`" for c in cols_desc[:3]) if cols_desc else f"`{nk_d}`"
        slicers_rows.append(
            f"| **{humanizar_identificador(nt_d)}** | {campos_slicer} | `{nt_d}` | *Dropdown* com Busca | **Global (Páginas 1, 2 e 3)** — filtra as Fatos via relacionamento `1:*`. |"
        )
        if any(c["nome_dw"].upper() == "SIN_ATIVO" for c in d["colunas"]):
            slicers_rows.append(
                f"| **Vigência SCD2 ({humanizar_identificador(nt_d)})** | `SIN_ATIVO` (`'S'` / `'N'`) | `{nt_d}` | Botão (*Tile*) | **Opcional (Página 4 / Auditoria)** — permite isolar cadastro atual vs histórico. |"
            )

    for idx_f, f in enumerate(fatos, 1):
        nt_f = f["nome_tabela"].upper()
        leg_f = humanizar_identificador(re.sub(r"^(FATO_|FAT_)", "", nt_f))
        fks_f = fks_por_fato.get(nt_f, [])
        fk_tempo_col = None
        fk_dim_princ = None
        for fk in fks_f:
            if "TEMPO" in fk["tabela_ref"].upper() or "TEMPO" in fk["coluna"].upper():
                if not fk_tempo_col:
                    fk_tempo_col = fk["coluna"].upper()
            elif not fk_dim_princ:
                fk_dim_princ = fk

        nome_med_qtd_reg = f"Qtd Registros ({leg_f})"
        medidas_kpi_topo.append(f"[{nome_med_qtd_reg}]")

        bloco_dax = [
            f"### 4.{idx_f + 1} Catálogo Detalhado de Medidas DAX da Tabela Fato `{nt_f}` ({leg_f})",
            "",
            f"* **Conceito de Negócio:** Consolida os indicadores de **{leg_f}** no grão das chaves estrangeiras ({', '.join('`' + fk['coluna'].upper() + '`' for fk in fks_f) or 'registro transacional'}).",
            "",
            "#### A. Volumetria e Contagens Distintas Blindadas contra SCD Tipo 2 (`SCD2 Safe`)",
            "",
            _render_ficha_medida(
                nome_med=nome_med_qtd_reg,
                o_que_calcula=f"Contabiliza o volume total de linhas/eventos registrados na tabela fato `{nt_f}` dentro dos filtros ativos no painel.",
                por_que_existe=f"Fornece ao gestor e ao analista o indicador base de volumetria operacional de **{leg_f}**, além de servir como denominador para os indicadores de qualidade e participação.",
                por_que_formula_assim=f"Utiliza `COUNTROWS('{nt_f}')` encapsulado em `COALESCE(..., 0)`. No motor colunar *VertiPaq*, `COUNTROWS` lê diretamente a cardinalidade do segmento de tabela (muito mais performático que `COUNT` em coluna física), e o `COALESCE` garante que os cartões KPI exibam `0` em vez de `(Em branco)` quando um filtro não retornar registros.",
                onde_usar_formato="Cartão KPI de Topo na **Página 1 (Visão Executiva)**, eixo de tendência e denominador na **Página 4 (Governança)**. Formatar como **Número Inteiro** (`#,0`).",
                expr_dax_padrao=f"COALESCE(COUNTROWS('{nt_f}'), 0)",
                comentario_dax=f"Total de lançamentos/eventos na tabela {nt_f}",
            ),
        ]

        medida_entidade_principal = None
        for fk in fks_f:
            tab_r = fk["tabela_ref"].upper()
            col_fk = fk["coluna"].upper()
            if "TEMPO" in tab_r or "CALENDARIO" in tab_r or "TEMPO" in col_fk:
                continue
            d_obj = nomes_dims.get(tab_r)
            nk_dim = _obter_nk_dim(d_obj) if d_obj else "DIMENSION_KEY"
            ent_leg = humanizar_identificador(re.sub(r"^DIM_", "", tab_r))
            nome_med_scd2 = f"Qtd {ent_leg} Ativos (SCD2 Safe)"
            if not medida_entidade_principal:
                medida_entidade_principal = (nome_med_scd2, ent_leg, tab_r, nk_dim, col_fk)
                medidas_kpi_topo.append(f"[{nome_med_scd2}]")

            expr_scd2 = (
                "COALESCE(\n"
                "    COUNTROWS(\n"
                "        SUMMARIZE(\n"
                f"            FILTER('{nt_f}', '{nt_f}'[{col_fk}] <> -1 && NOT(ISBLANK(RELATED('{tab_r}'[{nk_dim}])))),\n"
                f"            '{tab_r}'[{nk_dim}]\n"
                "        )\n"
                "    ),\n"
                "    0\n"
                ")"
            )
            expr_dist_sk = (
                "COALESCE(\n"
                "    CALCULATE(\n"
                f"        DISTINCTCOUNT('{nt_f}'[{col_fk}]),\n"
                f"        '{nt_f}'[{col_fk}] <> -1\n"
                "    ),\n"
                "    0\n"
                ")"
            )
            bloco_dax.extend([
                _render_ficha_medida(
                    nome_med=nome_med_scd2,
                    o_que_calcula=f"Quantidade real de entidades únicas de **{ent_leg}** (identificadas pela Chave Natural `{tab_r}[{nk_dim}]`) com movimentação na fato `{nt_f}`.",
                    por_que_existe=f"Na modelagem Kimball com **SCD Tipo 2**, quando um registro de `{tab_r}` sofre alteração cadastral ao longo do tempo, o ODI 12c gera uma nova versão histórica (`DIMENSION_KEY`) mantendo a mesma Chave Natural (`{nk_dim}`). Contar a FK da Fato duplicaria a mesma entidade no ano. Esta medida entrega ao gestor o número **exato e sem duplicidade** de **{ent_leg}** reais.",
                    por_que_formula_assim=f"Filtra a fato `{nt_f}` excluindo a linha sentinela `-1` (`'{nt_f}'[{col_fk}] <> -1`) e eventuais *Blank Rows* de FKs órfãs (`NOT(ISBLANK(RELATED('{tab_r}'[{nk_dim}])))`), agrupa as transações pela Chave Natural `{tab_r}[{nk_dim}]` via `SUMMARIZE` e conta os grupos reais com `COUNTROWS`.",
                    onde_usar_formato="Cartão KPI Estratégico na **Página 1 (Visão Executiva)** e denominador de intensidade média na **Página 2**. Formatar como **Número Inteiro** (`#,0`).",
                    expr_dax_padrao=expr_scd2,
                    comentario_dax=f"Contagem Distinta de {ent_leg} pela Chave Natural ({tab_r}[{nk_dim}]) — Blindada contra SCD Tipo 2 e Blank Row",
                ),
                _render_ficha_medida(
                    nome_med=f"Distintos {ent_leg} (SK)",
                    o_que_calcula=f"Quantidade distinta de chaves substitutas (`{nt_f}[{col_fk}]`) referenciadas na tabela fato `{nt_f}`, desconsiderando a linha sentinela `-1`.",
                    por_que_existe=f"Permite ao analista de BI e à engenharia de dados confrontar o volume de versões históricas (`SK`) movimentadas na Fato contra a quantidade de entidades reais (`[{nome_med_scd2}]`). A diferença entre as duas medidas revela quantas entidades mudaram de versão cadastral (SCD2) no período.",
                    por_que_formula_assim=f"Aplica `CALCULATE(DISTINCTCOUNT('{nt_f}'[{col_fk}]), '{nt_f}'[{col_fk}] <> -1)` com `COALESCE(..., 0)`, isolando o código técnico `-1` (`Não Informado`).",
                    onde_usar_formato="Tabela de Auditoria na **Página 4 (Governança de Dados)** ao lado da medida `(SCD2 Safe)`. Formatar como **Número Inteiro** (`#,0`).",
                    expr_dax_padrao=expr_dist_sk,
                    comentario_dax=f"Contagem Distinta de Versões SK de {ent_leg} (Excluindo Linha Sentinela -1)",
                ),
            ])

        # B. Somatórios Base, Médias e Percentuais
        bloco_somas = ["#### B. Somatórios Base, Médias Operacionais e Taxas Ponderadas (`SUM`, `AVERAGE`, `DIVIDE`)", ""]
        cols_metricas_sql = []
        cols_val_num = []
        for c in f["colunas"]:
            cn = c["nome_dw"].upper()
            if cn.startswith(("VAL_", "VLR_", "QTD_", "QT_")):
                leg = humanizar_identificador(re.sub(r"^(VAL|VLR|QTD|QT)_", "", cn))
                nome_tot = f"Total {leg}"
                nome_med = f"Media {leg}"
                cols_val_num.append((cn, leg, nome_tot))
                medidas_kpi_topo.append(f"[{nome_tot}]")
                eh_moeda = cn.startswith(("VAL_", "VLR_"))
                fmt_recomendado = "Moeda (`R$ #,0.00`)" if eh_moeda else "Número Inteiro ou Decimal (`#,0`)"
                bloco_somas.extend([
                    _render_ficha_medida(
                        nome_med=nome_tot,
                        o_que_calcula=f"Somatório consolidado da métrica aditiva `{nt_f}[{cn}]` (**{leg}**) para o recorte selecionado.",
                        por_que_existe=f"Representa a grandeza financeira/quantitativa principal de **{leg}** nos eventos de **{leg_f}**, permitindo agregar valores desde o nível diário até o consolidado anual por dimensão.",
                        por_que_formula_assim=f"Utiliza `SUM('{nt_f}'[{cn}])` com `COALESCE(..., 0)` sem filtrar a chave sentinela `-1`, garantindo que o total exibido nos cartões do Power BI feche em **100%** com o `SELECT SUM({cn}) FROM {schema}.{nt_f}` no banco Oracle.",
                        onde_usar_formato=f"Cartão KPI Principal na **Página 1**, Gráfico de Evolução Mensal, Ranking Top 10 e Curva de Pareto na **Página 3**. Formatar como **{fmt_recomendado}**.",
                        expr_dax_padrao=f"COALESCE(SUM('{nt_f}'[{cn}]), 0)",
                        comentario_dax=f"Somatório de {leg} ({nt_f}[{cn}])",
                    ),
                    _render_ficha_medida(
                        nome_med=nome_med,
                        o_que_calcula=f"Valor médio aritmético por transação/registro da coluna `{nt_f}[{cn}]` (**{leg}**) na tabela fato `{nt_f}`.",
                        por_que_existe=f"Enquanto `[{nome_tot}]` mede o volume acumulado (influenciado pelo porte da unidade), `[{nome_med}]` expõe o **ticket médio por lançamento**, revelando dispersões, *outliers* e mudanças no padrão unitário de **{leg_f}**.",
                        por_que_formula_assim=f"Aplica `AVERAGE('{nt_f}'[{cn}])` com `COALESCE(..., 0)`, dividindo a soma de `{cn}` pela contagem de registros válidos no grão da fato `{nt_f}`.",
                        onde_usar_formato=f"**Página 2 (Eficiência e Detalhamento Operacional)** e Matriz Resumo Executiva. Formatar como **{fmt_recomendado}**.",
                        expr_dax_padrao=f"COALESCE(AVERAGE('{nt_f}'[{cn}]), 0)",
                        comentario_dax=f"Média por transação de {leg} ({nt_f}[{cn}])",
                    ),
                ])
                cols_metricas_sql.append(f"    SUM(NVL(f.{cn}, 0)) AS TOTAL_{cn}")
                radar_rows.append(
                    f"| **Curva ABC e Concentração de {leg}** | `{nt_f}.{cn}` | Identifica os 20% das categorias/entidades que concentram 80% do volume de `{cn}` (Análise de Pareto). |"
                )
            elif cn.startswith(("PER_", "PRC_")):
                leg = humanizar_identificador(re.sub(r"^(PER|PRC)_", "", cn))
                nome_per = f"Taxa Media {leg}"
                medidas_eficiencia.append(f"[{nome_per}]")
                bloco_somas.append(
                    _render_ficha_medida(
                        nome_med=nome_per,
                        o_que_calcula=f"Taxa média aritmética observada na coluna de percentual `{nt_f}[{cn}]` (**{leg}**).",
                        por_que_existe=f"Permite acompanhar o indicador percentual médio de **{leg}** sem incorrer no erro grave de somar taxas pré-calculadas.",
                        por_que_formula_assim=f"**Regra de Ouro DAX:** colunas prefixadas por `PER_`/`PRC_` armazenam razões não-aditivas e **jamais devem usar `SUM()`** (somar `50% + 50%` geraria `100%` ou `200%`). Utiliza-se `AVERAGE('{nt_f}'[{cn}])` com `COALESCE(..., 0)`.",
                        onde_usar_formato="Cartões de Eficiência na **Página 2** e Matriz Analítica. Formatar como **Percentual (`0.00%`)**.",
                        expr_dax_padrao=f"COALESCE(AVERAGE('{nt_f}'[{cn}]), 0)",
                        comentario_dax=f"Atenção: Coluna de percentual ({cn}) — NUNCA usar SUM()!",
                    )
                )
                cols_metricas_sql.append(f"    ROUND(AVG(NVL(f.{cn}, 0)), 2) AS MEDIA_{cn}")
            elif cn.startswith(("IND_", "FLG_", "SIN_")):
                leg = humanizar_identificador(re.sub(r"^(IND|FLG|SIN)_", "", cn))
                slicers_rows.append(
                    f"| **Flag {leg}** | `{cn}` | `{nt_f}` | Botão (*Tile*) | Filtro rápido de status/indicador direto na Fato `{nt_f}`. |"
                )

        # Se houver pelo menos 2 métricas numéricas, cria razão ponderada DIVIDE entre elas; e média por entidade
        if len(cols_val_num) >= 2:
            c1, leg1, tot1 = cols_val_num[0]
            c2, leg2, tot2 = cols_val_num[1]
            if c1.startswith(("VAL_", "VLR_")) and c2.startswith(("QTD_", "QT_")):
                nome_rel = f"Valor Medio {leg1} por {leg2}"
            else:
                nome_rel = f"Indice Ponderado {leg1} vs {leg2}"
            medidas_eficiencia.append(f"[{nome_rel}]")
            bloco_somas.append(
                _render_ficha_medida(
                    nome_med=nome_rel,
                    o_que_calcula=f"Razão ponderada entre o somatório `[{tot1}]` (numerador) e o somatório `[{tot2}]` (denominador).",
                    por_que_existe=f"Avalia a relação financeira/operacional real entre **{leg1}** e **{leg2}** (ex: proporção de execução/pagamento ou custo unitário ponderado), respeitando o peso de grandes contratos/eventos frente a pequenos lançamentos.",
                    por_que_formula_assim=f"Utiliza `DIVIDE([{tot1}], [{tot2}], 0)` sobre medidas já agregadas (`SUM` dividido por `SUM`), nunca média simples de razões linha a linha. A função `DIVIDE` protege automaticamente contra divisão por zero retornando `0`.",
                    onde_usar_formato="Cartões de Eficiência na **Página 2 (Metas e Eficiência)** e Matriz Executiva. Formatar como **Moeda/Decimal (`#,0.00`)** ou **Percentual (`0.00%`)**.",
                    expr_dax_padrao=f"DIVIDE([{tot1}], [{tot2}], 0)",
                    comentario_dax="Razão Ponderada (Regra de Ouro: Soma do Numerador dividida pela Soma do Denominador)",
                )
            )

        if cols_val_num and medida_entidade_principal:
            c1, leg1, tot1 = cols_val_num[0]
            nome_med_scd2, ent_leg, _, _, _ = medida_entidade_principal
            nome_med_por_ent = f"Media {leg1} por {ent_leg}"
            medidas_eficiencia.append(f"[{nome_med_por_ent}]")
            bloco_somas.append(
                _render_ficha_medida(
                    nome_med=nome_med_por_ent,
                    o_que_calcula=f"Intensidade média de **{leg1}** (`[{tot1}]`) por entidade única ativa de **{ent_leg}** (`[{nome_med_scd2}]`).",
                    por_que_existe=f"Responde à pergunta executiva: *\"Qual é o volume/valor médio de {leg1} alocado para cada {ent_leg} real?\"*, normalizando a comparação entre diferentes órgãos ou períodos.",
                    por_que_formula_assim=f"Divide a medida aditiva `[{tot1}]` pela medida blindada `[{nome_med_scd2}]` via `DIVIDE(..., ..., 0)`. Como o denominador já agrupa pela Chave Natural (`NK`) e remove a linha sentinela `-1`, o indicador per-capita não sofre distorção por múltiplas versões SCD Tipo 2.",
                    onde_usar_formato="**Página 2 (Acompanhamento de Metas e Eficiência)** e gráfico de dispersão/intensidade. Formatar como **Moeda (`R$ #,0.00`)** ou **Decimal (`#,0.00`)**.",
                    expr_dax_padrao=f"DIVIDE([{tot1}], [{nome_med_scd2}], 0)",
                    comentario_dax=f"Intensidade Média de {leg1} por {ent_leg} Ativo (SCD2 Safe)",
                )
            )

        med_base_share = f"[{cols_val_num[0][2]}]" if cols_val_num else f"[{nome_med_qtd_reg}]"
        leg_base_share = cols_val_num[0][1] if cols_val_num else leg_f
        expr_share = (
            "DIVIDE(\n"
            f"    {med_base_share},\n"
            f"    CALCULATE({med_base_share}, ALLSELECTED('{nt_f}')),\n"
            "    0\n"
            ")"
        )
        bloco_somas.append(
            _render_ficha_medida(
                nome_med=f"% Participacao {leg_base_share}",
                o_que_calcula=f"Participação percentual (*% Share*) de cada categoria/entidade sobre o total visível da métrica `{med_base_share}`.",
                por_que_existe=f"Indispensável para gráficos de composição (Rosca) e **Curva de Pareto (80/20)**, mostrando de imediato quais categorias concentram a maior fatia de **{leg_base_share}**.",
                por_que_formula_assim=f"Divide `{med_base_share}` (avaliado na linha/fatia atual do visual) por `CALCULATE({med_base_share}, ALLSELECTED('{nt_f}'))`, que remove o filtro da categoria do gráfico mas **respeita todos os segmentadores (*slicers*) externos escolhidos pelo usuário no topo da página**.",
                onde_usar_formato="Gráfico de Rosca na **Página 1**, Curva de Pareto na **Página 3** e coluna `% Total` na Matriz Executiva. Formatar como **Percentual (`0.00%`)**.",
                expr_dax_padrao=expr_share,
                comentario_dax="Participação Percentual (% Share) sobre o Total Selecionado",
            )
        )
        bloco_dax.extend(bloco_somas)

        # C. Inteligência Temporal e Auditoria de Qualidade (-1)
        expr_py = (
            "CALCULATE(\n"
            f"    {med_base_share},\n"
            f"    SAMEPERIODLASTYEAR('{dim_tempo_nome}'[DTC_DATA])\n"
            ")"
        )
        expr_yoy = (
            "DIVIDE(\n"
            f"    {med_base_share} - [{leg_base_share} (Ano Anterior)],\n"
            f"    [{leg_base_share} (Ano Anterior)],\n"
            "    0\n"
            ")"
        )
        bloco_tempo_qual = [
            "#### C. Inteligência Temporal (`YoY`, `MoM`) e Auditoria da Linha Sentinela (`-1`)",
            "",
            _render_ficha_medida(
                nome_med=f"{leg_base_share} (Ano Anterior)",
                o_que_calcula=f"Valor da métrica `{med_base_share}` apurado exatamente no mesmo período do ano anterior (*Same Period Last Year*).",
                por_que_existe=f"Fornece a referência histórica homóloga para avaliar sazonalidade e evolução real de **{leg_base_share}** entre exercícios.",
                por_que_formula_assim=f"Utiliza `CALCULATE({med_base_share}, SAMEPERIODLASTYEAR('{dim_tempo_nome}'[DTC_DATA]))` sobre a dimensão `{dim_tempo_nome}` marcada como *Tabela de Data*, deslocando automaticamente o contexto de dia, mês, semestre ou ano em `-1 ano`.",
                onde_usar_formato="Gráfico comparativo *Atual vs. Ano Anterior* na **Página 3** e base do cálculo de `% Variação YoY`.",
                expr_dax_padrao=expr_py,
                comentario_dax=f"Valor no Ano Anterior (SamePeriodLastYear) — requer {dim_tempo_nome} marcada como Tabela de Data",
            ),
            _render_ficha_medida(
                nome_med=f"% Variacao YoY ({leg_base_share})",
                o_que_calcula=f"Variação percentual (*Year-over-Year*) de `{med_base_share}` em relação ao mesmo período do exercício anterior.",
                por_que_existe=f"Alimenta os badges de tendência (`▲ +X%` / `▼ -Y%`) nos cartões KPI executivos, sinalizando aceleração ou retração de **{leg_base_share}**.",
                por_que_formula_assim=f"Calcula a diferença `{med_base_share} - [{leg_base_share} (Ano Anterior)]` e divide pela base do ano anterior via `DIVIDE(..., ..., 0)`, prevenindo erros matemáticos quando não houver histórico no ano anterior.",
                onde_usar_formato="Rótulo secundário nos Cartões KPI da **Página 1** e destaque na **Página 3**. Formatar como **Percentual (`+0.0%;-0.0%;0.0%`)**.",
                expr_dax_padrao=expr_yoy,
                comentario_dax="Variação Percentual Ano contra Ano (% YoY)",
            ),
        ]

        if fk_dim_princ:
            col_fk_p = fk_dim_princ["coluna"].upper()
            nome_med_orfao = f"Qtd Nao Informado -1 ({leg_f})"
            nome_per_orfao = f"% Nao Informado -1 ({leg_f})"
            medidas_qualidade.append(f"[{nome_med_orfao}]")
            medidas_qualidade.append(f"[{nome_per_orfao}]")
            expr_orfao = (
                "COALESCE(\n"
                f"    CALCULATE(COUNTROWS('{nt_f}'), '{nt_f}'[{col_fk_p}] = -1),\n"
                "    0\n"
                ")"
            )
            bloco_tempo_qual.extend([
                _render_ficha_medida(
                    nome_med=nome_med_orfao,
                    o_que_calcula=f"Quantidade absoluta de registros na fato `{nt_f}` vinculados à linha sentinela `-1` (`Não Informado`) na chave estrangeira `{col_fk_p}`.",
                    por_que_existe=f"Quando o processo ETL no ODI 12c encontra um evento sem código dimensional válido na origem, ele grava `{col_fk_p} = -1` para preservar 100% do valor financeiro/operacional. Esta medida permite auditar quantos registros possuem pendência cadastral na origem.",
                    por_que_formula_assim=f"Aplica `CALCULATE(COUNTROWS('{nt_f}'), '{nt_f}'[{col_fk_p}] = -1)` com `COALESCE(..., 0)`, isolando estritamente as linhas mapeadas para a chave sentinela `-1`.",
                    onde_usar_formato="Cartão KPI de Governança na **Página 4 (Governança de Dados e Monitoramento de Sentinela `-1`)**. Formatar como **Número Inteiro (`#,0`)**.",
                    expr_dax_padrao=expr_orfao,
                    comentario_dax=f"Monitoramento de Governança: Registros com Chave Sentinela -1 em {col_fk_p}",
                ),
                _render_ficha_medida(
                    nome_med=nome_per_orfao,
                    o_que_calcula=f"Percentual de registros da tabela fato `{nt_f}` alocados na chave sentinela `-1` em relação ao total de registros `[{nome_med_qtd_reg}]`.",
                    por_que_existe=f"Atua como SLA de Qualidade de Dados (*Data Quality Threshold*): se ultrapassar o limite de tolerância (ex: `> 5%`), alerta a engenharia e o gestor de negócio sobre falha de preenchimento no sistema transacional de origem.",
                    por_que_formula_assim=f"Divide `[{nome_med_orfao}]` pelo volume total `[{nome_med_qtd_reg}]` utilizando `DIVIDE(..., ..., 0)`.",
                    onde_usar_formato="Cartão KPI de Qualidade e gráfico de evolução mensal na **Página 4**. Formatar como **Percentual (`0.00%`)** com regra condicional de alerta se `> 5%`.",
                    expr_dax_padrao=f"DIVIDE([{nome_med_orfao}], [{nome_med_qtd_reg}], 0)",
                    comentario_dax=f"Taxa percentual de registros na linha sentinela -1 em {nt_f}",
                ),
            ])

        bloco_dax.extend(bloco_tempo_qual)
        medidas_dax.append("\n".join(bloco_dax))

        # Queries SQL de Reconciliação completas com JOIN em DIM_TEMPO e Dimensão Principal
        expr_sql = ",\n".join(cols_metricas_sql[:4]) if cols_metricas_sql else "    COUNT(*) AS QTD_REGISTROS"
        if fk_dim_princ:
            tab_d_p = fk_dim_princ["tabela_ref"].upper()
            col_fk_p = fk_dim_princ["coluna"].upper()
            d_obj_p = nomes_dims.get(tab_d_p)
            pk_d_p = _obter_sk_dim(d_obj_p) if d_obj_p else "DIMENSION_KEY"
            nk_d_p = _obter_nk_dim(d_obj_p) if d_obj_p else pk_d_p
            cols_desc_p = [
                c["nome_dw"].upper()
                for c in (d_obj_p["colunas"] if d_obj_p else [])
                if c["nome_dw"].upper().startswith(("DES_", "NOM_", "DSC_", "SIG_"))
            ]
            col_agrup_p = cols_desc_p[0] if cols_desc_p else nk_d_p
            join_tempo_sql = (
                f"LEFT JOIN {schema}.{dim_tempo_nome} t ON t.{pk_tempo} = f.{fk_tempo_col}\n"
                if fk_tempo_col
                else ""
            )
            sel_tempo_sql = "    t.NUM_ANO,\n    t.NUM_MES,\n" if fk_tempo_col else ""
            grp_tempo_sql = "\nGROUP BY t.NUM_ANO, t.NUM_MES\nORDER BY t.NUM_ANO DESC, t.NUM_MES DESC" if fk_tempo_col else ""

            sql_conferencia.append(
                f"-- =====================================================================\n"
                f"-- 1. Reconciliação Mensal e Contagem SCD2-Safe: {schema}.{nt_f}\n"
                f"-- =====================================================================\n"
                f"SELECT\n"
                f"{sel_tempo_sql}"
                f"    COUNT(*) AS QTD_REGISTROS_FATO,\n"
                f"    COUNT(DISTINCT CASE WHEN f.{col_fk_p} <> -1 THEN d.{nk_d_p} END) AS QTD_DISTINTOS_NK_SCD2_SAFE,\n"
                f"{expr_sql}\n"
                f"FROM {schema}.{nt_f} f\n"
                f"{join_tempo_sql}"
                f"LEFT JOIN {schema}.{tab_d_p} d ON d.{pk_d_p} = f.{col_fk_p}{grp_tempo_sql};\n\n"
                f"-- =====================================================================\n"
                f"-- 2. Conferência por Recorte Dimensional ({tab_d_p}.{col_agrup_p})\n"
                f"-- =====================================================================\n"
                f"SELECT\n"
                f"    NVL(TO_CHAR(d.{col_agrup_p}), 'NAO INFORMADO (-1)') AS CATEGORIA_DIMENSAO,\n"
                f"    COUNT(*) AS QTD_REGISTROS,\n"
                f"    COUNT(DISTINCT CASE WHEN f.{col_fk_p} <> -1 THEN d.{nk_d_p} END) AS QTD_ENTIDADES_UNICAS_NK,\n"
                f"{expr_sql}\n"
                f"FROM {schema}.{nt_f} f\n"
                f"LEFT JOIN {schema}.{tab_d_p} d ON d.{pk_d_p} = f.{col_fk_p}\n"
                f"GROUP BY NVL(TO_CHAR(d.{col_agrup_p}), 'NAO INFORMADO (-1)')\n"
                f"ORDER BY QTD_REGISTROS DESC;\n\n"
                f"-- =====================================================================\n"
                f"-- 3. Auditoria de Qualidade: Taxa de Chave Sentinela (-1) em {nt_f}\n"
                f"-- =====================================================================\n"
                f"SELECT\n"
                f"    COUNT(*) AS TOTAL_LINHAS_FATO,\n"
                f"    SUM(CASE WHEN f.{col_fk_p} = -1 THEN 1 ELSE 0 END) AS QTD_SENTINELA_MENOS_1,\n"
                f"    ROUND(SUM(CASE WHEN f.{col_fk_p} = -1 THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0), 2) AS PERC_NAO_INFORMADO\n"
                f"FROM {schema}.{nt_f} f;"
            )
        else:
            sql_conferencia.append(
                f"-- Conferência Geral da Fato {schema}.{nt_f}\n"
                f"SELECT\n"
                f"    COUNT(*) AS QTD_REGISTROS,\n"
                f"{expr_sql}\n"
                f"FROM {schema}.{nt_f} f;"
            )

    secao_indicadores_negocio = ""
    if indicadores_negocio:
        arq_origem_ind = indicadores_negocio[0].get("arquivo_origem", "Planilha de Indicadores")
        linhas_tab_ind = []
        dax_metas = ["### 🎯 Medidas DAX de Indicadores e Metas Oficiais do Negócio\n"]
        nt_fato_princ = fatos[0]["nome_tabela"].upper() if fatos else "FATO"
        medida_qtd_padrao = f"[Qtd Registros ({humanizar_identificador(re.sub(r'^(FATO_|FAT_)', '', nt_fato_princ))})]"
        medida_valor_padrao = medidas_kpi_topo[0] if medidas_kpi_topo else medida_qtd_padrao

        for idx_i, ind in enumerate(indicadores_negocio, 1):
            linhas_tab_ind.append(
                f"| **{idx_i}. {ind['indicador']}** | {ind['formula'] or '-'} | `{ind['unidade'] or '-'}` | `{ind['periodicidade'] or '-'}` | {ind['meta'] or '-'} | `{ind['filtros'] or '-'}` |"
            )
            unid_up = (ind.get("unidade") or "").upper()
            form_up = (ind.get("formula") or "").upper()
            if any(k in unid_up or k in form_up for k in ("R$", "VALOR", "MONET", "RECEITA", "DESPESA", "PAGO")):
                medida_base_ref = medida_valor_padrao
            else:
                medida_base_ref = medida_qtd_padrao

            filtro_ind = (ind.get("filtros") or "").strip()
            expr_realizado_ind = medida_base_ref
            if filtro_ind and "=" in filtro_ind and not filtro_ind.startswith("-"):
                m_f_ind = re.search(r"([A-Za-z0-9_]+)\s*=\s*'([^']+)'", filtro_ind)
                if m_f_ind:
                    col_f_i = m_f_ind.group(1).upper()
                    val_f_i = m_f_ind.group(2)
                    tab_f_i = nt_fato_princ
                    for d_cand in dims:
                        if any(c["nome_dw"].upper() == col_f_i for c in d_cand["colunas"]):
                            tab_f_i = d_cand["nome_tabela"].upper()
                            break
                    expr_realizado_ind = f"CALCULATE({medida_base_ref}, '{tab_f_i}'[{col_f_i}] = \"{val_f_i}\")"

            for m_num in ind.get("metas_numericas", []):
                val_m = m_num["valor"]
                ctx_m = m_num["contexto"]
                if ctx_m and ctx_m != "%":
                    sufixo_meta = re.sub(r"^bolsas\s+(?:de\s+|do\s+)?", "", ctx_m, flags=re.IGNORECASE).strip().title()
                    nome_med_meta = f"Meta {sufixo_meta}"
                else:
                    nome_med_meta = f"Meta {ind['indicador']}"
                val_dax = f"{float(val_m) / 100.0:.2f}" if ctx_m == "%" else val_m
                dax_metas.append(
                    _render_ficha_medida(
                        nome_med=nome_med_meta,
                        o_que_calcula=f"Constante oficial de meta pactuada para o indicador **{ind['indicador']}** ({ctx_m or 'Geral'}).",
                        por_que_existe=f"Permite traçar linhas de referência constante em gráficos de evolução e servir de denominador para o cálculo de atingimento da meta estipulada na planilha `{arq_origem_ind}`.",
                        por_que_formula_assim=f"Retorna o valor escalar `{val_dax}` extraído diretamente da especificação de metas do negócio (`{ind['meta']}`).",
                        onde_usar_formato="Linha de Meta constante em gráficos da **Página 1** e **Página 2**, ou referência de velocímetro (*Gauge*).",
                        expr_dax_padrao=str(val_dax),
                        comentario_dax=f"Meta oficial estabelecida para {ind['indicador']}",
                    )
                )
                dax_metas.append(
                    _render_ficha_medida(
                        nome_med=f"% Atingimento {nome_med_meta}",
                        o_que_calcula=f"Percentual de cumprimento da meta `[{nome_med_meta}]` pelo valor realizado `{expr_realizado_ind}`.",
                        por_que_existe=f"Mostra ao gestor o quão próximo o realizado está do alvo pactuado para **{ind['indicador']}** (`>= 100%` indica meta batida).",
                        por_que_formula_assim=f"Utiliza `DIVIDE({expr_realizado_ind}, [{nome_med_meta}], 0)`, aplicando eventual filtro obrigatório (`{filtro_ind or 'Sem filtro fixo'}`) no numerador e dividindo pela medida de meta.",
                        onde_usar_formato="Cartões de Atingimento na **Página 2 (Metas e Eficiência)** com semáforo condicional (Verde `>= 100%`, Amarelo `80%..99%`, Vermelho `< 80%`). Formatar como **Percentual (`0.00%`)**.",
                        expr_dax_padrao=f"DIVIDE({expr_realizado_ind}, [{nome_med_meta}], 0)",
                        comentario_dax=f"Percentual de atingimento da {nome_med_meta}",
                    )
                )
        if len(dax_metas) > 1:
            medidas_dax.append("\n".join(dax_metas))

        secao_indicadores_negocio = (
            f"\n### 4.1 Matriz Oficial de Indicadores e Metas do Negócio (`{arq_origem_ind}`)\n\n"
            "| Indicador Oficial | Fórmula de Cálculo | Unidade | Periodicidade | Meta Estabelecida | Filtros Obrigatórios |\n"
            "| :--- | :--- | :---: | :---: | :--- | :--- |\n"
            + "\n".join(linhas_tab_ind)
            + "\n"
        )

    # Elementos dinâmicos para a Seção 6 (Mockup detalhado página a página)
    dim1_nome = dims_negocio[0]["nome_tabela"].upper() if dims_negocio else dim_tempo_nome
    dim1_col = next(
        (c["nome_dw"].upper() for c in (dims_negocio[0]["colunas"] if dims_negocio else []) if c["nome_dw"].upper().startswith(("DES_", "NOM_", "SIG_"))),
        _obter_nk_dim(dims_negocio[0]) if dims_negocio else "NUM_ANO",
    )
    dim1_nk = _obter_nk_dim(dims_negocio[0]) if dims_negocio else "DIMENSION_KEY"

    dim2_nome = dims_negocio[1]["nome_tabela"].upper() if len(dims_negocio) > 1 else dim1_nome
    dim2_col = next(
        (c["nome_dw"].upper() for c in (dims_negocio[1]["colunas"] if len(dims_negocio) > 1 else []) if c["nome_dw"].upper().startswith(("DES_", "NOM_", "SIG_"))),
        dim1_col,
    )

    kpis_p1_txt = " | ".join(f"`{m}`" for m in (medidas_kpi_topo[:5] or ["[Qtd Registros]"]))
    kpis_p2_txt = " | ".join(f"`{m}`" for m in (medidas_eficiencia[:4] + medidas_kpi_topo[:2]))
    kpis_p4_txt = " | ".join(f"`{m}`" for m in (medidas_qualidade[:4] or ["[Qtd Registros]"]))

    matriz_rel_txt = "\n".join(linhas_rel_matrix) if linhas_rel_matrix else "| _Sem FKs detectadas_ | - | - | - | - | - | - |"
    radar_txt = "\n".join(radar_rows[:8]) if radar_rows else "| **Evolução Temporal e Concentração (Pareto 80/20)** | Colunas de Métricas e FKs | Permite avaliar sazonalidade, participação percentual (`% Share`) e desvios em relação à meta. |"
    sql_conf_txt = "\n\n".join(sql_conferencia) if sql_conferencia else (f"SELECT COUNT(*) FROM {schema}.{fatos[0]['nome_tabela']};" if fatos else "-- Sem fatos")

    if homologado_pos_carga:
        titulo_doc = f"# 📊 Guia Oficial do Analista de BI (VERSÃO OFICIAL — HOMOLOGADA PÓS-CARGA) — Projeto {projeto}"
        status_doc_meta = (
            f"> **Status do Documento:** ✅ **VERSÃO OFICIAL (Homologada Pós-Carga com Amostra Real — "
            f"{len(dados_amostra.get('medidas_avaliadas', []))} Medidas DAX Conciliadas)**  "
        )
        banner_ciclo_vida = (
            "> [!IMPORTANT]\n"
            f"> **✅ Guia Oficial Homologado Pós-Carga (`DIM_*` + `FATO_*`):**\n"
            f"> Todas as medidas DAX, relacionamentos `1:*`, chaves sentinelas (`-1`) e regras de negócio deste guia foram "
            f"testadas e conciliadas contra a amostra pós-carga da tabela fato `{dados_amostra.get('nome_fato')}` "
            f"(`{dados_amostra.get('total_linhas_fato', 0)}` registros analisados; `{dados_amostra.get('qtd_ok', 0)}` medidas exatas e "
            f"`{dados_amostra.get('qtd_parciais', 0)}` medida(s) parcialmente correta(s) já corrigida(s) automaticamente nas fichas técnicas da Seção 4). "
            "Consulte a **Seção 10** para o laudo completo de conciliação SQL x DAX."
        )
        linhas_sec10 = [
            "\n---\n",
            "## 10. 🧪 Prova Real Pós-Carga (`DIM_*` + `FATO_*`) e Conciliação de Medidas DAX\n",
            f"- **Origem da Amostra Auditada:** `{dados_amostra.get('origem_amostra', 'AMOSTRA_FORNECIDA')}`",
            f"- **Linhas avaliadas na Fato (`{dados_amostra.get('nome_fato')}`):** `{dados_amostra.get('total_linhas_fato', 0)}`",
            f"- **Registros em Chave Sentinela (`SK = -1`):** `{dados_amostra.get('qtd_sentinela_fato', 0)}` (`{dados_amostra.get('pct_sentinela_fato', 0.0):.2f}%`)",
            f"- **FKs Órfãs detectadas:** `{dados_amostra.get('qtd_orfaos_fato', 0)}`",
            f"- **Medidas DAX auditadas:** `{len(dados_amostra.get('medidas_avaliadas', []))}` (`{dados_amostra.get('qtd_ok', 0)}` exatas | `{dados_amostra.get('qtd_parciais', 0)}` parcialmente corretas corrigidas)\n",
            "| Medida DAX | Valor Calculado na Amostra | Status | Diagnóstico / Correção Automática |",
            "| :--- | :---: | :---: | :--- |",
        ]
        for mr in dados_amostra.get("medidas_avaliadas", []):
            st_ic = "✅ Exata" if mr["status"] == "OK" else "⚠️ Parcial (Corrigida)"
            diag_res = " ".join(mr.get("diagnosticos", [])) or "Validada contra SQL na amostra."
            if mr.get("dax_corrigido"):
                diag_res += f" **DAX Corrigido:** `{mr['nome']} = {mr['dax_corrigido']}`"
            linhas_sec10.append(f"| `[{mr['nome']}]` | **{mr['valor_formatado']}** | {st_ic} | {diag_res} |")
        secao_prova_final = "\n".join(linhas_sec10) + "\n"
    else:
        titulo_doc = f"# 📊 Guia do Analista de BI (VERSÃO PRÉVIA — PRÉ-CARGA) — Projeto {projeto}"
        status_doc_meta = (
            "> **Status do Documento:** ⏳ **VERSÃO PRÉVIA (Pré-Carga — Aguardando Validação com Amostra Real Pós-Carga)**  "
        )
        banner_ciclo_vida = (
            "> [!WARNING]\n"
            "> **⚠️ Documento em Versão Prévia (Gerado Antes da Carga e Validação com Amostra Real):**\n"
            "> Este guia foi projetado a partir do DDL das tabelas (`DIM_*` e `FATO_*`) para orientar o desenho inicial do modelo e o entendimento do racional de cada medida. "
            "**Após processar a carga do DW (ODI 12c / Hop)**, deposite uma amostra dos dados carregados em `entrega/planejador_dw/amostras/` e execute **`/validar-medidas-bi`**: "
            "o NINHO testará todas as fórmulas na prova real, corrigirá eventuais medidas parcialmente corretas e promoverá este documento automaticamente para o **Guia Oficial do Analista de BI**."
        )
        secao_prova_final = ""

    return f"""{titulo_doc}

> **Schema Oracle:** `{schema}` | **Data de Geração:** {datetime.now().strftime('%Y-%m-%d %H:%M')}  
{status_doc_meta}
> **Público-Alvo:** Analistas de BI, Engenheiros de Analytics, Gestores de Negócio e Designers de UI/UX  
> **Padrão Arquitetural:** Modelo Estrela (`Star Schema` / *Fact Constellation*) em Modo Importação (`Import Mode`)

{banner_ciclo_vida}

---

## 1. Visão Geral, Contexto Executivo e Catálogo de Dados

### 1.1 Dores de Negócio Resolvidas por esta Arquitetura
Este guia documenta a camada analítica do projeto **{projeto}** no schema `{schema}`, projetada para eliminar quatro riscos clássicos em painéis executivos:
1. **Proteção contra Dupla Contagem em Dimensões SCD Tipo 2:** Quando uma entidade (`{dim1_nome}`) muda de atributo ao longo do tempo e ganha uma nova versão histórica (`DIMENSION_KEY`), contagens ingênuas pela chave substituta inflam os indicadores. Este guia fornece as fórmulas DAX blindadas via `SUMMARIZE` na Chave Natural (`{dim1_nk}`).
2. **Integridade Referencial Total via Linha Sentinela (`-1`):** Nenhum registro de Fato é perdido por ausência de cadastro dimensional; ocorrências órfãs ou não aplicáveis convergem para a chave `-1` (`"Não Informado"`), garantindo batimento de **100%** entre o Power BI e o Oracle.
3. **Proibição de Somatórios Inválidos em Taxas e Percentuais (`PER_*`):** Percentuais pré-calculados nunca são somados (`SUM`); toda taxa agregada utiliza razão ponderada (`DIVIDE(SUM(numerador), SUM(denominador), 0)`).
4. **Independência entre Tabelas Fato (*Conformed Dimensions*):** Múltiplas tabelas Fato compartilham as mesmas dimensões conformadas (`{dim_tempo_nome}`, `{dim1_nome}`) sem jamais se relacionarem diretamente entre si (`Fato <-> Fato`).

### 1.2 Estratégia de Conexão Recomendada
- **Modo de Armazenamento:** **Importação (`Import Mode`)** no motor colunar *VertiPaq* do Power BI.
- **Justificativa Técnica:** O modo Importação entrega tempo de resposta sub-segundo para cálculos de cardinalidade dinâmica (`SUMMARIZE` + `COUNTROWS`), inteligência temporal (`SAMEPERIODLASTYEAR`) e cruzamento simultâneo entre múltiplas tabelas Fato.
- **Janela de Atualização Sugerida:** Agendar refresh no Power BI Service logo após o término do pacote de carga no ODI 12c (`PACK_CARGA_*`).

### 1.3 Catálogo Detalhado de Tabelas Fato (Métricas e Eventos)

| Tabela Fato Oracle | Chave Primária (PK) | Grão Analítico (Chaves Estrangeiras) | Colunas de Métricas / Flags | Papel Funcional no Painel |
| :--- | :--- | :--- | :--- | :--- |
{chr(10).join(linhas_cat_fatos)}

### 1.4 Catálogo Detalhado de Tabelas Dimensão (Contexto, Filtros e Vigência SCD2)

| Tabela Dimensão Oracle | Chave Primária (SK) | Chave Natural (NK) | Atributos Descritivos Principais | Colunas de Controle SCD Tipo 2 |
| :--- | :--- | :--- | :--- | :--- |
{chr(10).join(linhas_cat_dims)}

---

## 2. Diagrama e Matriz de Relacionamentos (Star Schema no Power BI)

Configure todos os relacionamentos na aba **Exibição de Modelo** do Power BI Desktop seguindo estritamente o diagrama abaixo:

{chr(10).join(linhas_er)}

### 2.1 Matriz de Configuração de Relacionamentos

| Tabela Dimensão (Lado `1`) | Coluna PK (Dimensão) | Tabela Fato (Lado `*`) | Coluna FK (Fato) | Cardinalidade | Direção do Filtro Cruzado | Status |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: |
{matriz_rel_txt}

### 2.2 Regras Críticas de Modelagem na Exibição de Modelo
1. **Proibição de Filtro Bidirecional (`Ambos`):** Mantenha **100%** dos relacionamentos com direção **Única (`1 ➔ *`)**. O filtro bidirecional gera caminhos ambíguos entre Fatos que compartilham as mesmas dimensões e degrada severamente a performance do *VertiPaq*.
2. **Proibição de Ligação Direta `Fato <-> Fato`:** Quando houver mais de uma tabela Fato no modelo, o cruzamento de medidas no mesmo visual deve ocorrer **exclusivamente** através das dimensões compartilhadas (`{dim_tempo_nome}`, `{dim1_nome}`).
3. **Ocultação de Colunas Técnicas:** Na *Exibição de Modelo*, clique com o botão direito e marque **"Ocultar na exibição de relatório"** em todas as colunas `DIMENSION_KEY`, `SK_*`, `DTC_CARGA` e nas colunas brutas de métrica das Fatos (exponha apenas as Medidas DAX da tabela `_Medidas_{projeto}`).

---

## 3. Dimensão Tempo (`{dim_tempo_nome}`), SCD Tipo 2 e Linha Sentinela (`-1`)

### 3.1 Configuração Obrigatória da Dimensão Calendário (`{dim_tempo_nome}`)
1. **Desative a Data/Hora Automática:** Em *Arquivo ➔ Opções e configurações ➔ Opções ➔ Carregamento de Dados*, desmarque **"Data/hora automática para novos arquivos"**.
2. **Marque como Tabela de Data:** Clique com o botão direito em `{dim_tempo_nome}` ➔ *Marcar como tabela de data* ➔ selecione a coluna de data (`DTC_DATA` ou `DTC_COMPLETA`).
3. **Regra de Ordenação Cronológica (*Classificar por Coluna* / *Sort by Column*):**

| Coluna Exibida nos Visuais (Texto) | Classificar Pela Coluna (Numérica) | Evita o Erro Clássico de... |
| :--- | :--- | :--- |
| `DES_MES` (`Janeiro`, `Fevereiro`...) | `NUM_MES` (`1` a `12`) | Ordenar alfabeticamente (`Abril`, `Agosto`, `Dezembro`...) |
| `DES_MES_ANO` (`Jan/2026`, `Fev/2026`...) | `COD_ANO_MES` / `NUM_ANO_MES` (`202601`) | Misturar meses de anos diferentes fora de ordem |
| `DES_SEMESTRE` (`1º Semestre`, `2º Semestre`) | `NUM_SEMESTRE` (`1`, `2`) | Inversão de semestres em gráficos de linha |
| `DES_DIA_SEMANA` (`Segunda`, `Terça`...) | `NUM_DIA_SEMANA` (`1` a `7`) | Exibir `Domingo, Quarta, Quinta, Sábado...` |

### 3.2 Como Analisar Dimensões SCD Tipo 2 no Power BI sem Distorcer Contagens
As dimensões do `{schema}` utilizam **SCD Tipo 2** (`DTC_EFETIVACAO`, `DTC_EXPIRACAO`, `SIN_ATIVO`):
- **Ao filtrar por um atributo descritivo (ex: `{dim1_nome}[{dim1_col}]`):** O Power BI mostra exatamente os fatos ocorridos enquanto a entidade estava naquela classificação histórica (*análise ponto-no-tempo*).
- **Ao contar quantas entidades reais atuaram no período:** Uma mesma entidade (mesma Chave Natural `{dim1_nk}`) pode ter tido 2 versões de `DIMENSION_KEY` no ano. Por isso, **nunca use `DISTINCTCOUNT` direto na FK da Fato** para contar pessoas/entidades; utilize sempre as medidas **`(SCD2 Safe)`** da Seção 4, que agrupam pela Chave Natural `{dim1_nk}` da dimensão.

### 3.3 Tratamento do Registro Sentinela (`-1` — Não Informado / Não Aplicável)
- **Nos Somatórios (`SUM`):** Mantenha os registros com FK igual a `-1` para que os cartões de volume/valor total fechem em **100%** com o banco Oracle. Nos gráficos por categoria, eles aparecerão rotulados como `"Não Informado"`.
- **Nas Contagens Distintas de Entidades:** A condição `'{fatos[0]['nome_tabela'].upper() if fatos else 'FATO'}'[FK] <> -1` já está embutida nas fórmulas DAX abaixo para impedir que o código técnico `-1` seja contado como um indivíduo real.

---

## 4. Dicionário Completo de Métricas e Fórmulas DAX

> [!IMPORTANT]
> **Duas Regras de Ouro DAX neste Projeto:**
> 1. **Proibição de `SUM()` em Colunas `PER_*` / Taxas:** Jamais some percentuais pré-calculados linha a linha. Utilize sempre `DIVIDE([Total Numerador], [Total Denominador], 0)` ou `AVERAGE()`.
> 2. **Contagem Distinta `SCD2 Safe` pela Chave Natural (`NK`):** Para contar entidades reais sem duplicar quem mudou de versão histórica no SCD2, utilize o padrão `COUNTROWS(SUMMARIZE(FILTER(FATO, FK <> -1), DIM[NK]))`.
{secao_indicadores_negocio}
Crie uma tabela vazia no Power BI chamada **`_Medidas_{projeto}`** (*Inserir Dados ➔ Carregar*) e cadastre as medidas abaixo organizadas por pasta (*Display Folder*):

{chr(10).join(medidas_dax) if medidas_dax else "_Nenhuma coluna numérica de métrica explícita (`VAL_`, `QTD_`) detectada nas tabelas Fato._"}

---

## 5. Configuração de Filtros Globais e Segmentadores (*Sync Slicers*)

Configure o painel de filtros e os segmentadores no topo das páginas sincronizando-os via *Exibição ➔ Sincronizar Segmentações de Dados*:

| Filtro no Dashboard | Campo(s) Físicos a Utilizar | Tabela de Origem | Tipo de Visual Recomendado | Escopo de Sincronização (*Sync Slicers*) |
| :--- | :--- | :--- | :--- | :--- |
{chr(10).join(slicers_rows)}

---

## 6. Proposta Detalhada de Estrutura Visual para o Painel (Power BI) & Mockup Visual

> [!TIP]
> **🎨 Pacote Visual Interativo e Executivos Gerados Automaticamente nesta Pasta (`08_datasets_bi/`):**
> * 🖼️ **[`preview_painel_bi.html`](preview_painel_bi.html)**: Visualizador Interativo (com alternância **Tema Claro / Dark Mode**, **Modo Executivo vs. Dev Mode Redlines `①..⑦`** e botão **Baixar PNG 2x Alta Resolução**).
> * 📐 **[`mockup_painel_bi.svg`](mockup_painel_bi.svg)** e **[`mockup_painel_bi_devmode.svg`](mockup_painel_bi_devmode.svg)**: Mockups vetoriais Full HD (`1440x960`) prontos para anexar na validação com o cliente ou guiar o desenvolvedor Power BI.
> * ⭐ **[`../11_dicionario_dados/diagrama_star_schema.svg`](../11_dicionario_dados/diagrama_star_schema.svg)**: Diagrama vetorial da topologia Star Schema (`FATO` no centro + `DIMs` satélites com `PK`, `NK`, `SCD2` e `SK -1`).
> * 📊 **[`Indicadores_PowerBI_{projeto}.xlsx`](Indicadores_PowerBI_{projeto}.xlsx)**: Planilha Excel formatada em 3 abas (`Catalogo_Indicadores`, `Metas_e_Thresholds` e `Guia_Preenchimento`) com larguras auto-ajustadas e painel congelado.
> * 📽️ **[`apresentacao_executiva_{projeto.lower()}.pptx`](apresentacao_executiva_{projeto.lower()}.pptx)** e **[`apresentacao_slides.html`](apresentacao_slides.html)**: Deck executivo `16:9` de Kickoff/Entrega do projeto.
> * 📄 **[`GUIA_ANALISTA_BI_{projeto}.docx`](GUIA_ANALISTA_BI_{projeto}.docx)**: Versão corporativa em Microsoft Word deste guia.

![Mockup Visual do Painel Power BI](mockup_painel_bi.svg)

### 6.1 Mapa de Navegação Superior (Wireframe do Painel)

```text
+---------------------------------------------------------------------------------------------------+
|  [Logo / Título: Painel Executivo {projeto}]                   [Última Carga: MAX(DTC_CARGA)]     |
|  +-------------------------+-------------------------+-------------------------+---------------+  |
|  | 1. Visão Executiva      | 2. Metas e Eficiência   | 3. Perfil e Pareto 80/20| 4. Governança |  |
|  +-------------------------+-------------------------+-------------------------+---------------+  |
|  [Filtros Globais: Ano | Semestre | Mês ({dim_tempo_nome}) | {dim1_nome}[{dim1_col}] | {dim2_nome}[{dim2_col}] ] |
+---------------------------------------------------------------------------------------------------+
```

### 📄 Página 1: Visão Executiva e KPIs Estratégicos
* **Objetivo:** Entregar à alta gestão uma leitura imediata do volume, valores consolidados, entidades ativas (SCD2 Safe) e tendência temporal do domínio **{projeto}**.
* **Filtros no Topo:** `{dim_tempo_nome}[NUM_ANO]`, `{dim_tempo_nome}[DES_MES]`, `{dim1_nome}[{dim1_col}]` e `{dim2_nome}[{dim2_col}]`.
* **Linha Superior (Faixa de Cartões KPI):**
  * Exibir lado a lado: {kpis_p1_txt}.
  * Adicionar rótulo de referência secundário com `[% Variacao YoY]`.
* **Corpo Principal (4 Quadrantes):**
  * **Superior Esquerdo (Evolução Mensal):** Gráfico de Colunas Agrupadas e Linha — Eixo X: `{dim_tempo_nome}[DES_MES_ANO]` (ordenado por `COD_ANO_MES`); Colunas: métrica principal de volume/valor; Linha secundária: entidade ativa `(SCD2 Safe)` ou meta.
  * **Superior Direito (Ranking Top 10 por `{dim1_nome}`):** Gráfico de Barras Horizontais — Eixo Y: `{dim1_nome}[{dim1_col}]`; Valores: medida principal de volume/valor com rótulo de dados e formatação condicional de gradiente.
  * **Inferior Esquerdo (Composição por `{dim2_nome}`):** Gráfico de Rosca ou Barras 100% Empilhadas — Legenda/Eixo: `{dim2_nome}[{dim2_col}]`; Valores: `[% Participacao ...]`.
  * **Inferior Direito (Matriz Resumo Executiva):** Visual de Matriz cruzando `{dim1_nome}[{dim1_col}]` nas linhas com os principais indicadores DAX nas colunas e barra de dados embutida.

### 📄 Página 2: Acompanhamento de Metas, Eficiência e Detalhamento Operacional
* **Objetivo:** Avaliar produtividade média por entidade ativa, taxas ponderadas (`DIVIDE`) e permitir *drill-down* até o nível individual da Chave Natural (`{dim1_nk}`).
* **Linha Superior (Cartões de Eficiência e Metas):**
  * Exibir: {kpis_p2_txt}.
* **Corpo Principal:**
  * **Esquerda (Análise de Intensidade / Dispersão):** Gráfico de Combo ou Dispersão comparando o total de registros/valores versus a quantidade de entidades ativas `(SCD2 Safe)` por `{dim1_nome}[{dim1_col}]`.
  * **Direita / Rodapé (Matriz Analítica com Drill-Down):** Hierarquia nas linhas: `{dim1_nome}[{dim1_col}]` ➔ `{dim2_nome}[{dim2_col}]` ➔ `{dim1_nome}[{dim1_nk}]`, permitindo exportar o detalhamento nominal auditável.

### 📄 Página 3: Análise de Perfil, Cruzamentos Dimensionais e Concentração (Pareto 80/20)
* **Objetivo:** Identificar sazonalidade, concentração de recursos e comparativos Ano contra Ano (`YoY`).
* **Corpo Principal:**
  * **Esquerda (Curva de Concentração / Pareto):** Gráfico de Colunas e Linha mostrando o valor absoluto por categoria e o acumulado percentual (`% Participacao`).
  * **Direita (Comparativo Atual vs. Ano Anterior):** Gráfico de Barras Agrupadas comparando a medida principal com a medida `(Ano Anterior)` e cartão de destaque para `[% Variacao YoY]`.

### 📄 Página 4: Governança de Dados, Qualidade e Monitoramento de Sentinela (`-1`)
* **Objetivo:** Garantir transparência técnica para a equipe de Engenharia de Dados e gestores sobre registros órfãos (`FK = -1`) e histórico de versões SCD Tipo 2 (`SIN_ATIVO`).
* **Linha Superior (Cartões de Qualidade):**
  * Exibir: {kpis_p4_txt}.
* **Corpo Principal:**
  * **Esquerda:** Gráfico de Colunas Empilhadas por `{dim_tempo_nome}[DES_MES_ANO]` exibindo a proporção de registros válidos (`FK <> -1`) vs. registros na linha sentinela (`FK = -1`).
  * **Direita:** Tabela de Auditoria listando `{dim1_nome}[{dim1_nk}]`, `{dim1_nome}[{dim1_col}]`, `SIN_ATIVO`, `DTC_EFETIVACAO` e `DTC_EXPIRACAO` para conferência das versões históricas abertas pelo ODI 12c.

---

## 7. Consultas SQL Rápidas de Conferência (Power BI vs. Oracle `{schema}`)

Execute as consultas abaixo no DBeaver / SQL Developer antes de publicar o painel. Os valores retornados pelo banco **devem bater em 100%** com os cartões da Página 1 e da Página 4 do Power BI:

```sql
{sql_conf_txt}
```

---

## 8. 💡 Radar Consultivo da IA — Potencial Analítico Adicional no Modelo

> [!TIP]
> **Escopo Consultivo Separado:** Cruzamentos e indicadores de alto valor já suportados pelas colunas físicas de `{schema}` que podem ser ativados na fase evolutiva do dashboard:

| Análise / KPI Sugerido | Coluna Física no DW | Valor Estratégico para a Gestão |
| :--- | :--- | :--- |
{radar_txt}

---

## 9. Checklist de Homologação Pré-Publicação (Quality Gate BI)

- [ ] **Check 1 (Star Schema `1:*` Único):** Todos os relacionamentos estão ativos como `1:*` com direção de filtro **Única (`Single`)** e não há nenhum relacionamento direto entre tabelas Fato.
- [ ] **Check 2 (Dimensão Calendário e Ordenação):** `{dim_tempo_nome}` foi marcada como *Tabela de Data* e as colunas `DES_MES`, `DES_MES_ANO` e `DES_SEMESTRE` estão classificadas pelas respectivas colunas numéricas (`Sort by Column`).
- [ ] **Check 3 (Blindagem SCD Tipo 2):** Todas as contagens de entidades/pessoas utilizam as medidas **`(SCD2 Safe)`** baseadas em `SUMMARIZE(..., DIM[NK])` em vez de `DISTINCTCOUNT` ingênuo na `DIMENSION_KEY`.
- [ ] **Check 4 (Proibição de Soma de Percentuais):** Nenhuma coluna `PER_*` ou taxa possui agregação `SUM`; todas utilizam `DIVIDE` ponderado ou `AVERAGE`.
- [ ] **Check 5 (Tratamento da Linha Sentinela `-1`):** Somatórios gerais incluem a linha `-1` (`"Não Informado"`) e contagens distintas de entidades filtram `FK <> -1`.
- [ ] **Check 6 (*Sync Slicers*):** Os filtros globais de Ano, Mês e dimensões principais estão sincronizados entre as Páginas 1, 2 e 3.
- [ ] **Check 7 (Reconciliação SQL 100%):** Os números exibidos nos Cartões KPI do Power BI foram confrontados com as 3 queries SQL da **Seção 7** e apresentaram divergência **zero**.
{secao_prova_final}"""


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


def derivar_sigla_curta_odi(projeto: str) -> str:
    """
    Deriva uma sigla curta de 2 a 4 caracteres para uso em objetos sujeitos ao
    limite estrito de 30 caracteres do ODI 12c (ORA-00972: identifier is too long),
    evitando que prefixos de steps internos (ex: C$_0, I$_, E$_, TGT_INS_, LKP_)
    ultrapassem 30 bytes no repositório do ODI 12c.
    """
    limpo = re.sub(r"[^A-Z0-9_]", "_", (projeto or "DW").upper()).strip("_")
    partes = [p for p in limpo.split("_") if p and p not in ("DW", "PROJETO", "SISTEMA", "DE", "DA", "DO", "DOS", "DAS", "E")]
    if not partes:
        return limpo[:4] or "DW"
    if len(partes) == 1:
        p0 = partes[0]
        return p0[:4] if len(p0) > 4 else p0
    iniciais = "".join(p[0] for p in partes)
    if 2 <= len(iniciais) <= 4:
        return iniciais
    return iniciais[:4]


def validar_tamanho_identificador_odi(nome_obj: str, tipo_obj: str = "GERAL") -> tuple:
    """
    Valida se o identificador físico respeita a margem de segurança do ODI 12c (<= 30 bytes com prefixos).
    Retorna (aprovado: bool, tamanho_atual: int, limite_recomendado: int).
    - DIM_*: máx 22 chars (para caber ODI_DIM_* <= 26 e TGT_INS_DIM_* <= 30)
    - ODI_DIM_* / SEQ_* / FATO_* / STG_*: máx 26 chars (para caber C$_0 / I$_ <= 30)
    """
    up = (nome_obj or "").upper().strip()
    tam = len(up)
    if tipo_obj.upper() == "DIM" or (up.startswith("DIM_") and not up.startswith("ODI_DIM_")):
        lim = 22
    else:
        lim = 26
    return (tam <= lim, tam, lim)


def abreviar_identificador_odi(prefixo: str, raw_name: str, sigla_curta: str = "", max_len: int = 22) -> str:
    """
    Gera um nome físico `<PREFIXO>_[<SIGLA>_]<TEMA>` garantidamente `<= max_len` caracteres
    (22 para DIM_*, 26 para FATO_*/STG_*/ODI_DIM_*) para evitar `ORA-00972` no ODI 12c.
    """
    pref = prefixo.upper().rstrip("_")
    corpo = re.sub(r"[^A-Z0-9_]", "_", (raw_name or "").upper()).strip("_")
    sig = (sigla_curta or "").upper().strip("_")
    if sig and not corpo.startswith(f"{sig}_") and corpo != sig:
        candidato = f"{pref}_{sig}_{corpo}"
    else:
        candidato = f"{pref}_{corpo}"
    if len(candidato) <= max_len:
        return candidato

    # Sem duplicar sigla se ainda couber
    candidato_sem_sig = f"{pref}_{corpo}"
    if len(candidato_sem_sig) <= max_len and not sig:
        return candidato_sem_sig

    mapa_abrev = {
        "PROFISSIONAL": "PROF",
        "PROFISSIONAIS": "PROF",
        "DEPARTAMENTO": "DEPTO",
        "SECRETARIA": "SEC",
        "ALOCACAO": "ALOC",
        "ATENDIMENTO": "ATEND",
        "FORNECEDOR": "FORN",
        "MOVIMENTACAO": "MOV",
        "PAGAMENTO": "PAG",
        "ORCAMENTO": "ORC",
        "INDICADOR": "IND",
        "ORGANIZACAO": "ORG",
        "CAPACIDADE": "CAPAC",
        "SUSTENTACAO": "SUST",
        "GESTAO": "GS",
        "MENSAL": "MENS",
        "RESUMO": "RES",
        "HISTORICO": "HIST",
        "CONTRATO": "CONTR",
        "UNIDADE": "UNID",
    }
    tokens = [mapa_abrev.get(tok, tok) for tok in corpo.split("_") if tok]
    corpo_abrev = "_".join(tokens)
    if sig and not corpo_abrev.startswith(f"{sig}_") and corpo_abrev != sig:
        cand = f"{pref}_{sig}_{corpo_abrev}"
    else:
        cand = f"{pref}_{corpo_abrev}"
    if len(cand) <= max_len:
        return cand
    return cand[:max_len].rstrip("_")


def _fato_possui_sk_propria(f: dict, nomes_dims: set) -> tuple[bool, str]:
    """
    Verifica se a tabela Fato possui uma coluna de Surrogate Key própria (ex: SK_FATO_*, SK_RESUMO, ID_FATO_*)
    distinta das chaves estrangeiras (FKs) para Dimensões.
    Retorna `(possui_sk_propria: bool, nome_coluna_sk: str)`.
    Quando a Fato possui grão composto apenas pelas FKs de dimensão + chaves degeneradas (como em COPSD),
    retorna `(False, "")` para que não seja referenciada uma `SEQ_FATO_*.NEXTVAL` inexistente.
    """
    cols = f.get("colunas", [])
    if not cols:
        return False, ""
    fks_cols = {fk["coluna"].upper() for fk in identificar_fks_fato(f, nomes_dims)}
    pks = [p.upper() for p in f.get("pks", [])]

    for c in cols:
        cn = c["nome_dw"].upper()
        if cn.startswith(("SK_FATO", "SK_FAT", "ID_FATO", "ID_FAT")):
            return True, cn

    if len(pks) == 1:
        pk0 = pks[0]
        if pk0 not in fks_cols and not pk0.startswith("DIM_"):
            return True, pk0

    c0 = cols[0]["nome_dw"].upper()
    if c0.startswith("SK_") and c0 not in fks_cols:
        # Verificar se c0 aponta para alguma dimensão pelo sufixo
        suf = re.sub(r"^SK_", "", c0)
        aponta_dim = any(
            d_up.endswith(f"_{suf}") or d_up == f"DIM_{suf}" or "TEMPO" in suf
            for d_up in nomes_dims
        )
        if not aponta_dim:
            return True, c0

    return False, ""


def construir_script_controle_carga_eta(
    dims: list,
    fatos: list,
    schema: str,
    projeto: str,
    ts_dat: str,
    ts_idx: str,
) -> str:
    """
    Gera o script `01_tb_controle_carga.sql` com o padrão corporativo completo:
      1) `ETA_ETAPAS_CARGA` (bloco PL/SQL idempotente seguro contra ORA-00955, comentários 100% nas 5 colunas e MERGE INTO das etapas STG/DIM/FATO)
      2) `TB_CONTROLE_CARGA` (telemetria detalhada de execução por lote)
    """
    linhas = [
        "-- =============================================================================",
        f"-- NINHO — 01_tb_controle_carga.sql (PROJETO: {projeto} | SCHEMA: {schema})",
        "-- Padrão Corporativo: ETA_ETAPAS_CARGA (Idempotente ORA-00955 Safe) + TB_CONTROLE_CARGA",
        "-- =============================================================================",
        "",
        "-- 1. Criação idempotente de ETA_ETAPAS_CARGA (Padrão Apache Hop / ODI 12c)",
        "DECLARE",
        "    e_table_exists EXCEPTION;",
        "    PRAGMA EXCEPTION_INIT(e_table_exists, -955);",
        "BEGIN",
        "    EXECUTE IMMEDIATE '",
        f"        CREATE TABLE {schema}.ETA_ETAPAS_CARGA (",
        "            ETA_COD_ETAPA           NUMBER(10)          NOT NULL,",
        "            ETA_DES_ETAPA           VARCHAR2(200 CHAR)  NOT NULL,",
        "            ETA_TABELA_ALVO         VARCHAR2(100 CHAR)  NOT NULL,",
        "            ETA_DATA_ULT_ATUALIZACAO DATE               DEFAULT SYSDATE NOT NULL,",
        "            ETA_STATUS_ULT_EXECUCAO VARCHAR2(30 CHAR)   DEFAULT ''PENDENTE'' NOT NULL,",
        f"            CONSTRAINT PK_ETA_ETAPAS_CARGA PRIMARY KEY (ETA_COD_ETAPA) USING INDEX TABLESPACE {ts_idx}",
        f"        ) TABLESPACE {ts_dat}",
        "    ';",
        "EXCEPTION",
        "    WHEN e_table_exists THEN NULL;",
        "END;",
        "/",
        "",
        f"COMMENT ON TABLE {schema}.ETA_ETAPAS_CARGA IS 'Tabela corporativa de controle de etapas de carga ETL (Apache Hop / ODI 12c). Uma linha representa uma etapa monitorada do pipeline.';",
        f"COMMENT ON COLUMN {schema}.ETA_ETAPAS_CARGA.ETA_COD_ETAPA IS 'Código identificador sequencial da etapa de carga (PK).';",
        f"COMMENT ON COLUMN {schema}.ETA_ETAPAS_CARGA.ETA_DES_ETAPA IS 'Descrição funcional da etapa de extração/transformação/carga.';",
        f"COMMENT ON COLUMN {schema}.ETA_ETAPAS_CARGA.ETA_TABELA_ALVO IS 'Nome físico da tabela alvo (STG_*, DIM_* ou FATO_*) atualizada pela etapa.';",
        f"COMMENT ON COLUMN {schema}.ETA_ETAPAS_CARGA.ETA_DATA_ULT_ATUALIZACAO IS 'Data e hora da última execução bem-sucedida da etapa.';",
        f"COMMENT ON COLUMN {schema}.ETA_ETAPAS_CARGA.ETA_STATUS_ULT_EXECUCAO IS 'Status operacional da última execução (SUCESSO, ERRO, EM_ANDAMENTO, PENDENTE).';",
        "",
    ]

    etapas = []
    cod = 1
    for d in dims:
        dn = d["nome_tabela"].upper()
        if "TEMPO" in dn or "CALENDARIO" in dn:
            continue
        stg_n = re.sub(r"^DIM_", "STG_", dn)
        etapas.append((cod, f"Carga Stage {stg_n}", stg_n))
        cod += 1
        etapas.append((cod, f"Carga Dimensão SCD2 {dn}", dn))
        cod += 1
    for f in fatos:
        fn = f["nome_tabela"].upper()
        stg_f = re.sub(r"^(FATO|FAT)_", "STG_", fn)
        etapas.append((cod, f"Carga Stage {stg_f}", stg_f))
        cod += 1
        etapas.append((cod, f"Carga Tabela Fato {fn}", fn))
        cod += 1

    if etapas:
        linhas.append("-- Registro idempotente das etapas do projeto em ETA_ETAPAS_CARGA")
        for c_etapa, desc_etapa, tab_alvo in etapas:
            linhas.extend([
                f"MERGE INTO {schema}.ETA_ETAPAS_CARGA T",
                f"USING (SELECT {c_etapa} AS COD, '{desc_etapa}' AS DES, '{tab_alvo}' AS ALVO FROM DUAL) S",
                "ON (T.ETA_COD_ETAPA = S.COD)",
                "WHEN NOT MATCHED THEN",
                "    INSERT (ETA_COD_ETAPA, ETA_DES_ETAPA, ETA_TABELA_ALVO, ETA_DATA_ULT_ATUALIZACAO, ETA_STATUS_ULT_EXECUCAO)",
                "    VALUES (S.COD, S.DES, S.ALVO, SYSDATE, 'PENDENTE');",
            ])
        linhas.append("COMMIT;")
        linhas.append("")

    linhas.extend([
        "-- 2. Tabela complementar de telemetria detalhada de lotes (TB_CONTROLE_CARGA)",
        f"CREATE TABLE {schema}.TB_CONTROLE_CARGA (",
        "    COD_CARGA         NUMBER(10)          GENERATED BY DEFAULT AS IDENTITY NOT NULL,",
        f"    SGL_PROJETO       VARCHAR2(50 CHAR)   DEFAULT '{projeto}' NOT NULL,",
        "    NOM_OBJETO_ALVO   VARCHAR2(128 CHAR)  NOT NULL,",
        "    TIP_CAMADA        VARCHAR2(20 CHAR)   NOT NULL,",
        "    DTC_INICIO_CARGA  TIMESTAMP           DEFAULT SYSTIMESTAMP NOT NULL,",
        "    DTC_FIM_CARGA     TIMESTAMP           NULL,",
        "    QTD_LIDOS         NUMBER(15)          DEFAULT 0,",
        "    QTD_INSERIDOS     NUMBER(15)          DEFAULT 0,",
        "    QTD_ATUALIZADOS   NUMBER(15)          DEFAULT 0,",
        "    QTD_REJEITADOS    NUMBER(15)          DEFAULT 0,",
        "    IND_STATUS        VARCHAR2(20 CHAR)   DEFAULT 'EM_ANDAMENTO' NOT NULL,",
        "    DES_MENSAGEM_ERRO VARCHAR2(4000 CHAR) NULL,",
        f"    CONSTRAINT PK_TB_CONTROLE_CARGA PRIMARY KEY (COD_CARGA) USING INDEX TABLESPACE {ts_idx}",
        f") TABLESPACE {ts_dat};",
        "",
        f"COMMENT ON TABLE {schema}.TB_CONTROLE_CARGA IS 'Tabela corporativa de auditoria e telemetria de execução de cargas ETL (STG/DIM/FATO). Uma linha representa uma execução de lote.';",
        "",
    ])
    return "\n".join(linhas)


def _obter_nk_dim(d: dict) -> str:
    sk = _obter_sk_dim(d)
    for c in d.get("colunas", []):
        cn = c["nome_dw"].upper()
        if cn != sk and cn.startswith(("ID_", "COD_", "NUM_", "SIG_")):
            return cn
    for c in d.get("colunas", []):
        cn = c["nome_dw"].upper()
        if cn not in (sk, "VERSION", "DTC_INICIO", "DTC_EFETIVACAO", "DTC_EXPIRACAO", "FLG_ATUAL", "SIN_ATIVO", "DES_ATUALIZAR"):
            return cn
    return sk


def _eh_nk_textual(d: dict, nk_col: str) -> bool:
    """Retorna True se a coluna de Chave Natural (NK) for textual (VARCHAR2/CHAR/CLOB)."""
    nk_up = (nk_col or "").upper()
    for c in d.get("colunas", []):
        if c["nome_dw"].upper() == nk_up:
            tp = c.get("tipo_oracle", "").upper()
            return any(t in tp for t in ("CHAR", "CLOB", "TEXT"))
    return False


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
      1. 03_create_odi_dim_tables.sql (Tabelas auxiliares ODI_DIM_* 100% NULLABLE para Dimension Pattern)
      2. 03_selects_odi_dimensoes.sql (Consultas analíticas SCD2 com UPPER(TRIM(NK)) + ROW_NUMBER + LEAD)
      3. 04_select_odi_fato.sql (Consulta da Fato com LEFT JOIN simétrico nas Dimensões e NVL -1)
    """
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    schema_s = (schema_stg or schema).upper()
    stg_map = {s["nome_tabela"].upper().replace("STG_", ""): s["nome_tabela"].upper() for s in stgs}

    linhas_odi_ddl = [
        "-- =============================================================================",
        f"-- TABELAS AUXILIARES DE PREPARAÇÃO SCD2 DO ODI (ODI_DIM_*) — PROJETO {projeto}",
        f"-- Schema Alvo: {schema} | Gerado em: {agora}",
        "-- Padrão ODI : Utilizadas como 'Armazenamento de Dados de Teste' (STG_DIM_*)",
        "--              no componente nativo de Dimensão (Dimension Pattern / Asterisco).",
        "--              ATENÇÃO: Todas as colunas (inclusive DIMENSION_KEY, DTC_EFETIVACAO",
        "--              e DTC_EXPIRACAO) DEVEM ser NULLABLE e sem PK para evitar ORA-01400",
        "--              na etapa intermediária STG_DIM antes do disparo da Sequence no Target.",
        "-- =============================================================================",
        "",
    ]
    linhas_odi_sel_dim = [
        "-- =============================================================================",
        f"-- CONSULTAS ANALÍTICAS SQL PARA O ODI 12c (CARGA_DIM_* / MAP_001) — PROJETO {projeto}",
        f"-- Schema Alvo: {schema} | Stage Origem: {schema_s} | Gerado em: {agora}",
        "-- Instrução  : No padrão Dimension Pattern (CARGA_DIM_*), aplique UPPER(TRIM(NK))",
        "--              no componente EXPRESSION; ou cole este SELECT na aba Custom SQL.",
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
        nk_textual = _eh_nk_textual(d, nk_col)

        col_defs = []
        cols_negocio = []
        nomes_cols_dim = {c["nome_dw"].upper() for c in d["colunas"]}
        for c in d["colunas"]:
            cname = c["nome_dw"].upper()
            # Remover qualquer DEFAULT / NOT NULL residual para garantir 100% NULLABLE na ODI_DIM_* (evita ORA-01400 no STG_DIM)
            ctype = re.sub(r"\bDEFAULT\s+(?:'[^']*'|[A-Z0-9_]+)\b", "", c["tipo_oracle"], flags=re.IGNORECASE)
            ctype = re.sub(r"\bNOT\s+NULL\b", "", ctype, flags=re.IGNORECASE).strip()
            col_defs.append(f"    {cname:<28} {ctype}")
            if cname not in (sk_col, nk_col) and cname not in cols_scd_controle:
                cols_negocio.append(cname)
        if "DES_STATUS_REGISTRO" not in nomes_cols_dim:
            col_defs.append(f"    {'DES_STATUS_REGISTRO':<28} CHAR(1 CHAR)")

        col_dt_idx = next(
            (c for c in ("DTC_EFETIVACAO", "DTC_INICIO", "DTC_INICIO_VIGENCIA") if c in nomes_cols_dim),
            None,
        )
        clausula_idx_cols = f"{nk_col}, {col_dt_idx} DESC" if col_dt_idx else nk_col

        linhas_odi_ddl.extend([
            f"-- Tabela Auxiliar ODI para {tname} (100% NULLABLE para STG_DIM do Dimension Pattern)",
            f"CREATE TABLE {schema}.{odi_table} (",
            ",\n".join(col_defs),
            ");",
            f"CREATE INDEX {schema}.IDX_{odi_table[:18]}_NK ON {schema}.{odi_table} ({clausula_idx_cols});",
            f"COMMENT ON TABLE {schema}.{odi_table} IS 'Tabela intermediária de stage analítico (Armazenamento de Dados de Teste) do ODI 12c para cálculo de versão e vigência SCD2 de {tname}.';",
            "",
        ])

        expr_nk_stg = f"UPPER(TRIM(S.{nk_col}))" if nk_textual else f"S.{nk_col}"
        sel_cols = ",\n        ".join([f"S.{c}" for c in cols_negocio]) if cols_negocio else f"{expr_nk_stg}"
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
            f"        {expr_nk_stg} AS {nk_col},",
            f"        {sel_cols},",
            "        SYSDATE AS DTC_MOVIMENTO,",
            f"        ROW_NUMBER() OVER (PARTITION BY {expr_nk_stg} ORDER BY {expr_nk_stg}) AS NR_VERSAO,",
            f"        LEAD(SYSDATE, 1) OVER (PARTITION BY {expr_nk_stg} ORDER BY {expr_nk_stg}) AS PROX_DTC_INICIO",
            f"    FROM {schema_s}.{stg_origem} S",
            f"    WHERE {expr_nk_stg} IS NOT NULL",
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
        f"-- CONSULTAS DE RESOLUÇÃO DE SKs PARA TABELAS FATO (CARGA_FATO_*) — PROJETO {projeto}",
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
        tem_sk_fato, sk_fato = _fato_possui_sk_propria(f, nomes_dims_set)
        fks_f_map = {fk["coluna"].upper(): fk["tabela_ref"].upper() for fk in identificar_fks_fato(f, nomes_dims_set)}

        select_parts = []
        join_parts = []
        alias_idx = 1

        for c in f["colunas"]:
            cname = c["nome_dw"].upper()
            if tem_sk_fato and cname == sk_fato and cname not in fks_f_map:
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
                if cname in ("DIM_TEMPO", "SK_TEMPO") or (dim_match and dim_match["nome_tabela"].upper() in ("DIM_TEMPO", "DIM_CALENDARIO", "DIM_DATA")):
                    d_name = dim_match["nome_tabela"].upper() if dim_match else "DIM_TEMPO"
                    d_sk = _obter_sk_dim(dim_match) if dim_match else "DIMENSION_KEY"
                    col_dt_orig = (c.get("nome_original") or "").strip().upper()
                    if not re.match(r"^[A-Z0-9_]+$", col_dt_orig) or col_dt_orig in ("DIM_TEMPO", "SK_TEMPO", "SEQUENCE"):
                        col_dt_orig = next(
                            (
                                col_f["nome_dw"].upper()
                                for col_f in f["colunas"]
                                if col_f["nome_dw"].upper().startswith(("DTC_", "DT_", "DAT_"))
                                or "DATE" in (col_f.get("tipo_oracle") or "").upper()
                            ),
                            "",
                        )
                    expr_dt_stg = f"TRUNC(S.{col_dt_orig})" if col_dt_orig else "TRUNC(SYSDATE)"
                    select_parts.append(f"    NVL({alias}.{d_sk}, -1) AS {cname}")
                    join_parts.append(
                        f"LEFT JOIN {schema}.{d_name} {alias}\n"
                        f"    ON {expr_dt_stg} = {alias}.DTC_COMPLETA"
                    )
                elif dim_match:
                    d_name = dim_match["nome_tabela"].upper()
                    d_sk = _obter_sk_dim(dim_match)
                    d_nk = _obter_nk_dim(dim_match)
                    d_nk_textual = _eh_nk_textual(dim_match, d_nk)
                    cond_join_nk = (
                        f"UPPER(TRIM(S.{d_nk})) = UPPER(TRIM({alias}.{d_nk}))"
                        if d_nk_textual
                        else f"S.{d_nk} = {alias}.{d_nk}"
                    )
                    tem_scd2 = any(col["nome_dw"].upper() in ("DTC_EXPIRACAO", "DTC_FIM_VIGENCIA") for col in dim_match["colunas"])
                    col_exp = "DTC_FIM_VIGENCIA" if any(col["nome_dw"].upper() == "DTC_FIM_VIGENCIA" for col in dim_match["colunas"]) else "DTC_EXPIRACAO"
                    select_parts.append(f"    NVL({alias}.{d_sk}, -1) AS {cname}")
                    if tem_scd2:
                        join_parts.append(
                            f"LEFT JOIN {schema}.{d_name} {alias}\n"
                            f"    ON {cond_join_nk}\n"
                            f"   AND {alias}.{col_exp} IS NULL"
                        )
                    else:
                        join_parts.append(
                            f"LEFT JOIN {schema}.{d_name} {alias}\n"
                            f"    ON {cond_join_nk}"
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
    """
    Gera os guias modulares completos de construção no Canvas do ODI 12c (09_relatorio_estrategias/):
    1. RELATORIO_ESTRATEGIAS.md (auditoria <= 30 chars, Dimension Pattern, diagrama ASCII do pacote PACK_CARGA_* e matriz ok/ko)
    2. guia_estrategias_odi_dim_*.md (5 seções com Atributos de Nível SCD2 coluna por coluna e tabela completa do EXPRESSION com setas brancas)
    3. guia_estrategias_odi_fato_*.md (5 seções com SQL deduplicado RN_DEDUP, comparativo 3 estratégias, Canvas ASCII, Lookups exatos, tabela coluna por coluna da Fato e Generate Inline View = true)
    """
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sigla_odi = derivar_sigla_curta_odi(projeto)
    arquivos = {}

    dims_by_name = {d["nome_tabela"].upper(): d for d in dims}
    nomes_dims_set = set(dims_by_name.keys())
    dim_tempo_nome = "DIM_TEMPO"
    for d in dims:
        dn = d["nome_tabela"].upper()
        if "TEMPO" in dn or "CALENDARIO" in dn:
            dim_tempo_nome = dn
            break

    linhas_conformidade_30 = []
    linhas_tab_dims_resumo = []
    linhas_tab_fatos_resumo = []
    passos_pacote_ascii_dims = []
    passos_pacote_ascii_fatos = []
    matriz_pacote_rows = []
    ordem_pkg = 1

    for d in dims:
        tname = d["nome_tabela"].upper()
        if "TEMPO" in tname or "CALENDARIO" in tname:
            continue
        ent = re.sub(r"^DIM_", "", tname)
        ent_low = ent.lower()
        odi_tname = f"ODI_{tname}"
        seq_tname = f"SEQ_{tname}"
        stg_tname = f"STG_{ent}"
        mapa_dim = f"CARGA_{tname}"
        guia_dim_arq = f"guia_estrategias_odi_dim_{ent_low}.md"

        nk_col = _obter_nk_dim(d)
        sk_col = _obter_sk_dim(d)
        nk_textual = _eh_nk_textual(d, nk_col)
        expr_nk_odi = (
            f"UPPER(TRIM(NVL({stg_tname}.{nk_col}, 'NAO INFORMADO')))"
            if nk_textual
            else f"NVL({stg_tname}.{nk_col}, -1)"
        )

        tgt_ins_nome = f"TGT_INS_{tname}"
        status_30_dim = "✅ OK" if len(tname) <= 22 and len(odi_tname) <= 26 else "⚠️ Revisar Sigla"
        linhas_conformidade_30.append(
            f"| **Dimensão (SCD2)** | `{tname}` | `{len(tname)}` chars | `{tgt_ins_nome}` (`{len(tgt_ins_nome)}` chars) | {status_30_dim} |"
        )
        linhas_conformidade_30.append(
            f"| **Stage Teste ODI** | `{odi_tname}` | `{len(odi_tname)}` chars | `I$_{odi_tname}` (`{len('I$_' + odi_tname)}` chars) | {status_30_dim} |"
        )

        linhas_tab_dims_resumo.append(
            f"| `{schema}.{tname}` | `{schema}.{odi_tname}` | `{schema}.{seq_tname}` | `{mapa_dim}` | [`{guia_dim_arq}`](./{guia_dim_arq}) |"
        )
        passos_pacote_ascii_dims.append(
            f"   │  {ordem_pkg}. [Mapeamento] {mapa_dim:<26} (SCD Tipo 2 via {odi_tname})      │"
        )
        matriz_pacote_rows.append(
            f"| **{ordem_pkg}** | Mapeamento (Dimensão) | `{mapa_dim}` | Passo {ordem_pkg + 1} | Notificar Erro / Abortar | Carrega `{tname}` via *Dimension Pattern* usando `{odi_tname}` como Stage de Teste |"
        )
        ordem_pkg += 1

        # Construir tabelas coluna por coluna da Dimensão (Seção 3.3 e Seção 4.2)
        linhas_atributos_nivel = []
        linhas_expression_dim = []
        for c in d["colunas"]:
            cn = c["nome_dw"].upper()
            tp_c = c.get("tipo_oracle", "VARCHAR2(255)").upper()
            if cn == sk_col:
                linhas_atributos_nivel.append(
                    f"| `{cn}` | **`[x] Marcado`** | `Nenhum` | Chave Substituta (PK incremental gerada pela Sequence `{seq_tname}`) |"
                )
                linhas_expression_dim.append(
                    f"| `{cn}` | *(Não mapear — deixar em branco)* | *(Seta branca)* | O ODI preenche automaticamente via Sequence `{seq_tname}` na etapa física `TGT_INS_{tname}` |"
                )
            elif cn == nk_col:
                linhas_atributos_nivel.append(
                    f"| `{cn}` | `[ ] Desmarcado` | `Nenhum` | Chave Natural (NK) — declarada na grade *Membro da Chave Natural* abaixo |"
                )
                linhas_expression_dim.append(
                    f"| `{cn}` | `{expr_nk_odi}` | `{stg_tname}.{cn}` ➔ `EXPRESSION` ➔ `{tname}` | **Chave Natural (NK)** higienizada (garante simetria 100% com o Lookup da Fato) |"
                )
            elif cn in ("DTC_EFETIVACAO", "DTC_INICIO", "DT_INICIO_VIGENCIA"):
                linhas_atributos_nivel.append(
                    f"| `{cn}` | `[ ] Desmarcado` | **`Data de Início`** | Data de abertura da versão do registro no SCD Tipo 2 |"
                )
                linhas_expression_dim.append(
                    f"| `{cn}` | *(Não mapear — deixar em branco)* | *(Seta branca)* | O ODI preenche automaticamente a data de início da vigência na etapa física |"
                )
            elif cn in ("DTC_EXPIRACAO", "DTC_FIM", "DTC_FIM_VIGENCIA", "DT_FIM_VIGENCIA"):
                linhas_atributos_nivel.append(
                    f"| `{cn}` | `[ ] Desmarcado` | **`Data Final`** | Data de fechamento da versão anterior (fica `NULL` na versão ativa) |"
                )
                linhas_expression_dim.append(
                    f"| `{cn}` | *(Não mapear — deixar em branco)* | *(Seta branca)* | O ODI controla o fechamento (`SYSDATE`) automaticamente na etapa física `TGT_CLS_` |"
                )
            elif cn in ("SIN_ATIVO", "FLG_ATIVO", "IND_ATIVO", "FLG_ATUAL"):
                linhas_atributos_nivel.append(
                    f"| `{cn}` | `[ ] Desmarcado` | **`Histórico de Triggers`** | Flag de versão ativa (`'S'` vigente / `'N'` histórico fechado) |"
                )
                linhas_expression_dim.append(
                    f"| `{cn}` | `'S'` | `EXPRESSION` ➔ `{tname}` | Literal fixo indicando registro ativo na entrada |"
                )
            elif cn == "DES_ATUALIZAR":
                linhas_atributos_nivel.append(
                    f"| `{cn}` | `[ ] Desmarcado` | **`Histórico de Triggers`** | Atributo de controle operacional do padrão corporativo |"
                )
                linhas_expression_dim.append(
                    f"| `{cn}` | `'S'` | `EXPRESSION` ➔ `{tname}` | Literal fixo de controle operacional |"
                )
            else:
                eh_num = any(k in tp_c for k in ("NUMBER", "INT", "DECIMAL", "FLOAT")) and not cn.startswith(("DES_", "NOM_", "SIG_"))
                eh_dt = "DATE" in tp_c or "TIMESTAMP" in tp_c or cn.startswith(("DTC_", "DT_", "DAT_"))
                if eh_num:
                    expr_col = f"NVL({stg_tname}.{cn}, 0)"
                elif eh_dt:
                    expr_col = f"{stg_tname}.{cn}"
                else:
                    expr_col = f"UPPER(TRIM(NVL({stg_tname}.{cn}, 'NAO INFORMADO')))"
                linhas_atributos_nivel.append(
                    f"| `{cn}` | `[ ] Desmarcado` | **`Histórico de Triggers`** | Se `{cn}` mudar na origem, o ODI fecha a versão antiga e abre uma nova linha vigente *(use `Nenhum` se preferir apenas sobrescrever sem versionar)* |"
                )
                linhas_expression_dim.append(
                    f"| `{cn}` | `{expr_col}` | `{stg_tname}.{cn}` ➔ `EXPRESSION` ➔ `{tname}` | Atributo descritivo de negócio higienizado |"
                )

        guia_dim = [
            f"# 🛠️ Guia Passo a Passo no ODI 12c: Dimensão `{tname}` (Padrão Nativo `Dimension Pattern`)",
            "",
            f"> **Projeto:** `{projeto}` (`{sigla_odi}`) | **Schema:** `{schema}` | **Tabela Alvo:** `{tname}` (`{len(tname)}` chars) | **Tabela Auxiliar (Teste):** `{odi_tname}` (`{len(odi_tname)}` chars)",
            "",
            "Este guia documenta passo a passo como configurar o objeto Dimensão **`" + tname + "`** (em *Dimensões e Cubos*) e o seu **Mapa Único (`" + mapa_dim + "`)** no Oracle Data Integrator (ODI 12c), seguindo o padrão corporativo PRODEB.",
            "",
            "---",
            "",
            "## 1. Visão Geral da Arquitetura Nativa (`Dimension Pattern` / Mapa Único)",
            "",
            "No ODI 12c, você **não precisa criar dois mapas manuais** para a dimensão. Ao cadastrar `" + tname + "` em **Dimensões e Cubos** com o padrão `Dimension Pattern` (`Asterisco`) e apontar o **Armazenamento de Dados de Teste** para `" + schema + "." + odi_tname + "`, você desenha apenas um mapa lógico simples e o próprio ODI gera toda a árvore física de SCD Tipo 2:",
            "",
            "```text",
            f"  [ABA LÓGICO DO MAPA: {mapa_dim}]",
            "",
            "  +-----------------------+       +----------------+       +-------------------------------+",
            f"  | {stg_tname:<21} | ----> |   EXPRESSION   | ----> | {tname:<29} |",
            f"  | (Datastore Stage)     |       | (Padronização) |       | (Componente Dimensão - Nível) |",
            "  +-----------------------+       +----------------+       +-------------------------------+",
            "",
            "  ==========================================================================================",
            "  [ABA FÍSICO — EXPANSÃO AUTOMÁTICA PELO DIMENSION PATTERN DO ODI 12c]",
            "",
            "  EXPRESSION ──► DEDUP_EXPR ──► DEDUP_FLTR ──► FLTR_SRC ──► STG_" + tname[:18] + " (Grava em " + odi_tname + ")",
            "                                                                  │",
            "                                                                  ▼",
            "                                                            SCD2_SRC_" + tname[:15] + " ──► EXTRACT_",
            "                                                                                      │",
            "                                                                                      ▼",
            "                                                                                   LKP_CURR (Compara com " + tname + ")",
            "                                                                                      │",
            "                                                                                      ▼",
            "                                                                                    SPLIT",
            "                                                        ┌─────────────────────────────┼─────────────────────────────┐",
            "                                                        ▼                             ▼                             ▼",
            f"                                              TGT_INS_{tname:<16}      TGT_CLS_{tname:<16}      TGT_UPD_{tname:<16}",
            "                                              (Insere Novos / Nova Versão)  (Fecha Versão Antiga)         (Atualiza Sem Mudança SCD2)",
            "```",
            "",
            "---",
            "",
            "## 2. Pré-Requisitos no Oracle (Já Contemplados nos Scripts DDL)",
            "",
            f"1. **Tabela Física da Dimensão (`{schema}.{tname}` — `{len(tname)} caracteres`):** Criada em `02_create_dimensions.sql` com `{sk_col}` (`NOT NULL`), `{nk_col}`, atributos descritivos e colunas de vigência SCD2 (`SIN_ATIVO`, `DTC_EFETIVACAO`, `DTC_EXPIRACAO`, `DES_ATUALIZAR`).",
            f"2. **Tabela Auxiliar de Stage/Teste (`{schema}.{odi_tname}` — `{len(odi_tname)} caracteres`):** Criada em `03_create_odi_dim_tables.sql` com a **mesma estrutura de colunas** da `{tname}`, porém **100% NULLABLE e sem Constraint de PK**.",
            f"   * *Por que `100% NULLABLE`?* Porque na etapa física `STG_{tname}`, o ODI grava em `{odi_tname}` apenas os atributos vindos da `EXPRESSION` (deixando `{sk_col}`, `DTC_EFETIVACAO` e `DTC_EXPIRACAO` com `NULL` até a etapa final `TGT_INS_{tname}`). Se houvesse `NOT NULL` na tabela `ODI_DIM_*`, o mapa abortaria com `ORA-01400`.",
            f"3. **Sequence (`{schema}.{seq_tname}` — `{len(seq_tname)} caracteres`):** Criada em `01_create_sequences.sql` (`START WITH 1 INCREMENT BY 1 CACHE 1000 NOORDER NOCYCLE`).",
            "",
            "---",
            "",
            f"## 3. Passo 1 — Configurar o Objeto `{tname}` em *Dimensões e Cubos*",
            "",
            f"No **ODI Studio** ➔ aba **Designer** ➔ **Projetos** ➔ sua pasta ➔ **Dimensões e Cubos**, crie (ou edite) a dimensão **`{tname}`**:",
            "",
            "### 3.1 Aba `Definição`",
            "",
            "| Propriedade no ODI Studio | Valor Exato a Configurar |",
            "| :--- | :--- |",
            f"| **Nome** | `{tname}` |",
            "| **Tipo de Implementação** | **`Asterisco`** (com `[x] Usar Padrão` marcado) |",
            "| **Nome do Padrão** | `Dimension Pattern` |",
            f"| **Binding > Armazenamento de dados** | `{schema}.{tname}` |",
            f"| **Binding > Sequência de Chave Substituta** | `{seq_tname}` |",
            "",
            "### 3.2 Aba `Níveis` (Tabela Superior `Níveis`)",
            "",
            "| Nome | Rótulo | Descrição | Armazenamento de dados | Armazenamento de Dados de Teste |",
            "| :--- | :--- | :--- | :--- | :--- |",
            f"| `{ent}` | `{ent}` | `{ent}` | `{schema}.{tname}` | **`{schema}.{odi_tname}`** |",
            "",
            "> [!TIP]",
            f"> O campo **Armazenamento de Dados de Teste** (`{schema}.{odi_tname}`) é o segredo que faz o ODI usar a tabela `ODI_DIM_*` automaticamente como *staging* intermediária da dimensão!",
            "",
            "### 3.3 Aba `Níveis` ➔ Grade Inferior `Atributos de Nível` (Regra SCD Tipo 2 Coluna por Coluna)",
            "",
            f"Com o nível `{ent}` selecionado, configure cada atributo exatamente como na tabela abaixo:",
            "",
            "| Nome do Atributo | Chave Substituta | Definição do Tipo 2 (SCD2) | Papel no Motor SCD2 do ODI |",
            "| :--- | :---: | :--- | :--- |",
            *linhas_atributos_nivel,
            "",
            "### 3.4 Aba `Níveis` ➔ Grade `Membro da Chave Natural do Nível`",
            "",
            "Logo abaixo de *Atributos de Nível*, na grade **Membro da Chave Natural do Nível**, clique no ícone **`+`** e adicione:",
            f"* **`{ent}.{nk_col}`** *(É por esta coluna que o componente `LKP_CURR` do ODI identifica se o registro já existe na dimensão).* ",
            "",
            "### 3.5 Aba `Hierarquias`",
            "",
            f"* Mantenha a hierarquia `DEFAULT` contendo o nível `{ent}`.",
            "",
            "---",
            "",
            f"## 4. Passo 2 — Construir o Mapa Único `{mapa_dim}`",
            "",
            f"Em **Projetos** ➔ sua pasta ➔ **Mapeamentos**, crie o mapeamento **`{mapa_dim}`**:",
            "",
            "### 4.1 Montagem na Aba `Lógico`",
            "",
            f"1. Arraste o datastore de origem **`{stg_tname}`** (do Modelo `{schema}`) para o Canvas.",
            "2. Da paleta de Componentes, arraste um componente **`EXPRESSION`** para o meio do Canvas.",
            f"3. Da árvore **Dimensões e Cubos**, arraste o componente de Dimensão **`{tname}`** para a direita do Canvas.",
            f"4. Conecte a saída de `{stg_tname}` na entrada de `EXPRESSION`, e a saída de `EXPRESSION` no conector de nível `{tname}.{ent}`.",
            "",
            "### 4.2 Tabela Completa de Atributos dentro do `EXPRESSION` (Coluna por Coluna)",
            "",
            f"Selecione o componente `EXPRESSION` (ou o alvo `{tname}`) e configure as expressões abaixo. **Atenção especial às 3 colunas que NÃO devem ser mapeadas (devem ficar com a seta branca no alvo):**",
            "",
            f"| Atributo na Dimensão Alvo (`{tname}`) | Expressão no Componente `EXPRESSION` | Ligação no Canvas | Observação Técnica |",
            "| :--- | :--- | :---: | :--- |",
            *linhas_expression_dim,
            "",
            "> [!WARNING]",
            f"> **Regra de Ouro das Setas Brancas:** No componente alvo `{tname}` da aba **Lógico**, os atributos **`{sk_col}`**, **`DTC_EFETIVACAO`** e **`DTC_EXPIRACAO`** devem permanecer com o ícone de **seta branca (sem ligação vinda da `EXPRESSION`)**. O *Dimension Pattern* do ODI injeta `SEQ_{tname}.NEXTVAL` e `SYSDATE` automaticamente na aba **Físico**!",
            "",
            "### 4.3 Conferência na Aba `Físico`",
            "",
            f"Ao clicar na aba **Físico** do mapeamento `{mapa_dim}`, verifique:",
            f"1. **`DEDUP_EXPR` + `DEDUP_FLTR`:** O ODI cria automaticamente um `ROW_NUMBER()` particionado por `{nk_col}` para descartar duplicatas vindas da `{stg_tname}`.",
            f"2. **`STG_{tname}` (`{schema}.{odi_tname}`):** O ODI faz `TRUNCATE` e insere a carga deduplicada na tabela auxiliar `{odi_tname}`.",
            f"3. **`LKP_CURR`:** Faz lookup com as linhas vigentes da `{schema}.{tname}`.",
            "4. **`SPLIT`:** Divide o fluxo em 3 destinos físicos na tabela final:",
            f"   * **`TGT_INS_{tname}`:** Insere registros novos (e novas versões de registros que mudaram de atributo `Histórico de Triggers`), acionando `{seq_tname}.NEXTVAL`.",
            f"   * **`TGT_CLS_{tname}`:** Fecha a vigência (`DTC_EXPIRACAO = SYSDATE`, `SIN_ATIVO = 'N'`) da versão anterior.",
            f"   * **`TGT_UPD_{tname}`:** Atualiza atributos caso configurado sem abertura de versão.",
            "",
            "---",
            "",
            "## 5. Passo 3 — Linha Default `-1` e Inclusão no Pacote",
            "",
            f"1. **Garantia da Linha Sentinela (`-1`):** Certifique-se de que o script `06_init_default_records.sql` (ou a Procedure `TRT_GARANTIR_LINHA_DEFAULT_DIM`) foi executado para manter `{sk_col} = -1` (`'Não Informado'`) em `{schema}.{tname}`.",
            f"2. **Orquestração no Pacote (`PACK_CARGA_{sigla_odi}_DW`):** Arraste o mapeamento `{mapa_dim}` para a **Fase 1 (Carga de Dimensões)** do pacote, sempre **antes** dos mapeamentos das tabelas Fato.",
            "",
            "---",
            "",
            "## 📎 Apêndice Opcional — Padrão Tabular em 2 Mapas (`MAP_001` / `MAP_002`)",
            "",
            "Caso em algum cenário específico opte por mapeamentos tabulares tradicionais sem usar o objeto *Dimensões e Cubos*:",
            f"- **Procedure `TRT_TRUNC_{odi_tname}`:** `TRUNCATE TABLE {schema}.{odi_tname}`",
            f"- **Mapping `MAP_001_{odi_tname}` (`{stg_tname}` ➔ `{odi_tname}`):** utilize o SQL de `03_selects_odi_dimensoes.sql` com `IKM Oracle Insert` (`APPEND`).",
            f"- **Mapping `MAP_002_{tname}` (`{odi_tname}` ➔ `{tname}`):** Update Key `({nk_col}, DTC_EFETIVACAO)`, Sequence `:{seq_tname}.NEXTVAL` no *Target* e `IKM Oracle Incremental Update (MERGE)`.",
            "",
        ]
        arquivos[guia_dim_arq] = "\n".join(guia_dim)

    # Passo intermediário no pacote: Garantir linha default -1
    passos_pacote_ascii_dims.append(
        f"   │  {ordem_pkg}. [Procedure ] TRT_GARANTIR_LINHA_DEFAULT_DIM  (MERGE INTO SK = -1 nas DIMs) │"
    )
    matriz_pacote_rows.append(
        f"| **{ordem_pkg}** | Procedure Oracle | `TRT_GARANTIR_LINHA_DEFAULT_DIM` | Passo {ordem_pkg + 1} | Notificar Erro / Abortar | Garante idempotentemente o registro sentinela `DIMENSION_KEY = -1` em todas as dimensões |"
    )
    ordem_pkg += 1

    # Construir guias completos das Tabelas Fato
    dim_by_key = {}
    for d in dims:
        ent_k = re.sub(r"^DIM_", "", d["nome_tabela"].upper())
        dim_by_key[ent_k] = d

    for f in fatos:
        fname = f["nome_tabela"].upper()
        ent_f = re.sub(r"^(FATO_|FAT_)", "", fname)
        ent_f_low = ent_f.lower()
        stg_fato = f"STG_{ent_f}"
        seq_fato = f"SEQ_{fname}"
        mapa_fato = f"MAP_{fname}"
        guia_fato_arq = f"guia_estrategias_odi_fato_{ent_f_low}.md"
        ikm_fato = (
            "IKM Oracle Insert (TRUNCATE + APPEND)"
            if estrategia.upper() == "A"
            else "IKM Oracle Incremental Update (MERGE)"
        )
        desc_estrat_fato = (
            "Estratégia A — Carga Full / Janela (`PRC_PRE_CARGA_FATO` + `APPEND` + `PRC_POS_CARGA_FATO`)"
            if estrategia.upper() == "A"
            else "Estratégia B — Carga Incremental (`ROW_NUMBER` Dedup + Lookups Vigentes + `MERGE`)"
        )

        status_30_fato = "✅ OK" if len(fname) <= 26 else "⚠️ Revisar Sigla"
        linhas_conformidade_30.append(
            f"| **Tabela Fato** | `{fname}` | `{len(fname)}` chars | `I$_{fname}` (`{len('I$_' + fname)}` chars) | {status_30_fato} |"
        )
        linhas_tab_fatos_resumo.append(
            f"| `{schema}.{fname}` | `{mapa_fato}` | {desc_estrat_fato} | [`{guia_fato_arq}`](./{guia_fato_arq}) |"
        )

        if estrategia.upper() == "A":
            passos_pacote_ascii_fatos.append(
                f"   │  {ordem_pkg}. [Procedure ] PRC_PRE_CARGA_FATO('{fname}', 'S')  (TRUNCATE + UNUSABLE) │"
            )
            matriz_pacote_rows.append(
                f"| **{ordem_pkg}** | Procedure Oracle | `PRC_PRE_CARGA_FATO('{fname}', 'S')` | Passo {ordem_pkg + 1} | Notificar Erro / Abortar | Trunca `{fname}` e marca Bitmap Indexes como `UNUSABLE` antes da carga |"
            )
            ordem_pkg += 1

        passos_pacote_ascii_fatos.append(
            f"   │  {ordem_pkg}. [Mapeamento] {mapa_fato:<32} (Lookups + NVL -1)     │"
        )
        matriz_pacote_rows.append(
            f"| **{ordem_pkg}** | Mapeamento (Fato) | `{mapa_fato}` | Passo {ordem_pkg + 1} | Notificar Erro / Abortar | Carrega `{fname}` resolvendo SKs nas dimensões vigentes (`DTC_EXPIRACAO IS NULL`) com fallback `-1` |"
        )
        ordem_pkg += 1

        passos_pacote_ascii_fatos.append(
            f"   │  {ordem_pkg}. [Procedure ] PRC_POS_CARGA_FATO('{fname}')       (REBUILD + STATS)   │"
        )
        prox_txt = f"Passo {ordem_pkg + 1}"
        matriz_pacote_rows.append(
            f"| **{ordem_pkg}** | Procedure Oracle | `PRC_POS_CARGA_FATO('{fname}')` | {prox_txt} | Notificar Erro / Abortar | Reconstrói índices `UNUSABLE` com `NOLOGGING` e coleta estatísticas `DBMS_STATS` |"
        )
        ordem_pkg += 1

        # Inspecionar todas as colunas e FKs da Fato para montar:
        # 1) SQL completo com STG_DEDUP (RN_DEDUP = 1)
        # 2) Lista de Lookups passo a passo
        # 3) Tabela numerada coluna por coluna da Fato
        tem_sk_fato, sk_fato = _fato_possui_sk_propria(f, nomes_dims_set)
        fks_f_map = {fk["coluna"].upper(): fk["tabela_ref"].upper() for fk in identificar_fks_fato(f, nomes_dims_set)}

        if tem_sk_fato:
            select_sql_parts = [f"    {schema}.{seq_fato}.NEXTVAL AS {sk_fato}"]
            tabela_cols_passo4 = [
                f"| 1 | `{sk_fato}` | `{schema}.{seq_fato}.NEXTVAL` *(Executar no Hint: **Destino / Target**)* | `NUMBER(10)` | **Não** (PK gerada no INSERT) |"
            ]
            num_col_idx = 2
            target_canvas_note = f"{seq_fato}.NEXTVAL + NVL(LKP.DIMENSION_KEY, -1)"
            chk_sk_line = f"- [ ] A coluna `{sk_fato}` está configurada com `{schema}.{seq_fato}.NEXTVAL` para executar no **Target (Destino)** e está **desmarcada** como *Update Key* (`UK`)."
        else:
            select_sql_parts = []
            tabela_cols_passo4 = []
            num_col_idx = 1
            target_canvas_note = "Grão Composto pelas FKs (UK no MERGE) + NVL(LKP.DIMENSION_KEY, -1)"
            chk_sk_line = "- [ ] O grão da Fato é composto pelas chaves estrangeiras (`FKs` marcadas como `UK` no `IKM MERGE`), sem necessidade de Sequence própria na Fato."

        join_sql_parts = []
        lookups_passo3 = []
        ascii_lkps_names = []
        nks_partition = []
        alias_idx = 1

        for c in f["colunas"]:
            cname = c["nome_dw"].upper()
            tp_c = c.get("tipo_oracle", "NUMBER").upper()
            if tem_sk_fato and cname == sk_fato and cname not in fks_f_map:
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
                    d_nk_textual = _eh_nk_textual(dim_match, d_nk)
                    is_tempo_d = "TEMPO" in d_name or "CALENDARIO" in d_name or "TEMPO" in cname
                    lkp_comp_name = f"LKP_{d_name}"
                    ascii_lkps_names.append(f"{lkp_comp_name} ({d_name})")
                    if d_nk not in nks_partition:
                        nks_partition.append(f"UPPER(TRIM({d_nk}))" if d_nk_textual else d_nk)

                    if is_tempo_d:
                        cond_join_nk = f"TRUNC(S.{d_nk}) = {alias}.{d_nk}" if "DT" in d_nk or "DAT" in d_nk else f"S.{d_nk} = {alias}.{d_nk}"
                        cond_lkp_odi = f"TRUNC(FLT_RN_IGUAL_1.{d_nk}) = {lkp_comp_name}.{d_nk}"
                    elif d_nk_textual:
                        cond_join_nk = f"UPPER(TRIM(S.{d_nk})) = UPPER(TRIM({alias}.{d_nk}))"
                        cond_lkp_odi = f"UPPER(TRIM(FLT_RN_IGUAL_1.{d_nk})) = UPPER(TRIM({lkp_comp_name}.{d_nk}))"
                    else:
                        cond_join_nk = f"S.{d_nk} = {alias}.{d_nk}"
                        cond_lkp_odi = f"FLT_RN_IGUAL_1.{d_nk} = {lkp_comp_name}.{d_nk}"

                    tem_scd2 = any(col["nome_dw"].upper() in ("DTC_EXPIRACAO", "DTC_FIM_VIGENCIA") for col in dim_match["colunas"])
                    col_exp = "DTC_FIM_VIGENCIA" if any(col["nome_dw"].upper() == "DTC_FIM_VIGENCIA" for col in dim_match["colunas"]) else "DTC_EXPIRACAO"

                    select_sql_parts.append(f"    NVL({alias}.{d_sk}, -1) AS {cname}")
                    if tem_scd2 and not is_tempo_d:
                        join_sql_parts.append(
                            f"LEFT JOIN {schema}.{d_name} {alias}\n"
                            f"    ON {cond_join_nk}\n"
                            f"   AND {alias}.{col_exp} IS NULL"
                        )
                        cond_lkp_full = f"{cond_lkp_odi} AND {lkp_comp_name}.{col_exp} IS NULL"
                    else:
                        join_sql_parts.append(
                            f"LEFT JOIN {schema}.{d_name} {alias}\n"
                            f"    ON {cond_join_nk}"
                        )
                        cond_lkp_full = cond_lkp_odi

                    lookups_passo3.append(
                        f"{len(lookups_passo3) + 1}. **`{lkp_comp_name}`** (Tabela `{schema}.{d_name}` para preencher `{cname}`):\n"
                        f"   * **Tipo de Lookup no ODI:** *Left Outer Join* (ou *SQL Expression no Lookup* com Valor Padrão `-1`).\n"
                        f"   * **Condição de Lookup Exata:**\n"
                        f"     ```sql\n"
                        f"     {cond_lkp_full}\n"
                        f"     ```"
                    )
                    tabela_cols_passo4.append(
                        f"| {num_col_idx} | `{cname}` | `NVL({lkp_comp_name}.{d_sk}, -1)` | `{tp_c}` | **Sim (UK)** |"
                    )
                else:
                    select_sql_parts.append(f"    NVL(S.{cname}, -1) AS {cname}")
                    tabela_cols_passo4.append(
                        f"| {num_col_idx} | `{cname}` | `NVL(FLT_RN_IGUAL_1.{cname}, -1)` | `{tp_c}` | **Sim (UK)** |"
                    )
            elif cname.startswith(("VLR_", "VAL_", "QTD_", "QTDE_", "NUM_", "PER_", "PRC_")):
                select_sql_parts.append(f"    NVL(S.{cname}, 0) AS {cname}")
                tabela_cols_passo4.append(
                    f"| {num_col_idx} | `{cname}` | `NVL(FLT_RN_IGUAL_1.{cname}, 0)` | `{tp_c}` | Não (Métrica) |"
                )
            elif cname in ("DTC_CARGA", "DT_CARGA"):
                select_sql_parts.append(f"    SYSDATE AS {cname}")
                tabela_cols_passo4.append(
                    f"| {num_col_idx} | `{cname}` | `SYSDATE` | `DATE` | Não (Auditoria) |"
                )
            else:
                select_sql_parts.append(f"    S.{cname} AS {cname}")
                tabela_cols_passo4.append(
                    f"| {num_col_idx} | `{cname}` | `FLT_RN_IGUAL_1.{cname}` | `{tp_c}` | Não (Atributo Degenerado/Flag) |"
                )
            num_col_idx += 1

        part_by_expr = ", ".join(nks_partition[:4]) if nks_partition else "1"
        lkps_ascii_block = "\n".join(f"                         ├──► [ {ln:<32} ]" for ln in ascii_lkps_names) if ascii_lkps_names else "                         ├──► [ LKP_DIM_* ]"
        joins_sql_txt = ("\n" + "\n".join(join_sql_parts)) if join_sql_parts else ""
        lookups_passo3_txt = "\n".join(lookups_passo3) if lookups_passo3 else "1. Configure os componentes `LOOKUP` conectando `FLT_RN_IGUAL_1` às dimensões correspondentes."

        guia_fato = [
            f"# 🛠️ Guia Passo a Passo no ODI 12c: Tabela Fato `{fname}`",
            "",
            f"> **Projeto:** `{projeto}` (`{sigla_odi}`) | **Schema:** `{schema}` | **Tabela Alvo:** `{fname}` (`{len(fname)}` chars) | **Estratégia:** `{estrategia.upper()}`",
            "",
            f"Este documento apresenta a consulta SQL completa de carga da tabela fato **`{schema}.{fname}`** a partir da stage **`{schema}.{stg_fato}`**, seguida do passo a passo detalhado de construção no Canvas do **Oracle Data Integrator (ODI 12c)**.",
            "",
            "---",
            "",
            "## 1. A Consulta SQL Alvo Completa (`04_select_odi_fato.sql`)",
            "",
            "A consulta abaixo realiza:",
            f"1. **Deduplicação na Stage (`STG_DEDUP`)** via `ROW_NUMBER() OVER (PARTITION BY ...)` (`RN_DEDUP = 1`) para blindar o `MERGE`/`INSERT` contra o erro `ORA-30926: unable to get a stable set of rows in the source tables`.",
            "2. **Resolução de Surrogate Keys (`SKs`)** via `LEFT JOIN` nas versões vigentes das dimensões (`DTC_EXPIRACAO IS NULL`) usando simetria exata `UPPER(TRIM(...))`.",
            "3. **Tratamento de Órfãos (`NVL(..., -1)`)** para qualquer dimensão não localizada ou não aplicável, garantindo perda **zero** de registros na Fato.",
            "",
            "```sql",
            "SELECT",
            ",\n".join(select_sql_parts),
            "FROM (",
            "    SELECT",
            "        STG.*,",
            "        ROW_NUMBER() OVER (",
            f"            PARTITION BY {part_by_expr}",
            "            ORDER BY ROWID DESC",
            "        ) AS RN_DEDUP",
            f"    FROM {schema}.{stg_fato} STG",
            f") S{joins_sql_txt}",
            "WHERE S.RN_DEDUP = 1;",
            "```",
            "",
            "---",
            "",
            "## 2. Comparativo das 3 Estratégias de Implementação no ODI 12c",
            "",
            "| Critério | Estratégia 1: View no Banco (`VW_ODI_FATO_*`) | Estratégia 2: Mapeamento 100% Visual no Canvas (Recomendada) | Estratégia 3: *Custom SQL Override* no ODI |",
            "| :--- | :--- | :--- | :--- |",
            "| **Como Funciona** | Cria-se uma View no Oracle com o SQL da Seção 1 e o ODI faz `1:1` da View para a Fato. | Usa `EXPRESSION` (`RN_DEDUP` com *Inline View*) + `FILTER` + componentes `LOOKUP` nativos no Canvas. | Cola-se o SQL da Seção 1 na propriedade *Custom SQL* do Datastore temporário no ODI. |",
            "| **Rastreabilidade (Lineage)** | Média (lógica fica no banco Oracle). | **Alta (100% documentada visualmente no ODI Studio).** | Baixa (caixa-preta textual dentro do mapa). |",
            "| **Manutenção** | Simples via DDL SQL. | Padrão oficial de fábrica PRODEB. | Exige cuidado ao alterar colunas da tabela. |",
            "",
            "---",
            "",
            f"## 3. Passo a Passo Completo — Construção no Canvas Lógico (`{mapa_fato}`)",
            "",
            "### 3.1 Desenho Arquitetural no Canvas Lógico",
            "",
            "```text",
            f" [ {stg_fato} ]",
            "        │",
            "        ▼",
            " [ EXPR_RN_DEDUP ]  (Calcula RN_DEDUP = ROW_NUMBER() OVER (...) | Marcar [x] Generate Inline View na aba Physical!)",
            "        │",
            "        ▼",
            " [ FLT_RN_IGUAL_1 ] (Filtro: EXPR_RN_DEDUP.RN_DEDUP = 1)",
            "        │",
            f"{lkps_ascii_block}",
            "                         │",
            "                         ▼",
            f"                 [ {fname} ] (Target: {target_canvas_note})",
            "```",
            "",
            "### 3.2 Instruções Passo a Passo no ODI Studio",
            "",
            f"#### Passo 1: Criar o Mapeamento (`{mapa_fato}`)",
            f"1. Em **Projetos** ➔ sua pasta ➔ **Mapeamentos**, clique com o botão direito e selecione **Novo Mapeamento**: `{mapa_fato}`.",
            f"2. Arraste o datastore de origem **`{schema}.{stg_fato}`** para a esquerda do Canvas e a tabela fato alvo **`{schema}.{fname}`** para a direita.",
            "",
            "#### Passo 2: Deduplicar a Stage (`EXPR_RN_DEDUP` + `FLT_RN_IGUAL_1`)",
            f"1. Arraste um componente **`EXPRESSION`** (`EXPR_RN_DEDUP`) logo após `{stg_fato}`.",
            "2. Passe todas as colunas da Stage para frente e adicione um atributo extra chamado **`RN_DEDUP`** (`NUMERIC(10)`) com a expressão:",
            "   ```sql",
            f"   ROW_NUMBER() OVER (PARTITION BY {part_by_expr} ORDER BY ROWID DESC)",
            "   ```",
            "3. Arraste um componente **`FILTER`** (`FLT_RN_IGUAL_1`) após `EXPR_RN_DEDUP` com a condição:",
            "   ```sql",
            "   EXPR_RN_DEDUP.RN_DEDUP = 1",
            "   ```",
            "",
            "#### Passo 3: Configurar os Lookups / Left Joins Dimensionais",
            "Adicione um componente **`LOOKUP`** (ou **`JOIN`** configurado como *Left Outer Join*) para cada dimensão ligada à Fato:",
            "",
            lookups_passo3_txt,
            "",
            f"#### Passo 4: Mapeamento Completo de Todas as Colunas na Tabela Alvo (`{fname}`)",
            f"Clique na tabela alvo **`{fname}`** e preencha o painel de propriedades de cada coluna exatamente como na tabela abaixo:",
            "",
            "| # | Coluna Destino (`" + fname + "`) | Expressão no ODI (Target / Mapping) | Tipo Oracle | Chave (`UK`) no MERGE |",
            "| :---: | :--- | :--- | :--- | :---: |",
            *tabela_cols_passo4,
            "",
            "---",
            "",
            "## 4. Configurações Físicas e Performance (Aba *Physical*)",
            "",
            "1. ** Dica de Ouro contra `ORA-30483: window functions are not allowed here`:**",
            "   * O Oracle não permite funções analíticas (`ROW_NUMBER() OVER ...`) diretamente dentro de cláusulas `WHERE`. Para que o ODI gere uma subquery (`SELECT * FROM (SELECT ..., ROW_NUMBER() ...)`), clique na aba **Físico (`Physical`)** do mapeamento, selecione o nó **`EXPR_RN_DEDUP`** e, no painel de propriedades, marque a caixa **`[x] Generate Inline View`**.",
            f"2. **Escolha do IKM no Alvo `{fname}`:**",
            f"   * **Módulo de Conhecimento de Integração (IKM):** `{ikm_fato}`.",
            "   * **`FLOW_CONTROL`:** `FALSE` (evita criação de tabela `E$_` desnecessária quando as FKs já estão protegidas por `NVL(..., -1)`).",
            "   * **`COMMIT_INTERVAL`:** `100000`.",
            "3. **Procedures de Manutenção de Índices Bitmap (`PRC_PRE_CARGA_FATO` e `PRC_POS_CARGA_FATO`):**",
            f"   * Em cargas de grande volume, chame `BEGIN {schema}.PRC_PRE_CARGA_FATO('{fname}', '{'S' if estrategia.upper() == 'A' else 'N'}'); END;` antes do mapa e `BEGIN {schema}.PRC_POS_CARGA_FATO('{fname}'); END;` imediatamente após o mapa.",
            "",
            "---",
            "",
            "## 5. Checklist Rápido Pré-Execução",
            "",
            f"- [ ] Todas as dimensões referenciadas pela `{fname}` já foram carregadas na Fase 1 do pacote e possuem a linha default `DIMENSION_KEY = -1`.",
            "- [ ] A propriedade **`[x] Generate Inline View`** está marcada no componente `EXPR_RN_DEDUP` na aba **Physical**.",
            chk_sk_line,
            "- [ ] Todas as chaves estrangeiras (`FKs`) possuem fallback `NVL(..., -1)` e todos os Lookups em dimensões SCD2 filtram `DTC_EXPIRACAO IS NULL`.",
            "",
        ]
        arquivos[guia_fato_arq] = "\n".join(guia_fato)

    # Fechar a última linha da matriz do pacote com "Fim do Pacote (Sucesso)"
    if matriz_pacote_rows:
        matriz_pacote_rows[-1] = re.sub(
            r"\| Passo \d+ \|",
            "| **Fim do Pacote (Sucesso)** |",
            matriz_pacote_rows[-1],
        )

    ascii_dims_txt = "\n".join(passos_pacote_ascii_dims) if passos_pacote_ascii_dims else "   │  (Sem dimensões SCD2 adicionais)                                       │"
    ascii_fatos_txt = "\n".join(passos_pacote_ascii_fatos) if passos_pacote_ascii_fatos else "   │  (Sem tabelas Fato detectadas)                                         │"

    resumo_linhas = [
        f"# 📘 Relatório Consolidado de Estratégias e Orquestração no ODI 12c — Projeto `{projeto}`",
        "",
        f"> **Schema Alvo:** `{schema}` | **Sigla Curta ODI (<= 30 chars):** `{sigla_odi}` | **Estratégia da Fato:** `Estratégia {estrategia.upper()}` | **Gerado em:** `{agora}`",
        "",
        "Este documento consolida a arquitetura de integração de dados no **Oracle Data Integrator (ODI 12c)** para o Data Warehouse do projeto **`" + projeto + "`**, conectando os scripts SQL gerados aos guias passo a passo de cada Dimensão e Tabela Fato.",
        "",
        "> 🎨 **Topologia Visual do Canvas ODI 12c e Documento Word:**",
        "> * 🖼️ **[`mapa_canvas_odi.svg`](mapa_canvas_odi.svg)**: Diagrama vetorial completo do fluxo `MAP_DIM_*` (*Dimension Pattern SCD2*), `MAP_FATO_*` (`FIL_VALIDOS` ➔ `RN_DEDUP` ➔ `LKP_DIM_*` ➔ `EXP NVL(-1)` ➔ `IKM`) e pacote `PACK_CARGA_*`.",
        "> * 📄 **[`RELATORIO_ESTRATEGIAS.docx`](RELATORIO_ESTRATEGIAS.docx)**: Versão corporativa em Microsoft Word deste relatório consolidado.",
        "",
        "![Topologia do Canvas ODI 12c](mapa_canvas_odi.svg)",
        "",
        "---",
        "",
        "## 1. Regra de Ouro de Nomenclatura Física no ODI 12c (Limite de 30 Caracteres — `ORA-00972`)",
        "",
        "Durante a execução dos *Knowledge Modules* (`LKM`, `IKM`), o ODI 12c cria tabelas temporárias de trabalho concatenando prefixos como `C$_0`, `I$_`, `E$_` e passos internos do *Dimension Pattern* (`TGT_INS_`, `TGT_CLS_`, `TGT_UPD_`, `SCD2_SRC_`) ao nome físico da tabela alvo. Em repositórios e instâncias com compatibilidade de **30 bytes**, qualquer identificador temporário que ultrapasse 30 caracteres provoca falha imediata com **`ORA-00972: identifier is too long`**.",
        "",
        "### 1.1 Tabela de Conformidade de Nomenclatura Física (`<= 27` Caracteres)",
        "",
        "| Camada | Nome do Objeto Físico | Tamanho Físico | Objeto Temporário Crítico no ODI (`I$_` / `TGT_INS_`) | Status (`<= 30`) |",
        "| :--- | :--- | :---: | :--- | :---: |",
        *linhas_conformidade_30,
        "",
        "---",
        "",
        "## 2. Padrão Oficial de Carga de Dimensões SCD Tipo 2 (`Dimension Pattern` / Mapa Único)",
        "",
        "Todas as dimensões de negócio deste projeto seguem o **Padrão Nativo de Dimensão (`Dimension Pattern` / `Asterisco`)** do ODI 12c:",
        "1. **Um Único Mapa por Dimensão (`CARGA_DIM_*`):** Na aba *Lógico*, conecta-se `STG_* ──► EXPRESSION ──► DIM_*`.",
        "2. **Uso Automático da Tabela `ODI_DIM_*`:** No objeto Dimensão (*Dimensões e Cubos ➔ Níveis*), a propriedade **Armazenamento de Dados de Teste** aponta para `ODI_DIM_*` (criada **100% NULLABLE e sem PK** em `03_create_odi_dim_tables.sql` para evitar `ORA-01400` na etapa `STG_DIM_*`).",
        "3. **Setas Brancas Obrigatórias:** No componente `EXPRESSION`, os campos `DIMENSION_KEY`, `DTC_EFETIVACAO` e `DTC_EXPIRACAO` permanecem **sem mapeamento (seta branca)**, pois o próprio ODI os preenche nas etapas físicas `TGT_INS_` e `TGT_CLS_`.",
        "",
        "### 2.1 Guias Passo a Passo das Dimensões",
        "",
        "| Dimensão Alvo | Tabela Auxiliar (Stage de Teste) | Sequence | Mapa Único no ODI | Guia Passo a Passo Detalhado |",
        "| :--- | :--- | :--- | :--- | :--- |",
        *(linhas_tab_dims_resumo or ["| _Sem dimensões SCD2_ | - | - | - | - |"]),
        "",
        "---",
        "",
        "## 3. Estratégias para Carga das Tabelas Fato",
        "",
        "Cada tabela Fato possui seu guia individual contendo a **Consulta SQL Completa deduplicada (`RN_DEDUP = 1`)**, o comparativo das 3 abordagens no ODI 12c, a configuração exata de cada `LOOKUP` dimensional com simetria `UPPER(TRIM(...))` e a **tabela coluna por coluna** do mapeamento:",
        "",
        "| Tabela Fato Alvo | Mapa no ODI | Estratégia de Carga | Guia Passo a Passo Detalhado |",
        "| :--- | :--- | :--- | :--- |",
        *(linhas_tab_fatos_resumo or ["| _Sem tabelas Fato_ | - | - | - |"]),
        "",
        "---",
        "",
        f"## 4. Orquestração do Pacote (`PACK_CARGA_{sigla_odi}_DW`) e Cenário (`SCEN_`)",
        "",
        "### 4.1 Fluxo Visual Completo do Pacote no Diagrama do ODI",
        "",
        "```text",
        f" ┌──────────────────────────────────────────────────────────────────────────────┐",
        f" │ PACOTE: PACK_CARGA_{sigla_odi}_DW                                                   │",
        f" └──────────────────────────────────────┬───────────────────────────────────────┘",
        "                                        │",
        "                                        ▼",
        " ┌──────────────────────────────────────────────────────────────────────────────┐",
        " │ FASE 1: CARGA DAS DIMENSÕES (PADRÃO NATIVO SCD TIPO 2 + LINHA DEFAULT -1)    │",
        " │ ---------------------------------------------------------------------------- │",
        f"{ascii_dims_txt}",
        " └──────────────────────────────────────┬───────────────────────────────────────┘",
        "                                        │ (ok)",
        "                                        ▼",
        " ┌──────────────────────────────────────────────────────────────────────────────┐",
        " │ FASE 2: CARGA DAS TABELAS FATO (COM LOOKUP NAS DIMENSÕES VIGENTES)           │",
        " │ ---------------------------------------------------------------------------- │",
        f"{ascii_fatos_txt}",
        " └──────────────────────────────────────────────────────────────────────────────┘",
        "```",
        "",
        f"### 4.2 Matriz Completa de Objetos do Pacote (`PACK_CARGA_{sigla_odi}_DW`)",
        "",
        "| Ordem | Tipo de Passo no ODI | Nome do Objeto no ODI | Ação em Sucesso (`ok`) | Ação em Erro (`ko`) | Observação Técnica |",
        "| :---: | :--- | :--- | :--- | :--- | :--- |",
        *matriz_pacote_rows,
    ]

    arquivos["RELATORIO_ESTRATEGIAS.md"] = "\n".join(resumo_linhas) + "\n"
    return arquivos


def executar_melhoria_rapida(
    caminho_ddl: Path,
    modo: str = "tudo",
    estrategia: str = "A",
    schema_cli: str = None,
    projeto_cli: str = None,
    ts_idx_cli: str = None,
    caminho_amostras: Path = None,
    incluir_extras: bool = False,
) -> dict:
    base_dir = get_base_dir()
    saida_dw = base_dir / "saida" / "planejador_dw"

    if caminho_ddl.is_file():
        arquivos_sql = [caminho_ddl]
    elif caminho_ddl.is_dir():
        arquivos_sql = sorted([
            f for f in caminho_ddl.rglob("*")
            if f.is_file() and f.suffix.lower() in (".sql", ".txt", ".ddl", ".csv") and f.name.lower() != "readme.md"
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
    gerar_guia_bi = modo_norm in (
        "guia-bi",
        "mockup-bi",
        "validar-medidas-bi",
        "apresentacao",
        "exportar-docx",
        "exportar-pdf",
        "patch",
        "melhorias",
        "ajustes",
        "tudo",
        "all",
    )
    gerar_sel_odi = modo_norm in ("selects-odi", "odi")
    gerar_guia_odi = modo_norm in ("guia-odi", "odi", "exportar-docx", "exportar-pdf")

    # Formatos alternativos (.docx, .pdf) e Apresentação Executiva (.pptx / slides HTML)
    # são gerados SOMENTE quando solicitados explicitamente pelo modo ou via --todos-formatos (incluir_extras=True)
    gerar_apresentacao_flag = (modo_norm == "apresentacao") or incluir_extras
    gerar_docx_flag = (modo_norm == "exportar-docx") or incluir_extras
    gerar_pdf_flag = (modo_norm == "exportar-pdf") or incluir_extras

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

    # 1.1 Dicionário de Dados HTML Interativo + Diagrama Star Schema SVG
    if gerar_dic:
        html_dic = construir_dicionario_html(tabelas_classificadas, schema, projeto)
        p_dic = saida_dw / "11_dicionario_dados" / "dicionario_dados.html"
        p_dic.parent.mkdir(parents=True, exist_ok=True)
        p_dic.write_text(html_dic, encoding="utf-8")
        arquivos_gerados.append(str(p_dic.relative_to(base_dir).as_posix()))
        print(f"  {VERDE}[OK]{RESET} Dicionário de Dados HTML interativo -> {p_dic.relative_to(base_dir)}")

        if _TEM_ARTEFATOS_VISUAIS and gerar_diagrama_star_schema_svg is not None:
            svg_star = gerar_diagrama_star_schema_svg(dims, fatos, schema, projeto)
            p_star = saida_dw / "11_dicionario_dados" / "diagrama_star_schema.svg"
            p_star.write_text(svg_star, encoding="utf-8")
            arquivos_gerados.append(str(p_star.relative_to(base_dir).as_posix()))
            print(f"  {VERDE}[OK]{RESET} Diagrama Vetorial Star Schema (SVG) -> {p_star.relative_to(base_dir)}")

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

    # 6. Guia do Analista de BI + Mockup Visual (SVG/HTML/PNG 2x) + Planilha .xlsx + Deck .pptx + Word .docx
    if gerar_guia_bi:
        pasta_bi = saida_dw / "08_datasets_bi"
        pasta_bi.mkdir(parents=True, exist_ok=True)
        # Garante que exista apenas 1 Guia do Analista de BI na pasta (remove versões órfãs de siglas anteriores)
        for padrao_antigo in ("GUIA_ANALISTA_BI_*.*", "Indicadores_PowerBI_*.xlsx", "apresentacao_executiva_*.pptx"):
            for arq_ant in list(pasta_bi.glob(padrao_antigo)):
                nome_up = arq_ant.stem.upper()
                if not nome_up.endswith(f"_{projeto.upper()}"):
                    try:
                        arq_ant.unlink()
                    except OSError:
                        pass

        md_bi_previa = construir_guia_bi_rapido(dims, fatos, schema, projeto, base_dir=base_dir, dados_amostra=None)
        p_bi = pasta_bi / f"GUIA_ANALISTA_BI_{projeto}.md"

        dados_amostra = None
        if _TEM_ARTEFATOS_VISUAIS and avaliar_medidas_guia_bi_amostra is not None:
            try:
                dados_amostra = avaliar_medidas_guia_bi_amostra(
                    dims,
                    fatos,
                    schema,
                    projeto,
                    base_dir=base_dir,
                    caminho_amostras=caminho_amostras,
                    guia_md_texto=md_bi_previa,
                )
            except Exception:
                dados_amostra = None

        promover_para_oficial = bool(
            dados_amostra
            and dados_amostra.get("tem_amostra")
            and (
                modo_norm == "validar-medidas-bi"
                or dados_amostra.get("origem_amostra") == "AMOSTRA_FORNECIDA"
                or caminho_amostras is not None
            )
        )

        if promover_para_oficial:
            md_bi = construir_guia_bi_rapido(
                dims, fatos, schema, projeto, base_dir=base_dir, dados_amostra=dados_amostra
            )
            label_versao_guia = "VERSÃO OFICIAL — HOMOLOGADA PÓS-CARGA"
        else:
            md_bi = md_bi_previa
            label_versao_guia = "VERSÃO PRÉVIA — PRÉ-CARGA"

        p_bi.write_text(md_bi, encoding="utf-8")
        arquivos_gerados.append(str(p_bi.relative_to(base_dir).as_posix()))
        print(
            f"  {VERDE}[OK]{RESET} Guia do Analista de BI ({label_versao_guia}) -> {p_bi.relative_to(base_dir)}"
        )

        if promover_para_oficial and dados_amostra:
            p_rel_prova = pasta_bi / "RELATORIO_PROVA_REAL_MEDIDAS.md"
            p_rel_prova.write_text(dados_amostra.get("relatorio_md", ""), encoding="utf-8")
            arquivos_gerados.append(str(p_rel_prova.relative_to(base_dir).as_posix()))
            print(
                f"  {VERDE}[OK]{RESET} Prova Real de Medidas DAX na Amostra ({len(dados_amostra.get('medidas_avaliadas', []))} medidas, "
                f"{dados_amostra.get('qtd_parciais', 0)} corrigida(s)) -> {p_rel_prova.relative_to(base_dir)}"
            )

        if _TEM_ARTEFATOS_VISUAIS:
            ind_neg = carregar_indicadores_negocio_entrega(base_dir)
            pasta_bi = saida_dw / "08_datasets_bi"

            # Garante também o diagrama Star Schema caso gerar_dic não tenha rodado neste modo isolado
            p_star = saida_dw / "11_dicionario_dados" / "diagrama_star_schema.svg"
            if not p_star.exists() and gerar_diagrama_star_schema_svg is not None:
                p_star.parent.mkdir(parents=True, exist_ok=True)
                p_star.write_text(gerar_diagrama_star_schema_svg(dims, fatos, schema, projeto), encoding="utf-8")
                arquivos_gerados.append(str(p_star.relative_to(base_dir).as_posix()))

            if gerar_mockup_painel_bi_svg is not None and gerar_preview_painel_bi_html is not None:
                svg_mock_l = gerar_mockup_painel_bi_svg(
                    dims, fatos, schema, projeto, dev_mode=False, tema="light", dados_amostra=dados_amostra
                )
                svg_dev_l = gerar_mockup_painel_bi_svg(
                    dims, fatos, schema, projeto, dev_mode=True, tema="light", dados_amostra=dados_amostra
                )

                p_mock = pasta_bi / "mockup_painel_bi.svg"
                p_mock.write_text(svg_mock_l, encoding="utf-8")
                arquivos_gerados.append(str(p_mock.relative_to(base_dir).as_posix()))

                p_mock_dev = pasta_bi / "mockup_painel_bi_devmode.svg"
                p_mock_dev.write_text(svg_dev_l, encoding="utf-8")
                arquivos_gerados.append(str(p_mock_dev.relative_to(base_dir).as_posix()))

                p_prev = pasta_bi / "preview_painel_bi.html"
                p_prev.write_text(
                    gerar_preview_painel_bi_html(dims, fatos, schema, projeto, dados_amostra=dados_amostra),
                    encoding="utf-8",
                )
                arquivos_gerados.append(str(p_prev.relative_to(base_dir).as_posix()))
                print(f"  {VERDE}[OK]{RESET} Mockup Visual do Painel BI (SVG + Dev Mode Redlines + HTML/PNG 2x) -> {p_prev.relative_to(base_dir)}")

            if gerar_planilha_indicadores_xlsx is not None:
                p_xlsx = pasta_bi / f"Indicadores_PowerBI_{projeto}.xlsx"
                gerar_planilha_indicadores_xlsx(dims, fatos, schema, projeto, str(p_xlsx), ind_neg)
                arquivos_gerados.append(str(p_xlsx.relative_to(base_dir).as_posix()))
                print(f"  {VERDE}[OK]{RESET} Planilha Estilizada de Indicadores e Metas (3 abas .xlsx) -> {p_xlsx.relative_to(base_dir)}")

            if gerar_apresentacao_flag and gerar_apresentacao_executiva is not None:
                p_pptx, p_slides = gerar_apresentacao_executiva(
                    dims, fatos, schema, projeto, str(pasta_bi)
                )
                arquivos_gerados.append(str(Path(p_pptx).relative_to(base_dir).as_posix()))
                arquivos_gerados.append(str(Path(p_slides).relative_to(base_dir).as_posix()))
                print(f"  {VERDE}[OK]{RESET} Apresentação Executiva (.pptx + .html 16:9) -> {Path(p_pptx).relative_to(base_dir)}")

            if gerar_docx_flag and exportar_markdown_para_docx is not None:
                p_docx_bi = pasta_bi / f"GUIA_ANALISTA_BI_{projeto}.docx"
                exportar_markdown_para_docx(str(p_bi), str(p_docx_bi), titulo=f"Guia do Analista de BI — {projeto}")
                arquivos_gerados.append(str(p_docx_bi.relative_to(base_dir).as_posix()))
                print(f"  {VERDE}[OK]{RESET} Guia do Analista de BI em Word (.docx) -> {p_docx_bi.relative_to(base_dir)}")

            if gerar_pdf_flag and exportar_markdown_para_pdf is not None:
                p_pdf_bi = pasta_bi / f"GUIA_ANALISTA_BI_{projeto}.pdf"
                exportar_markdown_para_pdf(str(p_bi), str(p_pdf_bi), titulo=f"Guia Oficial do Analista de BI - {projeto}")
                arquivos_gerados.append(str(p_pdf_bi.relative_to(base_dir).as_posix()))
                print(f"  {VERDE}[OK]{RESET} Guia do Analista de BI em PDF Oficial (.pdf) -> {p_pdf_bi.relative_to(base_dir)}")

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

    # 8. Micro-Processo ODI: Guias Modulares do Canvas ODI 12c + Diagrama SVG + Word .docx + PDF .pdf
    if gerar_guia_odi:
        guias_odi = construir_guias_odi_modulares(dims, fatos, schema, projeto, estrategia)
        pasta_rel = saida_dw / "09_relatorio_estrategias"
        pasta_rel.mkdir(parents=True, exist_ok=True)
        for nome_arq, conteudo_md in guias_odi.items():
            p_g = pasta_rel / nome_arq
            p_g.write_text(conteudo_md, encoding="utf-8")
            arquivos_gerados.append(str(p_g.relative_to(base_dir).as_posix()))
            print(f"  {VERDE}[OK]{RESET} Guia Modular ODI 12c -> {p_g.relative_to(base_dir)}")

        if _TEM_ARTEFATOS_VISUAIS:
            if gerar_mapa_canvas_odi_svg is not None:
                p_odi_svg = pasta_rel / "mapa_canvas_odi.svg"
                p_odi_svg.write_text(
                    gerar_mapa_canvas_odi_svg(dims, fatos, schema, projeto, estrategia=estrategia),
                    encoding="utf-8",
                )
                arquivos_gerados.append(str(p_odi_svg.relative_to(base_dir).as_posix()))
                print(f"  {VERDE}[OK]{RESET} Diagrama Vetorial do Canvas ODI 12c (SVG) -> {p_odi_svg.relative_to(base_dir)}")

            if gerar_docx_flag and exportar_markdown_para_docx is not None and "RELATORIO_ESTRATEGIAS.md" in guias_odi:
                p_docx_odi = pasta_rel / "RELATORIO_ESTRATEGIAS.docx"
                exportar_markdown_para_docx(
                    str(pasta_rel / "RELATORIO_ESTRATEGIAS.md"),
                    str(p_docx_odi),
                    titulo=f"Relatório de Estratégias ODI 12c — {projeto}",
                )
                arquivos_gerados.append(str(p_docx_odi.relative_to(base_dir).as_posix()))
                print(f"  {VERDE}[OK]{RESET} Relatório de Estratégias ODI em Word (.docx) -> {p_docx_odi.relative_to(base_dir)}")

            if gerar_pdf_flag and exportar_markdown_para_pdf is not None and "RELATORIO_ESTRATEGIAS.md" in guias_odi:
                p_pdf_odi = pasta_rel / "RELATORIO_ESTRATEGIAS.pdf"
                exportar_markdown_para_pdf(
                    str(pasta_rel / "RELATORIO_ESTRATEGIAS.md"),
                    str(p_pdf_odi),
                    titulo=f"Relatorio de Estrategias ODI 12c - {projeto}",
                )
                arquivos_gerados.append(str(p_pdf_odi.relative_to(base_dir).as_posix()))
                print(f"  {VERDE}[OK]{RESET} Relatório de Estratégias ODI em PDF Oficial (.pdf) -> {p_pdf_odi.relative_to(base_dir)}")

    # Gera o diagnóstico consolidado apenas nos modos de auditoria/patch amplo (evita poluir micro-processos isolados como guia-bi)
    if modo_norm in ("patch", "melhorias", "ajustes", "tudo", "all", "diagnostico"):
        rel_md = construir_relatorio_diagnostico(tabelas_classificadas, schema, projeto, modo_norm, arquivos_gerados)
        p_rel = saida_dw / "09_relatorio_estrategias" / "DIAGNOSTICO_MELHORIAS_DW_EXISTENTE.md"
        p_rel.parent.mkdir(parents=True, exist_ok=True)
        p_rel.write_text(rel_md, encoding="utf-8")
        arquivos_gerados.append(str(p_rel.relative_to(base_dir).as_posix()))
        print(f"  {VERDE}[OK]{RESET} Relatório Diagnóstico -> {p_rel.relative_to(base_dir)}")

    print(f"\n{VERDE}{NEGRITO}✅ Micro-processo '{modo_norm}' concluído com sucesso! {len(arquivos_gerados)} artefato(s) gerado(s) em 'saida/planejador_dw/'.{RESET}")
    print(f"{CIANO}🧭 O que você pode fazer agora:{RESET}")
    print("  • `/iniciar-semantica`  ➔ Gerar as 3 camadas de Views Semânticas + Catálogo META_* sobre este DW")
    print("  • `/exportar-docx` / `/exportar-pdf` / `/gerar-apresentacao` ➔ Exportar guias (.docx/.pdf) ou Apresentação (.pptx) sob demanda")
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
            "mockup-bi",
            "validar-medidas-bi",
            "apresentacao",
            "exportar-docx",
            "exportar-pdf",
            "selects-odi",
            "guia-odi",
            "odi",
            "patch",
            "tudo",
        ],
        help=(
            "Micro-processo a executar: 'comentarios', 'dicionario', 'indices', 'linha-default', "
            "'constraints', 'testes', 'guia-bi', 'validar-medidas-bi', 'selects-odi', 'guia-odi', 'odi', 'patch' ou 'tudo'"
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
    parser.add_argument(
        "--amostras",
        type=str,
        default=None,
        help="Caminho opcional de arquivo/pasta com amostras pós-carga (DIM_* e FATO_* em CSV/SQL/XLSX/ODS)",
    )
    parser.add_argument(
        "--todos-formatos",
        "--incluir-extras",
        dest="incluir_extras",
        action="store_true",
        help="Gera também os formatos sob demanda (.docx, .pdf e Apresentação Executiva .pptx/.html)",
    )

    args = parser.parse_args()
    base_dir = get_base_dir()
    caminho_alvo = Path(args.caminho)
    if not caminho_alvo.is_absolute():
        caminho_alvo = base_dir / caminho_alvo

    caminho_amostras = None
    if args.amostras:
        caminho_amostras = Path(args.amostras)
        if not caminho_amostras.is_absolute():
            caminho_amostras = base_dir / caminho_amostras

    res = executar_melhoria_rapida(
        caminho_ddl=caminho_alvo,
        modo=args.modo,
        estrategia=args.estrategia.upper(),
        schema_cli=args.schema,
        projeto_cli=args.projeto,
        ts_idx_cli=args.tablespace_idx,
        caminho_amostras=caminho_amostras,
        incluir_extras=args.incluir_extras,
    )
    sys.exit(1 if res["erros"] > 0 else 0)


if __name__ == "__main__":
    main()

