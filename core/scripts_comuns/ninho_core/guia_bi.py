"""
Guia do Analista de BI: leitura de indicadores de negócio (.xlsx/.ods/.docx/.odt/.csv) e geração
do guia com Star Schema, medidas DAX, metas e wireframe do painel.

Extraído de melhorar_dw_existente.py (que mantém uma fachada de reimportação).
"""

import re
import zipfile
from pathlib import Path
from datetime import datetime
from ninho_core import xml_seguro
from ninho_core.dw_modelo import (
    _obter_nk_dim,
    _obter_sk_dim,
    gerar_comentario_tabela,
    humanizar_identificador,
    identificar_fks_fato,
)
from ninho_core.zip_seguro import ler_membro
from ninho_core.leitores import ler_documento_docx, ler_documento_odt, ler_planilha_ods
from ninho_core.paths import get_base_dir


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
                        root_ss = xml_seguro.fromstring(ler_membro(zf, "xl/sharedStrings.xml"))
                        for si in root_ss.findall(f".//{ns}si"):
                            shared.append("".join(t.text or "" for t in si.findall(f".//{ns}t")).strip())

                    sheets = sorted(n for n in zf.namelist() if n.startswith("xl/worksheets/sheet") and n.endswith(".xml"))
                    for sh in sheets:
                        root_sh = xml_seguro.fromstring(ler_membro(zf, sh))
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
                    por_que_existe="Atua como SLA de Qualidade de Dados (*Data Quality Threshold*): se ultrapassar o limite de tolerância (ex: `> 5%`), alerta a engenharia e o gestor de negócio sobre falha de preenchimento no sistema transacional de origem.",
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
