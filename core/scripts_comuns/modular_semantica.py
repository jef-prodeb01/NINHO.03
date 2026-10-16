#!/usr/bin/env python3
"""
NINHO — Motor Modular da Camada Semântica (Micro-Processos & Fast-Track)
========================================================================
Permite executar a Camada Semântica Oracle de forma 100% granular (micro-processos)
ou completa a partir dos DDLs do DW (depositados em `entrega/camada_semantica/ddl/`,
`saida/planejador_dw/` ou `entrega/planejador_dw/ddl/`).

Modos disponíveis (`--modo`):
  - `views-dim`       : Gera apenas Camada 1 (`01_vw_dim_atuais.sql` com `DTC_EXPIRACAO IS NULL`)
  - `views-evento`    : Gera apenas Camada 2 (`02_vw_eventos.sql` desnormalizada com `NVL`)
  - `views-kpi`       : Gera apenas Camada 3 (`03_vw_kpis.sql` pré-agregada com `NULLIF`)
  - `views-semantica` : Gera todas as 3 camadas de Views (`01_vw_dim_atuais`, `02_vw_eventos`, `03_vw_kpis`)
  - `catalogo-meta`   : Gera apenas os scripts `01_meta_glossario.sql` a `08_meta_valor_dominio.sql` (`META_*`)
  - `rls`             : Gera apenas o script de Row-Level Security VPD (`02_rls.sql`)
  - `validacoes`      : Gera apenas o script de Smoke Tests e auditoria (`09_validacoes.sql`)
  - `documento`       : Gera apenas o Documento de Entendimento (`DOCUMENTO_ENTENDIMENTO_<PROJETO>.md`)
  - `tudo`            : Executa todos os micro-processos da Camada Semântica
"""

import argparse
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from melhorar_dw_existente import (
    _obter_nk_dim,
    _obter_sk_dim,
    classificar_tabela_dw,
    extrair_schema_e_projeto,
    gerar_comentario_coluna,
    identificar_fks_fato,
    parse_ddl_text,
)

ROOT_DIR = SCRIPT_DIR.parent.parent
ENTREGA_SEM_DDL_DIR = ROOT_DIR / "entrega" / "camada_semantica" / "ddl"
ENTREGA_DW_DDL_DIR = ROOT_DIR / "entrega" / "planejador_dw" / "ddl"
SAIDA_DW_DIR = ROOT_DIR / "saida" / "planejador_dw"
SAIDA_SEM_DIR = ROOT_DIR / "saida" / "camada_semantica"
TEMPLATES_SEM_DIR = ROOT_DIR / "modulos" / "camada_semantica" / "templates"


def localizar_ddls_para_semantica(caminho_custom: Path | None = None) -> tuple[list[Path], Path]:
    """Localiza arquivos .sql de DDL na ordem de prioridade da Camada Semântica."""
    if caminho_custom and caminho_custom.exists():
        if caminho_custom.is_file():
            return [caminho_custom], caminho_custom.parent
        arqs = sorted(caminho_custom.rglob("*.sql"))
        if arqs:
            return arqs, caminho_custom

    # 1. entrega/camada_semantica/ddl/
    if ENTREGA_SEM_DDL_DIR.exists():
        arqs = sorted(ENTREGA_SEM_DDL_DIR.rglob("*.sql"))
        if arqs:
            return arqs, ENTREGA_SEM_DDL_DIR

    # 2. saida/planejador_dw/03_dimensoes e 04_fatos (Handoff direto do DW)
    arqs_saida_dw = []
    for sub in ("03_dimensoes", "04_fatos"):
        p = SAIDA_DW_DIR / sub
        if p.exists():
            for f in sorted(p.glob("*.sql")):
                fname_l = f.name.lower()
                if (
                    "select" not in fname_l
                    and "odi_dim" not in fname_l
                    and "init_default" not in fname_l
                    and "patch_" not in fname_l
                ):
                    arqs_saida_dw.append(f)
    if arqs_saida_dw:
        return arqs_saida_dw, SAIDA_DW_DIR

    # 3. entrega/planejador_dw/ddl/
    if ENTREGA_DW_DDL_DIR.exists():
        arqs = sorted(ENTREGA_DW_DDL_DIR.rglob("*.sql"))
        if arqs:
            return arqs, ENTREGA_DW_DDL_DIR

    return [], ENTREGA_SEM_DDL_DIR


def carregar_tabelas_dw(arquivos_sql: list[Path]) -> list[dict]:
    """Lê todos os arquivos SQL e retorna apenas tabelas DIM_* e FATO_* deduplicadas."""
    por_nome: dict[str, dict] = {}
    for arq in arquivos_sql:
        txt = arq.read_text(encoding="utf-8", errors="replace")
        for t in parse_ddl_text(txt, arq.name):
            papel = classificar_tabela_dw(t)
            if papel in ("DIM", "FATO"):
                por_nome[t["nome_tabela"]] = t
    return list(por_nome.values())


def _nome_entidade_curto(nome_tabela: str) -> str:
    """Remove prefixos DIM_, FATO_, FAT_ para compor o nome canônico da View."""
    return re.sub(r"^(DIM|FATO|FAT)_", "", nome_tabela.upper())


def construir_views_dim_atuais(tabelas: list[dict], schema: str, projeto: str) -> str:
    """Gera Camada 1: `01_vw_dim_atuais.sql` (`VW_<PROJETO>_DIM_<ENTIDADE>_ATUAL`)."""
    dims = [t for t in tabelas if classificar_tabela_dw(t) == "DIM"]
    linhas = [
        "-- =============================================================================",
        "-- NINHO — CAMADA SEMÂNTICA ORACLE (MICRO-PROCESSO: VIEWS DE DIMENSÃO VIGENTE)",
        f"-- Projeto / Sigla : {projeto}",
        f"-- Schema Alvo     : {schema}",
        f"-- Gerado em       : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "-- Regra de Ouro   : Proibido SELECT *; obrigatório filtro DTC_EXPIRACAO IS NULL",
        "-- =============================================================================",
        "",
    ]

    for d in dims:
        tname = d["nome_tabela"]
        entidade = _nome_entidade_curto(tname)
        vw_name = f"VW_{projeto}_DIM_{entidade}_ATUAL"
        sk = _obter_sk_dim(d)
        nk = _obter_nk_dim(d)

        cols_negocio = [
            c for c in d["colunas"]
            if c["nome_dw"] not in ("DES_HASH_SCD2", "COD_EXECUCAO_CARGA", "DES_ATUALIZAR")
        ]
        if not cols_negocio:
            cols_negocio = d["colunas"]

        tem_dtc_exp = any(
            c["nome_dw"] in ("DTC_EXPIRACAO", "DT_FIM_VIGENCIA", "DTC_FIM_VIGENCIA") for c in d["colunas"]
        )
        col_exp = next(
            (c["nome_dw"] for c in d["colunas"] if c["nome_dw"] in ("DTC_EXPIRACAO", "DT_FIM_VIGENCIA", "DTC_FIM_VIGENCIA")),
            "DTC_EXPIRACAO",
        )

        linhas.append("-- -----------------------------------------------------------------------------")
        linhas.append(f"-- View Camada 1: {schema}.{vw_name}")
        linhas.append(f"-- Grão: Uma linha representa o registro atualmente vigente de {entidade} ({nk}).")
        linhas.append("-- -----------------------------------------------------------------------------")
        linhas.append(f"CREATE OR REPLACE FORCE VIEW {schema}.{vw_name} AS")
        linhas.append("SELECT")
        for idx, c in enumerate(cols_negocio):
            virg = "," if idx < len(cols_negocio) - 1 else ""
            cname = c["nome_dw"]
            if cname.startswith(("DES_", "NOM_", "DSC_")):
                linhas.append(f"    NVL(d.{cname}, 'Não Informado') AS {cname}{virg}")
            else:
                linhas.append(f"    d.{cname} AS {cname}{virg}")
        linhas.append(f"FROM {schema}.{tname} d")
        if tem_dtc_exp:
            linhas.append(f"WHERE d.{col_exp} IS NULL;")
        else:
            linhas.append("WHERE /* ATENÇÃO: Adicione coluna DTC_EXPIRACAO na Dimensão SCD2 */ 1 = 1;")
        linhas.append("")

        desc_vw = f"View semântica de registros vigentes (SCD2 ativo) da dimensão {tname}. Uma linha representa 1 registro vigente de {nk}."
        linhas.append(f"COMMENT ON TABLE {schema}.{vw_name} IS '{desc_vw}';")
        for c in cols_negocio:
            cname = c["nome_dw"]
            c_comment = c.get("comentario") or gerar_comentario_coluna(c, d, "DIM")
            c_comment_esc = c_comment.replace("'", "''")
            linhas.append(f"COMMENT ON COLUMN {schema}.{vw_name}.{cname} IS '{c_comment_esc}';")
        linhas.append("")

    return "\n".join(linhas)


def construir_views_eventos(tabelas: list[dict], schema: str, projeto: str) -> str:
    """Gera Camada 2: `02_vw_eventos.sql` (`VW_<PROJETO>_EVENTO_<ENTIDADE>`)."""
    dims = [t for t in tabelas if classificar_tabela_dw(t) == "DIM"]
    dims_map = {t["nome_tabela"].upper(): t for t in dims}
    nomes_dims = set(dims_map.keys())
    fatos = [t for t in tabelas if classificar_tabela_dw(t) == "FATO"]

    linhas = [
        "-- =============================================================================",
        "-- NINHO — CAMADA SEMÂNTICA ORACLE (MICRO-PROCESSO: VIEWS DE EVENTO DETALHADO)",
        f"-- Projeto / Sigla : {projeto}",
        f"-- Schema Alvo     : {schema}",
        f"-- Gerado em       : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "-- Regra de Ouro   : Desnormalização controlada Fato + Dimensões, sem SELECT *",
        "-- =============================================================================",
        "",
    ]

    for f in fatos:
        fname = f["nome_tabela"]
        entidade = _nome_entidade_curto(fname)
        vw_name = f"VW_{projeto}_EVENTO_{entidade}"
        fks = identificar_fks_fato(f, nomes_dims)

        linhas.append("-- -----------------------------------------------------------------------------")
        linhas.append(f"-- View Camada 2: {schema}.{vw_name}")
        linhas.append(f"-- Grão: Uma linha representa um evento individual registrado em {fname} enriquecido com suas dimensões.")
        linhas.append("-- -----------------------------------------------------------------------------")
        linhas.append(f"CREATE OR REPLACE FORCE VIEW {schema}.{vw_name} AS")
        linhas.append("SELECT")

        select_exprs = []
        comentarios_vw = []

        for c in f["colunas"]:
            cname = c["nome_dw"]
            if cname in ("COD_EXECUCAO_CARGA",):
                continue
            select_exprs.append(f"    f.{cname} AS {cname}")
            c_comment = c.get("comentario") or gerar_comentario_coluna(c, f, "FATO")
            comentarios_vw.append((cname, c_comment))

        joins_sql = []
        for idx_fk, fk in enumerate(fks, start=1):
            col_fk = fk["coluna"]
            dim_tab = fk["tabela_ref"].upper()
            alias = f"d{idx_fk}"
            if dim_tab in dims_map:
                d_obj = dims_map[dim_tab]
                col_pk_dim = _obter_sk_dim(d_obj)
                joins_sql.append(f"LEFT JOIN {schema}.{dim_tab} {alias} ON f.{col_fk} = {alias}.{col_pk_dim}")
                atributos_dim = [
                    c for c in d_obj["colunas"]
                    if c["nome_dw"] != col_pk_dim
                    and not c["nome_dw"].startswith(("DTC_", "DT_", "FLG_AT", "SIN_AT", "DES_ATUALIZAR", "DES_HASH"))
                ][:3]
                sufixo_dim = _nome_entidade_curto(dim_tab)
                for atr in atributos_dim:
                    aname = atr["nome_dw"]
                    alias_col = aname if aname.endswith(f"_{sufixo_dim}") else f"{aname}_{sufixo_dim}"
                    alias_col = alias_col[:30]
                    if aname.startswith(("DES_", "NOM_", "DSC_", "SGL_", "SIG_")):
                        select_exprs.append(f"    NVL({alias}.{aname}, 'Não Informado') AS {alias_col}")
                    else:
                        select_exprs.append(f"    {alias}.{aname} AS {alias_col}")
                    comentarios_vw.append((alias_col, f"Atributo {aname} oriundo da dimensão {dim_tab}."))

        select_exprs.append("    CASE WHEN 1 = 1 THEN 'REGULAR' ELSE 'PENDENTE' END AS IND_SITUACAO_EVENTO")
        comentarios_vw.append(("IND_SITUACAO_EVENTO", "Indicador semântico padronizado da situação do evento para consumo de BI e IA."))

        for i, expr in enumerate(select_exprs):
            virg = "," if i < len(select_exprs) - 1 else ""
            linhas.append(f"{expr}{virg}")

        linhas.append(f"FROM {schema}.{fname} f")
        for j in joins_sql:
            linhas.append(j)
        linhas[-1] = linhas[-1] + ";"
        linhas.append("")

        linhas.append(f"COMMENT ON TABLE {schema}.{vw_name} IS 'View semântica de eventos detalhados de {fname}. Uma linha representa um evento individual enriquecido com dimensões.';")
        for cname, c_comm in comentarios_vw:
            c_comm_esc = c_comm.replace("'", "''")
            linhas.append(f"COMMENT ON COLUMN {schema}.{vw_name}.{cname} IS '{c_comm_esc}';")
        linhas.append("")

    return "\n".join(linhas)


def construir_views_kpis(tabelas: list[dict], schema: str, projeto: str) -> str:
    """Gera Camada 3: `03_vw_kpis.sql` (`VW_<PROJETO>_KPI_<ENTIDADE>`)."""
    dims = [t for t in tabelas if classificar_tabela_dw(t) == "DIM"]
    nomes_dims = {t["nome_tabela"].upper() for t in dims}
    fatos = [t for t in tabelas if classificar_tabela_dw(t) == "FATO"]

    linhas = [
        "-- =============================================================================",
        "-- NINHO — CAMADA SEMÂNTICA ORACLE (MICRO-PROCESSO: VIEWS DE KPIs AGREGADOS)",
        f"-- Projeto / Sigla : {projeto}",
        f"-- Schema Alvo     : {schema}",
        f"-- Gerado em       : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "-- Regra de Ouro   : Divisão protegida com NULLIF(..., 0) e grão explícito",
        "-- =============================================================================",
        "",
    ]

    for f in fatos:
        fname = f["nome_tabela"]
        entidade = _nome_entidade_curto(fname)
        vw_evento = f"VW_{projeto}_EVENTO_{entidade}"
        vw_kpi = f"VW_{projeto}_KPI_{entidade}"
        fks = identificar_fks_fato(f, nomes_dims)

        col_grupo = fks[0]["coluna"] if fks else f["colunas"][0]["nome_dw"]
        metricas = [
            c["nome_dw"] for c in f["colunas"]
            if c["nome_dw"].startswith(("QTD_", "VLR_", "VAL_", "NUM_DIAS", "TMP_", "QT_"))
        ]

        linhas.append("-- -----------------------------------------------------------------------------")
        linhas.append(f"-- View Camada 3: {schema}.{vw_kpi}")
        linhas.append(f"-- Grão: Uma linha representa o consolidado de indicadores de {entidade} agrupado por {col_grupo}.")
        linhas.append("-- -----------------------------------------------------------------------------")
        linhas.append(f"CREATE OR REPLACE FORCE VIEW {schema}.{vw_kpi} AS")
        linhas.append("SELECT")
        linhas.append(f"    e.{col_grupo} AS {col_grupo},")
        linhas.append("    COUNT(1) AS QTD_TOTAL_REGISTROS,")

        comentarios_kpi = [
            (col_grupo, f"Eixo dimensional de agrupamento ({col_grupo})."),
            ("QTD_TOTAL_REGISTROS", f"Volume total de eventos contabilizados em {fname}."),
        ]

        for m in metricas[:4]:
            linhas.append(f"    SUM(NVL(e.{m}, 0)) AS SUM_{m[:24]},")
            linhas.append(f"    ROUND(AVG(NVL(e.{m}, 0)), 2) AS AVG_{m[:24]},")
            comentarios_kpi.append((f"SUM_{m[:24]}", f"Somatório da métrica {m} no agrupamento."))
            comentarios_kpi.append((f"AVG_{m[:24]}", f"Média aritmética da métrica {m} no agrupamento."))

        linhas.append("    ROUND((COUNT(1) * 100.0) / NULLIF(SUM(COUNT(1)) OVER (), 0), 2) AS PCT_PARTICIPACAO_TOTAL")
        comentarios_kpi.append(("PCT_PARTICIPACAO_TOTAL", "Percentual de participação do grupo sobre o volume total geral (divisão segura com NULLIF)."))

        linhas.append(f"FROM {schema}.{vw_evento} e")
        linhas.append(f"GROUP BY e.{col_grupo};")
        linhas.append("")

        linhas.append(f"COMMENT ON TABLE {schema}.{vw_kpi} IS 'View semântica pré-agregada de KPIs executivos de {fname}. Uma linha representa o consolidado por {col_grupo}.';")
        for cname, c_comm in comentarios_kpi:
            c_comm_esc = c_comm.replace("'", "''")
            linhas.append(f"COMMENT ON COLUMN {schema}.{vw_kpi}.{cname} IS '{c_comm_esc}';")
        linhas.append("")

    return "\n".join(linhas)


def construir_catalogo_meta(tabelas: list[dict], schema: str, projeto: str) -> dict[str, str]:
    """Gera os 8 scripts idempotentes `01_meta_glossario.sql` a `08_meta_valor_dominio.sql`."""
    dims = [t for t in tabelas if classificar_tabela_dw(t) == "DIM"]
    fatos = [t for t in tabelas if classificar_tabela_dw(t) == "FATO"]
    dims_map = {t["nome_tabela"].upper(): t for t in dims}
    nomes_dims = set(dims_map.keys())

    arquivos: dict[str, str] = {}

    # 01_meta_glossario.sql
    linhas_01 = [
        "-- =============================================================================",
        f"-- NINHO — CATÁLOGO SEMÂNTICO: 01_meta_glossario.sql (PROJETO: {projeto})",
        "-- Carga idempotente via MERGE INTO",
        "-- =============================================================================",
        "",
    ]
    for t in tabelas:
        tname = t["nome_tabela"]
        papel = classificar_tabela_dw(t)
        papel_label = "DIMENSAO" if papel == "DIM" else "FATO"
        ent = _nome_entidade_curto(tname)
        vw_ref = f"VW_{projeto}_DIM_{ent}_ATUAL" if papel == "DIM" else f"VW_{projeto}_EVENTO_{ent}"
        termo = f"{papel_label} {ent}".title()
        definicao = (t.get("comentario_tabela") or f"Entidade oficial de {papel_label.lower()} para {ent} no projeto {projeto}.").replace("'", "''")
        linhas_01.append(
            f"MERGE INTO {schema}.META_GLOSSARIO dst\n"
            f"USING (SELECT '{projeto}' AS SGL_PROJETO, '{termo}' AS NOM_TERMO, '{definicao}' AS DES_DEFINICAO, "
            f"'{papel_label}' AS IND_CATEGORIA, '{vw_ref}' AS NOM_OBJETO_FISICO, 'ATIVO' AS IND_STATUS FROM DUAL) src\n"
            f"ON (dst.SGL_PROJETO = src.SGL_PROJETO AND dst.NOM_TERMO = src.NOM_TERMO)\n"
            f"WHEN MATCHED THEN UPDATE SET dst.DES_DEFINICAO = src.DES_DEFINICAO, dst.NOM_OBJETO_FISICO = src.NOM_OBJETO_FISICO\n"
            f"WHEN NOT MATCHED THEN INSERT (SGL_PROJETO, NOM_TERMO, DES_DEFINICAO, IND_CATEGORIA, NOM_OBJETO_FISICO, IND_STATUS)\n"
            f"VALUES (src.SGL_PROJETO, src.NOM_TERMO, src.DES_DEFINICAO, src.IND_CATEGORIA, src.NOM_OBJETO_FISICO, src.IND_STATUS);\n"
        )
    linhas_01.append("COMMIT;\n")
    arquivos["01_meta_glossario.sql"] = "\n".join(linhas_01)

    # 02_meta_metrica.sql
    linhas_02 = [
        "-- =============================================================================",
        f"-- NINHO — CATÁLOGO SEMÂNTICO: 02_meta_metrica.sql (PROJETO: {projeto})",
        "-- =============================================================================",
        "",
    ]
    for f in fatos:
        fname = f["nome_tabela"]
        ent = _nome_entidade_curto(fname)
        vw_kpi = f"VW_{projeto}_KPI_{ent}"
        linhas_02.append(
            f"MERGE INTO {schema}.META_METRICA dst\n"
            f"USING (SELECT '{projeto}' AS SGL_PROJETO, 'QTD_TOTAL_{ent}' AS COD_METRICA, "
            f"'Volume Total de {ent.title()}' AS NOM_METRICA, "
            f"'Contagem total de registros na fato {fname}' AS DES_METRICA, "
            f"'COUNT(1)' AS DES_FORMULA_SQL, '{vw_kpi}' AS NOM_VIEW_ORIGEM, 'INTEIRO' AS TIP_FORMATO FROM DUAL) src\n"
            f"ON (dst.SGL_PROJETO = src.SGL_PROJETO AND dst.COD_METRICA = src.COD_METRICA)\n"
            f"WHEN MATCHED THEN UPDATE SET dst.DES_FORMULA_SQL = src.DES_FORMULA_SQL, dst.NOM_VIEW_ORIGEM = src.NOM_VIEW_ORIGEM\n"
            f"WHEN NOT MATCHED THEN INSERT (SGL_PROJETO, COD_METRICA, NOM_METRICA, DES_METRICA, DES_FORMULA_SQL, NOM_VIEW_ORIGEM, TIP_FORMATO)\n"
            f"VALUES (src.SGL_PROJETO, src.COD_METRICA, src.NOM_METRICA, src.DES_METRICA, src.DES_FORMULA_SQL, src.NOM_VIEW_ORIGEM, src.TIP_FORMATO);\n"
        )
        for c in f["colunas"]:
            cname = c["nome_dw"]
            if cname.startswith(("QTD_", "VLR_", "VAL_", "QT_")):
                linhas_02.append(
                    f"MERGE INTO {schema}.META_METRICA dst\n"
                    f"USING (SELECT '{projeto}' AS SGL_PROJETO, 'SUM_{cname}' AS COD_METRICA, "
                    f"'Somatório de {cname}' AS NOM_METRICA, "
                    f"'Soma consolidada da coluna {cname} em {fname}' AS DES_METRICA, "
                    f"'SUM(NVL({cname}, 0))' AS DES_FORMULA_SQL, '{vw_kpi}' AS NOM_VIEW_ORIGEM, 'NUMERICO' AS TIP_FORMATO FROM DUAL) src\n"
                    f"ON (dst.SGL_PROJETO = src.SGL_PROJETO AND dst.COD_METRICA = src.COD_METRICA)\n"
                    f"WHEN MATCHED THEN UPDATE SET dst.DES_FORMULA_SQL = src.DES_FORMULA_SQL\n"
                    f"WHEN NOT MATCHED THEN INSERT (SGL_PROJETO, COD_METRICA, NOM_METRICA, DES_METRICA, DES_FORMULA_SQL, NOM_VIEW_ORIGEM, TIP_FORMATO)\n"
                    f"VALUES (src.SGL_PROJETO, src.COD_METRICA, src.NOM_METRICA, src.DES_METRICA, src.DES_FORMULA_SQL, src.NOM_VIEW_ORIGEM, src.TIP_FORMATO);\n"
                )
    linhas_02.append("COMMIT;\n")
    arquivos["02_meta_metrica.sql"] = "\n".join(linhas_02)

    # 03_meta_hierarquia.sql
    linhas_03 = [
        "-- =============================================================================",
        f"-- NINHO — CATÁLOGO SEMÂNTICO: 03_meta_hierarquia.sql (PROJETO: {projeto})",
        "-- =============================================================================",
        "",
    ]
    for d in dims:
        ent = _nome_entidade_curto(d["nome_tabela"])
        vw_dim = f"VW_{projeto}_DIM_{ent}_ATUAL"
        nk = _obter_nk_dim(d)
        linhas_03.append(
            f"MERGE INTO {schema}.META_HIERARQUIA dst\n"
            f"USING (SELECT '{projeto}' AS SGL_PROJETO, 'HIER_{ent}' AS COD_HIERARQUIA, "
            f"'Hierarquia Analítica de {ent.title()}' AS NOM_HIERARQUIA, "
            f"'{vw_dim}' AS NOM_VIEW_DIMENSAO, 1 AS NUM_NIVEL, '{nk}' AS NOM_COLUNA_NIVEL FROM DUAL) src\n"
            f"ON (dst.SGL_PROJETO = src.SGL_PROJETO AND dst.COD_HIERARQUIA = src.COD_HIERARQUIA AND dst.NUM_NIVEL = src.NUM_NIVEL)\n"
            f"WHEN MATCHED THEN UPDATE SET dst.NOM_COLUNA_NIVEL = src.NOM_COLUNA_NIVEL\n"
            f"WHEN NOT MATCHED THEN INSERT (SGL_PROJETO, COD_HIERARQUIA, NOM_HIERARQUIA, NOM_VIEW_DIMENSAO, NUM_NIVEL, NOM_COLUNA_NIVEL)\n"
            f"VALUES (src.SGL_PROJETO, src.COD_HIERARQUIA, src.NOM_HIERARQUIA, src.NOM_VIEW_DIMENSAO, src.NUM_NIVEL, src.NOM_COLUNA_NIVEL);\n"
        )
    linhas_03.append("COMMIT;\n")
    arquivos["03_meta_hierarquia.sql"] = "\n".join(linhas_03)

    # 04_meta_relacionamento.sql
    linhas_04 = [
        "-- =============================================================================",
        f"-- NINHO — CATÁLOGO SEMÂNTICO: 04_meta_relacionamento.sql (PROJETO: {projeto})",
        "-- =============================================================================",
        "",
    ]
    for f in fatos:
        ent_f = _nome_entidade_curto(f["nome_tabela"])
        vw_ev = f"VW_{projeto}_EVENTO_{ent_f}"
        for fk in identificar_fks_fato(f, nomes_dims):
            dim_ref = fk["tabela_ref"].upper()
            ent_d = _nome_entidade_curto(dim_ref)
            vw_dim = f"VW_{projeto}_DIM_{ent_d}_ATUAL"
            col_pk_dim = _obter_sk_dim(dims_map[dim_ref]) if dim_ref in dims_map else "DIMENSION_KEY"
            linhas_04.append(
                f"MERGE INTO {schema}.META_RELACIONAMENTO dst\n"
                f"USING (SELECT '{projeto}' AS SGL_PROJETO, '{vw_ev}' AS NOM_OBJETO_ORIGEM, "
                f"'{fk['coluna']}' AS NOM_COLUNA_ORIGEM, '{vw_dim}' AS NOM_OBJETO_DESTINO, "
                f"'{col_pk_dim}' AS NOM_COLUNA_DESTINO, 'N:1' AS IND_CARDINALIDADE FROM DUAL) src\n"
                f"ON (dst.SGL_PROJETO = src.SGL_PROJETO AND dst.NOM_OBJETO_ORIGEM = src.NOM_OBJETO_ORIGEM AND dst.NOM_COLUNA_ORIGEM = src.NOM_COLUNA_ORIGEM)\n"
                f"WHEN MATCHED THEN UPDATE SET dst.NOM_OBJETO_DESTINO = src.NOM_OBJETO_DESTINO\n"
                f"WHEN NOT MATCHED THEN INSERT (SGL_PROJETO, NOM_OBJETO_ORIGEM, NOM_COLUNA_ORIGEM, NOM_OBJETO_DESTINO, NOM_COLUNA_DESTINO, IND_CARDINALIDADE)\n"
                f"VALUES (src.SGL_PROJETO, src.NOM_OBJETO_ORIGEM, src.NOM_COLUNA_ORIGEM, src.NOM_OBJETO_DESTINO, src.NOM_COLUNA_DESTINO, src.IND_CARDINALIDADE);\n"
            )
    linhas_04.append("COMMIT;\n")
    arquivos["04_meta_relacionamento.sql"] = "\n".join(linhas_04)

    # 05_meta_regra_negocio.sql
    linhas_05 = [
        "-- =============================================================================",
        f"-- NINHO — CATÁLOGO SEMÂNTICO: 05_meta_regra_negocio.sql (PROJETO: {projeto})",
        "-- =============================================================================",
        "",
        f"MERGE INTO {schema}.META_REGRA_NEGOCIO dst\n"
        f"USING (SELECT '{projeto}' AS SGL_PROJETO, 'RN_{projeto}_001' AS COD_REGRA, "
        f"'Filtro Obrigatório de Vigência SCD Tipo 2' AS NOM_REGRA, "
        f"'Toda consulta em dimensão histórica para estado atual deve filtrar DTC_EXPIRACAO IS NULL.' AS DES_REGRA, "
        f"'DTC_EXPIRACAO IS NULL' AS DES_EXPRESSAO_SQL FROM DUAL) src\n"
        f"ON (dst.SGL_PROJETO = src.SGL_PROJETO AND dst.COD_REGRA = src.COD_REGRA)\n"
        f"WHEN MATCHED THEN UPDATE SET dst.DES_REGRA = src.DES_REGRA\n"
        f"WHEN NOT MATCHED THEN INSERT (SGL_PROJETO, COD_REGRA, NOM_REGRA, DES_REGRA, DES_EXPRESSAO_SQL)\n"
        f"VALUES (src.SGL_PROJETO, src.COD_REGRA, src.NOM_REGRA, src.DES_REGRA, src.DES_EXPRESSAO_SQL);\n",
        f"MERGE INTO {schema}.META_REGRA_NEGOCIO dst\n"
        f"USING (SELECT '{projeto}' AS SGL_PROJETO, 'RN_{projeto}_002' AS COD_REGRA, "
        f"'Tratamento de Chave Surrogate Sentinela (-1)' AS NOM_REGRA, "
        f"'Chaves estrangeiras não informadas na origem são mapeadas para SK = -1 (Não Informado) evitando perda de fatos em INNER JOIN.' AS DES_REGRA, "
        f"'NVL(SK_DIM, -1)' AS DES_EXPRESSAO_SQL FROM DUAL) src\n"
        f"ON (dst.SGL_PROJETO = src.SGL_PROJETO AND dst.COD_REGRA = src.COD_REGRA)\n"
        f"WHEN MATCHED THEN UPDATE SET dst.DES_REGRA = src.DES_REGRA\n"
        f"WHEN NOT MATCHED THEN INSERT (SGL_PROJETO, COD_REGRA, NOM_REGRA, DES_REGRA, DES_EXPRESSAO_SQL)\n"
        f"VALUES (src.SGL_PROJETO, src.COD_REGRA, src.NOM_REGRA, src.DES_REGRA, src.DES_EXPRESSAO_SQL);\n",
        "COMMIT;\n",
    ]
    arquivos["05_meta_regra_negocio.sql"] = "\n".join(linhas_05)

    # 06_meta_pergunta_negocio.sql
    linhas_06 = [
        "-- =============================================================================",
        f"-- NINHO — CATÁLOGO SEMÂNTICO: 06_meta_pergunta_negocio.sql (PROJETO: {projeto})",
        "-- =============================================================================",
        "",
    ]
    for idx_f, f in enumerate(fatos, start=1):
        ent = _nome_entidade_curto(f["nome_tabela"])
        vw_kpi = f"VW_{projeto}_KPI_{ent}"
        linhas_06.append(
            f"MERGE INTO {schema}.META_PERGUNTA_NEGOCIO dst\n"
            f"USING (SELECT '{projeto}' AS SGL_PROJETO, 'PN_{projeto}_{idx_f:03d}' AS COD_PERGUNTA, "
            f"'Qual é o volume total e a participação percentual de {ent.title()} por categoria?' AS DES_PERGUNTA, "
            f"'SELECT * FROM {schema}.{vw_kpi} ORDER BY QTD_TOTAL_REGISTROS DESC' AS DES_SQL_REFERENCIA, "
            f"'{vw_kpi}' AS NOM_VIEW_RECOMENDADA FROM DUAL) src\n"
            f"ON (dst.SGL_PROJETO = src.SGL_PROJETO AND dst.COD_PERGUNTA = src.COD_PERGUNTA)\n"
            f"WHEN MATCHED THEN UPDATE SET dst.DES_SQL_REFERENCIA = src.DES_SQL_REFERENCIA\n"
            f"WHEN NOT MATCHED THEN INSERT (SGL_PROJETO, COD_PERGUNTA, DES_PERGUNTA, DES_SQL_REFERENCIA, NOM_VIEW_RECOMENDADA)\n"
            f"VALUES (src.SGL_PROJETO, src.COD_PERGUNTA, src.DES_PERGUNTA, src.DES_SQL_REFERENCIA, src.NOM_VIEW_RECOMENDADA);\n"
        )
    linhas_06.append("COMMIT;\n")
    arquivos["06_meta_pergunta_negocio.sql"] = "\n".join(linhas_06)

    # 07_meta_orientacao_ia.sql
    tpl_07 = TEMPLATES_SEM_DIR / "inserts" / "07_meta_orientacao_ia.sql"
    if tpl_07.exists():
        txt_07 = tpl_07.read_text(encoding="utf-8", errors="replace")
        txt_07 = txt_07.replace("<PROJETO>", projeto).replace("<SCHEMA>", schema)
        arquivos["07_meta_orientacao_ia.sql"] = txt_07
    else:
        arquivos["07_meta_orientacao_ia.sql"] = (
            f"-- 07_meta_orientacao_ia.sql ({projeto})\n"
            f"MERGE INTO {schema}.META_ORIENTACAO_IA dst\n"
            f"USING (SELECT '{projeto}' AS SGL_PROJETO, 'IA_001' AS COD_ORIENTACAO, "
            f"'Priorizar Views VW_{projeto}_KPI_* para perguntas agregadas e VW_{projeto}_EVENTO_* para detalhamento.' AS DES_ORIENTACAO FROM DUAL) src\n"
            f"ON (dst.SGL_PROJETO = src.SGL_PROJETO AND dst.COD_ORIENTACAO = src.COD_ORIENTACAO)\n"
            f"WHEN NOT MATCHED THEN INSERT (SGL_PROJETO, COD_ORIENTACAO, DES_ORIENTACAO) VALUES (src.SGL_PROJETO, src.COD_ORIENTACAO, src.DES_ORIENTACAO);\n"
            f"COMMIT;\n"
        )

    # 08_meta_valor_dominio.sql
    linhas_08 = [
        "-- =============================================================================",
        f"-- NINHO — CATÁLOGO SEMÂNTICO: 08_meta_valor_dominio.sql (PROJETO: {projeto})",
        "-- =============================================================================",
        "",
        f"MERGE INTO {schema}.META_VALOR_DOMINIO dst\n"
        f"USING (SELECT '{projeto}' AS SGL_PROJETO, 'FLG_PADRAO' AS NOM_DOMINIO, 'S' AS VLR_DOMINIO, 'Sim / Verdadeiro / Ativo' AS DES_SIGNIFICADO FROM DUAL) src\n"
        f"ON (dst.SGL_PROJETO = src.SGL_PROJETO AND dst.NOM_DOMINIO = src.NOM_DOMINIO AND dst.VLR_DOMINIO = src.VLR_DOMINIO)\n"
        f"WHEN NOT MATCHED THEN INSERT (SGL_PROJETO, NOM_DOMINIO, VLR_DOMINIO, DES_SIGNIFICADO) VALUES (src.SGL_PROJETO, src.NOM_DOMINIO, src.VLR_DOMINIO, src.DES_SIGNIFICADO);\n",
        f"MERGE INTO {schema}.META_VALOR_DOMINIO dst\n"
        f"USING (SELECT '{projeto}' AS SGL_PROJETO, 'FLG_PADRAO' AS NOM_DOMINIO, 'N' AS VLR_DOMINIO, 'Não / Falso / Inativo' AS DES_SIGNIFICADO FROM DUAL) src\n"
        f"ON (dst.SGL_PROJETO = src.SGL_PROJETO AND dst.NOM_DOMINIO = src.NOM_DOMINIO AND dst.VLR_DOMINIO = src.VLR_DOMINIO)\n"
        f"WHEN NOT MATCHED THEN INSERT (SGL_PROJETO, NOM_DOMINIO, VLR_DOMINIO, DES_SIGNIFICADO) VALUES (src.SGL_PROJETO, src.NOM_DOMINIO, src.VLR_DOMINIO, src.DES_SIGNIFICADO);\n",
        f"MERGE INTO {schema}.META_VALOR_DOMINIO dst\n"
        f"USING (SELECT '{projeto}' AS SGL_PROJETO, 'SK_SENTINELA' AS NOM_DOMINIO, '-1' AS VLR_DOMINIO, 'Não Informado / Não Aplicável na Origem' AS DES_SIGNIFICADO FROM DUAL) src\n"
        f"ON (dst.SGL_PROJETO = src.SGL_PROJETO AND dst.NOM_DOMINIO = src.NOM_DOMINIO AND dst.VLR_DOMINIO = src.VLR_DOMINIO)\n"
        f"WHEN NOT MATCHED THEN INSERT (SGL_PROJETO, NOM_DOMINIO, VLR_DOMINIO, DES_SIGNIFICADO) VALUES (src.SGL_PROJETO, src.NOM_DOMINIO, src.VLR_DOMINIO, src.DES_SIGNIFICADO);\n",
        "COMMIT;\n",
    ]
    arquivos["08_meta_valor_dominio.sql"] = "\n".join(linhas_08)

    return arquivos


def construir_script_rls(tabelas: list[dict], schema: str, projeto: str) -> str:
    """Gera `02_rls.sql` com Oracle VPD (`DBMS_RLS` + `SYS_CONTEXT`) para as Views Semânticas."""
    fatos = [t for t in tabelas if classificar_tabela_dw(t) == "FATO"]
    dims = [t for t in tabelas if classificar_tabela_dw(t) == "DIM"]
    nomes_dims = {t["nome_tabela"].upper() for t in dims}

    col_segregacao = "SK_UNIDADE"
    if fatos:
        fks = identificar_fks_fato(fatos[0], nomes_dims)
        if fks:
            col_segregacao = fks[0]["coluna"]

    linhas = [
        "-- =============================================================================",
        f"-- NINHO — SEGURANÇA RLS / ORACLE VPD: 02_rls.sql (PROJETO: {projeto})",
        f"-- Coluna de Segregação : {col_segregacao}",
        "-- =============================================================================",
        "",
        f"CREATE OR REPLACE CONTEXT CTX_{projeto}_RLS USING {schema}.PKG_SECURITY_{projeto};",
        "/",
        "",
        f"CREATE OR REPLACE PACKAGE {schema}.PKG_SECURITY_{projeto} AS",
        "    PROCEDURE PRC_SET_CONTEXTO(p_valor_filtro IN VARCHAR2, p_acesso_total IN VARCHAR2 DEFAULT 'N');",
        "    FUNCTION FN_PREDICADO_RLS(p_schema IN VARCHAR2, p_object IN VARCHAR2) RETURN VARCHAR2;",
        f"END PKG_SECURITY_{projeto};",
        "/",
        "",
        f"CREATE OR REPLACE PACKAGE BODY {schema}.PKG_SECURITY_{projeto} AS",
        "    PROCEDURE PRC_SET_CONTEXTO(p_valor_filtro IN VARCHAR2, p_acesso_total IN VARCHAR2 DEFAULT 'N') IS",
        "    BEGIN",
        f"        DBMS_SESSION.SET_CONTEXT('CTX_{projeto}_RLS', 'VALOR_FILTRO', p_valor_filtro);",
        f"        DBMS_SESSION.SET_CONTEXT('CTX_{projeto}_RLS', 'ACESSO_TOTAL', UPPER(NVL(p_acesso_total, 'N')));",
        "    END PRC_SET_CONTEXTO;",
        "",
        "    FUNCTION FN_PREDICADO_RLS(p_schema IN VARCHAR2, p_object IN VARCHAR2) RETURN VARCHAR2 IS",
        "        v_acesso_total VARCHAR2(10);",
        "        v_valor_filtro VARCHAR2(4000);",
        "    BEGIN",
        f"        v_acesso_total := SYS_CONTEXT('CTX_{projeto}_RLS', 'ACESSO_TOTAL');",
        f"        v_valor_filtro := SYS_CONTEXT('CTX_{projeto}_RLS', 'VALOR_FILTRO');",
        "        IF v_acesso_total = 'S' THEN",
        "            RETURN '1 = 1';",
        "        ELSIF v_valor_filtro IS NOT NULL THEN",
        f"            RETURN '{col_segregacao} IN (' || v_valor_filtro || ', -1)';",
        "        ELSE",
        "            -- Fail-Closed: sem contexto inicializado, bloqueia retorno de linhas sensíveis",
        "            RETURN '1 = 0';",
        "        END IF;",
        "    END FN_PREDICADO_RLS;",
        f"END PKG_SECURITY_{projeto};",
        "/",
        "",
    ]

    for f in fatos:
        ent = _nome_entidade_curto(f["nome_tabela"])
        for prefix in ("EVENTO", "KPI"):
            vw_name = f"VW_{projeto}_{prefix}_{ent}"
            pol_name = f"POL_RLS_{vw_name}"[:30]
            linhas.extend([
                "BEGIN",
                "    BEGIN",
                f"        DBMS_RLS.DROP_POLICY(object_schema => '{schema}', object_name => '{vw_name}', policy_name => '{pol_name}');",
                "    EXCEPTION WHEN OTHERS THEN NULL;",
                "    END;",
                "    DBMS_RLS.ADD_POLICY(",
                f"        object_schema   => '{schema}',",
                f"        object_name     => '{vw_name}',",
                f"        policy_name     => '{pol_name}',",
                f"        function_schema => '{schema}',",
                f"        policy_function => 'PKG_SECURITY_{projeto}.FN_PREDICADO_RLS',",
                "        statement_types => 'SELECT',",
                "        enable          => TRUE",
                "    );",
                "END;",
                "/",
                "",
            ])

    return "\n".join(linhas)


def construir_script_validacoes_semantica(tabelas: list[dict], schema: str, projeto: str) -> str:
    """Gera `09_validacoes.sql` para auditoria pós-implantação da Camada Semântica."""
    dims = [t for t in tabelas if classificar_tabela_dw(t) == "DIM"]
    fatos = [t for t in tabelas if classificar_tabela_dw(t) == "FATO"]

    linhas = [
        "-- =============================================================================",
        "-- NINHO — SMOKE TESTS E AUDITORIA DA CAMADA SEMÂNTICA: 09_validacoes.sql",
        f"-- Projeto: {projeto} | Schema: {schema}",
        "-- =============================================================================",
        "",
        "-- 1. Verificação de Objetos Inválidos no Schema",
        f"SELECT OBJECT_NAME, OBJECT_TYPE, STATUS FROM ALL_OBJECTS WHERE OWNER = '{schema}' AND OBJECT_NAME LIKE 'VW_{projeto}_%' AND STATUS <> 'VALID';",
        "",
        "-- 2. Contagem de Registros nas Views de Dimensão Vigente (Camada 1)",
    ]
    for d in dims:
        ent = _nome_entidade_curto(d["nome_tabela"])
        vw = f"VW_{projeto}_DIM_{ent}_ATUAL"
        linhas.append(f"SELECT '{vw}' AS VIEW_SEMANTICA, COUNT(1) AS QTD_VIGENTES FROM {schema}.{vw};")

    linhas.append("")
    linhas.append("-- 3. Contagem de Registros nas Views de Evento (Camada 2) e KPIs (Camada 3)")
    for f in fatos:
        ent = _nome_entidade_curto(f["nome_tabela"])
        vw_ev = f"VW_{projeto}_EVENTO_{ent}"
        vw_kpi = f"VW_{projeto}_KPI_{ent}"
        linhas.append(f"SELECT '{vw_ev}' AS VIEW_EVENTO, COUNT(1) AS QTD_LINHAS FROM {schema}.{vw_ev};")
        linhas.append(f"SELECT '{vw_kpi}' AS VIEW_KPI, COUNT(1) AS QTD_GRUPOS, SUM(QTD_TOTAL_REGISTROS) AS SOMA_EVENTOS FROM {schema}.{vw_kpi};")

    linhas.extend([
        "",
        "-- 4. Auditoria de Preenchimento do Catálogo META_* para o Projeto",
        f"SELECT 'META_GLOSSARIO' AS TABELA, COUNT(1) AS QTD FROM {schema}.META_GLOSSARIO WHERE SGL_PROJETO = '{projeto}'",
        "UNION ALL",
        f"SELECT 'META_METRICA', COUNT(1) FROM {schema}.META_METRICA WHERE SGL_PROJETO = '{projeto}'",
        "UNION ALL",
        f"SELECT 'META_RELACIONAMENTO', COUNT(1) FROM {schema}.META_RELACIONAMENTO WHERE SGL_PROJETO = '{projeto}';",
        "",
    ])
    return "\n".join(linhas)


def construir_documento_entendimento(tabelas: list[dict], schema: str, projeto: str) -> str:
    """Gera `DOCUMENTO_ENTENDIMENTO_<PROJETO>.md` em `saida/camada_semantica/meta_projeto/`."""
    dims = [t for t in tabelas if classificar_tabela_dw(t) == "DIM"]
    fatos = [t for t in tabelas if classificar_tabela_dw(t) == "FATO"]

    linhas = [
        f"# 🏛️ Documento de Entendimento da Camada Semântica — `{projeto}`",
        "",
        f"**Gerado em:** `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`  ",
        f"**Schema Oracle:** `{schema}`  ",
        f"**Sigla do Projeto:** `{projeto}`  ",
        "",
        "---",
        "",
        "## 1. Arquitetura em 3 Camadas de Views Analíticas",
        "",
        "| Camada | Nome da View | Tabela Base | Grão Declarado | Regra Principal |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ]
    for d in dims:
        ent = _nome_entidade_curto(d["nome_tabela"])
        nk = _obter_nk_dim(d)
        linhas.append(
            f"| **1. Dimensão Vigente** | `VW_{projeto}_DIM_{ent}_ATUAL` | `{d['nome_tabela']}` | 1 linha por `{nk}` vigente | `WHERE DTC_EXPIRACAO IS NULL` + `NVL` |"
        )
    for f in fatos:
        ent = _nome_entidade_curto(f["nome_tabela"])
        linhas.append(
            f"| **2. Evento Detalhado** | `VW_{projeto}_EVENTO_{ent}` | `{f['nome_tabela']}` | 1 linha por evento em `{f['nome_tabela']}` | `LEFT JOIN` dimensões + `NVL` |"
        )
        linhas.append(
            f"| **3. KPI Consolidado** | `VW_{projeto}_KPI_{ent}` | `VW_{projeto}_EVENTO_{ent}` | 1 linha por eixo dimensional agrupado | `SUM`/`AVG` + `NULLIF(..., 0)` |"
        )

    linhas.extend([
        "",
        "---",
        "",
        "## 2. Catálogo de Metadados Ativos (`META_*`)",
        "",
        "- **`01_meta_glossario.sql`**: Dicionário executivo de termos de negócio vinculados às Views.",
        "- **`02_meta_metrica.sql`**: Fórmulas oficiais de KPIs com proteção contra divisão por zero.",
        "- **`03_meta_hierarquia.sql`**: Caminhos de drill-down aprovados para ferramentas de BI.",
        "- **`04_meta_relacionamento.sql`**: Mapa de joins `N:1` entre Views de Evento e Views de Dimensão.",
        "- **`05_meta_regra_negocio.sql`**: Regras corporativas de filtragem SCD2 e tratamento da linha `-1`.",
        "- **`06_meta_pergunta_negocio.sql`**: Perguntas executivas com SQL de referência (Golden Queries).",
        "- **`07_meta_orientacao_ia.sql`**: Diretrizes de prompt engineering para agentes Text-to-SQL / LLM.",
        "- **`08_meta_valor_dominio.sql`**: Significado semântico de flags (`S`/`N`) e chaves sentinelas (`-1`).",
        "",
    ])
    return "\n".join(linhas)


def executar_modular_semantica(
    modo: str = "tudo",
    caminho_custom: Path | None = None,
    schema_override: str | None = None,
    projeto_override: str | None = None,
    incluir_rls: bool = True,
) -> list[Path]:
    """Executa os micro-processos solicitados da Camada Semântica e retorna os arquivos gerados."""
    arquivos_sql, pasta_origem = localizar_ddls_para_semantica(caminho_custom)
    if not arquivos_sql:
        print(
            "[ERRO] Nenhum arquivo .sql de DDL encontrado em:\n"
            f"  1) {ENTREGA_SEM_DDL_DIR}\n"
            f"  2) {SAIDA_DW_DIR / '03_dimensoes'} e {SAIDA_DW_DIR / '04_fatos'}\n"
            f"  3) {ENTREGA_DW_DDL_DIR}"
        )
        sys.exit(1)

    tabelas = carregar_tabelas_dw(arquivos_sql)
    if not tabelas:
        print("[ERRO] Nenhuma tabela DIM_* ou FATO_* identificada nos arquivos SQL analisados.")
        sys.exit(1)

    schema_det, projeto_det, _, _ = extrair_schema_e_projeto(tabelas)
    schema = (schema_override or schema_det).upper()
    projeto = (projeto_override or projeto_det).upper()

    vw_dir = SAIDA_SEM_DIR / "vw_analiticas"
    meta_dir = SAIDA_SEM_DIR / "meta_projeto"
    vw_dir.mkdir(parents=True, exist_ok=True)
    meta_dir.mkdir(parents=True, exist_ok=True)

    gerados: list[Path] = []

    if modo in ("views-dim", "views-semantica", "tudo"):
        p = vw_dir / "01_vw_dim_atuais.sql"
        p.write_text(construir_views_dim_atuais(tabelas, schema, projeto), encoding="utf-8")
        gerados.append(p)

    if modo in ("views-evento", "views-semantica", "tudo"):
        p = vw_dir / "02_vw_eventos.sql"
        p.write_text(construir_views_eventos(tabelas, schema, projeto), encoding="utf-8")
        gerados.append(p)

    if modo in ("views-kpi", "views-semantica", "tudo"):
        p = vw_dir / "03_vw_kpis.sql"
        p.write_text(construir_views_kpis(tabelas, schema, projeto), encoding="utf-8")
        gerados.append(p)

    if modo in ("catalogo-meta", "tudo"):
        ddl_meta_dst = meta_dir / "01_create_meta_tables.sql"
        ddl_meta_tpl = TEMPLATES_SEM_DIR / "01_create_meta_tables.sql"
        if not ddl_meta_dst.exists() and ddl_meta_tpl.exists():
            shutil.copy2(ddl_meta_tpl, ddl_meta_dst)
            gerados.append(ddl_meta_dst)

        scripts_meta = construir_catalogo_meta(tabelas, schema, projeto)
        for nome_arq, conteudo in scripts_meta.items():
            p = meta_dir / nome_arq
            p.write_text(conteudo, encoding="utf-8")
            gerados.append(p)

    if modo == "rls" or (modo == "tudo" and incluir_rls):
        p = meta_dir / "02_rls.sql"
        p.write_text(construir_script_rls(tabelas, schema, projeto), encoding="utf-8")
        gerados.append(p)

    if modo in ("validacoes", "tudo"):
        p = meta_dir / "09_validacoes.sql"
        p.write_text(construir_script_validacoes_semantica(tabelas, schema, projeto), encoding="utf-8")
        gerados.append(p)

    if modo in ("documento", "tudo"):
        p = meta_dir / f"DOCUMENTO_ENTENDIMENTO_{projeto}.md"
        p.write_text(construir_documento_entendimento(tabelas, schema, projeto), encoding="utf-8")
        gerados.append(p)

    print("=" * 80)
    print(f"✨ NINHO — CAMADA SEMÂNTICA MODULAR CONCLUÍDA (MODO: {modo.upper()})")
    print("=" * 80)
    print(f"  📂 Fonte DDL lida     : {pasta_origem}")
    print(f"  🏛️  Schema / Projeto   : {schema} / {projeto}")
    print(f"  📦 Arquivos gerados   : {len(gerados)}")
    for g in gerados:
        print(f"     - {g.relative_to(ROOT_DIR)}")
    print("=" * 80)

    return gerados


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Motor Modular da Camada Semântica Oracle (Micro-Processos & Fast-Track)"
    )
    parser.add_argument(
        "--modo",
        choices=[
            "views-dim",
            "views-evento",
            "views-kpi",
            "views-semantica",
            "catalogo-meta",
            "rls",
            "validacoes",
            "documento",
            "tudo",
        ],
        default="tudo",
        help="Selecione o micro-processo específico da Camada Semântica (padrão: tudo).",
    )
    parser.add_argument(
        "--caminho",
        type=str,
        default=None,
        help="Caminho opcional para pasta ou arquivo .sql com os DDLs do DW.",
    )
    parser.add_argument("--schema", type=str, default=None, help="Override do schema Oracle.")
    parser.add_argument("--projeto", type=str, default=None, help="Override da sigla do projeto.")
    parser.add_argument(
        "--sem-rls",
        action="store_true",
        help="Não gera 02_rls.sql quando --modo=tudo.",
    )

    args = parser.parse_args()
    caminho = Path(args.caminho) if args.caminho else None
    executar_modular_semantica(
        modo=args.modo,
        caminho_custom=caminho,
        schema_override=args.schema,
        projeto_override=args.projeto,
        incluir_rls=not args.sem_rls,
    )


if __name__ == "__main__":
    main()
