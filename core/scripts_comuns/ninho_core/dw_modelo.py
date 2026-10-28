"""
Modelo dimensional base: classificação DIM/FATO, identificação de SK/NK e FKs da Fato,
inferência de comentários semânticos e valores da linha sentinela -1.

Extraído de melhorar_dw_existente.py (que mantém uma fachada de reimportação).
"""

import re
from ninho_core.paths import get_base_dir


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
