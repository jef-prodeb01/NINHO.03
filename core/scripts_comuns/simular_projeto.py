#!/usr/bin/env python3
"""
NINHO — Gerador de Simulações e Blueprint Editável (Planejador DW & Camada Semântica)
=====================================================================================
Gera uma simulação ponta a ponta do projeto em uma Blueprint 100% editável antes de
fechar o cenário e iniciar a geração física na pasta `saida/`.

Fluxo de Trabalho:
  1. `simular`  : Lê os insumos/DDLs e gera a Blueprint de Simulação editável:
                  - `entrega/planejador_dw/SIMULACAO_BLUEPRINT_DW.md`
                  - `entrega/camada_semantica/SIMULACAO_BLUEPRINT_SEMANTICA.md`
  2. Revisão    : O Engenheiro de Dados tem ciência completa de como o projeto começa
                  e termina, podendo editar parâmetros, nomes de tabelas/colunas, tipos,
                  classificação SCD1/SCD2, descrições, KPIs do Radar da IA e quais
                  entregáveis serão gerados.
  3. `executar` : Verifica se a simulação está aprovada (`[x] SIMULAÇÃO 100% FECHADA...`
                  ou `--forcar`), lê todas as edições feitas na Blueprint e executa a
                  esteira real gerando os artefatos físicos em `saida/planejador_dw/`
                  e/ou `saida/camada_semantica/`.
  4. `status`   : Exibe o estado atual das Blueprints de Simulação (Pendente/Aprovada).
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
    construir_dicionario_html,
    construir_guia_bi_rapido,
    construir_guias_odi_modulares,
    construir_patches_ajustes_nao_destrutivos,
    construir_script_comentarios,
    construir_script_linha_default,
    construir_scripts_indices,
    construir_scripts_odi,
    construir_testes_integridade,
    extrair_schema_e_projeto,
    gerar_comentario_coluna,
    gerar_comentario_tabela,
    identificar_fks_fato,
    parse_ddl_text,
)
from modular_semantica import (
    _nome_entidade_curto,
    construir_catalogo_meta,
    construir_documento_entendimento,
    construir_script_rls,
    construir_script_validacoes_semantica,
    construir_views_dim_atuais,
    construir_views_eventos,
    construir_views_kpis,
    localizar_ddls_para_semantica,
)

ROOT_DIR = SCRIPT_DIR.parent.parent
ENTREGA_DW_DIR = ROOT_DIR / "entrega" / "planejador_dw"
ENTREGA_SEM_DIR = ROOT_DIR / "entrega" / "camada_semantica"
SAIDA_DW_DIR = ROOT_DIR / "saida" / "planejador_dw"
SAIDA_SEM_DIR = ROOT_DIR / "saida" / "camada_semantica"

BLUEPRINT_DW_PATH = ENTREGA_DW_DIR / "SIMULACAO_BLUEPRINT_DW.md"
BLUEPRINT_SEM_PATH = ENTREGA_SEM_DIR / "SIMULACAO_BLUEPRINT_SEMANTICA.md"


# =============================================================================
# 1. MOTOR DE PROPOSTA DIMENSIONAL (OLTP OU DW -> MODELO SIMULADO)
# =============================================================================

def _classificar_papel_coluna_dim(cname: str, sk_col: str, nk_col: str) -> str:
    """Classifica o papel/SCD de uma coluna em uma Dimensão."""
    u = cname.upper()
    if u == sk_col:
        return "SK"
    if u == nk_col:
        return "NK"
    if u in (
        "DTC_INICIO",
        "DTC_EFETIVACAO",
        "DTC_EXPIRACAO",
        "FLG_ATIVO",
        "SIN_ATIVO",
        "DT_INICIO_VIGENCIA",
        "DT_FIM_VIGENCIA",
    ):
        return "AUDITORIA_SCD2"
    if u.startswith(("DTC_", "DT_", "DAT_")):
        return "SCD1"
    if u.startswith(("DES_", "NOM_", "SGL_", "SIG_", "IND_", "FLG_", "COD_")):
        return "SCD2"
    return "SCD1"


def _classificar_papel_coluna_fato(cname: str, pks: list[str], fks_cols: set[str]) -> str:
    """Classifica o papel de uma coluna em uma Tabela Fato."""
    u = cname.upper()
    if u in fks_cols or u.startswith(("SK_", "DIM_")):
        return "FK_DIMENSAO"
    if u in pks:
        return "PK_DEGENERADA"
    if u.startswith(("QTD_", "VLR_", "VAL_", "NUM_DIAS", "TMP_", "PCT_", "QT_")):
        return "METRICA"
    if u.startswith(("DTC_", "DT_", "DAT_")):
        return "DATA_EVENTO"
    return "DIM_DEGENERADA"


def _converter_oltp_para_dw_se_necessario(tabelas_brutas: list[dict]) -> list[dict]:
    """
    Se as tabelas de entrada já forem DIM_* / FATO_*, preserva-as.
    Se forem tabelas OLTP (TB_*, TAB_*, CAD_*, MOV_*), projeta automaticamente DIM_* e FATO_*.
    """
    dims_ou_fatos = [
        t for t in tabelas_brutas
        if t["nome_tabela"].upper().startswith(("DIM_", "DM_", "FATO_", "FAT_", "FT_"))
    ]
    if dims_ou_fatos:
        return dims_ou_fatos

    propostas: list[dict] = []
    for idx, t in enumerate(tabelas_brutas):
        raw_name = re.sub(r"^(TB|TAB|TBL|CAD|MOV|REL|RL)_", "", t["nome_tabela"].upper())
        tem_metricas = any(c["nome_dw"].startswith(("QTD_", "VLR_", "VAL_", "QT_")) for c in t["colunas"])
        eh_fato = tem_metricas or (idx == len(tabelas_brutas) - 1 and len(tabelas_brutas) > 1)

        if not eh_fato:
            dim_name = f"DIM_{raw_name}"
            sk_name = "DIMENSION_KEY"
            cols_novas = [
                {
                    "nome_original": "SEQUENCE",
                    "nome_dw": sk_name,
                    "tipo_origem": "NUMBER(10)",
                    "tipo_oracle": "NUMBER(10)",
                    "obrigatorio": "NOT NULL",
                    "comentario": "",
                }
            ]
            for c in t["colunas"]:
                cols_novas.append(dict(c))
            for aud_col, aud_tipo, aud_obrig in [
                ("DTC_EFETIVACAO", "DATE", "NOT NULL"),
                ("DTC_EXPIRACAO", "DATE", "NULL"),
            ]:
                if not any(x["nome_dw"] == aud_col for x in cols_novas):
                    cols_novas.append({
                        "nome_original": "SYSDATE/SCD2",
                        "nome_dw": aud_col,
                        "tipo_origem": aud_tipo,
                        "tipo_oracle": aud_tipo,
                        "obrigatorio": aud_obrig,
                        "comentario": "",
                    })
            propostas.append({
                "arquivo": t.get("arquivo", "simulacao.sql"),
                "nome_completo_origem": t.get("nome_completo_origem", t["nome_tabela"]),
                "nome_tabela": dim_name,
                "tabela_origem": t["nome_tabela"],
                "comentario_tabela": t.get("comentario_tabela", ""),
                "colunas": cols_novas,
                "pks": [sk_name],
                "fks": [],
                "indices": [],
            })
        else:
            fato_name = f"FATO_{raw_name}"
            propostas.append({
                "arquivo": t.get("arquivo", "simulacao.sql"),
                "nome_completo_origem": t.get("nome_completo_origem", t["nome_tabela"]),
                "nome_tabela": fato_name,
                "tabela_origem": t["nome_tabela"],
                "comentario_tabela": t.get("comentario_tabela", ""),
                "colunas": [dict(c) for c in t["colunas"]],
                "pks": list(t.get("pks", [])),
                "fks": list(t.get("fks", [])),
                "indices": [],
            })
    return propostas


# =============================================================================
# 2. GERAÇÃO DO RELATÓRIO DE SIMULAÇÃO E BLUEPRINT EDITÁVEL — DW
# =============================================================================

def gerar_blueprint_simulacao_dw(
    tabelas: list[dict],
    schema: str,
    projeto: str,
    estrategia: str,
    pasta_origem: Path,
) -> str:
    """Constrói o conteúdo completo de `entrega/planejador_dw/SIMULACAO_BLUEPRINT_DW.md`."""
    dims = [t for t in tabelas if classificar_tabela_dw(t) == "DIM"]
    fatos = [t for t in tabelas if classificar_tabela_dw(t) == "FATO"]
    dims_map = {t["nome_tabela"].upper(): t for t in dims}
    nomes_dims = set(dims_map.keys())
    total_cols = sum(len(t["colunas"]) for t in tabelas)

    linhas = [
        f"# 🧪 Simulação Ponta a Ponta & Blueprint Editável — Planejador DW (`{projeto}`)",
        "",
        "> [!IMPORTANT]",
        "> **Como funciona esta Simulação Editável:**",
        "> 1. Este documento apresenta **exatamente como o seu projeto de Data Warehouse vai começar, transformar e terminar** antes de gerar qualquer script físico em `saida/planejador_dw/`.",
        "> 2. **Tudo abaixo é 100% editável**: você pode alterar parâmetros globais, desmarcar colunas (`[ ]`), renomear colunas destino, trocar tipos de dados Oracle, mudar a classificação `SCD1`/`SCD2`, editar descrições de negócio e escolher quais pastas/scripts serão gerados.",
        "> 3. Quando estiver de acordo com o cenário, marque `[x]` na caixa de aprovação da **Seção 1** e execute:",
        ">    `python core/scripts_comuns/simular_projeto.py --modulo dw --acao executar`",
        "",
        "---",
        "",
        "## 1. 🚦 Gate de Aprovação da Simulação (Controle de Esteira)",
        "",
        "- [ ] **SIMULAÇÃO 100% FECHADA E APROVADA PARA EXECUÇÃO REAL**",
        "",
        f"- **Data/Hora da Simulação:** `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`",
        f"- **Fonte Analisada:** `{pasta_origem}`",
        "",
        "---",
        "",
        "## 2. ⚙️ Parâmetros Globais Editáveis do Projeto",
        "",
        "Edite a coluna **Valor Configurado** caso deseje customizar schemas, estratégia de carga ou tablespaces:",
        "",
        "| Parâmetro | Valor Configurado | Descrição Técnica |",
        "| :--- | :--- | :--- |",
        f"| `PROJETO_SIGLA` | `{projeto}` | Sigla corporativa do projeto/assunto |",
        f"| `SCHEMA_DW` | `{schema}` | Schema Oracle onde residirão `DIM_*` e `FATO_*` |",
        f"| `SCHEMA_STG` | `STG_{projeto}` | Schema Oracle de Staging (`STG_*` e `ODI_DIM_*`) |",
        f"| `ESTRATEGIA_CARGA` | `{estrategia}` | `A` = Truncate & Load + Bitmap Index; `B` = MERGE Incremental + B-Tree |",
        f"| `TABLESPACE_DADOS` | `TS_DW_{projeto}_DAT` | Tablespace padrão de armazenamento de tabelas |",
        f"| `TABLESPACE_INDICES` | `TS_DW_{projeto}_IDX` | Tablespace dedicada para índices de performance |",
        "",
        "---",
        "",
        "## 3. 🗺️ Jornada Ponta a Ponta do Projeto (Como Começa e Como Termina)",
        "",
        "```mermaid",
        "flowchart LR",
        f'    A["1. Origem / DDL ({len(tabelas)} Tabelas)"] --> B["2. Staging (STG_*) & Auxiliares (ODI_DIM_*)"]',
        f'    B --> C["3. Dimensões SCD2 ({len(dims)} DIM_*) + Linha -1"]',
        f'    C --> D["4. Tabelas Fato ({len(fatos)} FATO_*) + FKs"]',
        '    D --> E["5. Pós-Carga (Índices + DBMS_STATS)"]',
        '    E --> F["6. Dicionário HTML + Guia BI + Guias ODI 12c"]',
        "```",
        "",
        "### Resumo Volumétrico da Simulação",
        "",
        "| Indicador da Arquitetura | Quantidade Simulada | Detalhamento |",
        "| :--- | :---: | :--- |",
        f"| **Tabelas de Dimensão (`DIM_*`)** | `{len(dims)}` | {', '.join('`' + d['nome_tabela'] + '`' for d in dims) or 'Nenhuma'} |",
        f"| **Tabelas Fato (`FATO_*`)** | `{len(fatos)}` | {', '.join('`' + f['nome_tabela'] + '`' for f in fatos) or 'Nenhuma'} |",
        f"| **Tabelas Auxiliares (`STG_*` + `ODI_DIM_*`)** | `{len(tabelas) + len(dims)}` | Preparação de carga e controle de versionamento SCD2 |",
        f"| **Total de Colunas Mapeadas** | `{total_cols}` | 100% comentadas e tipadas para o Oracle |",
        f"| **Sequences de Surrogate Key (`SEQ_*`)** | `{len(dims)}` | `CACHE 1000 NOORDER` para alta vazão |",
        "",
        "---",
        "",
        "## 4. 🛠️ Matriz De/Para Editável de Modelagem Dimensional",
        "",
        "> [!TIP]",
        "> Para **excluir** uma coluna da geração final, troque `[x]` por `[ ]` na primeira coluna. Para **renomear**, **mudar o tipo Oracle**, **alterar SCD1/SCD2** ou **ajustar o comentário**, basta editar o texto diretamente na célula da tabela correspondente.",
        "",
    ]

    for d in dims:
        tname = d["nome_tabela"]
        torig = d.get("tabela_origem", re.sub(r"^DIM_", "TB_", tname))
        sk = _obter_sk_dim(d)
        nk = _obter_nk_dim(d)
        desc_tab = d.get("comentario_tabela") or gerar_comentario_tabela(d, "DIM", projeto)

        linhas.extend([
            f"### 4.D. `{tname}` (Dimensão)",
            "",
            f"- **Tabela Origem:** `{torig}`",
            f"- **Tabela Destino:** `{tname}`",
            f"- **Papel Dimensional:** `DIMENSAO`",
            f"- **Chave Surrogate (SK):** `{sk}` | **Chave Natural (NK):** `{nk}`",
            f"- **Descrição da Tabela:** `{desc_tab}`",
            "",
            "| Ativo | Coluna Origem | Coluna Destino (DW) | Tipo Oracle | Classificação / SCD | Transformação / Default (`-1`) | Comentário de Negócio |",
            "| :---: | :--- | :--- | :--- | :--- | :--- | :--- |",
        ])

        for c in d["colunas"]:
            cname = c["nome_dw"]
            corig = c.get("nome_original", cname)
            tipo = c["tipo_oracle"]
            papel_scd = _classificar_papel_coluna_dim(cname, sk, nk)
            comm = c.get("comentario") or gerar_comentario_coluna(c, d, "DIM")
            comm = comm.replace("|", "/")

            if papel_scd == "SK":
                transf = f"SEQ_{tname}.NEXTVAL (Default: -1)"
            elif papel_scd == "NK":
                transf = "Chave de Negócio (Default: -1)"
            elif cname in ("DTC_INICIO", "DTC_EFETIVACAO"):
                transf = "SYSDATE (Default: 1900-01-01)"
            elif cname == "DTC_EXPIRACAO":
                transf = "NULL na vigência atual"
            elif cname in ("FLG_ATIVO", "SIN_ATIVO"):
                transf = "'S' vigente / 'N' expirado"
            elif tipo.startswith(("VARCHAR", "CHAR")):
                transf = "TRIM(UPPER(ORIGEM)) (Default: 'NÃO INFORMADO')"
            else:
                transf = "NVL(ORIGEM, 0)"

            linhas.append(
                f"| [x] | `{corig}` | `{cname}` | `{tipo}` | `{papel_scd}` | `{transf}` | {comm} |"
            )
        linhas.append("")

    for f in fatos:
        fname = f["nome_tabela"]
        forig = f.get("tabela_origem", re.sub(r"^(FATO|FAT)_", "TB_", fname))
        fks = identificar_fks_fato(f, nomes_dims)
        fks_cols = {fk["coluna"] for fk in fks}
        fks_por_col = {fk["coluna"]: fk for fk in fks}
        desc_tab = f.get("comentario_tabela") or gerar_comentario_tabela(f, "FATO", projeto)

        linhas.extend([
            f"### 4.F. `{fname}` (Fato)",
            "",
            f"- **Tabela Origem:** `{forig}`",
            f"- **Tabela Destino:** `{fname}`",
            f"- **Papel Dimensional:** `FATO`",
            f"- **Grão Declarado:** `Uma linha por evento/registro individual de {fname} associado às chaves {', '.join(sorted(fks_cols)) or 'de negócio'}.`",
            f"- **Descrição da Tabela:** `{desc_tab}`",
            "",
            "| Ativo | Coluna Origem | Coluna Destino (DW) | Tipo Oracle | Classificação / Papel | Regra de Lookup / Tratamento | Comentário de Negócio |",
            "| :---: | :--- | :--- | :--- | :--- | :--- | :--- |",
        ])

        for c in f["colunas"]:
            cname = c["nome_dw"]
            corig = c.get("nome_original", cname)
            tipo = c["tipo_oracle"]
            papel_col = _classificar_papel_coluna_fato(cname, f["pks"], fks_cols)
            comm = c.get("comentario") or gerar_comentario_coluna(c, f, "FATO")
            comm = comm.replace("|", "/")

            if cname in fks_por_col:
                fk_info = fks_por_col[cname]
                dim_ref = fk_info["tabela_ref"].upper()
                sk_ref = _obter_sk_dim(dims_map[dim_ref]) if dim_ref in dims_map else "DIMENSION_KEY"
                transf = f"NVL(LKP_{dim_ref}.{sk_ref}, -1)"
            elif papel_col == "METRICA":
                transf = f"NVL(stg.{cname}, 0)"
            else:
                transf = f"stg.{cname}"

            linhas.append(
                f"| [x] | `{corig}` | `{cname}` | `{tipo}` | `{papel_col}` | `{transf}` | {comm} |"
            )
        linhas.append("")

    linhas.extend([
        "---",
        "",
        "## 5. 🧪 Simulação Visual de Dados (Dry-Run Preview: Linha `-1` + Amostra)",
        "",
        "Abaixo está a prévia de como os registros ficarão estruturados no Oracle após a execução:",
        "",
    ])

    if dims:
        d0 = dims[0]
        sk0 = _obter_sk_dim(d0)
        nk0 = _obter_nk_dim(d0)
        linhas.extend([
            f"### Prévia Simulada: `{schema}.{d0['nome_tabela']}` (Com Linha Sentinela `-1` e Versionamento SCD2)",
            "",
            f"| `{sk0}` | `{nk0}` | Atributo Descritivo Principal | `DTC_EFETIVACAO` | `DTC_EXPIRACAO` | Cenário Simulado |",
            "| :---: | :---: | :--- | :---: | :---: | :--- |",
            "| `-1` | `-1` | `'NÃO INFORMADO'` | `1900-01-01` | `NULL` | Registro Sentinela Obrigatório (Evita perda em INNER JOIN) |",
            "| `101` | `10` | `'UNIDADE / REGISTRO EXEMPLO A (V1)'` | `2025-01-10` | `2026-03-14` | Histórico Expirado (SCD Tipo 2 fechado) |",
            "| `245` | `10` | `'UNIDADE / REGISTRO EXEMPLO A (V2 ATUAL)'` | `2026-03-15` | `NULL` | Versão Atual Vigente (`DTC_EXPIRACAO IS NULL`) |",
            "",
        ])

    linhas.extend([
        "---",
        "",
        "## 6. 💡 Radar Consultivo da IA (Sugestões Editáveis de Alto Valor)",
        "",
        "Marque `[x]` nas sugestões que deseja manter ativas ou `[ ]` para descartar:",
        "",
        "- [x] **RADAR_DW_01 (Integridade Referencial Tolerante a Falhas):** Garantir `NVL(DIMENSION_KEY, -1)` em todos os `LEFT JOIN` da consulta da Fato no ODI 12c, impedindo descarte silencioso de transações órfãs.",
        "- [x] **RADAR_DW_02 (Higienização Determinística em Staging):** Aplicar `TRIM(UPPER(...))` em siglas/códigos e padronizar descrições nulas como `'NÃO INFORMADO'`.",
        "- [x] **RADAR_DW_03 (Automação de Pós-Carga e Estatísticas CBO):** Gerar procedure `PRC_POS_CARGA_FATO` para gerenciar índices e atualizar `DBMS_STATS.GATHER_TABLE_STATS` automaticamente ao fim do pacote ODI.",
        "- [x] **RADAR_DW_04 (Auditoria Automatizada Pós-Carga):** Incluir script de Smoke Test para detectar duplicidade de chave natural ativa (`DTC_EXPIRACAO IS NULL`) nas dimensões.",
        "",
        "---",
        "",
        "## 7. 📦 Escopo de Entregáveis Físicos na Esteira Real (`saida/planejador_dw/`)",
        "",
        "Desmarque (`[ ]`) qualquer entregável que você **não** queira gerar ao executar a simulação aprovada:",
        "",
        "- [x] `01_tablespaces` : Script DDL de criação de Tablespaces de Dados e Índices (`01_controle_carga/01_create_tablespaces.sql`)",
        "- [x] `02_staging` : Script DDL das tabelas `STG_*` (`02_staging/02_create_stg_tables.sql`)",
        "- [x] `03_dimensoes_ddl` : Script DDL das tabelas `DIM_*` com comentários (`03_dimensoes/03_create_dim_tables.sql`)",
        "- [x] `03_odi_dim_tables` : Script DDL das tabelas auxiliares `ODI_DIM_*` (`03_dimensoes/03_create_odi_dim_tables.sql`)",
        "- [x] `03_selects_odi_dim` : Consultas SQL analíticas de SCD2 para o ODI (`03_dimensoes/03_selects_odi_dimensoes.sql`)",
        "- [x] `03_linha_default` : Script idempotente `MERGE INTO` da linha `-1` (`03_dimensoes/06_init_default_records.sql`)",
        "- [x] `04_fatos_ddl` : Script DDL das tabelas `FATO_*` com FKs `ENABLE NOVALIDATE` (`04_fatos/04_create_fato_tables.sql`)",
        "- [x] `04_select_odi_fato` : Consulta SQL de carga da Fato com `LEFT JOIN` e `NVL(-1)` (`04_fatos/04_select_odi_fato.sql`)",
        "- [x] `05_sequences` : Script de criação de Sequences `CACHE 1000 NOORDER` (`03_dimensoes/05_create_sequences.sql`)",
        "- [x] `06_indices` : Scripts de criação de Índices Bitmap/B-Tree e `DBMS_STATS` (`03_dimensoes/06_create_indexes_dim.sql` e `04_fatos/06_create_indexes_fato.sql`)",
        "- [x] `07_procedures` : Procedure `PRC_POS_CARGA_FATO` (`05_procedimentos_manutencao/07_prc_pos_carga_fato.sql`)",
        "- [x] `08_testes_qualidade` : Script de auditoria de integridade pós-carga (`10_testes_integridade/13_testes_integridade.sql`)",
        "- [x] `09_guias_odi` : Relatório de Estratégias e Guias passo a passo de Canvas ODI 12c (`09_relatorio_estrategias/`)",
        "- [x] `10_guia_bi` : Guia do Analista de BI e Power BI (`08_datasets_bi/GUIA_ANALISTA_BI_<PROJETO>.md`)",
        "- [x] `11_dicionario_html` : Dicionário de Dados HTML Interativo (`11_dicionario_dados/dicionario_dados.html`)",
        "",
    ])

    return "\n".join(linhas)


# =============================================================================
# 3. GERAÇÃO DO RELATÓRIO DE SIMULAÇÃO E BLUEPRINT EDITÁVEL — CAMADA SEMÂNTICA
# =============================================================================

def gerar_blueprint_simulacao_semantica(
    tabelas: list[dict],
    schema: str,
    projeto: str,
    pasta_origem: Path,
) -> str:
    """Constrói o conteúdo completo de `entrega/camada_semantica/SIMULACAO_BLUEPRINT_SEMANTICA.md`."""
    dims = [t for t in tabelas if classificar_tabela_dw(t) == "DIM"]
    fatos = [t for t in tabelas if classificar_tabela_dw(t) == "FATO"]
    nomes_dims = {t["nome_tabela"].upper() for t in dims}

    col_rls_padrao = "SK_UNIDADE"
    if fatos:
        fks_f0 = identificar_fks_fato(fatos[0], nomes_dims)
        if fks_f0:
            col_rls_padrao = fks_f0[0]["coluna"]

    linhas = [
        f"# 🧪 Simulação Ponta a Ponta & Blueprint Editável — Camada Semântica (`{projeto}`)",
        "",
        "> [!IMPORTANT]",
        "> **Como funciona esta Simulação Editável:**",
        "> 1. Este documento projeta **toda a arquitetura da Camada Semântica Oracle** (Views em 3 camadas, Catálogo Ativo `META_*` para IA/Text-to-SQL e Segurança RLS/VPD) antes da geração física em `saida/camada_semantica/`.",
        "> 2. **100% Editável**: revise ou edite os parâmetros, ative/desative Views, ajuste os KPIs e regras do Radar Consultivo e selecione os entregáveis desejados.",
        "> 3. Quando estiver pronto, marque `[x]` na caixa de aprovação da **Seção 1** e execute:",
        ">    `python core/scripts_comuns/simular_projeto.py --modulo semantica --acao executar`",
        "",
        "---",
        "",
        "## 1. 🚦 Gate de Aprovação da Simulação (Controle de Esteira)",
        "",
        "- [ ] **SIMULAÇÃO 100% FECHADA E APROVADA PARA EXECUÇÃO REAL**",
        "",
        f"- **Data/Hora da Simulação:** `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`",
        f"- **Fonte Analisada:** `{pasta_origem}`",
        "",
        "---",
        "",
        "## 2. ⚙️ Parâmetros Globais Editáveis da Camada Semântica",
        "",
        "| Parâmetro | Valor Configurado | Descrição Técnica |",
        "| :--- | :--- | :--- |",
        f"| `PROJETO_SIGLA` | `{projeto}` | Sigla usada nos prefixos `VW_<PROJETO>_*` e `SGL_PROJETO` nas tabelas `META_*` |",
        f"| `SCHEMA_SEMANTICA` | `{schema}` | Schema Oracle das Views Analíticas e tabelas `META_*` |",
        "| `CENARIO_META` | `2_MERGE_IDEMPOTENTE` | `1_NOVO_SCHEMA` ou `2_MERGE_IDEMPOTENTE` (preserva outros projetos) |",
        "| `ATIVAR_RLS_VPD` | `SIM` | `SIM` ou `NAO` para geração de política `DBMS_RLS` (`02_rls.sql`) |",
        f"| `COLUNA_SEGREGACAO_RLS` | `{col_rls_padrao}` | Chave usada pelo predicado VPD para isolamento multi-órgão/unidade |",
        "",
        "---",
        "",
        "## 3. 🗺️ Jornada Ponta a Ponta da Camada Semântica (Como Começa e Como Termina)",
        "",
        "```mermaid",
        "flowchart LR",
        f'    A["DW Físico ({len(dims)} DIM + {len(fatos)} FATO)"] --> B["Camada 1: Views Dimensão Atual (DTC_EXPIRACAO IS NULL)"]',
        '    A --> C["Camada 2: Views de Evento Detalhado (LEFT JOIN + NVL)"]',
        '    C --> D["Camada 3: Views de KPIs Consolidados (SUM/AVG + NULLIF)"]',
        '    B & C & D --> E["Catálogo Ativo META_* (8 Tabelas para Text-to-SQL & IA)"]',
        '    C & D --> F["Segurança RLS / VPD (SYS_CONTEXT + DBMS_RLS)"]',
        "```",
        "",
        "---",
        "",
        "## 4. 🛠️ Matriz Editável de Views Semânticas em 3 Camadas",
        "",
        "Desmarque `[ ]` caso queira omitir alguma View específica ou edite o grão e a regra de negócio:",
        "",
        "| Ativo | Camada | Nome da View Semântica | Tabela / View Base | Grão Declarado (`-- Grão:`) | Regra Semântica Aplicada |",
        "| :---: | :--- | :--- | :--- | :--- | :--- |",
    ]

    for d in dims:
        ent = _nome_entidade_curto(d["nome_tabela"])
        nk = _obter_nk_dim(d)
        vw_dim = f"VW_{projeto}_DIM_{ent}_ATUAL"
        linhas.append(
            f"| [x] | `CAMADA_1_DIM` | `{vw_dim}` | `{d['nome_tabela']}` | Uma linha representa o registro vigente de {ent} ({nk}) | `WHERE DTC_EXPIRACAO IS NULL` + `NVL('Não Informado')` |"
        )

    for f in fatos:
        ent = _nome_entidade_curto(f["nome_tabela"])
        vw_ev = f"VW_{projeto}_EVENTO_{ent}"
        vw_kpi = f"VW_{projeto}_KPI_{ent}"
        linhas.append(
            f"| [x] | `CAMADA_2_EVENTO` | `{vw_ev}` | `{f['nome_tabela']}` | Uma linha representa um evento individual de {ent} enriquecido | `LEFT JOIN` Dimensões + `NVL` + `IND_SITUACAO_EVENTO` |"
        )
        linhas.append(
            f"| [x] | `CAMADA_3_KPI` | `{vw_kpi}` | `{vw_ev}` | Uma linha representa o consolidado de KPIs de {ent} por eixo | `COUNT(1)`, `SUM`, `AVG` e `NULLIF(..., 0)` |"
        )

    linhas.extend([
        "",
        "---",
        "",
        "## 5. 📊 Catálogo Editável de Indicadores e Fórmulas (`META_METRICA`)",
        "",
        "| Ativo | Código da Métrica | Nome Executivo do Indicador | Fórmula SQL Oficial | View Recomendada | Formato |",
        "| :---: | :--- | :--- | :--- | :--- | :--- |",
    ])

    for f in fatos:
        ent = _nome_entidade_curto(f["nome_tabela"])
        vw_kpi = f"VW_{projeto}_KPI_{ent}"
        linhas.append(
            f"| [x] | `QTD_TOTAL_{ent}` | Volume Total de {ent.title()} | `COUNT(1)` | `{vw_kpi}` | `INTEIRO` |"
        )
        linhas.append(
            f"| [x] | `PCT_PART_{ent}` | Participação Percentual sobre o Total | `ROUND((COUNT(1)*100.0)/NULLIF(SUM(COUNT(1)) OVER(), 0), 2)` | `{vw_kpi}` | `PERCENTUAL` |"
        )
        for c in f["colunas"]:
            cname = c["nome_dw"]
            if cname.startswith(("QTD_", "VLR_", "VAL_", "QT_")):
                linhas.append(
                    f"| [x] | `SUM_{cname}` | Somatório de {cname} | `SUM(NVL({cname}, 0))` | `{vw_kpi}` | `NUMERICO` |"
                )

    linhas.extend([
        "",
        "---",
        "",
        "## 6. 💡 Radar Consultivo da IA (Governança Semântica & Text-to-SQL)",
        "",
        "- [x] **RADAR_SEM_01 (Proteção Anti-Explosão Cartesiana SCD2):** Forçar nas orientações de IA (`META_ORIENTACAO_IA`) que agentes LLM utilizem exclusivamente `VW_*_DIM_*_ATUAL` quando o usuário não pedir evolução histórica.",
        "- [x] **RADAR_SEM_02 (Blindagem contra `ORA-01476` Divisão por Zero):** Envolver todos os denominadores de taxas e percentuais em `NULLIF(denominador, 0)`.",
        "- [x] **RADAR_SEM_03 (Isolamento Multi-Projeto via `MERGE INTO`):** Utilizar `MERGE INTO` com chave composta `(SGL_PROJETO, ...)` nas 8 tabelas `META_*`, garantindo convivência segura com outros projetos no mesmo schema.",
        "- [x] **RADAR_SEM_04 (Política VPD Fail-Closed):** Configurar `PKG_SECURITY_*` para retornar predicado `'1 = 0'` caso o `SYS_CONTEXT` não tenha sido inicializado na sessão.",
        "",
        "---",
        "",
        "## 7. 📦 Escopo de Entregáveis Físicos na Esteira Real (`saida/camada_semantica/`)",
        "",
        "Desmarque (`[ ]`) qualquer entregável que você **não** queira gerar ao executar a simulação aprovada:",
        "",
        "- [x] `views_dim` : Script Camada 1 — Views de Dimensão Vigente (`vw_analiticas/01_vw_dim_atuais.sql`)",
        "- [x] `views_evento` : Script Camada 2 — Views de Evento Detalhado (`vw_analiticas/02_vw_eventos.sql`)",
        "- [x] `views_kpi` : Script Camada 3 — Views de KPIs Consolidados (`vw_analiticas/03_vw_kpis.sql`)",
        "- [x] `catalogo_meta` : DDL e Scripts Idempotentes das 8 Tabelas `META_*` (`meta_projeto/01_meta_glossario.sql` a `08_meta_valor_dominio.sql`)",
        "- [x] `seguranca_rls` : Script de Segurança Row-Level Security / VPD (`meta_projeto/02_rls.sql`)",
        "- [x] `validacoes` : Script de Smoke Tests e Validação Semântica (`meta_projeto/09_validacoes.sql`)",
        "- [x] `documento_entendimento` : Documento Executivo de Entendimento (`meta_projeto/DOCUMENTO_ENTENDIMENTO_<PROJETO>.md`)",
        "",
    ])

    return "\n".join(linhas)


# =============================================================================
# 4. PARSER DE EDIÇÕES DA BLUEPRINT E EXECUÇÃO REAL NA PASTA SAIDA/
# =============================================================================

def verificar_aprovacao_blueprint(caminho_bp: Path) -> tuple[bool, dict[str, str], set[str]]:
    """
    Lê um arquivo de Blueprint de Simulação e retorna:
      - `aprovado` (bool): True se `[x] SIMULAÇÃO 100% FECHADA E APROVADA...` estiver marcado
      - `parametros` (dict): Parâmetros globais lidos da Seção 2
      - `entregaveis_ativos` (set): Chaves de entregáveis marcados com `[x]` na Seção 7
    """
    if not caminho_bp.exists():
        return False, {}, set()

    txt = caminho_bp.read_text(encoding="utf-8", errors="replace")
    aprovado = bool(re.search(r"-\s*\[[xX]\]\s*\*\*SIMULAÇÃO 100% FECHADA E APROVADA", txt))

    parametros: dict[str, str] = {}
    for m in re.finditer(r"^\|\s*`([^`]+)`\s*\|\s*`([^`]*)`\s*\|", txt, flags=re.MULTILINE):
        parametros[m.group(1).strip()] = m.group(2).strip()

    entregaveis_ativos: set[str] = set()
    for m in re.finditer(r"^-\s*\[([xX ])\]\s*`([^`]+)`\s*:", txt, flags=re.MULTILINE):
        if m.group(1).upper() == "X":
            entregaveis_ativos.add(m.group(2).strip())

    return aprovado, parametros, entregaveis_ativos


def parse_tabelas_editadas_blueprint_dw(caminho_bp: Path, tabelas_base: list[dict]) -> list[dict]:
    """
    Lê as tabelas Markdown editadas pelo engenheiro na Seção 4 da `SIMULACAO_BLUEPRINT_DW.md`
    e aplica exclusões de colunas (`[ ]`), renomeações, tipos Oracle e descrições editadas.
    """
    if not caminho_bp.exists():
        return tabelas_base

    txt = caminho_bp.read_text(encoding="utf-8", errors="replace")
    blocos = re.split(r"^###\s+4\.[DF]\.\s+`([^`]+)`", txt, flags=re.MULTILINE)
    if len(blocos) < 3:
        return tabelas_base

    edicoes_por_tabela: dict[str, list[dict]] = {}
    desc_por_tabela: dict[str, str] = {}

    for i in range(1, len(blocos), 2):
        tname = blocos[i].strip().upper()
        corpo = blocos[i + 1]
        m_desc = re.search(r"-\s*\*\*Descrição da Tabela:\*\*\s*`([^`]+)`", corpo)
        if m_desc:
            desc_por_tabela[tname] = m_desc.group(1).strip()

        cols_editadas = []
        for line in corpo.splitlines():
            line_s = line.strip()
            m_row = re.match(
                r"^\|\s*\[([xX ])\]\s*\|\s*`([^`]+)`\s*\|\s*`([^`]+)`\s*\|\s*`([^`]+)`\s*\|\s*`([^`]+)`\s*\|\s*`([^`]+)`\s*\|\s*(.+?)\s*\|$",
                line_s,
            )
            if m_row:
                ativo = m_row.group(1).upper() == "X"
                if not ativo:
                    continue
                papel_s = m_row.group(5).strip().upper()
                nome_col_dw = m_row.group(3).strip().upper()
                tipo_col_ora = m_row.group(4).strip().upper()
                is_not_null = papel_s in ("SK", "NK", "PK_DEGENERADA", "FK_DIMENSAO")
                cols_editadas.append({
                    "nome_original": m_row.group(2).strip(),
                    "nome": nome_col_dw,
                    "nome_dw": nome_col_dw,
                    "tipo_origem": tipo_col_ora,
                    "tipo_sql": tipo_col_ora,
                    "tipo_oracle": tipo_col_ora,
                    "papel_scd": papel_s,
                    "transformacao": m_row.group(6).strip(),
                    "comentario": m_row.group(7).strip(),
                    "nullable": not is_not_null,
                    "obrigatorio": "NOT NULL" if is_not_null else "NULL",
                })
        if cols_editadas:
            edicoes_por_tabela[tname] = cols_editadas

    tabelas_finais = []
    vistas: set[str] = set()
    for t in tabelas_base:
        tname = t["nome_tabela"].upper()
        vistas.add(tname)
        if tname in edicoes_por_tabela:
            cols_ed = edicoes_por_tabela[tname]
            t_novo = dict(t)
            t_novo["colunas"] = cols_ed
            if tname in desc_por_tabela:
                t_novo["comentario_tabela"] = desc_por_tabela[tname]
            tabelas_finais.append(t_novo)
        else:
            tabelas_finais.append(t)

    # Suporta tabelas adicionadas na Blueprint ou execução 100% autônoma via Blueprint (sem DDL base)
    _, params_bp, _ = verificar_aprovacao_blueprint(caminho_bp)
    schema_bp = params_bp.get("SCHEMA_DW_ALVO", "DW").upper()
    for tname, cols_ed in edicoes_por_tabela.items():
        if tname not in vistas:
            pks = [c["nome_dw"] for c in cols_ed if c["papel_scd"] in ("SK", "PK_DEGENERADA")]
            fks = [
                {
                    "coluna": c["nome_dw"],
                    "tabela_ref": "DIM_" + c["nome_dw"].replace("SK_", ""),
                    "coluna_ref": c["nome_dw"],
                }
                for c in cols_ed
                if c["papel_scd"] == "FK_DIMENSAO"
            ]
            tabelas_finais.append({
                "arquivo": caminho_bp.name,
                "schema": schema_bp,
                "nome_completo_origem": f"{schema_bp}.{tname}",
                "nome_tabela": tname,
                "colunas": cols_ed,
                "pks": pks,
                "fks": fks,
                "indices": [],
                "comentario_tabela": desc_por_tabela.get(tname, f"Uma linha representa um registro de {tname}"),
                "arquivo_origem": caminho_bp.name,
            })

    return tabelas_finais


def _gerar_scripts_ddl_completos_dw(
    tabelas: list[dict],
    schema_dw: str,
    schema_stg: str,
    projeto: str,
    ts_dat: str,
    ts_idx: str,
    entregaveis: set[str],
) -> list[Path]:
    """Gera os scripts DDL estruturais (`01_tablespaces` a `05_sequences`) em `saida/planejador_dw/`."""
    dims = [t for t in tabelas if classificar_tabela_dw(t) == "DIM"]
    fatos = [t for t in tabelas if classificar_tabela_dw(t) == "FATO"]
    gerados: list[Path] = []

    # 01_tablespaces (salvo na pasta canônica 01_controle_carga)
    if "01_tablespaces" in entregaveis:
        p = SAIDA_DW_DIR / "01_controle_carga" / "01_create_tablespaces.sql"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            f"-- =============================================================================\n"
            f"-- NINHO — 01_create_tablespaces.sql (PROJETO: {projeto})\n"
            f"-- =============================================================================\n"
            f"CREATE TABLESPACE {ts_dat} DATAFILE '{ts_dat.lower()}01.dbf' SIZE 500M AUTOEXTEND ON NEXT 100M MAXSIZE UNLIMITED;\n"
            f"CREATE TABLESPACE {ts_idx} DATAFILE '{ts_idx.lower()}01.dbf' SIZE 250M AUTOEXTEND ON NEXT 50M MAXSIZE UNLIMITED;\n",
            encoding="utf-8",
        )
        gerados.append(p)

    # 02_staging
    if "02_staging" in entregaveis:
        p = SAIDA_DW_DIR / "02_staging" / "02_create_stg_tables.sql"
        p.parent.mkdir(parents=True, exist_ok=True)
        linhas_stg = [
            "-- =============================================================================",
            f"-- NINHO — 02_create_stg_tables.sql (SCHEMA: {schema_stg})",
            "-- =============================================================================",
            "",
        ]
        for t in tabelas:
            stg_name = re.sub(r"^(DIM|FATO|FAT)_", "STG_", t["nome_tabela"])
            cols_stg = [
                c for c in t["colunas"]
                if c["nome_dw"] != "DIMENSION_KEY"
                and not c["nome_dw"].startswith("SK_")
                and c["nome_dw"] not in ("DTC_INICIO", "DTC_EFETIVACAO", "DTC_EXPIRACAO", "FLG_ATIVO")
            ]
            if not cols_stg:
                cols_stg = t["colunas"]
            linhas_stg.append(f"CREATE TABLE {schema_stg}.{stg_name} (")
            for idx, c in enumerate(cols_stg):
                virg = "," if idx < len(cols_stg) - 1 else ""
                linhas_stg.append(f"    {c['nome_dw']} {c['tipo_oracle']}{virg}")
            linhas_stg.append(f") TABLESPACE {ts_dat};")
            linhas_stg.append("")
        p.write_text("\n".join(linhas_stg), encoding="utf-8")
        gerados.append(p)

    # 03_dimensoes_ddl
    if "03_dimensoes_ddl" in entregaveis and dims:
        p = SAIDA_DW_DIR / "03_dimensoes" / "03_create_dim_tables.sql"
        p.parent.mkdir(parents=True, exist_ok=True)
        linhas_dim = [
            "-- =============================================================================",
            f"-- NINHO — 03_create_dim_tables.sql (SCHEMA: {schema_dw})",
            "-- =============================================================================",
            "",
        ]
        for d in dims:
            tname = d["nome_tabela"]
            sk = _obter_sk_dim(d)
            linhas_dim.append(f"CREATE TABLE {schema_dw}.{tname} (")
            for c in d["colunas"]:
                eh_nn = c.get("obrigatorio") in (True, "NOT NULL") or c["nome_dw"] == sk
                nn = " NOT NULL" if eh_nn else ""
                linhas_dim.append(f"    {c['nome_dw']} {c['tipo_oracle']}{nn},")
            linhas_dim.append(f"    CONSTRAINT PK_{tname} PRIMARY KEY ({sk}) USING INDEX TABLESPACE {ts_idx}")
            linhas_dim.append(f") TABLESPACE {ts_dat};")
            linhas_dim.append("")
        sql_comm_dim, _, _ = construir_script_comentarios([(d, "DIM") for d in dims], schema_dw, "DIMENSÕES (DIM_*)")
        linhas_dim.append(sql_comm_dim)
        p.write_text("\n".join(linhas_dim), encoding="utf-8")
        gerados.append(p)

    # 04_fatos_ddl
    if "04_fatos_ddl" in entregaveis and fatos:
        p = SAIDA_DW_DIR / "04_fatos" / "04_create_fato_tables.sql"
        p.parent.mkdir(parents=True, exist_ok=True)
        linhas_fato = [
            "-- =============================================================================",
            f"-- NINHO — 04_create_fato_tables.sql (SCHEMA: {schema_dw})",
            "-- =============================================================================",
            "",
        ]
        for f in fatos:
            fname = f["nome_tabela"]
            linhas_fato.append(f"CREATE TABLE {schema_dw}.{fname} (")
            for idx, c in enumerate(f["colunas"]):
                eh_nn = c.get("obrigatorio") in (True, "NOT NULL")
                nn = " NOT NULL" if eh_nn else ""
                virg = "," if idx < len(f["colunas"]) - 1 else ""
                linhas_fato.append(f"    {c['nome_dw']} {c['tipo_oracle']}{nn}{virg}")
            linhas_fato.append(f") TABLESPACE {ts_dat};")
            linhas_fato.append("")
        _, sql_aj_fato = construir_patches_ajustes_nao_destrutivos(dims, fatos, schema_dw)
        sql_comm_fato, _, _ = construir_script_comentarios([(f, "FATO") for f in fatos], schema_dw, "TABELAS FATO (FATO_*)")
        linhas_fato.append(sql_aj_fato)
        linhas_fato.append("")
        linhas_fato.append(sql_comm_fato)
        p.write_text("\n".join(linhas_fato), encoding="utf-8")
        gerados.append(p)

    # 05_sequences (salvo em 03_dimensoes/05_create_sequences.sql para manter estrutura canônica)
    if "05_sequences" in entregaveis and dims:
        p = SAIDA_DW_DIR / "03_dimensoes" / "05_create_sequences.sql"
        p.parent.mkdir(parents=True, exist_ok=True)
        linhas_seq = [
            "-- =============================================================================",
            f"-- NINHO — 05_create_sequences.sql (SCHEMA: {schema_dw})",
            "-- Regra Corporativa: CACHE 1000 NOORDER para performance de carga SCD2",
            "-- =============================================================================",
            "",
        ]
        for d in dims:
            tname = d["nome_tabela"]
            seq_name = f"SEQ_{tname}"[:30]
            linhas_seq.append(
                f"CREATE SEQUENCE {schema_dw}.{seq_name} START WITH 1 INCREMENT BY 1 CACHE 1000 NOORDER NOCYCLE;"
            )
        p.write_text("\n".join(linhas_seq) + "\n", encoding="utf-8")
        gerados.append(p)

    return gerados


def executar_simulacao_aprovada_dw(tabelas_base: list[dict], forcar: bool = False) -> list[Path]:
    """Lê `SIMULACAO_BLUEPRINT_DW.md`, valida aprovação, aplica edições e gera `saida/planejador_dw/`."""
    if not BLUEPRINT_DW_PATH.exists():
        print(f"[ERRO] Blueprint de simulação não encontrada em: {BLUEPRINT_DW_PATH}")
        print("       Execute primeiro: python core/scripts_comuns/simular_projeto.py --modulo dw --acao simular")
        sys.exit(1)

    aprovado, params, entregaveis = verificar_aprovacao_blueprint(BLUEPRINT_DW_PATH)
    if not aprovado and not forcar:
        print("=" * 80)
        print("⏸️  SIMULAÇÃO DW PENDENTE DE APROVAÇÃO DO ENGENHEIRO")
        print("=" * 80)
        print(f"  Arquivo: {BLUEPRINT_DW_PATH.relative_to(ROOT_DIR)}")
        print("  Para executar na esteira real:")
        print("    1) Abra o arquivo acima, revise/edite as tabelas e marque:")
        print("       - [x] **SIMULAÇÃO 100% FECHADA E APROVADA PARA EXECUÇÃO REAL**")
        print("    2) Ou adicione a flag `--forcar` no comando CLI.")
        print("=" * 80)
        sys.exit(1)

    tabelas = parse_tabelas_editadas_blueprint_dw(BLUEPRINT_DW_PATH, tabelas_base)
    schema_det, projeto_det, _, _ = extrair_schema_e_projeto(tabelas)
    projeto = params.get("PROJETO_SIGLA", projeto_det).upper()
    schema_dw = params.get("SCHEMA_DW", schema_det).upper()
    schema_stg = params.get("SCHEMA_STG", f"STG_{projeto}").upper()
    estrategia = params.get("ESTRATEGIA_CARGA", "A").upper()[:1]
    if estrategia not in ("A", "B"):
        estrategia = "A"
    ts_dat = params.get("TABLESPACE_DADOS", f"TS_DW_{projeto}_DAT").upper()
    ts_idx = params.get("TABLESPACE_INDICES", f"TS_DW_{projeto}_IDX").upper()

    dims = [t for t in tabelas if classificar_tabela_dw(t) == "DIM"]
    fatos = [t for t in tabelas if classificar_tabela_dw(t) == "FATO"]
    stgs = [t for t in tabelas if classificar_tabela_dw(t) == "STG"]

    gerados = _gerar_scripts_ddl_completos_dw(
        tabelas, schema_dw, schema_stg, projeto, ts_dat, ts_idx, entregaveis
    )

    sql_odi_tbl, sql_odi_dim, sql_odi_fato = construir_scripts_odi(
        dims, fatos, stgs, schema_dw, projeto, estrategia
    )
    if "03_odi_dim_tables" in entregaveis and dims:
        p = SAIDA_DW_DIR / "03_dimensoes" / "03_create_odi_dim_tables.sql"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(sql_odi_tbl, encoding="utf-8")
        gerados.append(p)

    if "03_selects_odi_dim" in entregaveis and dims:
        p = SAIDA_DW_DIR / "03_dimensoes" / "03_selects_odi_dimensoes.sql"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(sql_odi_dim, encoding="utf-8")
        gerados.append(p)

    if "03_linha_default" in entregaveis and dims:
        p = SAIDA_DW_DIR / "03_dimensoes" / "06_init_default_records.sql"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(construir_script_linha_default(dims, schema_dw), encoding="utf-8")
        gerados.append(p)

    if "04_select_odi_fato" in entregaveis and fatos:
        p = SAIDA_DW_DIR / "04_fatos" / "04_select_odi_fato.sql"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(sql_odi_fato, encoding="utf-8")
        gerados.append(p)

    if "06_indices" in entregaveis:
        sql_idx_dim, sql_idx_fato, _, _ = construir_scripts_indices(
            dims, fatos, schema_dw, ts_idx, estrategia
        )
        if dims:
            p_id = SAIDA_DW_DIR / "03_dimensoes" / "06_create_indexes_dim.sql"
            p_id.parent.mkdir(parents=True, exist_ok=True)
            p_id.write_text(sql_idx_dim, encoding="utf-8")
            gerados.append(p_id)
        if fatos:
            p_if = SAIDA_DW_DIR / "04_fatos" / "06_create_indexes_fato.sql"
            p_if.parent.mkdir(parents=True, exist_ok=True)
            p_if.write_text(sql_idx_fato, encoding="utf-8")
            gerados.append(p_if)

    if "07_procedures" in entregaveis:
        tpl_prc = ROOT_DIR / "modulos" / "planejador_dw" / "templates" / "07_prc_pos_carga_fato.sql"
        p = SAIDA_DW_DIR / "05_procedimentos_manutencao" / "07_prc_pos_carga_fato.sql"
        p.parent.mkdir(parents=True, exist_ok=True)
        if tpl_prc.exists():
            conteudo_prc = tpl_prc.read_text(encoding="utf-8", errors="ignore").replace("<SCHEMA_ALVO>", schema_dw)
        else:
            conteudo_prc = f"-- Procedure PRC_POS_CARGA_FATO ({schema_dw})\n"
        p.write_text(conteudo_prc, encoding="utf-8")
        gerados.append(p)

    if "08_testes_qualidade" in entregaveis:
        p = SAIDA_DW_DIR / "10_testes_integridade" / "13_testes_integridade.sql"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(construir_testes_integridade(dims, fatos, schema_dw, projeto), encoding="utf-8")
        gerados.append(p)

    if "09_guias_odi" in entregaveis:
        guias = construir_guias_odi_modulares(dims, fatos, schema_dw, projeto, estrategia)
        pasta_09 = SAIDA_DW_DIR / "09_relatorio_estrategias"
        pasta_09.mkdir(parents=True, exist_ok=True)
        for nome_g, cont_g in guias.items():
            pg = pasta_09 / nome_g
            pg.write_text(cont_g, encoding="utf-8")
            gerados.append(pg)

    if "10_guia_bi" in entregaveis:
        p = SAIDA_DW_DIR / "08_datasets_bi" / f"GUIA_ANALISTA_BI_{projeto}.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(construir_guia_bi_rapido(dims, fatos, schema_dw, projeto), encoding="utf-8")
        gerados.append(p)

    if "11_dicionario_html" in entregaveis:
        p = SAIDA_DW_DIR / "11_dicionario_dados" / "dicionario_dados.html"
        p.parent.mkdir(parents=True, exist_ok=True)
        tabelas_classificadas = [(t, classificar_tabela_dw(t)) for t in tabelas]
        p.write_text(construir_dicionario_html(tabelas_classificadas, schema_dw, projeto), encoding="utf-8")
        gerados.append(p)

    print("=" * 80)
    print(f"🚀 EXECUÇÃO REAL DO DW CONCLUÍDA A PARTIR DA SIMULAÇÃO APROVADA ({projeto})")
    print("=" * 80)
    print(f"  📋 Blueprint Lida     : {BLUEPRINT_DW_PATH.relative_to(ROOT_DIR)}")
    print(f"  🏛️  Schema DW / STG    : {schema_dw} / {schema_stg} (Estratégia {estrategia})")
    print(f"  📦 Arquivos Gerados   : {len(gerados)} em saida/planejador_dw/")
    for g in gerados:
        print(f"     - {g.relative_to(ROOT_DIR)}")
    print("=" * 80)
    return gerados


def executar_simulacao_aprovada_semantica(tabelas_base: list[dict], forcar: bool = False) -> list[Path]:
    """Lê `SIMULACAO_BLUEPRINT_SEMANTICA.md`, valida aprovação e gera `saida/camada_semantica/`."""
    if not BLUEPRINT_SEM_PATH.exists():
        print(f"[ERRO] Blueprint de simulação semântica não encontrada em: {BLUEPRINT_SEM_PATH}")
        print("       Execute primeiro: python core/scripts_comuns/simular_projeto.py --modulo semantica --acao simular")
        sys.exit(1)

    aprovado, params, entregaveis = verificar_aprovacao_blueprint(BLUEPRINT_SEM_PATH)
    if not aprovado and not forcar:
        print("=" * 80)
        print("⏸️  SIMULAÇÃO DA CAMADA SEMÂNTICA PENDENTE DE APROVAÇÃO DO ENGENHEIRO")
        print("=" * 80)
        print(f"  Arquivo: {BLUEPRINT_SEM_PATH.relative_to(ROOT_DIR)}")
        print("  Para executar na esteira real:")
        print("    1) Abra o arquivo acima, revise/edite as Views/KPIs e marque:")
        print("       - [x] **SIMULAÇÃO 100% FECHADA E APROVADA PARA EXECUÇÃO REAL**")
        print("    2) Ou adicione a flag `--forcar` no comando CLI.")
        print("=" * 80)
        sys.exit(1)

    tabelas = parse_tabelas_editadas_blueprint_dw(BLUEPRINT_DW_PATH, tabelas_base)
    schema_det, projeto_det, _, _ = extrair_schema_e_projeto(tabelas)
    projeto = params.get("PROJETO_SIGLA", projeto_det).upper()
    schema = params.get("SCHEMA_SEMANTICA", schema_det).upper()
    ativar_rls = params.get("ATIVAR_RLS_VPD", "SIM").upper().startswith("S")

    vw_dir = SAIDA_SEM_DIR / "vw_analiticas"
    meta_dir = SAIDA_SEM_DIR / "meta_projeto"
    vw_dir.mkdir(parents=True, exist_ok=True)
    meta_dir.mkdir(parents=True, exist_ok=True)

    gerados: list[Path] = []

    if "views_dim" in entregaveis:
        p = vw_dir / "01_vw_dim_atuais.sql"
        p.write_text(construir_views_dim_atuais(tabelas, schema, projeto), encoding="utf-8")
        gerados.append(p)

    if "views_evento" in entregaveis:
        p = vw_dir / "02_vw_eventos.sql"
        p.write_text(construir_views_eventos(tabelas, schema, projeto), encoding="utf-8")
        gerados.append(p)

    if "views_kpi" in entregaveis:
        p = vw_dir / "03_vw_kpis.sql"
        p.write_text(construir_views_kpis(tabelas, schema, projeto), encoding="utf-8")
        gerados.append(p)

    if "catalogo_meta" in entregaveis:
        tpl_meta = ROOT_DIR / "modulos" / "camada_semantica" / "templates" / "01_create_meta_tables.sql"
        dst_meta = meta_dir / "01_create_meta_tables.sql"
        if not dst_meta.exists() and tpl_meta.exists():
            shutil.copy2(tpl_meta, dst_meta)
            gerados.append(dst_meta)

        for nome_m, cont_m in construir_catalogo_meta(tabelas, schema, projeto).items():
            pm = meta_dir / nome_m
            pm.write_text(cont_m, encoding="utf-8")
            gerados.append(pm)

    if "seguranca_rls" in entregaveis and ativar_rls:
        p = meta_dir / "02_rls.sql"
        p.write_text(construir_script_rls(tabelas, schema, projeto), encoding="utf-8")
        gerados.append(p)

    if "validacoes" in entregaveis:
        p = meta_dir / "09_validacoes.sql"
        p.write_text(construir_script_validacoes_semantica(tabelas, schema, projeto), encoding="utf-8")
        gerados.append(p)

    if "documento_entendimento" in entregaveis:
        p = meta_dir / f"DOCUMENTO_ENTENDIMENTO_{projeto}.md"
        p.write_text(construir_documento_entendimento(tabelas, schema, projeto), encoding="utf-8")
        gerados.append(p)

    print("=" * 80)
    print(f"🚀 EXECUÇÃO REAL DA CAMADA SEMÂNTICA CONCLUÍDA A PARTIR DA SIMULAÇÃO ({projeto})")
    print("=" * 80)
    print(f"  📋 Blueprint Lida     : {BLUEPRINT_SEM_PATH.relative_to(ROOT_DIR)}")
    print(f"  🏛️  Schema / Projeto   : {schema} / {projeto}")
    print(f"  📦 Arquivos Gerados   : {len(gerados)} em saida/camada_semantica/")
    for g in gerados:
        print(f"     - {g.relative_to(ROOT_DIR)}")
    print("=" * 80)
    return gerados


def carregar_insumos_para_simulacao(caminho_custom: Path | None = None, acao: str = "simular") -> tuple[list[dict], Path]:
    """Localiza e faz o parse de arquivos .sql em `entrega/planejador_dw/ddl/`, `entrega/camada_semantica/ddl/`, `--caminho` ou da própria Blueprint."""
    arqs, pasta = localizar_ddls_para_semantica(caminho_custom)
    if not arqs:
        if acao == "executar" and BLUEPRINT_DW_PATH.exists():
            return parse_tabelas_editadas_blueprint_dw(BLUEPRINT_DW_PATH, []), ENTREGA_DW_DIR
        print(
            "[ERRO] Nenhum arquivo .sql encontrado para simulação em:\n"
            f"  - {ENTREGA_DW_DIR / 'ddl'}\n"
            f"  - {ENTREGA_SEM_DIR / 'ddl'}\n"
            "Deposite o DDL de origem ou do DW existente ou informe `--caminho <arquivo_ou_pasta>`."
        )
        sys.exit(1)

    por_nome: dict[str, dict] = {}
    for arq in arqs:
        txt = arq.read_text(encoding="utf-8", errors="replace")
        for t in parse_ddl_text(txt, arq.name):
            por_nome[t["nome_tabela"]] = t

    tabelas_brutas = list(por_nome.values())
    tabelas_dw = _converter_oltp_para_dw_se_necessario(tabelas_brutas)
    return tabelas_dw, pasta


def exibir_status_simulacoes() -> None:
    """Mostra o status atual das Blueprints de Simulação no workspace."""
    print("=" * 80)
    print("📊 STATUS DAS SIMULAÇÕES E BLUEPRINTS EDITÁVEIS (NINHO)")
    print("=" * 80)
    for rotulo, bp_path in [
        ("Planejador de DW", BLUEPRINT_DW_PATH),
        ("Camada Semântica", BLUEPRINT_SEM_PATH),
    ]:
        if not bp_path.exists():
            print(f"  ⚪ {rotulo:<20} : Não gerada ({bp_path.relative_to(ROOT_DIR)})")
        else:
            aprov, params, entreg = verificar_aprovacao_blueprint(bp_path)
            st = "✅ APROVADA PARA EXECUÇÃO" if aprov else "⏳ AGUARDANDO REVISÃO/APROVAÇÃO ([ ])"
            proj = params.get("PROJETO_SIGLA", "?")
            print(f"  {st} | {rotulo:<18} | Projeto: {proj} | Entregáveis marcados: {len(entreg)}")
            print(f"     Arquivo: {bp_path.relative_to(ROOT_DIR)}")
    print("=" * 80)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gerador de Simulações e Blueprint Editável antes da Execução Real (DW e Camada Semântica)"
    )
    parser.add_argument(
        "--modulo",
        choices=["dw", "semantica", "ambos"],
        default="ambos",
        help="Módulo alvo da simulação ou execução (dw, semantica ou ambos).",
    )
    parser.add_argument(
        "--acao",
        choices=["simular", "executar", "status"],
        default="simular",
        help="'simular' gera a Blueprint editável; 'executar' roda a esteira real a partir da Blueprint aprovada; 'status' consulta aprovação.",
    )
    parser.add_argument("--caminho", type=str, default=None, help="Caminho opcional para DDL .sql de entrada.")
    parser.add_argument("--schema", type=str, default=None, help="Override do Schema Oracle.")
    parser.add_argument("--projeto", type=str, default=None, help="Override da Sigla do Projeto.")
    parser.add_argument(
        "--estrategia",
        choices=["A", "B"],
        default="A",
        help="Estratégia de carga da Fato para simulação DW (A = Truncate/Bitmap, B = MERGE/B-Tree).",
    )
    parser.add_argument(
        "--forcar",
        action="store_true",
        help="Autoriza a execução real (`--acao executar`) mesmo sem o checkbox `[x]` marcado no arquivo Markdown.",
    )

    args = parser.parse_args()

    if args.acao == "status":
        exibir_status_simulacoes()
        return

    caminho_custom = Path(args.caminho) if args.caminho else None
    tabelas, pasta_origem = carregar_insumos_para_simulacao(caminho_custom, acao=args.acao)
    schema_det, projeto_det, _, _ = extrair_schema_e_projeto(tabelas)
    schema = (args.schema or schema_det).upper()
    projeto = (args.projeto or projeto_det).upper()

    if args.acao == "simular":
        gerados_bp: list[Path] = []
        if args.modulo in ("dw", "ambos"):
            ENTREGA_DW_DIR.mkdir(parents=True, exist_ok=True)
            conteudo_dw = gerar_blueprint_simulacao_dw(
                tabelas, schema, projeto, args.estrategia, pasta_origem
            )
            BLUEPRINT_DW_PATH.write_text(conteudo_dw, encoding="utf-8")
            gerados_bp.append(BLUEPRINT_DW_PATH)

        if args.modulo in ("semantica", "ambos"):
            ENTREGA_SEM_DIR.mkdir(parents=True, exist_ok=True)
            conteudo_sem = gerar_blueprint_simulacao_semantica(
                tabelas, schema, projeto, pasta_origem
            )
            BLUEPRINT_SEM_PATH.write_text(conteudo_sem, encoding="utf-8")
            gerados_bp.append(BLUEPRINT_SEM_PATH)

        print("=" * 80)
        print("🧪 SIMULAÇÃO E BLUEPRINT EDITÁVEL GERADAS COM SUCESSO!")
        print("=" * 80)
        print(f"  🏛️  Projeto / Schema Simulado : {projeto} / {schema}")
        print(f"  📊 Tabelas Modeladas         : {len(tabelas)}")
        for bp in gerados_bp:
            print(f"  📝 Blueprint Editável        : {bp.relative_to(ROOT_DIR)}")
        print("-" * 80)
        print("  👉 PRÓXIMO PASSO:")
        print("     1. Revise e edite livremente a(s) Blueprint(s) acima.")
        print("     2. Marque `- [x] SIMULAÇÃO 100% FECHADA E APROVADA PARA EXECUÇÃO REAL`.")
        print(f"     3. Execute: python core/scripts_comuns/simular_projeto.py --modulo {args.modulo} --acao executar")
        print("=" * 80)

    elif args.acao == "executar":
        if args.modulo in ("dw", "ambos"):
            executar_simulacao_aprovada_dw(tabelas, forcar=args.forcar)
        if args.modulo in ("semantica", "ambos"):
            executar_simulacao_aprovada_semantica(tabelas, forcar=args.forcar)


if __name__ == "__main__":
    main()
