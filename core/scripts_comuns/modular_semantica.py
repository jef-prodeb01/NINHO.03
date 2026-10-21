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
from inspecionar_ddl_origem import ler_texto_sql

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
        txt = ler_texto_sql(arq)
        for t in parse_ddl_text(txt, arq.name):
            papel = classificar_tabela_dw(t)
            if papel in ("DIM", "FATO"):
                por_nome[t["nome_tabela"]] = t
    return list(por_nome.values())


def _nome_entidade_curto(nome_tabela: str) -> str:
    """Remove prefixos DIM_, FATO_, FAT_ para compor o nome canônico da View."""
    return re.sub(r"^(DIM|FATO|FAT)_", "", nome_tabela.upper())


def _obter_cfg_view_semantica(
    edicoes_sem: dict | None,
    camada: str,
    tabela_base: str,
    vw_default: str,
    grao_default: str = "Uma linha representa um registro.",
    ent: str | None = None,
) -> tuple[bool, str, str]:
    """Retorna (ativo, nome_view, grao) aplicando edições da Blueprint Semântica se existirem."""
    if not edicoes_sem:
        return True, vw_default, grao_default
    camada_up = camada.upper()
    if "DIM" in camada_up:
        cam_norm = "DIM"
    elif "EVENTO" in camada_up:
        cam_norm = "EVENTO"
    else:
        cam_norm = "KPI"
    ent_up = (ent or _nome_entidade_curto(tabela_base)).upper()
    mapa = edicoes_sem.get("views") or edicoes_sem.get("views_por_chave") or {}
    cfg = (
        mapa.get((cam_norm, tabela_base.upper()))
        or mapa.get((cam_norm, ent_up))
        or mapa.get((cam_norm, vw_default.upper()))
        or mapa.get((camada_up, tabela_base.upper()))
    )
    if not cfg:
        return True, vw_default, grao_default
    ativo = cfg.get("ativo", True)
    nome_vw = cfg.get("nome_view") or vw_default
    grao = cfg.get("grao") or grao_default
    if grao and "uma linha representa" not in grao.lower():
        grao = f"Uma linha representa {grao}"
    return ativo, nome_vw, grao


def construir_views_dim_atuais(
    tabelas: list[dict], schema: str, projeto: str, edicoes_sem: dict | None = None
) -> str:
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
        vw_default = f"VW_{projeto}_DIM_{entidade}_ATUAL"
        sk = _obter_sk_dim(d)
        nk = _obter_nk_dim(d)
        grao_default = f"Uma linha representa o registro atualmente vigente de {entidade} ({nk})."
        ativo, vw_name, grao_vw = _obter_cfg_view_semantica(
            edicoes_sem, "DIM", tname, vw_default, grao_default, entidade
        )
        if not ativo:
            continue

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
        linhas.append(f"-- Grão: {grao_vw}")
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

        desc_vw = f"View semântica de registros vigentes (SCD2 ativo) da dimensão {tname}. {grao_vw}".replace("'", "''")
        linhas.append(f"COMMENT ON TABLE {schema}.{vw_name} IS '{desc_vw}';")
        for c in cols_negocio:
            cname = c["nome_dw"]
            c_comment = c.get("comentario") or gerar_comentario_coluna(c, d, "DIM")
            c_comment_esc = c_comment.replace("'", "''")
            linhas.append(f"COMMENT ON COLUMN {schema}.{vw_name}.{cname} IS '{c_comment_esc}';")
        linhas.append("")

    return "\n".join(linhas)


def construir_views_eventos(
    tabelas: list[dict], schema: str, projeto: str, edicoes_sem: dict | None = None
) -> str:
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
        vw_default = f"VW_{projeto}_EVENTO_{entidade}"
        grao_default = f"Uma linha representa um evento individual registrado em {fname} enriquecido com suas dimensões."
        ativo, vw_name, grao_vw = _obter_cfg_view_semantica(
            edicoes_sem, "EVENTO", fname, vw_default, grao_default, entidade
        )
        if not ativo:
            continue
        fks = identificar_fks_fato(f, nomes_dims)

        linhas.append("-- -----------------------------------------------------------------------------")
        linhas.append(f"-- View Camada 2: {schema}.{vw_name}")
        linhas.append(f"-- Grão: {grao_vw}")
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

        grao_esc = grao_vw.replace("'", "''")
        linhas.append(f"COMMENT ON TABLE {schema}.{vw_name} IS 'View semântica de eventos detalhados de {fname}. {grao_esc}';")
        for cname, c_comm in comentarios_vw:
            c_comm_esc = c_comm.replace("'", "''")
            linhas.append(f"COMMENT ON COLUMN {schema}.{vw_name}.{cname} IS '{c_comm_esc}';")
        linhas.append("")

    return "\n".join(linhas)


def construir_views_kpis(
    tabelas: list[dict], schema: str, projeto: str, edicoes_sem: dict | None = None
) -> str:
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
        vw_ev_default = f"VW_{projeto}_EVENTO_{entidade}"
        _, vw_evento, _ = _obter_cfg_view_semantica(
            edicoes_sem, "EVENTO", fname, vw_ev_default, "", entidade
        )
        vw_kpi_default = f"VW_{projeto}_KPI_{entidade}"
        fks = identificar_fks_fato(f, nomes_dims)
        col_grupo = fks[0]["coluna"] if fks else f["colunas"][0]["nome_dw"]
        grao_default = f"Uma linha representa o consolidado de indicadores de {entidade} agrupado por {col_grupo}."
        ativo, vw_kpi, grao_kpi = _obter_cfg_view_semantica(
            edicoes_sem, "KPI", fname, vw_kpi_default, grao_default, entidade
        )
        if not ativo:
            continue

        metricas = [
            c["nome_dw"] for c in f["colunas"]
            if c["nome_dw"].startswith(("QTD_", "VLR_", "VAL_", "NUM_DIAS", "TMP_", "QT_"))
        ]

        linhas.append("-- -----------------------------------------------------------------------------")
        linhas.append(f"-- View Camada 3: {schema}.{vw_kpi}")
        linhas.append(f"-- Grão: {grao_kpi}")
        linhas.append("-- -----------------------------------------------------------------------------")
        linhas.append(f"CREATE OR REPLACE FORCE VIEW {schema}.{vw_kpi} AS")
        linhas.append("SELECT")

        exprs_kpi = [
            f"    e.{col_grupo} AS {col_grupo}",
            "    COUNT(1) AS QTD_TOTAL_REGISTROS",
        ]
        cols_ja_incluidas = {col_grupo.upper(), "QTD_TOTAL_REGISTROS", f"QTD_TOTAL_{entidade}".upper()}

        comentarios_kpi = [
            (col_grupo, f"Eixo dimensional de agrupamento ({col_grupo})."),
            ("QTD_TOTAL_REGISTROS", f"Volume total de eventos contabilizados em {fname}."),
        ]

        if edicoes_sem and edicoes_sem.get("metricas_definidas_bp"):
            todas_metricas_bp = list(edicoes_sem.get("metricas_ativas", [])) + list(edicoes_sem.get("radar_kpis", []))
            for m_bp in todas_metricas_bp:
                vw_rec = (m_bp.get("view_recomendada") or "").upper()
                if vw_rec and vw_rec not in (vw_kpi.upper(), vw_kpi_default.upper()):
                    continue
                cod_m = m_bp["cod_metrica"].upper()[:30]
                if cod_m in cols_ja_incluidas:
                    continue
                formula_m = m_bp["formula_sql"].strip()
                exprs_kpi.append(f"    {formula_m} AS {cod_m}")
                cols_ja_incluidas.add(cod_m)
                comentarios_kpi.append((cod_m, f"{m_bp['nom_metrica']} (Fórmula: {formula_m})."))
        else:
            for m in metricas[:4]:
                col_sum = f"SUM_{m[:24]}".upper()
                col_avg = f"AVG_{m[:24]}".upper()
                exprs_kpi.append(f"    SUM(NVL(e.{m}, 0)) AS {col_sum}")
                exprs_kpi.append(f"    ROUND(AVG(NVL(e.{m}, 0)), 2) AS {col_avg}")
                cols_ja_incluidas.add(col_sum)
                cols_ja_incluidas.add(f"SUM_{m}".upper())
                cols_ja_incluidas.add(col_avg)
                comentarios_kpi.append((col_sum, f"Somatório da métrica {m} no agrupamento."))
                comentarios_kpi.append((col_avg, f"Média aritmética da métrica {m} no agrupamento."))

            exprs_kpi.append("    ROUND((COUNT(1) * 100.0) / NULLIF(SUM(COUNT(1)) OVER (), 0), 2) AS PCT_PARTICIPACAO_TOTAL")
            cols_ja_incluidas.add("PCT_PARTICIPACAO_TOTAL")
            comentarios_kpi.append(("PCT_PARTICIPACAO_TOTAL", "Percentual de participação do grupo sobre o volume total geral (divisão segura com NULLIF)."))

        for idx_e, ex in enumerate(exprs_kpi):
            virg = "," if idx_e < len(exprs_kpi) - 1 else ""
            linhas.append(f"{ex}{virg}")

        linhas.append(f"FROM {schema}.{vw_evento} e")
        linhas.append(f"GROUP BY e.{col_grupo};")
        linhas.append("")

        grao_esc = grao_kpi.replace("'", "''")
        linhas.append(f"COMMENT ON TABLE {schema}.{vw_kpi} IS 'View semântica pré-agregada de KPIs executivos de {fname}. {grao_esc}';")
        for cname, c_comm in comentarios_kpi:
            c_comm_esc = c_comm.replace("'", "''")
            linhas.append(f"COMMENT ON COLUMN {schema}.{vw_kpi}.{cname} IS '{c_comm_esc}';")
        linhas.append("")

    return "\n".join(linhas)


def construir_catalogo_meta(
    tabelas: list[dict],
    schema: str,
    projeto: str,
    edicoes_sem: dict | None = None,
) -> dict[str, str]:
    """Gera os 8 scripts idempotentes `01_meta_glossario.sql` a `08_meta_valor_dominio.sql`."""
    dims = [t for t in tabelas if classificar_tabela_dw(t) == "DIM"]
    fatos = [t for t in tabelas if classificar_tabela_dw(t) == "FATO"]
    dims_map = {t["nome_tabela"].upper(): t for t in dims}
    nomes_dims = set(dims_map.keys())
    radar_ativos = (edicoes_sem or {}).get("radar_ativos", {})

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
        vw_default = f"VW_{projeto}_DIM_{ent}_ATUAL" if papel == "DIM" else f"VW_{projeto}_EVENTO_{ent}"
        camada_key = "DIM" if papel == "DIM" else "EVENTO"
        ativa, vw_ref, _ = _obter_cfg_view_semantica(edicoes_sem, camada_key, tname, vw_default, "Uma linha representa um registro.")
        if not ativa:
            continue
        identificador = f"{papel_label}_{ent}"[:200].replace("'", "''")
        dominio = ent[:100].replace("'", "''")
        definicao = (t.get("comentario_tabela") or f"Entidade oficial de {papel_label.lower()} para {ent} no projeto {projeto}.").replace("'", "''")
        sinonimos = f"{tname}, {vw_ref}"[:300].replace("'", "''")
        regra_uso = f"Consultar preferencialmente via view semântica {vw_ref}."[:1000].replace("'", "''")
        linhas_01.append(
            f"MERGE INTO {schema}.META_GLOSSARIO dst\n"
            f"USING (SELECT '{projeto}' AS PROJETO, '{dominio}' AS DOMINIO, '{identificador}' AS IDENTIFICADOR, "
            f"'{definicao}' AS DESCRICAO, '{sinonimos}' AS SINONIMOS, 'Ver catálogo de domínio' AS EXEMPLOS_VALORES, "
            f"'{regra_uso}' AS REGRA_USO, '{papel_label}' AS CLASSIFICACAO FROM DUAL) src\n"
            f"ON (dst.PROJETO = src.PROJETO AND dst.DOMINIO = src.DOMINIO AND dst.IDENTIFICADOR = src.IDENTIFICADOR)\n"
            f"WHEN MATCHED THEN UPDATE SET dst.DESCRICAO = src.DESCRICAO, dst.SINONIMOS = src.SINONIMOS, dst.REGRA_USO = src.REGRA_USO, dst.CLASSIFICACAO = src.CLASSIFICACAO\n"
            f"WHEN NOT MATCHED THEN INSERT (PROJETO, DOMINIO, IDENTIFICADOR, DESCRICAO, SINONIMOS, EXEMPLOS_VALORES, REGRA_USO, CLASSIFICACAO)\n"
            f"VALUES (src.PROJETO, src.DOMINIO, src.IDENTIFICADOR, src.DESCRICAO, src.SINONIMOS, src.EXEMPLOS_VALORES, src.REGRA_USO, src.CLASSIFICACAO);\n"
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
    if edicoes_sem and edicoes_sem.get("metricas_definidas_bp"):
        metricas_para_inserir = list(edicoes_sem.get("metricas_ativas", [])) + list(edicoes_sem.get("radar_kpis", []))
        cods_inseridos: set[str] = set()
        for m_bp in metricas_para_inserir:
            cod_m = m_bp["cod_metrica"].upper()[:100].replace("'", "''")
            if cod_m in cods_inseridos:
                continue
            cods_inseridos.add(cod_m)
            nom_m = m_bp["nom_metrica"].replace("'", "''")
            des_m = f"{nom_m} — {m_bp.get('des_metrica', m_bp['nom_metrica'])}".replace("'", "''")
            form_m = m_bp["formula_sql"].replace("'", "''")
            vw_m = m_bp["view_recomendada"].replace("'", "''")
            fmt_m = m_bp.get("tip_formato", "NUMERICO").replace("'", "''")
            form_upper = form_m.upper()
            if any(tok in form_upper for tok in ("AVG(", "ROUND(", "/", "NULLIF(", "DISTINCT")):
                aditividade = "NAO_ADITIVA"
            else:
                aditividade = "ADITIVA"
            linhas_02.append(
                f"MERGE INTO {schema}.META_METRICA dst\n"
                f"USING (SELECT '{projeto}' AS PROJETO, '{cod_m}' AS NOME_METRICA, "
                f"'{des_m}' AS DESCRICAO_NEGOCIO, "
                f"'{form_m}' AS FORMULA_SQL, '{aditividade}' AS TIPO_ADITIVIDADE, "
                f"'DTC_REFERENCIA' AS DATA_REFERENCIA, 'Nenhum' AS FILTROS_OBRIGATORIOS, "
                f"'{vw_m}' AS DIMENSOES_PERMITIDAS, '{fmt_m}' AS UNIDADE FROM DUAL) src\n"
                f"ON (dst.PROJETO = src.PROJETO AND dst.NOME_METRICA = src.NOME_METRICA)\n"
                f"WHEN MATCHED THEN UPDATE SET dst.DESCRICAO_NEGOCIO = src.DESCRICAO_NEGOCIO, dst.FORMULA_SQL = src.FORMULA_SQL, dst.TIPO_ADITIVIDADE = src.TIPO_ADITIVIDADE, dst.DIMENSOES_PERMITIDAS = src.DIMENSOES_PERMITIDAS, dst.UNIDADE = src.UNIDADE\n"
                f"WHEN NOT MATCHED THEN INSERT (PROJETO, NOME_METRICA, DESCRICAO_NEGOCIO, FORMULA_SQL, TIPO_ADITIVIDADE, DATA_REFERENCIA, FILTROS_OBRIGATORIOS, DIMENSOES_PERMITIDAS, UNIDADE)\n"
                f"VALUES (src.PROJETO, src.NOME_METRICA, src.DESCRICAO_NEGOCIO, src.FORMULA_SQL, src.TIPO_ADITIVIDADE, src.DATA_REFERENCIA, src.FILTROS_OBRIGATORIOS, src.DIMENSOES_PERMITIDAS, src.UNIDADE);\n"
            )
    else:
        for f in fatos:
            fname = f["nome_tabela"]
            ent = _nome_entidade_curto(fname)
            vw_kpi_default = f"VW_{projeto}_KPI_{ent}"
            _, vw_kpi, _ = _obter_cfg_view_semantica(edicoes_sem, "KPI", fname, vw_kpi_default, "Uma linha representa um grupo.")
            linhas_02.append(
                f"MERGE INTO {schema}.META_METRICA dst\n"
                f"USING (SELECT '{projeto}' AS PROJETO, 'QTD_TOTAL_{ent}' AS NOME_METRICA, "
                f"'Volume Total de {ent.title()} — Contagem total de registros na fato {fname}' AS DESCRICAO_NEGOCIO, "
                f"'COUNT(1)' AS FORMULA_SQL, 'ADITIVA' AS TIPO_ADITIVIDADE, "
                f"'DTC_REFERENCIA' AS DATA_REFERENCIA, 'Nenhum' AS FILTROS_OBRIGATORIOS, "
                f"'{vw_kpi}' AS DIMENSOES_PERMITIDAS, 'INTEIRO' AS UNIDADE FROM DUAL) src\n"
                f"ON (dst.PROJETO = src.PROJETO AND dst.NOME_METRICA = src.NOME_METRICA)\n"
                f"WHEN MATCHED THEN UPDATE SET dst.FORMULA_SQL = src.FORMULA_SQL, dst.DIMENSOES_PERMITIDAS = src.DIMENSOES_PERMITIDAS\n"
                f"WHEN NOT MATCHED THEN INSERT (PROJETO, NOME_METRICA, DESCRICAO_NEGOCIO, FORMULA_SQL, TIPO_ADITIVIDADE, DATA_REFERENCIA, FILTROS_OBRIGATORIOS, DIMENSOES_PERMITIDAS, UNIDADE)\n"
                f"VALUES (src.PROJETO, src.NOME_METRICA, src.DESCRICAO_NEGOCIO, src.FORMULA_SQL, src.TIPO_ADITIVIDADE, src.DATA_REFERENCIA, src.FILTROS_OBRIGATORIOS, src.DIMENSOES_PERMITIDAS, src.UNIDADE);\n"
            )
            for c in f["colunas"]:
                cname = c["nome_dw"]
                if cname.startswith(("QTD_", "VLR_", "VAL_", "QT_")):
                    linhas_02.append(
                        f"MERGE INTO {schema}.META_METRICA dst\n"
                        f"USING (SELECT '{projeto}' AS PROJETO, 'SUM_{cname}' AS NOME_METRICA, "
                        f"'Somatório de {cname} — Soma consolidada da coluna {cname} em {fname}' AS DESCRICAO_NEGOCIO, "
                        f"'SUM(NVL({cname}, 0))' AS FORMULA_SQL, 'ADITIVA' AS TIPO_ADITIVIDADE, "
                        f"'DTC_REFERENCIA' AS DATA_REFERENCIA, 'Nenhum' AS FILTROS_OBRIGATORIOS, "
                        f"'{vw_kpi}' AS DIMENSOES_PERMITIDAS, 'NUMERICO' AS UNIDADE FROM DUAL) src\n"
                        f"ON (dst.PROJETO = src.PROJETO AND dst.NOME_METRICA = src.NOME_METRICA)\n"
                        f"WHEN MATCHED THEN UPDATE SET dst.FORMULA_SQL = src.FORMULA_SQL\n"
                        f"WHEN NOT MATCHED THEN INSERT (PROJETO, NOME_METRICA, DESCRICAO_NEGOCIO, FORMULA_SQL, TIPO_ADITIVIDADE, DATA_REFERENCIA, FILTROS_OBRIGATORIOS, DIMENSOES_PERMITIDAS, UNIDADE)\n"
                        f"VALUES (src.PROJETO, src.NOME_METRICA, src.DESCRICAO_NEGOCIO, src.FORMULA_SQL, src.TIPO_ADITIVIDADE, src.DATA_REFERENCIA, src.FILTROS_OBRIGATORIOS, src.DIMENSOES_PERMITIDAS, src.UNIDADE);\n"
                    )
    linhas_02.append("COMMIT;\n")
    arquivos["02_meta_metrica.sql"] = "\n".join(linhas_02)

    # 03_meta_objeto.sql
    linhas_03 = [
        "-- =============================================================================",
        f"-- NINHO — CATÁLOGO SEMÂNTICO: 03_meta_objeto.sql (PROJETO: {projeto})",
        "-- =============================================================================",
        "",
    ]
    for d in dims:
        tname = d["nome_tabela"]
        ent = _nome_entidade_curto(tname)
        nk = _obter_nk_dim(d)
        vw_dim_default = f"VW_{projeto}_DIM_{ent}_ATUAL"
        grao_default = f"Uma linha representa 1 {nk} vigente"
        ativa, vw_dim, grao = _obter_cfg_view_semantica(edicoes_sem, "DIM", tname, vw_dim_default, grao_default)
        if not ativa:
            continue
        grao_esc = grao.replace("'", "''")[:500]
        linhas_03.append(
            f"MERGE INTO {schema}.META_OBJETO dst\n"
            f"USING (SELECT '{projeto}' AS PROJETO, '{vw_dim}' AS NOME_OBJETO, "
            f"'DIMENSAO' AS TIPO_OBJETO, '{ent[:100]}' AS DOMINIO, '{grao_esc}' AS GRAO, "
            f"'{schema}' AS SCHEMA_ORIGEM, '{tname}' AS OBJETO_FISICO, 'S' AS IND_GOVERNADO, 'S' AS IND_ATIVO FROM DUAL) src\n"
            f"ON (dst.PROJETO = src.PROJETO AND dst.NOME_OBJETO = src.NOME_OBJETO)\n"
            f"WHEN MATCHED THEN UPDATE SET dst.TIPO_OBJETO = src.TIPO_OBJETO, dst.GRAO = src.GRAO, dst.OBJETO_FISICO = src.OBJETO_FISICO\n"
            f"WHEN NOT MATCHED THEN INSERT (PROJETO, NOME_OBJETO, TIPO_OBJETO, DOMINIO, GRAO, SCHEMA_ORIGEM, OBJETO_FISICO, IND_GOVERNADO, IND_ATIVO, DT_INICIO_VIGENCIA)\n"
            f"VALUES (src.PROJETO, src.NOME_OBJETO, src.TIPO_OBJETO, src.DOMINIO, src.GRAO, src.SCHEMA_ORIGEM, src.OBJETO_FISICO, src.IND_GOVERNADO, src.IND_ATIVO, SYSDATE);\n"
        )
    for f in fatos:
        fname = f["nome_tabela"]
        ent = _nome_entidade_curto(fname)
        vw_ev_default = f"VW_{projeto}_EVENTO_{ent}"
        grao_ev_default = f"Uma linha representa 1 evento em {fname}"
        ativa_ev, vw_ev, grao_ev = _obter_cfg_view_semantica(edicoes_sem, "EVENTO", fname, vw_ev_default, grao_ev_default)
        if ativa_ev:
            grao_ev_esc = grao_ev.replace("'", "''")[:500]
            linhas_03.append(
                f"MERGE INTO {schema}.META_OBJETO dst\n"
                f"USING (SELECT '{projeto}' AS PROJETO, '{vw_ev}' AS NOME_OBJETO, "
                f"'EVENTO' AS TIPO_OBJETO, '{ent[:100]}' AS DOMINIO, '{grao_ev_esc}' AS GRAO, "
                f"'{schema}' AS SCHEMA_ORIGEM, '{fname}' AS OBJETO_FISICO, 'S' AS IND_GOVERNADO, 'S' AS IND_ATIVO FROM DUAL) src\n"
                f"ON (dst.PROJETO = src.PROJETO AND dst.NOME_OBJETO = src.NOME_OBJETO)\n"
                f"WHEN MATCHED THEN UPDATE SET dst.TIPO_OBJETO = src.TIPO_OBJETO, dst.GRAO = src.GRAO, dst.OBJETO_FISICO = src.OBJETO_FISICO\n"
                f"WHEN NOT MATCHED THEN INSERT (PROJETO, NOME_OBJETO, TIPO_OBJETO, DOMINIO, GRAO, SCHEMA_ORIGEM, OBJETO_FISICO, IND_GOVERNADO, IND_ATIVO, DT_INICIO_VIGENCIA)\n"
                f"VALUES (src.PROJETO, src.NOME_OBJETO, src.TIPO_OBJETO, src.DOMINIO, src.GRAO, src.SCHEMA_ORIGEM, src.OBJETO_FISICO, src.IND_GOVERNADO, src.IND_ATIVO, SYSDATE);\n"
            )
        vw_kpi_default = f"VW_{projeto}_KPI_{ent}"
        grao_kpi_default = "Uma linha representa 1 eixo dimensional agrupado"
        ativa_kpi, vw_kpi, grao_kpi = _obter_cfg_view_semantica(edicoes_sem, "KPI", fname, vw_kpi_default, grao_kpi_default)
        if ativa_kpi:
            grao_kpi_esc = grao_kpi.replace("'", "''")[:500]
            linhas_03.append(
                f"MERGE INTO {schema}.META_OBJETO dst\n"
                f"USING (SELECT '{projeto}' AS PROJETO, '{vw_kpi}' AS NOME_OBJETO, "
                f"'KPI' AS TIPO_OBJETO, '{ent[:100]}' AS DOMINIO, '{grao_kpi_esc}' AS GRAO, "
                f"'{schema}' AS SCHEMA_ORIGEM, '{vw_ev if ativa_ev else fname}' AS OBJETO_FISICO, 'S' AS IND_GOVERNADO, 'S' AS IND_ATIVO FROM DUAL) src\n"
                f"ON (dst.PROJETO = src.PROJETO AND dst.NOME_OBJETO = src.NOME_OBJETO)\n"
                f"WHEN MATCHED THEN UPDATE SET dst.TIPO_OBJETO = src.TIPO_OBJETO, dst.GRAO = src.GRAO, dst.OBJETO_FISICO = src.OBJETO_FISICO\n"
                f"WHEN NOT MATCHED THEN INSERT (PROJETO, NOME_OBJETO, TIPO_OBJETO, DOMINIO, GRAO, SCHEMA_ORIGEM, OBJETO_FISICO, IND_GOVERNADO, IND_ATIVO, DT_INICIO_VIGENCIA)\n"
                f"VALUES (src.PROJETO, src.NOME_OBJETO, src.TIPO_OBJETO, src.DOMINIO, src.GRAO, src.SCHEMA_ORIGEM, src.OBJETO_FISICO, src.IND_GOVERNADO, src.IND_ATIVO, SYSDATE);\n"
            )
    linhas_03.append("COMMIT;\n")
    arquivos["03_meta_objeto.sql"] = "\n".join(linhas_03)

    # 04_meta_relacionamento.sql
    linhas_04 = [
        "-- =============================================================================",
        f"-- NINHO — CATÁLOGO SEMÂNTICO: 04_meta_relacionamento.sql (PROJETO: {projeto})",
        "-- =============================================================================",
        "",
    ]
    for f in fatos:
        ent_f = _nome_entidade_curto(f["nome_tabela"])
        vw_ev_default = f"VW_{projeto}_EVENTO_{ent_f}"
        ativa_ev, vw_ev, _ = _obter_cfg_view_semantica(edicoes_sem, "EVENTO", f["nome_tabela"], vw_ev_default, "Uma linha representa um evento.")
        if not ativa_ev:
            continue
        for fk in identificar_fks_fato(f, nomes_dims):
            dim_ref = fk["tabela_ref"].upper()
            ent_d = _nome_entidade_curto(dim_ref)
            vw_dim_default = f"VW_{projeto}_DIM_{ent_d}_ATUAL"
            ativa_dim, vw_dim, _ = _obter_cfg_view_semantica(edicoes_sem, "DIM", dim_ref, vw_dim_default, "Uma linha representa um registro.")
            if not ativa_dim:
                continue
            col_pk_dim = _obter_sk_dim(dims_map[dim_ref]) if dim_ref in dims_map else "DIMENSION_KEY"
            obs = f"Join dimensional N:1 entre {vw_ev} e {vw_dim} com fallback sentinela (-1).".replace("'", "''")
            linhas_04.append(
                f"MERGE INTO {schema}.META_RELACIONAMENTO dst\n"
                f"USING (SELECT '{projeto}' AS PROJETO, '{vw_ev}' AS OBJETO_ORIGEM, "
                f"'{fk['coluna']}' AS COLUNA_ORIGEM, '{vw_dim}' AS OBJETO_DESTINO, "
                f"'{col_pk_dim}' AS COLUNA_DESTINO, 'LEFT' AS TIPO_JOIN, 'N:1' AS CARDINALIDADE, "
                f"'{obs}' AS OBSERVACAO FROM DUAL) src\n"
                f"ON (dst.PROJETO = src.PROJETO AND dst.OBJETO_ORIGEM = src.OBJETO_ORIGEM AND dst.COLUNA_ORIGEM = src.COLUNA_ORIGEM AND dst.OBJETO_DESTINO = src.OBJETO_DESTINO AND dst.COLUNA_DESTINO = src.COLUNA_DESTINO)\n"
                f"WHEN MATCHED THEN UPDATE SET dst.TIPO_JOIN = src.TIPO_JOIN, dst.CARDINALIDADE = src.CARDINALIDADE, dst.OBSERVACAO = src.OBSERVACAO\n"
                f"WHEN NOT MATCHED THEN INSERT (PROJETO, OBJETO_ORIGEM, COLUNA_ORIGEM, OBJETO_DESTINO, COLUNA_DESTINO, TIPO_JOIN, CARDINALIDADE, OBSERVACAO)\n"
                f"VALUES (src.PROJETO, src.OBJETO_ORIGEM, src.COLUNA_ORIGEM, src.OBJETO_DESTINO, src.COLUNA_DESTINO, src.TIPO_JOIN, src.CARDINALIDADE, src.OBSERVACAO);\n"
            )
    linhas_04.append("COMMIT;\n")
    arquivos["04_meta_relacionamento.sql"] = "\n".join(linhas_04)

    # 05_meta_regra_negocio.sql
    linhas_05 = [
        "-- =============================================================================",
        f"-- NINHO — CATÁLOGO SEMÂNTICO: 05_meta_regra_negocio.sql (PROJETO: {projeto})",
        "-- =============================================================================",
        "",
    ]
    if radar_ativos.get("RADAR_SEM_01", True):
        linhas_05.append(
            f"MERGE INTO {schema}.META_REGRA_NEGOCIO dst\n"
            f"USING (SELECT '{projeto}' AS PROJETO, "
            f"'RN_{projeto}_001: Toda consulta em dimensão histórica para estado atual deve filtrar DTC_EXPIRACAO IS NULL.' AS REGRA, "
            f"'ALTA' AS SEVERIDADE, 'ATIVA' AS STATUS_REGRA, 'FILTRO_SCD2' AS CONTEXTO, "
            f"'Expressão SQL padrão: DTC_EXPIRACAO IS NULL' AS OBSERVACAO FROM DUAL) src\n"
            f"ON (dst.PROJETO = src.PROJETO AND dst.REGRA = src.REGRA)\n"
            f"WHEN MATCHED THEN UPDATE SET dst.SEVERIDADE = src.SEVERIDADE, dst.STATUS_REGRA = src.STATUS_REGRA, dst.OBSERVACAO = src.OBSERVACAO\n"
            f"WHEN NOT MATCHED THEN INSERT (PROJETO, REGRA, SEVERIDADE, STATUS_REGRA, CONTEXTO, OBSERVACAO)\n"
            f"VALUES (src.PROJETO, src.REGRA, src.SEVERIDADE, src.STATUS_REGRA, src.CONTEXTO, src.OBSERVACAO);\n"
        )
    if radar_ativos.get("RADAR_SEM_02", True):
        linhas_05.append(
            f"MERGE INTO {schema}.META_REGRA_NEGOCIO dst\n"
            f"USING (SELECT '{projeto}' AS PROJETO, "
            f"'RN_{projeto}_002: Chaves estrangeiras não informadas na origem são mapeadas para SK = -1 (Não Informado) evitando perda de fatos em INNER JOIN.' AS REGRA, "
            f"'ALTA' AS SEVERIDADE, 'ATIVA' AS STATUS_REGRA, 'INTEGRIDADE_DIMENSIONAL' AS CONTEXTO, "
            f"'Expressão SQL padrão: NVL(SK_DIM, -1)' AS OBSERVACAO FROM DUAL) src\n"
            f"ON (dst.PROJETO = src.PROJETO AND dst.REGRA = src.REGRA)\n"
            f"WHEN MATCHED THEN UPDATE SET dst.SEVERIDADE = src.SEVERIDADE, dst.STATUS_REGRA = src.STATUS_REGRA, dst.OBSERVACAO = src.OBSERVACAO\n"
            f"WHEN NOT MATCHED THEN INSERT (PROJETO, REGRA, SEVERIDADE, STATUS_REGRA, CONTEXTO, OBSERVACAO)\n"
            f"VALUES (src.PROJETO, src.REGRA, src.SEVERIDADE, src.STATUS_REGRA, src.CONTEXTO, src.OBSERVACAO);\n"
        )
    if radar_ativos.get("RADAR_SEM_03", False):
        linhas_05.append(
            f"MERGE INTO {schema}.META_REGRA_NEGOCIO dst\n"
            f"USING (SELECT '{projeto}' AS PROJETO, "
            f"'RN_{projeto}_003: Toda métrica de proporção ou taxa deve proteger o denominador com NULLIF(denominador, 0) para impedir ORA-01476.' AS REGRA, "
            f"'MEDIA' AS SEVERIDADE, 'ATIVA' AS STATUS_REGRA, 'DIVISAO_SEGURA' AS CONTEXTO, "
            f"'Expressão SQL padrão: ROUND(NUMERADOR / NULLIF(DENOMINADOR, 0), 2)' AS OBSERVACAO FROM DUAL) src\n"
            f"ON (dst.PROJETO = src.PROJETO AND dst.REGRA = src.REGRA)\n"
            f"WHEN MATCHED THEN UPDATE SET dst.SEVERIDADE = src.SEVERIDADE, dst.STATUS_REGRA = src.STATUS_REGRA, dst.OBSERVACAO = src.OBSERVACAO\n"
            f"WHEN NOT MATCHED THEN INSERT (PROJETO, REGRA, SEVERIDADE, STATUS_REGRA, CONTEXTO, OBSERVACAO)\n"
            f"VALUES (src.PROJETO, src.REGRA, src.SEVERIDADE, src.STATUS_REGRA, src.CONTEXTO, src.OBSERVACAO);\n"
        )
    if radar_ativos.get("RADAR_SEM_04", False):
        linhas_05.append(
            f"MERGE INTO {schema}.META_REGRA_NEGOCIO dst\n"
            f"USING (SELECT '{projeto}' AS PROJETO, "
            f"'RN_{projeto}_004: Sessões sem contexto inicializado em SYS_CONTEXT recebem predicado 1=0 (Fail-Closed).' AS REGRA, "
            f"'ALTA' AS SEVERIDADE, 'ATIVA' AS STATUS_REGRA, 'SEGURANCA_RLS' AS CONTEXTO, "
            f"'Expressão SQL padrão: SYS_CONTEXT(''CTX_{projeto}_RLS'', ''VALOR_FILTRO'') IS NOT NULL' AS OBSERVACAO FROM DUAL) src\n"
            f"ON (dst.PROJETO = src.PROJETO AND dst.REGRA = src.REGRA)\n"
            f"WHEN MATCHED THEN UPDATE SET dst.SEVERIDADE = src.SEVERIDADE, dst.STATUS_REGRA = src.STATUS_REGRA, dst.OBSERVACAO = src.OBSERVACAO\n"
            f"WHEN NOT MATCHED THEN INSERT (PROJETO, REGRA, SEVERIDADE, STATUS_REGRA, CONTEXTO, OBSERVACAO)\n"
            f"VALUES (src.PROJETO, src.REGRA, src.SEVERIDADE, src.STATUS_REGRA, src.CONTEXTO, src.OBSERVACAO);\n"
        )
    linhas_05.append("COMMIT;\n")
    arquivos["05_meta_regra_negocio.sql"] = "\n".join(linhas_05)

    # 06_meta_consulta_negocio.sql
    linhas_06 = [
        "-- =============================================================================",
        f"-- NINHO — CATÁLOGO SEMÂNTICO: 06_meta_consulta_negocio.sql (PROJETO: {projeto})",
        "-- =============================================================================",
        "",
    ]
    for idx_f, f in enumerate(fatos, start=1):
        ent = _nome_entidade_curto(f["nome_tabela"])
        vw_kpi_default = f"VW_{projeto}_KPI_{ent}"
        _, vw_kpi, _ = _obter_cfg_view_semantica(edicoes_sem, "KPI", f["nome_tabela"], vw_kpi_default, "Uma linha representa um grupo.")
        id_cons = f"PN_{projeto}_{idx_f:03d}"[:50]
        linhas_06.append(
            f"MERGE INTO {schema}.META_CONSULTA_NEGOCIO dst\n"
            f"USING (SELECT '{projeto}' AS PROJETO, '{id_cons}' AS ID_CONSULTA, "
            f"'Qual é o volume total e a participação percentual de {ent.title()} por categoria?' AS PERGUNTA_LINGUAGEM_NATURAL, "
            f"'PAINEL_{projeto}' AS PAINEL_RELACIONADO, 'Golden Query oficial da camada KPI' AS OBSERVACOES, "
            f"'SELECT * FROM {schema}.{vw_kpi} ORDER BY QTD_TOTAL_REGISTROS DESC' AS SQL_VALIDADO_INTERPRETACAO, "
            f"'{vw_kpi}' AS OBJETOS_CHAVE FROM DUAL) src\n"
            f"ON (dst.PROJETO = src.PROJETO AND dst.ID_CONSULTA = src.ID_CONSULTA)\n"
            f"WHEN MATCHED THEN UPDATE SET dst.PERGUNTA_LINGUAGEM_NATURAL = src.PERGUNTA_LINGUAGEM_NATURAL, dst.SQL_VALIDADO_INTERPRETACAO = src.SQL_VALIDADO_INTERPRETACAO, dst.OBJETOS_CHAVE = src.OBJETOS_CHAVE\n"
            f"WHEN NOT MATCHED THEN INSERT (PROJETO, ID_CONSULTA, PERGUNTA_LINGUAGEM_NATURAL, PAINEL_RELACIONADO, OBSERVACOES, SQL_VALIDADO_INTERPRETACAO, OBJETOS_CHAVE)\n"
            f"VALUES (src.PROJETO, src.ID_CONSULTA, src.PERGUNTA_LINGUAGEM_NATURAL, src.PAINEL_RELACIONADO, src.OBSERVACOES, src.SQL_VALIDADO_INTERPRETACAO, src.OBJETOS_CHAVE);\n"
        )
    if edicoes_sem:
        for pn_rad in edicoes_sem.get("perguntas_radar", []):
            cod_pn = pn_rad["cod_pergunta"].replace("'", "''")[:50]
            des_pn = pn_rad["des_pergunta"].replace("'", "''")
            sql_pn = pn_rad["sql_referencia"].replace("'", "''")
            vw_pn = pn_rad["view_recomendada"].replace("'", "''")
            linhas_06.append(
                f"MERGE INTO {schema}.META_CONSULTA_NEGOCIO dst\n"
                f"USING (SELECT '{projeto}' AS PROJETO, '{cod_pn}' AS ID_CONSULTA, "
                f"'{des_pn}' AS PERGUNTA_LINGUAGEM_NATURAL, "
                f"'PAINEL_{projeto}' AS PAINEL_RELACIONADO, 'Consulta analítica sugerida pelo Radar Consultivo' AS OBSERVACOES, "
                f"'{sql_pn}' AS SQL_VALIDADO_INTERPRETACAO, "
                f"'{vw_pn}' AS OBJETOS_CHAVE FROM DUAL) src\n"
                f"ON (dst.PROJETO = src.PROJETO AND dst.ID_CONSULTA = src.ID_CONSULTA)\n"
                f"WHEN MATCHED THEN UPDATE SET dst.PERGUNTA_LINGUAGEM_NATURAL = src.PERGUNTA_LINGUAGEM_NATURAL, dst.SQL_VALIDADO_INTERPRETACAO = src.SQL_VALIDADO_INTERPRETACAO, dst.OBJETOS_CHAVE = src.OBJETOS_CHAVE\n"
                f"WHEN NOT MATCHED THEN INSERT (PROJETO, ID_CONSULTA, PERGUNTA_LINGUAGEM_NATURAL, PAINEL_RELACIONADO, OBSERVACOES, SQL_VALIDADO_INTERPRETACAO, OBJETOS_CHAVE)\n"
                f"VALUES (src.PROJETO, src.ID_CONSULTA, src.PERGUNTA_LINGUAGEM_NATURAL, src.PAINEL_RELACIONADO, src.OBSERVACOES, src.SQL_VALIDADO_INTERPRETACAO, src.OBJETOS_CHAVE);\n"
            )
    linhas_06.append("COMMIT;\n")
    arquivos["06_meta_consulta_negocio.sql"] = "\n".join(linhas_06)

    # 07_meta_orientacao_ia.sql
    tpl_07 = TEMPLATES_SEM_DIR / "inserts" / "07_meta_orientacao_ia.sql"
    if tpl_07.exists():
        txt_07 = tpl_07.read_text(encoding="utf-8", errors="replace")
        txt_07 = txt_07.replace("<PROJETO>", projeto).replace("<SCHEMA>", schema)
        txt_07 = re.sub(r"\bMERGE\s+INTO\s+META_ORIENTACAO_IA\b", f"MERGE INTO {schema}.META_ORIENTACAO_IA", txt_07)
        bloco_proj_07 = (
            f"\n-- Diretriz Específica do Projeto {projeto}\n"
            f"MERGE INTO {schema}.META_ORIENTACAO_IA dst\n"
            f"USING (SELECT '{projeto}' AS PROJETO, 'REGRAS_GERAIS' AS SECAO, 1 AS ORDEM, "
            f"'Prioridade de Views do Projeto {projeto}' AS TITULO, "
            f"'Priorizar Views VW_{projeto}_KPI_* para perguntas agregadas e VW_{projeto}_EVENTO_* para detalhamento granular.' AS CONTEUDO FROM DUAL) src\n"
            f"ON (dst.PROJETO = src.PROJETO AND dst.SECAO = src.SECAO AND dst.ORDEM = src.ORDEM)\n"
            f"WHEN MATCHED THEN UPDATE SET dst.TITULO = src.TITULO, dst.CONTEUDO = src.CONTEUDO, dst.DT_ATUALIZACAO = SYSDATE\n"
            f"WHEN NOT MATCHED THEN INSERT (PROJETO, SECAO, ORDEM, TITULO, CONTEUDO) VALUES (src.PROJETO, src.SECAO, src.ORDEM, src.TITULO, src.CONTEUDO);\n"
            f"COMMIT;\n"
        )
        arquivos["07_meta_orientacao_ia.sql"] = txt_07.rstrip() + "\n" + bloco_proj_07
    else:
        arquivos["07_meta_orientacao_ia.sql"] = (
            f"-- 07_meta_orientacao_ia.sql ({projeto})\n"
            f"MERGE INTO {schema}.META_ORIENTACAO_IA dst\n"
            f"USING (SELECT '{projeto}' AS PROJETO, 'REGRAS_GERAIS' AS SECAO, 1 AS ORDEM, "
            f"'Prioridade de Views do Projeto {projeto}' AS TITULO, "
            f"'Priorizar Views VW_{projeto}_KPI_* para perguntas agregadas e VW_{projeto}_EVENTO_* para detalhamento.' AS CONTEUDO FROM DUAL) src\n"
            f"ON (dst.PROJETO = src.PROJETO AND dst.SECAO = src.SECAO AND dst.ORDEM = src.ORDEM)\n"
            f"WHEN MATCHED THEN UPDATE SET dst.TITULO = src.TITULO, dst.CONTEUDO = src.CONTEUDO\n"
            f"WHEN NOT MATCHED THEN INSERT (PROJETO, SECAO, ORDEM, TITULO, CONTEUDO) VALUES (src.PROJETO, src.SECAO, src.ORDEM, src.TITULO, src.CONTEUDO);\n"
            f"COMMIT;\n"
        )

    # 08_meta_valor_dominio.sql
    linhas_08 = [
        "-- =============================================================================",
        f"-- NINHO — CATÁLOGO SEMÂNTICO: 08_meta_valor_dominio.sql (PROJETO: {projeto})",
        "-- =============================================================================",
        "",
        f"MERGE INTO {schema}.META_VALOR_DOMINIO dst\n"
        f"USING (SELECT '{projeto}' AS PROJETO, 'GLOBAL' AS NOME_OBJETO, 'SIN_ATIVO' AS NOME_COLUNA, 'S' AS VALOR, 'Sim / Verdadeiro / Registro Vigente' AS DESCRICAO, 'S' AS IND_ATIVO FROM DUAL) src\n"
        f"ON (dst.PROJETO = src.PROJETO AND dst.NOME_OBJETO = src.NOME_OBJETO AND dst.NOME_COLUNA = src.NOME_COLUNA AND dst.VALOR = src.VALOR)\n"
        f"WHEN MATCHED THEN UPDATE SET dst.DESCRICAO = src.DESCRICAO, dst.IND_ATIVO = src.IND_ATIVO\n"
        f"WHEN NOT MATCHED THEN INSERT (PROJETO, NOME_OBJETO, NOME_COLUNA, VALOR, DESCRICAO, IND_ATIVO) VALUES (src.PROJETO, src.NOME_OBJETO, src.NOME_COLUNA, src.VALOR, src.DESCRICAO, src.IND_ATIVO);\n",
        f"MERGE INTO {schema}.META_VALOR_DOMINIO dst\n"
        f"USING (SELECT '{projeto}' AS PROJETO, 'GLOBAL' AS NOME_OBJETO, 'SIN_ATIVO' AS NOME_COLUNA, 'N' AS VALOR, 'Não / Falso / Registro Histórico Expirado' AS DESCRICAO, 'S' AS IND_ATIVO FROM DUAL) src\n"
        f"ON (dst.PROJETO = src.PROJETO AND dst.NOME_OBJETO = src.NOME_OBJETO AND dst.NOME_COLUNA = src.NOME_COLUNA AND dst.VALOR = src.VALOR)\n"
        f"WHEN MATCHED THEN UPDATE SET dst.DESCRICAO = src.DESCRICAO, dst.IND_ATIVO = src.IND_ATIVO\n"
        f"WHEN NOT MATCHED THEN INSERT (PROJETO, NOME_OBJETO, NOME_COLUNA, VALOR, DESCRICAO, IND_ATIVO) VALUES (src.PROJETO, src.NOME_OBJETO, src.NOME_COLUNA, src.VALOR, src.DESCRICAO, src.IND_ATIVO);\n",
        f"MERGE INTO {schema}.META_VALOR_DOMINIO dst\n"
        f"USING (SELECT '{projeto}' AS PROJETO, 'GLOBAL' AS NOME_OBJETO, 'SK_SENTINELA' AS NOME_COLUNA, '-1' AS VALOR, 'Não Informado / Não Aplicável na Origem' AS DESCRICAO, 'S' AS IND_ATIVO FROM DUAL) src\n"
        f"ON (dst.PROJETO = src.PROJETO AND dst.NOME_OBJETO = src.NOME_OBJETO AND dst.NOME_COLUNA = src.NOME_COLUNA AND dst.VALOR = src.VALOR)\n"
        f"WHEN MATCHED THEN UPDATE SET dst.DESCRICAO = src.DESCRICAO, dst.IND_ATIVO = src.IND_ATIVO\n"
        f"WHEN NOT MATCHED THEN INSERT (PROJETO, NOME_OBJETO, NOME_COLUNA, VALOR, DESCRICAO, IND_ATIVO) VALUES (src.PROJETO, src.NOME_OBJETO, src.NOME_COLUNA, src.VALOR, src.DESCRICAO, src.IND_ATIVO);\n",
        "COMMIT;\n",
    ]
    arquivos["08_meta_valor_dominio.sql"] = "\n".join(linhas_08)

    return arquivos


def construir_script_rls(
    tabelas: list[dict],
    schema: str,
    projeto: str,
    edicoes_sem: dict | None = None,
) -> str:
    """Gera `02_rls.sql` com Oracle VPD (`DBMS_RLS` + `SYS_CONTEXT`) para as Views Semânticas."""
    fatos = [t for t in tabelas if classificar_tabela_dw(t) == "FATO"]
    dims = [t for t in tabelas if classificar_tabela_dw(t) == "DIM"]
    nomes_dims = {t["nome_tabela"].upper() for t in dims}

    col_segregacao = "SK_UNIDADE"
    if fatos:
        fks = identificar_fks_fato(fatos[0], nomes_dims)
        if fks:
            col_segregacao = fks[0]["coluna"]

    if edicoes_sem:
        col_custom = (edicoes_sem.get("parametros", {}).get("COLUNA_SEGREGACAO_RLS") or "").strip()
        if col_custom:
            col_segregacao = col_custom.upper()

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
            vw_default = f"VW_{projeto}_{prefix}_{ent}"
            ativa, vw_name, _ = _obter_cfg_view_semantica(
                edicoes_sem, prefix, f["nome_tabela"], vw_default, "Uma linha representa um registro."
            )
            if not ativa:
                continue
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


def construir_script_validacoes_semantica(
    tabelas: list[dict],
    schema: str,
    projeto: str,
    edicoes_sem: dict | None = None,
) -> str:
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
        vw_default = f"VW_{projeto}_DIM_{ent}_ATUAL"
        ativa, vw, _ = _obter_cfg_view_semantica(edicoes_sem, "DIM", d["nome_tabela"], vw_default, "Uma linha representa um registro.")
        if ativa:
            linhas.append(f"SELECT '{vw}' AS VIEW_SEMANTICA, COUNT(1) AS QTD_VIGENTES FROM {schema}.{vw};")

    linhas.append("")
    linhas.append("-- 3. Contagem de Registros nas Views de Evento (Camada 2) e KPIs (Camada 3)")
    for f in fatos:
        ent = _nome_entidade_curto(f["nome_tabela"])
        vw_ev_default = f"VW_{projeto}_EVENTO_{ent}"
        vw_kpi_default = f"VW_{projeto}_KPI_{ent}"
        ativa_ev, vw_ev, _ = _obter_cfg_view_semantica(edicoes_sem, "EVENTO", f["nome_tabela"], vw_ev_default, "Uma linha representa um evento.")
        ativa_kpi, vw_kpi, _ = _obter_cfg_view_semantica(edicoes_sem, "KPI", f["nome_tabela"], vw_kpi_default, "Uma linha representa um grupo.")
        if ativa_ev:
            linhas.append(f"SELECT '{vw_ev}' AS VIEW_EVENTO, COUNT(1) AS QTD_LINHAS FROM {schema}.{vw_ev};")
        if ativa_kpi:
            linhas.append(f"SELECT '{vw_kpi}' AS VIEW_KPI, COUNT(1) AS QTD_GRUPOS, SUM(QTD_TOTAL_REGISTROS) AS SOMA_EVENTOS FROM {schema}.{vw_kpi};")

    linhas.extend([
        "",
        "-- 4. Auditoria de Preenchimento do Catálogo META_* para o Projeto",
        f"SELECT 'META_GLOSSARIO' AS TABELA, COUNT(1) AS QTD FROM {schema}.META_GLOSSARIO WHERE PROJETO = '{projeto}'",
        "UNION ALL",
        f"SELECT 'META_METRICA', COUNT(1) FROM {schema}.META_METRICA WHERE PROJETO = '{projeto}'",
        "UNION ALL",
        f"SELECT 'META_OBJETO', COUNT(1) FROM {schema}.META_OBJETO WHERE PROJETO = '{projeto}'",
        "UNION ALL",
        f"SELECT 'META_RELACIONAMENTO', COUNT(1) FROM {schema}.META_RELACIONAMENTO WHERE PROJETO = '{projeto}'",
        "UNION ALL",
        f"SELECT 'META_REGRA_NEGOCIO', COUNT(1) FROM {schema}.META_REGRA_NEGOCIO WHERE PROJETO = '{projeto}'",
        "UNION ALL",
        f"SELECT 'META_CONSULTA_NEGOCIO', COUNT(1) FROM {schema}.META_CONSULTA_NEGOCIO WHERE PROJETO = '{projeto}'",
        "UNION ALL",
        f"SELECT 'META_ORIENTACAO_IA', COUNT(1) FROM {schema}.META_ORIENTACAO_IA WHERE PROJETO IN ('{projeto}', 'GLOBAL')",
        "UNION ALL",
        f"SELECT 'META_VALOR_DOMINIO', COUNT(1) FROM {schema}.META_VALOR_DOMINIO WHERE PROJETO = '{projeto}';",
        "",
    ])
    return "\n".join(linhas)


def construir_documento_entendimento(
    tabelas: list[dict],
    schema: str,
    projeto: str,
    edicoes_sem: dict | None = None,
) -> str:
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
        vw_default = f"VW_{projeto}_DIM_{ent}_ATUAL"
        grao_default = f"Uma linha representa 1 `{nk}` vigente"
        ativa, vw_dim, grao = _obter_cfg_view_semantica(edicoes_sem, "DIM", d["nome_tabela"], vw_default, grao_default)
        if ativa:
            linhas.append(
                f"| **1. Dimensão Vigente** | `{vw_dim}` | `{d['nome_tabela']}` | {grao} | `WHERE DTC_EXPIRACAO IS NULL` + `NVL` |"
            )
    for f in fatos:
        ent = _nome_entidade_curto(f["nome_tabela"])
        vw_ev_default = f"VW_{projeto}_EVENTO_{ent}"
        grao_ev_default = f"Uma linha representa 1 evento em `{f['nome_tabela']}`"
        ativa_ev, vw_ev, grao_ev = _obter_cfg_view_semantica(edicoes_sem, "EVENTO", f["nome_tabela"], vw_ev_default, grao_ev_default)
        if ativa_ev:
            linhas.append(
                f"| **2. Evento Detalhado** | `{vw_ev}` | `{f['nome_tabela']}` | {grao_ev} | `LEFT JOIN` dimensões + `NVL` |"
            )
        vw_kpi_default = f"VW_{projeto}_KPI_{ent}"
        grao_kpi_default = "Uma linha representa 1 eixo dimensional agrupado"
        ativa_kpi, vw_kpi, grao_kpi = _obter_cfg_view_semantica(edicoes_sem, "KPI", f["nome_tabela"], vw_kpi_default, grao_kpi_default)
        if ativa_kpi:
            linhas.append(
                f"| **3. KPI Consolidado** | `{vw_kpi}` | `{vw_ev}` | {grao_kpi} | `SUM`/`AVG` + `NULLIF(..., 0)` |"
            )

    linhas.extend([
        "",
        "---",
        "",
        "## 2. Catálogo de Metadados Ativos (`META_*`)",
        "",
        "- **`01_meta_glossario.sql`**: Dicionário executivo de termos de negócio vinculados às Views.",
        "- **`02_meta_metrica.sql`**: Fórmulas oficiais de KPIs com proteção contra divisão por zero.",
        "- **`03_meta_objeto.sql`**: Catálogo de Views governadas (`DIMENSAO`, `EVENTO`, `KPI`) e grão declarado.",
        "- **`04_meta_relacionamento.sql`**: Mapa de joins `N:1` entre Views de Evento e Views de Dimensão.",
        "- **`05_meta_regra_negocio.sql`**: Regras corporativas de filtragem SCD2 e tratamento da linha `-1`.",
        "- **`06_meta_consulta_negocio.sql`**: Perguntas executivas com SQL de referência (Golden Queries).",
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
        if ddl_meta_tpl.exists():
            shutil.copy2(ddl_meta_tpl, ddl_meta_dst)
            gerados.append(ddl_meta_dst)
        for arq_legado in ("03_meta_hierarquia.sql", "06_meta_pergunta_negocio.sql"):
            p_leg = meta_dir / arq_legado
            if p_leg.exists():
                p_leg.unlink()

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
    print("-" * 80)
    print("  🧭 O QUE VOCÊ PODE FAZER AGORA (PRÓXIMOS PASSOS):")
    print("     • `/duvida camadas-views` ➔ Entender o papel de `VW_DIM`, `VW_EVENTO` e `VW_KPI`")
    print("     • `/validar-entrega`      ➔ Auditar a entrega completa na pasta `saida/`")
    print("     • `/empacotar-projeto`    ➔ Exportar a entrega final consolidada em `.zip`")
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
