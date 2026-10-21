#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Motor Determinístico de Engenharia Reversa e Auditoria de Arquivos Power BI (.pbix) — NINHO
Descompacta arquivos .pbix (ZIP nativo), decodifica Report/Layout e DiagramLayout (UTF-16-LE),
extrai Tabelas, Colunas, Medidas, Páginas, Visuais e Filtros (Relatório, Página e Visual),
traduz a AST de filtros do Power BI para expressões SQL/DAX legíveis e detecta anti-padrões:

- PBIX-H1: Clonagem Multi-Tenant de arquivos .pbix por Órgão/Tenant em vez de Row-Level Security (RLS)
- PBIX-H2: Bug de Copy-Paste / Vazamento de Filtro de Órgão/Tenant divergente dentro de visuais
- PBIX-H3: Tabelão Desnormalizado (Flat Table) exigindo decomposição Star Schema (Kimball)
- PBIX-H4: Regras de Negócio e KPIs ocultos em filtros visuais
- PBIX-H5: Sanitização de dados sujos/teste feita no visual do Power BI em vez do ETL/Staging

Uso:
    python core/scripts_comuns/inspecionar_pbix.py <caminho_arquivo_ou_pasta> [--output <caminho_relatorio.md>]
"""

import re
import sys
import json
import zipfile
import argparse
from pathlib import Path
from collections import defaultdict

# Configura encoding UTF-8 no stdout do Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

VERDE = "\033[92m"
AMARELO = "\033[93m"
VERMELHO = "\033[91m"
AZUL = "\033[94m"
CIANO = "\033[96m"
NEGRITO = "\033[1m"
RESET = "\033[0m"

COMPARISON_OPS = {
    0: "=",
    1: ">",
    2: ">=",
    3: "<",
    4: "<=",
}

TENANT_COLUMN_KEYWORDS = (
    "orgao",
    "sigla_orgao",
    "secretaria",
    "empresa",
    "filial",
    "tenant",
    "unidade_gestora",
)

GENERIC_FLAT_TABLE_NAMES = (
    "consulta1",
    "query1",
    "tabela1",
    "planilha1",
    "sheet1",
    "dadosconsolidados",
    "base_consolidada",
    "base",
    "dados",
    "relatorio",
    "relatório",
    "tabelao",
    "tabelão",
)


def print_banner():
    print(f"\n{AZUL}{NEGRITO}{'=' * 85}{RESET}")
    print(f"{CIANO}{NEGRITO}  📊 PLATAFORMA NINHO — MOTOR DE ENGENHARIA REVERSA & AUDITORIA POWER BI (.pbix){RESET}")
    print(f"{AZUL}{NEGRITO}{'=' * 85}{RESET}\n")


def print_ok(msg: str):
    print(f"  {VERDE}[OK]{RESET} {msg}")


def print_warn(msg: str):
    print(f"  {AMARELO}[AVISO]{RESET} {msg}")


def print_err(msg: str):
    print(f"  {VERMELHO}[ERRO]{RESET} {msg}")


def parse_pbi_filter_ast(where_list: list, alias_map: dict) -> str:
    """Converte a árvore sintática (Condition AST) de um filtro do Power BI em expressão legível."""

    def resolve_expr(node):
        if not isinstance(node, dict):
            return str(node)
        if "Column" in node:
            col = node["Column"]
            src = col.get("Expression", {}).get("SourceRef", {})
            entity = src.get("Entity") or alias_map.get(src.get("Source", ""), src.get("Source", "?"))
            prop = col.get("Property", "?")
            return f"{entity}.{prop}"
        if "Measure" in node:
            m = node["Measure"]
            src = m.get("Expression", {}).get("SourceRef", {})
            entity = src.get("Entity") or alias_map.get(src.get("Source", ""), src.get("Source", "?"))
            prop = m.get("Property", "?")
            return f"[{entity}.{prop}]"
        if "Literal" in node:
            val = node["Literal"].get("Value", "")
            return str(val)
        if "Not" in node:
            inner = resolve_expr(node["Not"].get("Expression", {}))
            return f"NOT ({inner})"
        if "And" in node:
            left = resolve_expr(node["And"].get("Left", {}))
            right = resolve_expr(node["And"].get("Right", {}))
            return f"({left} AND {right})"
        if "Or" in node:
            left = resolve_expr(node["Or"].get("Left", {}))
            right = resolve_expr(node["Or"].get("Right", {}))
            return f"({left} OR {right})"
        if "Comparison" in node:
            cmp_node = node["Comparison"]
            kind = cmp_node.get("ComparisonKind", 0)
            op = COMPARISON_OPS.get(kind, f"OP_{kind}")
            left = resolve_expr(cmp_node.get("Left", {}))
            right = resolve_expr(cmp_node.get("Right", {}))
            if right == "null":
                return f"{left} IS NULL" if op == "=" else f"{left} IS NOT NULL"
            return f"{left} {op} {right}"
        if "In" in node:
            in_node = node["In"]
            exprs = [resolve_expr(e) for e in in_node.get("Expressions", [])]
            vals = []
            for v_group in in_node.get("Values", []):
                if isinstance(v_group, list):
                    vals.append(", ".join(resolve_expr(v) for v in v_group))
            lhs = ", ".join(exprs)
            rhs = ", ".join(vals)
            return f"{lhs} IN ({rhs})"
        if "Contains" in node:
            c_node = node["Contains"]
            left = resolve_expr(c_node.get("Left", {}))
            right = resolve_expr(c_node.get("Right", {}))
            return f"{left} CONTAINS {right}"
        return json.dumps(node, ensure_ascii=False)

    parts = []
    for w in where_list:
        cond = w.get("Condition")
        if cond:
            parts.append(resolve_expr(cond))
    return " AND ".join(parts)


def extract_filter_list(raw_filters_str: str) -> list:
    """Extrai lista de dicionários de filtro a partir de filters JSON string no Layout."""
    if not raw_filters_str:
        return []
    try:
        flist = json.loads(raw_filters_str) if isinstance(raw_filters_str, str) else raw_filters_str
    except Exception:
        return []

    parsed = []
    for f in flist:
        expr_field = ""
        target = f.get("expression", {})
        if "Column" in target:
            ent = target["Column"].get("Expression", {}).get("SourceRef", {}).get("Entity", "")
            prop = target["Column"].get("Property", "")
            expr_field = f"{ent}.{prop}"
        elif "Measure" in target:
            ent = target["Measure"].get("Expression", {}).get("SourceRef", {}).get("Entity", "")
            prop = target["Measure"].get("Property", "")
            expr_field = f"[{ent}.{prop}]"

        filter_obj = f.get("filter", {})
        alias_map = {fr.get("Name"): fr.get("Entity") for fr in filter_obj.get("From", []) if isinstance(fr, dict)}
        where_list = filter_obj.get("Where", [])
        condition_str = parse_pbi_filter_ast(where_list, alias_map) if where_list else "(Filtro sem condição ativa)"
        if where_list:
            parsed.append({
                "field": expr_field,
                "condition": condition_str,
            })
    return parsed


def _is_tenant_filter(field_name: str, condition_str: str) -> bool:
    combined = f"{field_name} {condition_str}".lower()
    return any(kw in combined for kw in TENANT_COLUMN_KEYWORDS)


def _extract_string_literals(condition_str: str) -> list:
    return [m.strip() for m in re.findall(r"'([^']+)'", condition_str) if m.strip()]


class PBIXInspector:
    """Inspeciona um arquivo .pbix ou diretório de arquivos .pbix."""

    def __init__(self, target_path: Path):
        self.target_path = target_path
        self.pbix_files = []
        self.reports = []
        self.heuristics_triggered = []
        self.cross_tenant_leaks = []
        self.business_rules_filters = []
        self.business_rules_catalog = []
        self.sanitation_filters = []
        self.flat_tables_detected = set()

    def run(self):
        if self.target_path.is_dir():
            self.pbix_files = sorted(list(self.target_path.rglob("*.pbix")))
        else:
            self.pbix_files = [self.target_path]

        for pbix_path in self.pbix_files:
            rep = self._inspect_single_pbix(pbix_path)
            if rep:
                self.reports.append(rep)

        self._run_heuristics()

    def _inspect_single_pbix(self, pbix_path: Path) -> dict:
        info = {
            "file": pbix_path.name,
            "path": str(pbix_path),
            "connection_mode": "Local / Import",
            "tables": set(),
            "columns_by_table": defaultdict(set),
            "measures_by_table": defaultdict(set),
            "report_filters": [],
            "pages": [],
            "dominant_tenant": None,
        }

        try:
            with zipfile.ZipFile(pbix_path, "r") as zf:
                names = zf.namelist()

                # 1. Connections
                if "Connections" in names:
                    try:
                        conn_data = json.loads(zf.read("Connections").decode("utf-8", errors="replace"))
                        if conn_data.get("RemoteArtifacts"):
                            ds_id = conn_data["RemoteArtifacts"][0].get("DatasetId", "")
                            info["connection_mode"] = f"Live Connection / Power BI Service Dataset ({ds_id})"
                    except Exception:
                        pass

                # 2. DiagramLayout (Tabelas do Modelo)
                if "DiagramLayout" in names:
                    try:
                        diag = json.loads(zf.read("DiagramLayout").decode("utf-16-le", errors="replace"))
                        for d in diag.get("diagrams", []):
                            for node in d.get("nodes", []):
                                t_name = node.get("nodeIndex")
                                if t_name:
                                    info["tables"].add(t_name)
                    except Exception:
                        pass

                # 3. Report/Layout
                if "Report/Layout" in names:
                    raw_layout = zf.read("Report/Layout").decode("utf-16-le", errors="replace")
                    layout = json.loads(raw_layout)
                    info["report_filters"] = extract_filter_list(layout.get("filters", "[]"))

                    tenant_counts = defaultdict(int)
                    for rf in info["report_filters"]:
                        if _is_tenant_filter(rf.get("field", ""), rf["condition"]) and "NOT (" not in rf["condition"].upper():
                            for lit in _extract_string_literals(rf["condition"]):
                                tenant_counts[lit.upper()] += 1

                    for sec in layout.get("sections", []):
                        page_name = sec.get("displayName", sec.get("name", "Sem Nome"))
                        page_filters = extract_filter_list(sec.get("filters", "[]"))

                        # Detecta dinamicamente filtro de órgão/tenant dominante na página
                        for pf in page_filters:
                            cond = pf["condition"]
                            if _is_tenant_filter(pf.get("field", ""), cond) and "NOT (" not in cond.upper():
                                for lit in _extract_string_literals(cond):
                                    tenant_counts[lit.upper()] += 1

                        visuals_list = []
                        for vc in sec.get("visualContainers", []):
                            cfg_str = vc.get("config", "{}")
                            try:
                                cfg = json.loads(cfg_str)
                            except Exception:
                                cfg = {}

                            sv = cfg.get("singleVisual", {})
                            v_type = sv.get("visualType", "group/shape")
                            if v_type in ("shape", "image", "textbox", "actionButton"):
                                continue

                            # Título do visual
                            v_title = ""
                            vc_objs = sv.get("vcObjects", {})
                            for t_item in vc_objs.get("title", []):
                                props = t_item.get("properties", {})
                                txt_expr = props.get("text", {}).get("expr", {}).get("Literal", {}).get("Value", "")
                                if txt_expr:
                                    v_title = txt_expr.strip("'")

                            # Campos e Medidas no PrototypeQuery
                            proto = sv.get("prototypeQuery", {})
                            alias_map = {
                                fr.get("Name"): fr.get("Entity")
                                for fr in proto.get("From", [])
                                if isinstance(fr, dict)
                            }
                            for ent in alias_map.values():
                                if ent:
                                    info["tables"].add(ent)

                            fields_used = []
                            for sel in proto.get("Select", []):
                                if "Column" in sel:
                                    src = sel["Column"].get("Expression", {}).get("SourceRef", {}).get("Source", "")
                                    ent = alias_map.get(src, src)
                                    prop = sel["Column"].get("Property", "")
                                    info["columns_by_table"][ent].add(prop)
                                    fields_used.append(f"{ent}.{prop}")
                                elif "Measure" in sel:
                                    src = sel["Measure"].get("Expression", {}).get("SourceRef", {}).get("Source", "")
                                    ent = alias_map.get(src, src)
                                    prop = sel["Measure"].get("Property", "")
                                    info["measures_by_table"][ent].add(prop)
                                    fields_used.append(f"[Medida] {ent}.{prop}")
                                elif "Aggregation" in sel:
                                    agg_col = sel["Aggregation"].get("Expression", {}).get("Column", {})
                                    src = agg_col.get("Expression", {}).get("SourceRef", {}).get("Source", "")
                                    ent = alias_map.get(src, src)
                                    prop = agg_col.get("Property", "")
                                    if ent and prop:
                                        info["columns_by_table"][ent].add(prop)
                                        fields_used.append(f"AGG({ent}.{prop})")

                            v_filters = extract_filter_list(vc.get("filters", "[]"))
                            visuals_list.append({
                                "type": v_type,
                                "title": v_title or f"({v_type} sem título)",
                                "fields": fields_used,
                                "filters": v_filters,
                            })

                        info["pages"].append({
                            "name": page_name,
                            "filters": page_filters,
                            "visuals": visuals_list,
                        })

                    if tenant_counts:
                        info["dominant_tenant"] = max(tenant_counts.items(), key=lambda x: x[1])[0]

        except Exception as exc:
            print_err(f"Falha ao ler {pbix_path.name}: {exc}")
            return {}

        info["tables"] = sorted(list(info["tables"]))
        return info

    def _infer_star_schema_candidates(self) -> tuple:
        """Deriva sugestão dinâmica de Dimensões e Fatos a partir das tabelas e colunas extraídas."""
        dims = set()
        fatos = set()
        for rep in self.reports:
            for tbl, cols in rep["columns_by_table"].items():
                tbl_up = re.sub(r"[^A-Z0-9_]", "_", tbl.upper()).strip("_")
                if tbl_up.startswith("DIM_"):
                    dims.add(tbl_up)
                elif tbl_up.startswith(("FATO_", "FAT_")):
                    fatos.add(tbl_up)
                else:
                    fatos.add(f"FATO_{tbl_up}" if tbl_up else "FATO_EVENTO")
                for col in cols:
                    col_low = col.lower()
                    if any(k in col_low for k in ("data", "dt_", "dtc_", "mes", "ano", "periodo")):
                        dims.add("DIM_TEMPO")
                    elif any(k in col_low for k in ("orgao", "secretaria", "empresa", "filial")):
                        dims.add("DIM_ORGAO")
                    elif "unidade" in col_low or "setor" in col_low or "departamento" in col_low:
                        dims.add("DIM_UNIDADE")
                    elif "usuario" in col_low or "servidor" in col_low or "cliente" in col_low or "vendedor" in col_low:
                        dims.add("DIM_PESSOA_USUARIO")
                    elif col_low.startswith(("id_", "cod_", "cd_")) and len(col_low) > 3:
                        ent = re.sub(r"^(id_|cod_|cd_)", "", col_low).upper()
                        ent = re.sub(r"[^A-Z0-9_]", "_", ent).strip("_")
                        if ent:
                            dims.add(f"DIM_{ent}")
        if not dims:
            dims = {"DIM_TEMPO", "DIM_ENTIDADE"}
        if not fatos:
            fatos = {"FATO_PRINCIPAL"}
        return sorted(dims), sorted(fatos)

    def _run_heuristics(self):
        """Aplica as 5 Heurísticas de Engenharia Reversa e Qualidade de BI (PBIX-H1 a PBIX-H5) de forma 100% dinâmica."""

        tenants_by_file = {}
        seen_rule_conditions = set()

        for rep in self.reports:
            if rep.get("dominant_tenant"):
                tenants_by_file[rep["file"]] = rep["dominant_tenant"]

            # PBIX-H3: Detecção estrutural e dinâmica de Tabelão Desnormalizado (Flat Table)
            non_star_tables = [
                t for t in rep["tables"]
                if not t.upper().startswith(("DIM_", "FATO_", "FAT_", "VW_", "CALENDARIO", "D_", "F_"))
            ]
            for t in rep["tables"]:
                t_low = t.lower().strip()
                cols_count = len(rep["columns_by_table"].get(t, set()))
                measures_count = len(rep["measures_by_table"].get(t, set()))
                is_generic_name = any(
                    t_low == g or t_low.startswith(f"{g}_") or t_low.startswith(f"{g} ")
                    for g in GENERIC_FLAT_TABLE_NAMES
                )
                is_single_wide_table = len(non_star_tables) == 1 and t in non_star_tables and (cols_count + measures_count) >= 4
                is_wide_hybrid_table = (
                    t in non_star_tables and cols_count >= 6 and measures_count >= 1
                )
                if is_generic_name or is_single_wide_table or is_wide_hybrid_table:
                    self.flat_tables_detected.add(f"{rep['file']}: `{t}`")

            # Inspeciona filtros de página e visuais
            for page in rep["pages"]:
                for vf_owner, flist in [("Página", page["filters"])] + [
                    (f"Visual '{v['title']}' ({v['type']})", v["filters"]) for v in page["visuals"]
                ]:
                    for f in flist:
                        field_name = f.get("field", "")
                        cond = f["condition"]
                        cond_up = cond.upper()
                        cond_low = cond.lower()

                        # PBIX-H2: Vazamento dinâmico de filtro de órgão/tenant divergente do dominante do arquivo
                        dom = rep.get("dominant_tenant")
                        if dom and _is_tenant_filter(field_name, cond) and "NOT (" not in cond_up:
                            for lit in _extract_string_literals(cond):
                                if lit.upper() != dom.upper():
                                    leak_msg = (
                                        f"**{rep['file']}** (Tenant Dominante: `{dom}`) -> Aba `{page['name']}` -> "
                                        f"{vf_owner} possui filtro travado em `{cond}` (Vazamento de dados de `{lit}`!)"
                                    )
                                    if leak_msg not in self.cross_tenant_leaks:
                                        self.cross_tenant_leaks.append(leak_msg)

                        # PBIX-H5: Sanitização de lixo/teste no visual (exclusões manuais, códigos técnicos, strings vazias)
                        is_sanitation = (
                            any(k in cond_up for k in ("TESTE", "'*'", "'@'", "''", "<> ''"))
                            or ("NOT (" in cond_up and "IS NOT NULL" not in cond_up)
                        )
                        if is_sanitation:
                            san_msg = f"`{rep['file']}` | Aba `{page['name']}` | {vf_owner}: `{cond}`"
                            if san_msg not in self.sanitation_filters:
                                self.sanitation_filters.append(san_msg)

                        # PBIX-H4: Regras de negócio em filtros visuais (qualquer predicado seletivo que não seja tenant nem mera sanitização)
                        is_business_rule = (
                            not _is_tenant_filter(field_name, cond)
                            and not is_sanitation
                            and (
                                " IN (" in cond_up
                                or any(
                                    k in cond_low
                                    for k in (
                                        "id_",
                                        "cod_",
                                        "cd_",
                                        "status",
                                        "situacao",
                                        "tipo",
                                        "nivel",
                                        "unidade_n",
                                        "tarefa",
                                        "categoria",
                                        "indicador",
                                        "fl_",
                                        "sin_",
                                    )
                                )
                                or ("IS NOT NULL" in cond_up and "IS NULL" in cond_up)
                                or vf_owner.startswith("Visual ")
                            )
                        )
                        if is_business_rule:
                            rule_msg = f"`{rep['file']}` | Aba `{page['name']}` | {vf_owner}: `{cond}`"
                            if rule_msg not in self.business_rules_filters:
                                self.business_rules_filters.append(rule_msg)
                            if cond not in seen_rule_conditions:
                                seen_rule_conditions.add(cond)
                                self.business_rules_catalog.append({
                                    "contexto": f"{page['name']} — {vf_owner}",
                                    "expressao": cond,
                                    "campo": field_name or cond.split()[0],
                                })

        # PBIX-H1: Clonagem Multi-Tenant de arquivos .pbix
        if tenants_by_file:
            lista_clones = ", ".join(f"`{k}` -> `{v}`" for k, v in tenants_by_file.items())
            self.heuristics_triggered.append({
                "id": "PBIX_H1_CLONAGEM_MULTITENANT_SEM_RLS",
                "titulo": f"Clonagem Manual de Relatórios `.pbix` por Órgão/Tenant em vez de Row-Level Security ({len(tenants_by_file)} arquivos)",
                "gravidade": "CRÍTICA",
                "descricao": (
                    f"Os relatórios analisados utilizam filtros estáticos de página/relatório para isolar cada órgão/tenant: "
                    f"{lista_clones}. Manter arquivos `.pbix` separados por unidade/órgão multiplica o esforço de manutenção e gera divergência de versões."
                ),
                "prescricao": [
                    "Unificar os relatórios de mesma estrutura em um ÚNICO arquivo `.pbix` corporativo.",
                    "Implementar isolamento de acesso via **Row-Level Security (RLS)** no banco Oracle (`seguranca-rls-oracle` com `DBMS_RLS`) ou RLS dinâmico no modelo semântico.",
                ],
            })

        # PBIX-H2: Bug de Copy-Paste / Vazamento Cross-Tenant
        if self.cross_tenant_leaks:
            self.heuristics_triggered.append({
                "id": "PBIX_H2_VAZAMENTO_FILTRO_CROSS_TENANT",
                "titulo": f"Bug Real de Copy-Paste: Filtro de Outro Órgão/Tenant Esquecido Dentro de Visual ({len(self.cross_tenant_leaks)} ocorrências)",
                "gravidade": "CRÍTICA",
                "descricao": (
                    "Ao clonar ou adaptar o arquivo `.pbix` entre órgãos/unidades, um filtro interno permaneceu apontando "
                    "para outro tenant! Ocorrências detectadas: " + " ; ".join(self.cross_tenant_leaks)
                ),
                "prescricao": [
                    "Remover imediatamente os filtros visuais divergentes listados acima nos visuais afetados.",
                    "Substituir filtros manuais de órgão/tenant por política centralizada de RLS (`DBMS_RLS`).",
                ],
            })

        # PBIX-H3: Tabelão Desnormalizado (Flat Table)
        if self.flat_tables_detected:
            dims_sug, fatos_sug = self._infer_star_schema_candidates()
            nomes_tabeloes = ", ".join(sorted(self.flat_tables_detected))
            self.heuristics_triggered.append({
                "id": "PBIX_H3_TABELAO_FLAT_DESNORMALIZADO",
                "titulo": f"Modelo Baseado em Tabelão Flat Desnormalizado ({len(self.flat_tables_detected)} tabela(s) detectada(s))",
                "gravidade": "ALTA",
                "descricao": (
                    f"Foram detectadas tabelas planas desnormalizadas concentrando atributos dimensionais e métricas: "
                    f"{nomes_tabeloes}. Isso degrada a compressão colunar do VertiPaq, exige filtros complexos nos visuais e causa ambiguidade nos cálculos DAX."
                ),
                "prescricao": [
                    f"Decompor o tabelão no Star Schema oficial do DW Oracle (Dimensões sugeridas: `{', '.join(dims_sug)}` + Fato(s): `{', '.join(fatos_sug)}`).",
                    "Expor para o Power BI exclusivamente as Views da Camada Semântica (`VW_<PROJETO>_DIM_*`, `VW_<PROJETO>_EVENTO_*`, `VW_<PROJETO>_KPI_*`).",
                ],
            })

        # PBIX-H4: Regras de Negócio Ocultas em Filtros Visuais
        if self.business_rules_filters:
            exemplos_regras = "; ".join(self.business_rules_filters[:4])
            self.heuristics_triggered.append({
                "id": "PBIX_H4_REGRAS_NEGOCIO_HARDCODED_NO_VISUAL",
                "titulo": f"Regras de Negócio e KPIs Críticos Ocultos em Filtros Visuais ({len(self.business_rules_filters)} regras extraídas)",
                "gravidade": "ALTA",
                "descricao": (
                    "Regras de negócio e recortes de KPIs estão cravados manualmente nos filtros laterais de visuais/páginas "
                    f"do Power BI ({exemplos_regras}). Isso impede o reuso governado da regra em outros painéis e agentes de IA."
                ),
                "prescricao": [
                    "Promover essas condições para flags/atributos oficiais nas Dimensões (`DIM_*`) e métricas prontas nas views `VW_<PROJETO>_KPI_*`.",
                    "Catalogar todas as regras extraídas nas tabelas `META_OBJETO`, `META_METRICA` e `META_REGRA_NEGOCIO` da Camada Semântica.",
                ],
            })

        # PBIX-H5: Sanitização de Sujeira nos Filtros Visuais
        if self.sanitation_filters:
            exemplos_san = "; ".join(self.sanitation_filters[:4])
            self.heuristics_triggered.append({
                "id": "PBIX_H5_SANITIZACAO_DE_LIXO_NO_VISUAL",
                "titulo": f"Expurgo Manual de Dados de Teste/Sujeira no Visual do Relatório ({len(self.sanitation_filters)} ocorrências)",
                "gravidade": "ALERTA_QUALIDADE",
                "descricao": (
                    "Os visuais/páginas do Power BI estão filtrando manualmente registros inválidos, códigos técnicos ou dados de teste "
                    f"({exemplos_san}). Se um analista criar um novo visual e esquecer esses filtros, os indicadores sairão contaminados."
                ),
                "prescricao": [
                    "Mover o expurgo de registros inválidos/teste para a camada de Staging (`STG_*`) ou para a cláusula `WHERE` das Views `VW_<PROJETO>_DIM_*`.",
                ],
            })

    def print_summary(self):
        print(f"{NEGRITO}Arquivos .pbix Auditados ({len(self.reports)}):{RESET}")
        for r in self.reports:
            print(
                f"  - {CIANO}{r['file']}{RESET} | Modo: {r['connection_mode']} | "
                f"Tabelas: {len(r['tables'])} | Abas: {len(r['pages'])} | "
                f"Tenant Dominante: {r.get('dominant_tenant') or 'Global'}"
            )
        print()
        print(f"{NEGRITO}Heurísticas e Anti-Padrões Detectados ({len(self.heuristics_triggered)}):{RESET}")
        for h in self.heuristics_triggered:
            cor = VERMELHO if h["gravidade"] == "CRÍTICA" else (AMARELO if "ALTA" in h["gravidade"] or "ALERTA" in h["gravidade"] else VERDE)
            print(f"  {cor}[{h['gravidade']}]{RESET} {NEGRITO}[{h['id']}] {h['titulo']}{RESET}")
            print(f"     -> {h['descricao']}")
            print(f"     -> {CIANO}Prescrição:{RESET} {h['prescricao'][0]}\n")

    def generate_markdown_report(self, output_path: Path):
        lines = []
        lines.append("# Relatório de Engenharia Reversa & Auditoria de Relatórios Power BI (`.pbix`) — NINHO")
        lines.append(f"\n**Escopo Inspecionado:** `{self.target_path}` ({len(self.reports)} arquivo(s) `.pbix`)  ")
        lines.append("**Motor:** Extrator Determinístico `inspecionar_pbix.py` (Plataforma NINHO)\n")
        lines.append("---\n")

        lines.append("## 1. Resumo Executivo & Anti-Padrões Detectados\n")
        if not self.heuristics_triggered:
            lines.append("Nenhum anti-padrão crítico detectado nos arquivos inspecionados.\n")
        for idx, h in enumerate(self.heuristics_triggered, 1):
            lines.append(f"### 1.{idx}. [{h['id']}] {h['titulo']}")
            lines.append(f"- **Gravidade:** `{h['gravidade']}`")
            lines.append(f"- **Diagnóstico:** {h['descricao']}")
            lines.append("- **Prescrição Arquitetural:**")
            for p in h["prescricao"]:
                lines.append(f"  - {p}")
            lines.append("")

        lines.append("---\n")
        lines.append("## 2. Catálogo de Regras de Negócio e Filtros Extraídos dos Visuais\n")
        lines.append("| Contexto (Aba / Visual) | Expressão Extraída do Filtro Visual | Ação Recomendada no DW / Camada Semântica |")
        lines.append("| :--- | :--- | :--- |")
        if self.business_rules_catalog or self.sanitation_filters:
            for item in self.business_rules_catalog:
                lines.append(
                    f"| **{item['contexto']}** | `{item['expressao']}` | "
                    f"Promover regra sobre `{item['campo']}` para flag/métrica em `DIM_*` / `VW_<PROJETO>_KPI_*` e catalogar em `META_REGRA_NEGOCIO` |"
                )
            for san in self.sanitation_filters[:10]:
                lines.append(
                    f"| **Filtro de Sanitização** | {san} | "
                    "Aplicar expurgo na carga de `STG_*` e nas views vigentes `VW_<PROJETO>_DIM_*` |"
                )
        else:
            lines.append("| *(Sem filtros ocultos)* | *(Nenhuma expressão de filtro visual seletivo detectada)* | Manter regras centralizadas nas views `VW_<PROJETO>_*` |")
        lines.append("")

        lines.append("---\n")
        lines.append("## 3. Inventário Estrutural Detalhado por Arquivo `.pbix`\n")
        for rep in self.reports:
            lines.append(f"### 📊 Arquivo: `{rep['file']}`")
            lines.append(f"- **Modo de Conexão:** `{rep['connection_mode']}`")
            lines.append(f"- **Órgão/Tenant Dominante nos Filtros de Página:** `{rep.get('dominant_tenant') or 'Não restrito'}`")
            lines.append(f"- **Tabelas Mapeadas ({len(rep['tables'])}):** `{', '.join(rep['tables'])}`")
            if rep["measures_by_table"]:
                all_measures = []
                for tbl, mset in sorted(rep["measures_by_table"].items()):
                    for m in sorted(mset):
                        all_measures.append(f"`{tbl}.{m}`")
                lines.append(f"- **Medidas DAX Referenciadas:** {', '.join(all_measures)}")
            lines.append("\n#### Páginas e Visuais:")
            for p in rep["pages"]:
                pf_str = "; ".join(f"`{f['condition']}`" for f in p["filters"]) or "Nenhum"
                lines.append(f"- **Aba `{p['name']}`** (Filtros de Página: {pf_str}) — `{len(p['visuals'])}` visuais de dados:")
                for v in p["visuals"]:
                    vf_str = "; ".join(f"`{f['condition']}`" for f in v["filters"])
                    flds_str = ", ".join(f"`{fl}`" for fl in v["fields"][:6])
                    extra_vf = f" | **Filtro Visual:** {vf_str}" if vf_str else ""
                    lines.append(f"  - `{v['type']}` **{v['title']}**: Campos: {flds_str}{extra_vf}")
            lines.append("")

        output_path.write_text("\n".join(lines), encoding="utf-8")
        print_ok(f"Relatório de engenharia reversa PBIX gerado com sucesso em: {output_path}")


def main():
    print_banner()
    parser = argparse.ArgumentParser(description="Motor de Engenharia Reversa de Arquivos Power BI (.pbix) — NINHO")
    parser.add_argument("pbix_path", help="Caminho para arquivo .pbix ou pasta contendo arquivos .pbix")
    parser.add_argument("--output", "-o", help="Caminho de saída para o relatório Markdown", default=None)

    args = parser.parse_args()
    target = Path(args.pbix_path)

    if not target.exists():
        print_err(f"Caminho não encontrado: {target}")
        sys.exit(1)

    inspector = PBIXInspector(target)
    inspector.run()
    inspector.print_summary()

    if args.output:
        out_file = Path(args.output)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        inspector.generate_markdown_report(out_file)


if __name__ == "__main__":
    main()
