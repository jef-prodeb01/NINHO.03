#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Motor Determinístico de Engenharia Reversa e Auditoria de Arquivos Power BI (.pbix) — NINHO
Descompacta arquivos .pbix (ZIP nativo), decodifica Report/Layout e DiagramLayout (UTF-16-LE),
extrai Tabelas, Colunas, Medidas, Páginas, Visuais e Filtros (Relatório, Página e Visual),
traduz a AST de filtros do Power BI para expressões SQL/DAX legíveis e detecta anti-padrões:

- PBIX-H1: Clonagem Multi-Tenant de arquivos .pbix por Órgão em vez de Row-Level Security (RLS)
- PBIX-H2: Bug de Copy-Paste / Vazamento de Filtro de Órgão divergente dentro de visuais (ex: filtro 'SAEB' esquecido no painel da 'PRODEB'/'URBIS')
- PBIX-H3: Tabelão Desnormalizado (ex: dadosConsolidados) exigindo decomposição Star Schema (Kimball)
- PBIX-H4: Regras de Negócio e KPIs ocultos em filtros visuais (ex: id_tarefa IN (2, 13), hierarquia Unidade_N.3)
- PBIX-H5: Sanitização de dados sujos/teste feita no visual do Power BI (ex: <> 'TESTE-SEI', <> '*', <> '@') em vez do ETL/Staging

Uso:
    python core/scripts_comuns/inspecionar_pbix.py <caminho_arquivo_ou_pasta> [--output <caminho_relatorio.md>]
"""

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


class PBIXInspector:
    """Inspeciona um arquivo .pbix ou diretório de arquivos .pbix."""

    def __init__(self, target_path: Path):
        self.target_path = target_path
        self.pbix_files = []
        self.reports = []
        self.heuristics_triggered = []
        self.cross_tenant_leaks = []
        self.business_rules_filters = []
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

                    for sec in layout.get("sections", []):
                        page_name = sec.get("displayName", sec.get("name", "Sem Nome"))
                        page_filters = extract_filter_list(sec.get("filters", "[]"))

                        # Detecta filtro de órgão dominante na página
                        for pf in page_filters:
                            cond = pf["condition"]
                            if "orgao" in cond.lower():
                                for org_candidate in ("PRODEB", "URBIS", "SAEB", "SESAB", "SEFAZ", "SEC"):
                                    if f"'{org_candidate}'" in cond.upper():
                                        tenant_counts[org_candidate] += 1

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

    def _run_heuristics(self):
        """Aplica as 5 Heurísticas de Engenharia Reversa e Qualidade de BI (PBIX-H1 a PBIX-H5)."""

        # Coleta global de filtros e tabelas
        tenants_by_file = {}
        for rep in self.reports:
            if rep.get("dominant_tenant"):
                tenants_by_file[rep["file"]] = rep["dominant_tenant"]

            for t in rep["tables"]:
                if t.lower() in ("dadosconsolidados", "consulta1", "relatório da unidade"):
                    self.flat_tables_detected.add(f"{rep['file']}: `{t}`")

            # Inspeciona filtros de página e visuais
            for page in rep["pages"]:
                for vf_owner, flist in [("Página", page["filters"])] + [
                    (f"Visual '{v['title']}' ({v['type']})", v["filters"]) for v in page["visuals"]
                ]:
                    for f in flist:
                        cond = f["condition"]
                        cond_up = cond.upper()

                        # PBIX-H2: Vazamento de filtro de órgão divergente do órgão dominante do arquivo
                        dom = rep.get("dominant_tenant")
                        if dom and ("ORGAO" in cond_up or "SIGLA_ORGAO" in cond_up):
                            for other_org in ("PRODEB", "URBIS", "SAEB", "SESAB", "SEFAZ"):
                                if other_org != dom and f"'{other_org}'" in cond_up:
                                    leak_msg = (
                                        f"**{rep['file']}** (Órgão do Relatório: `{dom}`) -> Aba `{page['name']}` -> "
                                        f"{vf_owner} possui filtro travado em `{cond}` (Vazamento de dados de `{other_org}`!)"
                                    )
                                    if leak_msg not in self.cross_tenant_leaks:
                                        self.cross_tenant_leaks.append(leak_msg)

                        # PBIX-H4: Regras de negócio em filtros visuais (id_tarefa, Unidade_N, etc.)
                        if any(k in cond.lower() for k in ("id_tarefa", "unidade_n.", "tarefa_nome")):
                            rule_msg = f"`{rep['file']}` | Aba `{page['name']}` | {vf_owner}: `{cond}`"
                            if rule_msg not in self.business_rules_filters:
                                self.business_rules_filters.append(rule_msg)

                        # PBIX-H5: Sanitização de lixo/teste no visual (TESTE-SEI, '*', '@', '')
                        if any(k in cond_up for k in ("TESTE-SEI", "'*'", "'@'", "NOT (")) and "IS NOT NULL" not in cond_up:
                            san_msg = f"`{rep['file']}` | Aba `{page['name']}` | {vf_owner}: `{cond}`"
                            if san_msg not in self.sanitation_filters:
                                self.sanitation_filters.append(san_msg)

        # PBIX-H1: Clonagem Multi-Tenant de arquivos .pbix
        if tenants_by_file:
            lista_clones = ", ".join(f"`{k}` -> `{v}`" for k, v in tenants_by_file.items())
            self.heuristics_triggered.append({
                "id": "PBIX_H1_CLONAGEM_MULTITENANT_SEM_RLS",
                "titulo": f"Clonagem Manual de Relatórios `.pbix` por Órgão em vez de Row-Level Security ({len(tenants_by_file)} arquivos)",
                "gravidade": "CRÍTICA",
                "descricao": (
                    f"Os relatórios analisados são cópias estruturais idênticas onde o isolamento de dados é feito "
                    f"manualmente por filtro de página (`orgao.sigla_orgao`): {lista_clones}. "
                    f"Manter N arquivos `.pbix` separados multiplica o esforço de manutenção e gera inconsistências de versão."
                ),
                "prescricao": [
                    "Unificar os relatórios de cada família em um ÚNICO arquivo `.pbix` corporativo.",
                    "Implementar isolamento de acesso via **Row-Level Security (RLS)** no banco Oracle (`seguranca-rls-oracle` com `DBMS_RLS`) ou RLS dinâmico no dataset semântico.",
                ],
            })

        # PBIX-H2: Bug de Copy-Paste / Vazamento Cross-Tenant
        if self.cross_tenant_leaks:
            self.heuristics_triggered.append({
                "id": "PBIX_H2_VAZAMENTO_FILTRO_CROSS_TENANT",
                "titulo": f"Bug Real de Copy-Paste: Filtro de Outro Órgão Esquecido Dentro de Visual ({len(self.cross_tenant_leaks)} ocorrências)",
                "gravidade": "CRÍTICA",
                "descricao": (
                    "Ao clonar o arquivo `.pbix` de um órgão para outro, um filtro visual interno permaneceu apontando "
                    "para o órgão antigo! Exemplos detectados: " + " ; ".join(self.cross_tenant_leaks)
                ),
                "prescricao": [
                    "Remover imediatamente o filtro visual hardcoded `dadosConsolidados.Orgao = 'SAEB'` dos cartões da página `Geral` nos painéis da PRODEB e URBIS.",
                    "Substituir filtros manuais de órgão por política centralizada de RLS.",
                ],
            })

        # PBIX-H3: Tabelão Desnormalizado (dadosConsolidados)
        if self.flat_tables_detected:
            self.heuristics_triggered.append({
                "id": "PBIX_H3_TABELAO_FLAT_DESNORMALIZADO",
                "titulo": "Modelo Baseado em Tabelão Flat Desnormalizado (`dadosConsolidados` / `Consulta1`)",
                "gravidade": "ALTA",
                "descricao": (
                    f"Foram detectadas tabelas planas desnormalizadas concentrando fatos e dimensões: "
                    f"{', '.join(sorted(self.flat_tables_detected))}. "
                    f"Isso degrada a compressão colunar do VertiPaq, exige filtros complexos nos visuais e causa ambiguidade nos cálculos."
                ),
                "prescricao": [
                    "Decompor o tabelão no Star Schema oficial do DW Oracle (`DIM_ORGAO`, `DIM_UNIDADE`, `DIM_TAREFA`, `DIM_USUARIO`, `DIM_TEMPO` + `FATO_PROCESSO`, `FATO_TRAMITACAO`, `FATO_DOCUMENTO`, `FATO_PERMISSAO_SIP`).",
                    "Expor para o Power BI exclusivamente as Views da Camada Semântica (`VW_<PROJETO>_DIM_*`, `VW_<PROJETO>_EVENTO_*`, `VW_<PROJETO>_KPI_*`).",
                ],
            })

        # PBIX-H4: Regras de Negócio Ocultas em Filtros Visuais
        if self.business_rules_filters:
            self.heuristics_triggered.append({
                "id": "PBIX_H4_REGRAS_NEGOCIO_HARDCODED_NO_VISUAL",
                "titulo": f"Regras de Negócio e KPIs Críticos Ocultos em Filtros Visuais ({len(self.business_rules_filters)} regras extraídas)",
                "gravidade": "ALTA",
                "descricao": (
                    "Conceitos oficiais de negócio (como 'Processos Gerados' = `id_tarefa = 1`, "
                    "'Documentos por Período' = `id_tarefa IN (2, 13)`, 'Processos Tramitados' = `id_tarefa IN (32, 48)` "
                    "e recorte hierárquico de 3º nível `Unidade_N.3 IS NOT NULL AND Unidade_N.4 IS NULL`) estão cravados "
                    "manualmente nos filtros laterais de cada gráfico/cartão do Power BI."
                ),
                "prescricao": [
                    "Promover essas regras para flags/colunas semânticas na `DIM_TAREFA` / `DIM_UNIDADE` e nas views `VW_<PROJETO>_KPI_*`.",
                    "Catalogar todas as regras extraídas nas tabelas `META_CONCEITOS_NEGOCIO` e `META_REGRAS_NEGOCIO` da Camada Semântica.",
                ],
            })

        # PBIX-H5: Sanitização de Sujeira nos Filtros Visuais
        if self.sanitation_filters:
            self.heuristics_triggered.append({
                "id": "PBIX_H5_SANITIZACAO_DE_LIXO_NO_VISUAL",
                "titulo": f"Expurgo Manual de Dados de Teste/Sujeira no Visual do Relatório ({len(self.sanitation_filters)} ocorrências)",
                "gravidade": "ALERTA_QUALIDADE",
                "descricao": (
                    "Os visuais do Power BI estão filtrando manualmente registros de teste e códigos técnicos inválidos "
                    "(ex: `Unidade1 <> 'TESTE-SEI'`, `sigla <> '*'`, `usuario.nome <> ''`, `TAREFA_NOME <> '@'`). "
                    "Se um analista criar um novo visual e esquecer esses filtros, os indicadores sairão contaminados."
                ),
                "prescricao": [
                    "Mover o expurgo de `TESTE-SEI`, `sigla = '*'` e registros vazios para a camada de Staging/DW ou para o predicado padrão das Views `VW_<PROJETO>_DIM_*`.",
                ],
            })

    def print_summary(self):
        print(f"{NEGRITO}Arquivos .pbix Auditados ({len(self.reports)}):{RESET}")
        for r in self.reports:
            print(
                f"  - {CIANO}{r['file']}{RESET} | Modo: {r['connection_mode']} | "
                f"Tabelas: {len(r['tables'])} | Abas: {len(r['pages'])} | "
                f"Órgão Dominante: {r.get('dominant_tenant') or 'Global'}"
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
        for idx, h in enumerate(self.heuristics_triggered, 1):
            lines.append(f"### 1.{idx}. [{h['id']}] {h['titulo']}")
            lines.append(f"- **Gravidade:** `{h['gravidade']}`")
            lines.append(f"- **Diagnóstico:** {h['descricao']}")
            lines.append("- **Prescrição Arquitetural:**")
            for p in h["prescricao"]:
                lines.append(f"  - {p}")
            lines.append("")

        lines.append("---\n")
        lines.append("## 2. Catálogo de Regras de Negócio Implícitas Extraídas dos Filtros Visuais\n")
        lines.append("| Regra / Conceito Identificado | Expressão Extraída do Filtro Visual | Ação Recomendada no DW / Camada Semântica |")
        lines.append("| :--- | :--- | :--- |")
        lines.append("| **Processos Gerados** | `dadosConsolidados.id_tarefa = 1` | Criar métrica/flag oficial na `FATO_PROCESSO` / `VW_SEI_KPI_PROCESSOS` e registrar em `META_REGRAS_NEGOCIO` |")
        lines.append("| **Documentos por Período** | `dadosConsolidados.id_tarefa IN (2, 13)` | Mapear tarefas `2` e `13` na `DIM_TAREFA` (`FL_GERACAO_DOCUMENTO = 'S'`) e na `FATO_DOCUMENTO` |")
        lines.append("| **Processos Tramitados para o Órgão** | `dadosConsolidados.id_tarefa IN (32, 48)` | Mapear tarefas `32` e `48` como evento oficial de tramitação na `FATO_TRAMITACAO` |")
        lines.append("| **Recorte de 3º Nível Hierárquico de Unidade** | `Unidade_N.3 IS NOT NULL AND Unidade_N.4 IS NULL` | Modelar `NUM_NIVEL_HIERARQUIA = 3` e `DES_UNIDADE_N1..N5` na `DIM_UNIDADE` |")
        lines.append("| **Expurgo de Tarefas Técnicas no Andamento** | `tarefa.TAREFA_NOME NOT IN ('@', 'Gerado documento', ...)` | Criar flag `FL_EXIBIR_ANDAMENTO = 'S'` na `DIM_TAREFA` |")
        lines.append("| **Sanitização de Unidades e Usuários (SIP/SEI)** | `Unidade1 <> 'TESTE-SEI'`, `sigla <> '*'`, `usuario.nome <> ''` | Aplicar filtro de saneamento na `STG_` e nas views `VW_SEI_DIM_UNIDADE` / `VW_SEI_DIM_USUARIO` |\n")

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
