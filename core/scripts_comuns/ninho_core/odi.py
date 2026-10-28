"""
Oracle Data Integrator 12c: nomes físicos dentro do limite de 30 bytes, tabelas ODI_DIM_*,
consultas de carga SCD2/Fato e guias modulares de construção no canvas (MAP/TRT/PACK/SCEN).

Extraído de melhorar_dw_existente.py (que mantém uma fachada de reimportação).
"""

import re
from datetime import datetime
from ninho_core.dw_modelo import (
    _eh_nk_textual,
    _fato_possui_sk_propria,
    _obter_nk_dim,
    _obter_sk_dim,
    identificar_fks_fato,
)


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
            "  | (Datastore Stage)     |       | (Padronização) |       | (Componente Dimensão - Nível) |",
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
            "1. **Deduplicação na Stage (`STG_DEDUP`)** via `ROW_NUMBER() OVER (PARTITION BY ...)` (`RN_DEDUP = 1`) para blindar o `MERGE`/`INSERT` contra o erro `ORA-30926: unable to get a stable set of rows in the source tables`.",
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
        " ┌──────────────────────────────────────────────────────────────────────────────┐",
        f" │ PACOTE: PACK_CARGA_{sigla_odi}_DW                                                   │",
        " └──────────────────────────────────────┬───────────────────────────────────────┘",
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
