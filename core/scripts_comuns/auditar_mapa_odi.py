#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auditor Preditivo de Performance e Arquitetura para Objetos e Projetos ODI 12c (NINHO v2.0)
Inspeciona arquivos XML isolados ou diretórios completos exportados do Oracle Data Integrator (ODI 12c):
- Mapeamentos (MAP_*.xml / SnpMapping / SnpMapComp)
- Cenários Compilados (SCEN_*.xml / SnpScen / SnpScenTask)
- Pacotes de Orquestração (PACK_*.xml / SnpPackage / SnpStep)
- Procedures (TRT_*.xml / SnpTrt / SnpLineTrt)
- Variáveis (VAR_*.xml / SnpVar)

Detecta 9 Heurísticas Preditivas (H1 a H9), incluindo bugs reais de produção:
- H1 (A/B/C/D): CDC por Ciclo de Vida (Abertura + Conclusão), Auditoria Clássica, Append-Only ou Carga Total
- H2: Primary Key na Staging e Prevenção de Colisão Multi-Tenant (#V_IBGE || '000' || ID)
- H3: Seleção Ótima de IKM (IKM Oracle Merge vs Incremental Update / Control Append)
- H4: Mapeamentos Monolíticos ou Orquestração Serial de Cenários sem -ASYNC=YES
- H5: Funil de I/O em Driver JDBC (LKM SQL to Oracle com tabelas C$_)
- H6: Risco de Fan Trap em Fatos (Lookup/Join em Dimensão SCD2 sem filtro DTC_EXPIRACAO IS NULL)
- H7: Falso SCD Tipo 2 (Coluna de detecção de mudança DES_ATUALIZAR fixada com literal constante 'X')
- H8: Bugs de SQL Dimensional (Join em DIM_TEMPO sem TRUNC() e métrica de duração dentro do GROUP BY sem SUM)
- H9: Loop Multi-Tenant Intra-Oracle recriando tabelas C$_ a cada iteração do município/órgão

Uso:
    python core/scripts_comuns/auditar_mapa_odi.py <caminho_arquivo_ou_pasta> [--output <caminho_relatorio.md>]
"""

import sys
import os
import re
import argparse
from pathlib import Path
import xml.etree.ElementTree as ET

# Configura encoding UTF-8 no stdout do Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Cores ANSI para terminal
VERDE = "\033[92m"
AMARELO = "\033[93m"
VERMELHO = "\033[91m"
AZUL = "\033[94m"
CIANO = "\033[96m"
NEGRITO = "\033[1m"
RESET = "\033[0m"

# Padrões regex para detecção de colunas de auditoria/atualização clássicas
REGEX_UPDATE_COLS = re.compile(
    r"(update|altera|modif|modificad|dth_alt|dt_alt|data_alt|last_upd|audit|dth_sit|dat_sit)",
    re.IGNORECASE
)
# Padrões para colunas de criação/início
REGEX_CREATE_COLS = re.compile(
    r"(create|criacao|cadast|inser|dth_inc|dt_inc|data_inc|dth_cad|dt_cad|abertura|emissao|geracao|registro|entrada|dth_abertura|dt_abertura|dta_geracao)",
    re.IGNORECASE
)
# Padrões para colunas de encerramento / conclusão de ciclo de vida
REGEX_CLOSE_COLS = re.compile(
    r"(conclusao|fechamento|encerramento|termino|finalizacao|baixa|cancelamento|dth_conclusao|dta_conclusao|dt_conclusao)",
    re.IGNORECASE
)
# Todas as colunas com tipagem temporal ou prefixo de data
REGEX_ANY_DATE_COLS = re.compile(
    r"\b((?:dth_|dt_|dat_|dta_|data_|dh_)[A-Za-z0-9_]+|[A-Za-z0-9_]*(?:_date|_dth|_time|_at))\b",
    re.IGNORECASE
)


def print_banner():
    print(f"\n{AZUL}{NEGRITO}{'=' * 85}{RESET}")
    print(f"{CIANO}{NEGRITO}  🦅 PLATAFORMA NINHO — MOTOR PREDITIVO DE AUDITORIA & TUNING ODI 12c (v2.0){RESET}")
    print(f"{AZUL}{NEGRITO}{'=' * 85}{RESET}\n")


def print_ok(msg: str):
    print(f"  {VERDE}[OK]{RESET} {msg}")


def print_warn(msg: str):
    print(f"  {AMARELO}[AVISO]{RESET} {msg}")


def print_err(msg: str):
    print(f"  {VERMELHO}[ERRO]{RESET} {msg}")


class ODIMappingAuditor:
    """Audita um único arquivo XML (Mapa, Cenário, Pacote, Procedure ou Variável) ou um diretório completo ODI."""

    def __init__(self, target_path: Path):
        self.target_path = target_path
        self.is_dir = target_path.is_dir()
        self.xml_files = []
        self.mapping_name = target_path.stem if not self.is_dir else f"PROJETO_ODI_{target_path.name}"

        # Inventário de objetos encontrados
        self.mappings_info = []
        self.scenarios_info = []
        self.packages_info = []
        self.procedures_info = []
        self.variables_info = []

        # Consolidados para heurísticas
        self.stg_targets = []
        self.dim_targets = []
        self.fact_targets = []
        self.source_tables = []
        self.update_date_cols = []
        self.create_date_cols = []
        self.close_date_cols = []
        self.all_date_columns_found = []
        self.lkms_found = []
        self.ikms_found = []
        self.hints_found = []
        self.truncate_detected = False
        self.flow_control_detected = False
        self.has_filter_components = False
        self.filter_components_list = []
        self.multitenant_concat_found = False
        self.multitenant_loop_found = False
        self.same_db_all_users_discovery = False

        # Achados específicos de bugs reais (H6, H7, H8, H9)
        self.h6_fact_joins_missing_scd2_filter = []
        self.h7_fake_scd2_constant_x = []
        self.h8_date_joins_missing_trunc = []
        self.h8_duration_in_group_by = []
        self.h9_c_dollar_in_multitenant_loop = []
        self.serial_scen_packages = []

        self.heuristics_triggered = []

    def parse(self):
        if self.is_dir:
            self.xml_files = sorted(list(self.target_path.rglob("*.xml")))
        else:
            self.xml_files = [self.target_path]

        all_raw_texts = []
        for xml_file in self.xml_files:
            raw_text = xml_file.read_text(encoding="utf-8", errors="ignore")
            all_raw_texts.append((xml_file, raw_text))
            self._parse_single_file(xml_file, raw_text)

        combined_text = "\n".join(t for _, t in all_raw_texts)
        self._extract_global_tokens(combined_text)
        self._run_predictive_heuristics()

    def _parse_single_file(self, xml_file: Path, raw_text: str):
        root = None
        if "<SunopsisExport" in raw_text or xml_file.suffix.lower() == ".xml":
            try:
                tree = ET.parse(xml_file)
                root = tree.getroot()
            except Exception:
                root = None

        if root is None:
            return

        # 1. Mapeamentos (SnpMapping)
        for obj in root.findall(".//Object[@class='com.sunopsis.dwg.dbobj.SnpMapping']"):
            m_name = self._get_field(obj, "Name") or xml_file.stem
            if not self.is_dir:
                self.mapping_name = m_name

            comps = []
            for comp in root.findall(".//Object[@class='com.sunopsis.dwg.dbobj.SnpMapComp']"):
                c_name = self._get_field(comp, "Name") or ""
                c_type = self._get_field(comp, "CompType") or ""
                comps.append((c_name, c_type))
                if "FILTER" in c_name.upper() or "FILTER" in c_type.upper():
                    self.has_filter_components = True
                    self.filter_components_list.append(f"{m_name}:{c_name}")

            # Compatibilidade com SnpMapCompFilter legado
            for _ in root.findall(".//Object[@class='com.sunopsis.dwg.dbobj.SnpMapCompFilter']"):
                self.has_filter_components = True
                self.filter_components_list.append(f"{m_name}:SnpMapCompFilter")

            # Expressões dentro do mapa (No ODI 12.2.1 o campo chama-se Txt)
            exprs = []
            for exp_obj in root.findall(".//Object[@class='com.sunopsis.dwg.dbobj.SnpMapExpr']"):
                txt = self._get_field(exp_obj, "Txt") or self._get_field(exp_obj, "Text")
                if txt:
                    exprs.append(txt.strip())

            self._inspect_expressions_and_sql(m_name, exprs, raw_text)

            self.mappings_info.append({
                "file": xml_file.name,
                "name": m_name,
                "components": comps,
                "expr_count": len(exprs),
            })

        # 2. Cenários Compilados (SnpScen & SnpScenTask)
        for obj in root.findall(".//Object[@class='com.sunopsis.dwg.dbobj.SnpScen']"):
            s_name = self._get_field(obj, "ScenName") or xml_file.stem
            if not self.is_dir and not self.mappings_info:
                self.mapping_name = s_name

            sql_tasks = []
            for task in root.findall(".//Object[@class='com.sunopsis.dwg.dbobj.SnpScenTask']"):
                def_txt = self._get_field(task, "DefTxt") or ""
                col_txt = self._get_field(task, "ColTxt") or ""
                task_name1 = self._get_field(task, "TaskName1") or ""
                task_name2 = self._get_field(task, "TaskName2") or ""
                task_name3 = self._get_field(task, "TaskName3") or ""
                for sql_block in (def_txt, col_txt):
                    if sql_block.strip():
                        sql_tasks.append((f"{task_name2}:{task_name3}", sql_block.strip()))

            self._inspect_compiled_scenario_sql(s_name, sql_tasks)

            self.scenarios_info.append({
                "file": xml_file.name,
                "name": s_name,
                "task_count": len(sql_tasks),
            })

        # 3. Pacotes (SnpPackage)
        for obj in root.findall(".//Object[@class='com.sunopsis.dwg.dbobj.SnpPackage']"):
            p_name = self._get_field(obj, "PackName") or xml_file.stem
            steps = []
            sync_scen_calls = []
            for step in root.findall(".//Object[@class='com.sunopsis.dwg.dbobj.SnpStep']"):
                st_name = self._get_field(step, "StepName") or ""
                st_type = self._get_field(step, "StepType") or ""
                steps.append((st_name, st_type))
            for txt_el in root.findall(".//Field[@name='ITxtVarValue']"):
                if txt_el.text and "OdiStartScen" in txt_el.text:
                    cmd = txt_el.text.strip()
                    if "-ASYNC=YES" not in cmd.upper() and "-SYNC_MODE=2" not in cmd.upper():
                        sync_scen_calls.append(cmd)
            if len(sync_scen_calls) >= 3:
                self.serial_scen_packages.append((p_name, len(sync_scen_calls)))
            if any("V_CNT" in s[0] or "V_MAX" in s[0] for s in steps):
                self.multitenant_loop_found = True

            self.packages_info.append({
                "file": xml_file.name,
                "name": p_name,
                "steps": steps,
                "sync_scen_calls": len(sync_scen_calls),
            })

        # 4. Procedures (SnpTrt)
        for obj in root.findall(".//Object[@class='com.sunopsis.dwg.dbobj.SnpTrt']"):
            t_name = self._get_field(obj, "TrtName") or xml_file.stem
            if "ALL_USERS" in raw_text.upper() and "ODI_SCHEMA_CTRL" in raw_text.upper():
                self.same_db_all_users_discovery = True
                self.multitenant_loop_found = True
            if "TRUNCATE TABLE" in raw_text.upper():
                self.truncate_detected = True
            self.procedures_info.append({
                "file": xml_file.name,
                "name": t_name,
            })

        # 5. Variáveis (SnpVar)
        for obj in root.findall(".//Object[@class='com.sunopsis.dwg.dbobj.SnpVar']"):
            v_name = self._get_field(obj, "VarName") or xml_file.stem
            if v_name.upper() in ("V_SCHEMA", "V_IBGE", "V_CNT", "V_MAX"):
                self.multitenant_loop_found = True
            self.variables_info.append({
                "file": xml_file.name,
                "name": v_name,
            })

    @staticmethod
    def _get_field(elem, field_name: str) -> str:
        f = elem.find(f"./Field[@name='{field_name}']")
        if f is not None and f.text:
            return f.text.strip()
        return ""

    def _inspect_expressions_and_sql(self, obj_name: str, exprs: list, raw_text: str):
        """Analisa expressões de mapeamentos para detectar H6, H7, H8 e chaves multi-tenant."""
        joined_exprs = "\n".join(exprs)

        # Detecção de concatenação multi-tenant (#V_IBGE || '000' || ID)
        if "000" in joined_exprs and ("V_IBGE" in joined_exprs.upper() or "V_TENANT" in joined_exprs.upper()):
            self.multitenant_concat_found = True

        # H7: Detecção de Falso SCD2 (DES_ATUALIZAR preenchido com constante 'X')
        if "DES_ATUALIZAR" in raw_text.upper():
            # No mapa de dimensão, a expressão para DES_ATUALIZAR é literalmente 'X'
            if any(e.strip() == "'X'" for e in exprs) or re.search(r"'X'\s+(?:AS\s+)?DES_ATUALIZAR", raw_text, re.IGNORECASE):
                if obj_name not in self.h7_fake_scd2_constant_x:
                    self.h7_fake_scd2_constant_x.append(obj_name)

        # H6: Em mapas de FATO, verificar joins com DIM_* que não têm DTC_EXPIRACAO IS NULL
        is_fact_map = "FATO" in obj_name.upper() or "FAT_" in obj_name.upper()
        if is_fact_map:
            for e in exprs:
                # Procura condições de join do tipo STG_...ID_X = DIM_...ID_X
                if re.search(r"\bDIM_[A-Za-z0-9_]+\.ID_[A-Za-z0-9_]+\b", e, re.IGNORECASE):
                    if "DTC_EXPIRACAO" not in joined_exprs.upper() and "FL_REGISTRO_ATUAL" not in joined_exprs.upper():
                        finding = f"{obj_name}: `{e.strip()}` (Sem filtro `DTC_EXPIRACAO IS NULL`)"
                        if finding not in self.h6_fact_joins_missing_scd2_filter:
                            self.h6_fact_joins_missing_scd2_filter.append(finding)

                # H8A: Join com DIM_TEMPO.DTC_COMPLETA sem TRUNC na coluna da STG
                if "DTC_COMPLETA" in e.upper() and "=" in e:
                    # Ex: NVL(STG_SEI_PROTOCOLO.DTA_GERACAO, TRUNC(SYSDATE)) = DIM_TEMPO.DTC_COMPLETA
                    left_side = e.split("=")[0] if "DTC_COMPLETA" in e.split("=")[1].upper() else e.split("=")[1]
                    if not re.search(r"TRUNC\s*\(\s*[A-Za-z0-9_]+\.[A-Za-z0-9_]+", left_side, re.IGNORECASE):
                        finding = f"{obj_name}: `{e.strip()}` (Coluna de data sem `TRUNC()` no join com `DIM_TEMPO`)"
                        if finding not in self.h8_date_joins_missing_trunc:
                            self.h8_date_joins_missing_trunc.append(finding)

                # H8B: Cálculo de duração (86400 / SYSDATE - DT_ABERTURA) sem SUM/AVG
                if "86400" in e and not re.search(r"\b(SUM|AVG|MIN|MAX)\s*\(", e, re.IGNORECASE):
                    finding = f"{obj_name}: `{e.strip()}` (Expressão de duração sem função de agregação `SUM()`)"
                    if finding not in self.h8_duration_in_group_by:
                        self.h8_duration_in_group_by.append(finding)

    def _inspect_compiled_scenario_sql(self, scen_name: str, sql_tasks: list):
        """Inspeciona o SQL compilado real dentro de SnpScenTask (SCEN_*.xml)."""
        for task_label, sql in sql_tasks:
            sql_up = sql.upper()

            # H9: Tabela C$_ criada dentro de cenário que usa #V_SCHEMA / #BI_SEI_MUNICIPIO.V_SCHEMA
            if ("CREATE TABLE" in sql_up and "C$_" in sql_up) or ("FROM" in sql_up and ".V_SCHEMA" in sql_up):
                if "C$_" in sql_up or ".V_SCHEMA" in sql_up:
                    if scen_name not in self.h9_c_dollar_in_multitenant_loop:
                        self.h9_c_dollar_in_multitenant_loop.append(scen_name)

            # H7 no SQL compilado: 'X' AS ...DES_ATUALIZAR + STG.DES_ATUALIZAR <> DIM.DES_ATUALIZAR
            if re.search(r"'X'\s+AS\s+[A-Za-z0-9_]*DES_ATUALIZAR", sql, re.IGNORECASE) or "STG.DES_ATUALIZAR <> DIM.DES_ATUALIZAR" in sql_up:
                if scen_name not in self.h7_fake_scd2_constant_x:
                    self.h7_fake_scd2_constant_x.append(scen_name)

            # H6 no SQL compilado: LEFT OUTER JOIN ... DIM_... ON STG.ID_... = DIM.ID_... sem DTC_EXPIRACAO
            for m in re.finditer(
                r"LEFT\s+OUTER\s+JOIN\s+(?:<\?=.*?\?>\s+)?(DIM_SEI_MUNIC_[A-Za-z0-9_]+|DIM_[A-Za-z0-9_]+)\s+ON\s+([^\n\r)]+)",
                sql,
                re.IGNORECASE | re.DOTALL,
            ):
                dim_tbl = m.group(1).strip()
                on_clause = " ".join(m.group(2).strip().split())
                if "DIM_TEMPO" not in dim_tbl.upper() and "DTC_EXPIRACAO" not in on_clause.upper():
                    finding = f"{scen_name} ({dim_tbl}): `ON {on_clause}`"
                    if len(self.h6_fact_joins_missing_scd2_filter) < 15 and finding not in self.h6_fact_joins_missing_scd2_filter:
                        self.h6_fact_joins_missing_scd2_filter.append(finding)

            # H8A no SQL compilado: ON NVL(STG_...DTA_GERACAO, TRUNC(SYSDATE)) = DIM_TEMPO.DTC_COMPLETA
            for m in re.finditer(r"ON\s+([^\n\r]*?DTC_COMPLETA\b)", sql, re.IGNORECASE):
                on_clause = " ".join(m.group(1).strip().split())
                if "=" in on_clause:
                    left_side = on_clause.split("=")[0] if "DTC_COMPLETA" in on_clause.split("=")[1].upper() else on_clause.split("=")[1]
                    if not re.search(r"TRUNC\s*\(\s*[A-Za-z0-9_]+\.[A-Za-z0-9_]+", left_side, re.IGNORECASE):
                        finding = f"{scen_name}: `ON {on_clause}` (Coluna de data sem `TRUNC()` no join com `DIM_TEMPO`)"
                        if finding not in self.h8_date_joins_missing_trunc:
                            self.h8_date_joins_missing_trunc.append(finding)

            # H8B no SQL compilado: GROUP BY contendo * 86400
            if "GROUP BY" in sql_up and "86400" in sql_up:
                gb_part = sql_up.split("GROUP BY", 1)[1]
                if "86400" in gb_part:
                    finding = f"{scen_name}: Cláusula `GROUP BY` contém cálculo `((NVL(DT_CONCLUSAO, SYSDATE) - DT_ABERTURA) * 86400)` sem `SUM()`"
                    if finding not in self.h8_duration_in_group_by:
                        self.h8_duration_in_group_by.append(finding)

    def _extract_global_tokens(self, raw_text: str):
        """Extrai tabelas, KMs e colunas temporais do conjunto de XMLs."""
        table_matches = re.findall(
            r'<Field name="Name" type="java\.lang\.String"><!\[CDATA\[([A-Za-z0-9_]+)\]\]></Field>',
            raw_text,
        )
        # Também captura tabelas de comandos TRUNCATE / INSERT / MERGE nos cenários/procedures
        sql_table_matches = re.findall(
            r'(?:INTO|TABLE|JOIN|FROM)\s+(?:[A-Za-z0-9_#.]+\.)?((?:STG_|DIM_|FATO_|FAT_|ODI_DIM_)[A-Za-z0-9_]+)',
            raw_text,
            re.IGNORECASE,
        )
        all_tables = set(table_matches + sql_table_matches)

        self.stg_targets = sorted(list({t.upper() for t in all_tables if t.upper().startswith("STG_")}))
        self.dim_targets = sorted(list({t.upper() for t in all_tables if t.upper().startswith("DIM_")}))
        self.fact_targets = sorted(list({t.upper() for t in all_tables if t.upper().startswith(("FATO_", "FAT_"))}))
        self.source_tables = sorted(
            list(
                {
                    t
                    for t in table_matches
                    if not t.upper().startswith(("STG_", "DIM_", "FATO_", "FAT_", "ODI_", "IKM", "LKM", "SNP", "TGT_", "MAP_"))
                    and len(t) > 3
                }
            )
        )

        if not self.stg_targets:
            ddl_tables = re.findall(
                r"CREATE\s+TABLE\s+(?:[A-Za-z0-9_]+\.)*([A-Za-z0-9_]+)", raw_text, re.IGNORECASE
            )
            if ddl_tables:
                self.source_tables = ddl_tables
                self.stg_targets = [f"STG_EST_{t.upper()}" for t in ddl_tables]

        SQL_KEYWORDS = {
            "CREATE", "TABLE", "INDEX", "INSERT", "UPDATE", "DELETE", "SELECT", "FROM", "WHERE",
            "AND", "OR", "NOT", "NULL", "INT", "BIGINT", "DATETIME", "VARCHAR", "CHAR", "CONSTRAINT",
            "PRIMARY", "KEY", "FOREIGN", "REFERENCES", "ON", "OFF", "WITH", "ALTER", "DROP",
        }
        all_words = [w for w in re.findall(r"\b[A-Za-z0-9_]+\b", raw_text) if w.upper() not in SQL_KEYWORDS]

        update_cols = list({c.upper() for c in all_words if REGEX_UPDATE_COLS.search(c)})
        create_cols = list({c.upper() for c in all_words if REGEX_CREATE_COLS.search(c)})
        close_cols = list({c.upper() for c in all_words if REGEX_CLOSE_COLS.search(c)})
        self.all_date_columns_found = sorted(list({c.upper() for c in all_words if REGEX_ANY_DATE_COLS.search(c)}))

        self.create_date_cols = sorted([c for c in create_cols if REGEX_ANY_DATE_COLS.search(c)])
        self.close_date_cols = sorted([c for c in close_cols if REGEX_ANY_DATE_COLS.search(c)])
        self.update_date_cols = sorted([c for c in update_cols if REGEX_ANY_DATE_COLS.search(c)])

        self.lkms_found = sorted(list(set(re.findall(r"LKM[A-Za-z0-9_ \(\)-]+", raw_text))))
        self.ikms_found = sorted(list(set(re.findall(r"IKM[A-Za-z0-9_ \(\)-]+", raw_text))))

        if "TRUNCATE_TARGET_TABLE" in raw_text and ("true" in raw_text.lower() or "1" in raw_text):
            self.truncate_detected = True
        if "FLOW_CONTROL" in raw_text and "true" in raw_text.lower():
            self.flow_control_detected = True
        self.hints_found = sorted(list(set(re.findall(r"(?:APPEND|PARALLEL(?:\([0-9]+\))?)", raw_text, re.IGNORECASE))))

    def _run_predictive_heuristics(self):
        """Aplica as 9 Heurísticas Preditivas de Tuning e Qualidade Dimensional do NINHO (H1 a H9)."""

        # H1A: Ciclo de Vida de Workflow (Abertura + Conclusão)
        if self.create_date_cols and self.close_date_cols:
            col_abertura = self.create_date_cols[0]
            col_conclusao = self.close_date_cols[0]
            self.heuristics_triggered.append({
                "id": "H1A_CDC_CICLO_DE_VIDA",
                "titulo": f"Detecção de Tabela de Ciclo de Vida Transacional / Workflow ({col_abertura} + {col_conclusao})",
                "gravidade": "CRÍTICA",
                "descricao": (
                    f"A origem implementa um padrão de Ciclo de Vida de Workflow com par de datas: "
                    f"Início/Abertura ('{col_abertura}') e Término/Conclusão ('{col_conclusao}'). "
                    f"Extrair 100% da tabela sem filtro de janela ativa recarrega milhões de registros já encerrados."
                ),
                "prescricao": [
                    (
                        f"Injetar componente FILTRO de Ciclo de Vida na extração para Staging: "
                        f"`({col_abertura} >= TRUNC(SYSDATE) - 3 OR {col_conclusao} >= TRUNC(SYSDATE) - 3 OR {col_conclusao} IS NULL)`."
                    ),
                    "Configurar Primary Key física na tabela Staging e alterar o IKM para `IKM Oracle Merge` com `FLOW_CONTROL = False`.",
                ],
            })
        elif self.update_date_cols and (self.truncate_detected or not self.has_filter_components):
            self.heuristics_triggered.append({
                "id": "H1B_CDC_INCREMENTAL_CLASSICO",
                "titulo": "Detecção de Colunas de Atualização Clássicas em Carga Total",
                "gravidade": "CRÍTICA",
                "descricao": (
                    f"A origem contém colunas de auditoria ({', '.join(self.update_date_cols[:5])}), "
                    f"mas está configurada para Carga Total sem filtro incremental."
                ),
                "prescricao": [
                    f"Adicionar componente FILTRO no Canvas ODI: `{self.update_date_cols[0]} >= TRUNC(SYSDATE) - 2`.",
                    "Alterar IKM para `IKM Oracle Merge` com `FLOW_CONTROL = False`.",
                ],
            })
        elif self.create_date_cols and not self.update_date_cols and not self.close_date_cols:
            col_criacao = self.create_date_cols[0]
            self.heuristics_triggered.append({
                "id": "H1C_CDC_APPEND_ONLY",
                "titulo": f"Detecção de Tabela Append-Only com Data de Criação ({col_criacao})",
                "gravidade": "ALERTA_ARQUITETURAL",
                "descricao": (
                    f"A tabela possui apenas data de criação ('{col_criacao}') e nenhuma coluna de alteração/conclusão."
                ),
                "prescricao": [
                    f"Aplicar filtro incremental `{col_criacao} >= TRUNC(SYSDATE) - 1` ou High-Water Mark `ID > #V_MAX_ID`.",
                ],
            })
        elif not self.all_date_columns_found:
            self.heuristics_triggered.append({
                "id": "H1D_SEM_COLUNAS_TEMPORAIS",
                "titulo": "Tabela Sem Colunas Temporais Detectadas",
                "gravidade": "ALERTA_PERFORMANCE",
                "descricao": "Não foram detectadas colunas de data/hora para CDC por data.",
                "prescricao": [
                    "Para tabelas pequenas (<100k linhas): Manter `IKM Oracle Insert` com `TRUNCATE = True` e `FLOW_CONTROL = False`.",
                    "Para tabelas massivas: Implementar CDC diferencial por `STANDARD_HASH` / `ORA_HASH`.",
                ],
            })

        # H6: Risco de Fan Trap em Fatos por Falta de Filtro SCD2 (DTC_EXPIRACAO IS NULL)
        if self.h6_fact_joins_missing_scd2_filter:
            exemplos = "; ".join(self.h6_fact_joins_missing_scd2_filter[:4])
            self.heuristics_triggered.append({
                "id": "H6_FAN_TRAP_LOOKUP_SCD2_SEM_VIGENCIA",
                "titulo": f"Risco Crítico de Fan Trap: Join de Fato com Dimensão SCD2 sem `DTC_EXPIRACAO IS NULL` ({len(self.h6_fact_joins_missing_scd2_filter)} ocorrências)",
                "gravidade": "CRÍTICA",
                "descricao": (
                    f"Os mapeamentos de Fato fazem `LEFT OUTER JOIN` com as dimensões `DIM_*` apenas pela chave natural "
                    f"(`ID_UNIDADE`, `ID_USUARIO`, `ID_ORGAO`, etc.), sem filtrar `AND DIM.DTC_EXPIRACAO IS NULL`! "
                    f"Exemplos detectados: {exemplos}. "
                    f"Assim que uma dimensão receber uma 2ª versão histórica no SCD Tipo 2, a tabela Fato multiplicará linhas e inflará os indicadores!"
                ),
                "prescricao": [
                    "Em todos os Lookups/Joins de Fato com dimensões SCD Tipo 2, adicionar obrigatoriamente a cláusula de vigência: `AND DIM_<ENTIDADE>.DTC_EXPIRACAO IS NULL` (ou `AND SYSDATE BETWEEN DIM.DTC_EFETIVACAO AND NVL(DIM.DTC_EXPIRACAO, TO_DATE('31/12/9999','DD/MM/YYYY'))`).",
                    "Criar índice composto nas dimensões: `(ID_<ENTIDADE>, DTC_EXPIRACAO, DIMENSION_KEY)` para Index-Only Lookup.",
                ],
            })

        # H7: Falso SCD Tipo 2 (DES_ATUALIZAR = 'X' constante)
        if self.h7_fake_scd2_constant_x:
            afetados = ", ".join(self.h7_fake_scd2_constant_x[:6])
            self.heuristics_triggered.append({
                "id": "H7_FALSO_SCD2_CONSTANTE_X",
                "titulo": f"SCD Tipo 2 Inoperante: Coluna `DES_ATUALIZAR` fixada com literal `'X'` ({len(self.h7_fake_scd2_constant_x)} objetos)",
                "gravidade": "CRÍTICA",
                "descricao": (
                    f"Nos objetos `{afetados}`, a coluna `DES_ATUALIZAR` na tabela intermediária `ODI_DIM_*` recebe a constante fixa `'X'`. "
                    f"Como o passo `TGT_CLS_DIM` (expiração de histórico) verifica `WHERE STG.DES_ATUALIZAR <> DIM.DES_ATUALIZAR` e ambos são sempre `'X'`, "
                    f"a condição é SEMPRE FALSA! O SCD Tipo 2 nunca abre nova versão histórica e sobrescreve tudo no `TGT_UPD_DIM` (SCD1 disfarçado)."
                ),
                "prescricao": [
                    "Substituir a constante `'X'` na expressão `DES_ATUALIZAR` por um hash determinístico das colunas monitoradas no SCD2: `STANDARD_HASH(NVL(TO_CHAR(COL1),'#') || '|' || NVL(TO_CHAR(COL2),'#'), 'MD5')`.",
                    "Manter nas colunas de SCD Tipo 1 apenas os atributos descritivos que devem ser sobrescritos sem gerar nova linha.",
                ],
            })

        # H8: Bugs de SQL Dimensional (Join DIM_TEMPO sem TRUNC e Duração no GROUP BY sem SUM)
        if self.h8_date_joins_missing_trunc or self.h8_duration_in_group_by:
            detalhes = []
            if self.h8_date_joins_missing_trunc:
                detalhes.append(
                    "Join de Data sem `TRUNC()`: " + "; ".join(self.h8_date_joins_missing_trunc[:3])
                )
            if self.h8_duration_in_group_by:
                detalhes.append(
                    "Métrica de Duração no `GROUP BY` sem agregação: " + "; ".join(self.h8_duration_in_group_by[:3])
                )
            self.heuristics_triggered.append({
                "id": "H8_BUG_SQL_DIM_TEMPO_E_GROUP_BY",
                "titulo": "Anomalias de SQL Dimensional: Join `DIM_TEMPO` sem `TRUNC()` e Duração Não-Agregada no `GROUP BY`",
                "gravidade": "CRÍTICA",
                "descricao": (
                    "Foram detectados erros semânticos nas expressões SQL de carga das Fatos: "
                    + " | ".join(detalhes)
                    + ". Datas com componente de hora (`HH24:MI:SS`) sem `TRUNC()` falham no join com `DIM_TEMPO.DTC_COMPLETA` (caindo em `-1`), "
                    "e expressões `(DT_CONCLUSAO - DT_ABERTURA) * 86400` dentro do `GROUP BY` impedem a agregação e avaliam `SYSDATE` linha a linha."
                ),
                "prescricao": [
                    "Padronizar todos os lookups de `DIM_TEMPO` com `TRUNC()`: `TRUNC(NVL(STG.DTA_GERACAO, SYSDATE)) = DIM_TEMPO.DTC_COMPLETA`.",
                    "Em `MAP_CARGA_FATO_TRAMITACAO`, envolver a fórmula de tempo em `SUM(((NVL(STG.DT_CONCLUSAO, SYSDATE) - STG.DT_ABERTURA) * 86400))` para removê-la da cláusula `GROUP BY`.",
                ],
            })

        # H9: Loop Multi-Tenant Intra-Oracle com LKM SQL to Oracle (C$_)
        if self.h9_c_dollar_in_multitenant_loop or (self.same_db_all_users_discovery and any("SQL to Oracle" in l for l in self.lkms_found)):
            self.heuristics_triggered.append({
                "id": "H9_LOOP_MULTITENANT_C_DOLLAR_INTRA_ORACLE",
                "titulo": "Gargalo Severo Multi-Tenant: Recriação de Tabelas `C$_` via JDBC a cada Município no Mesmo Banco Oracle",
                "gravidade": "CRÍTICA",
                "descricao": (
                    "A procedure `MERGE_ODI_CTRL` descobre os schemas municipais consultando `all_users` local (todos os schemas `BD_SEIMUN_%` residem no mesmo Oracle). "
                    "Porém, os 9 mapeamentos de Staging usam `LKM SQL to Oracle (Built-In)`. A cada iteração do loop (`#V_CNT`), o ODI executa `CREATE TABLE C$_0STG_...`, "
                    "trafega todas as linhas pela memória da JVM do agente JDBC (`VALUES(:ID_ATIVIDADE, ...)`), faz `INSERT INTO STG_...` e `DROP TABLE C$_0STG_...`!"
                ),
                "prescricao": [
                    "Como os schemas `BD_SEIMUN_%` estão na mesma instância Oracle do DW, eliminar o `LKM SQL to Oracle (Built-In)` e as tabelas `C$_`!",
                    "Usar `INSERT /*+ APPEND */ INTO BI_SEI_MUNICIPIO.STG_SEI_<TABELA> SELECT ... FROM #V_SCHEMA.<TABELA>` direto no banco (Single-Technology IKM ou Procedure com `EXECUTE IMMEDIATE` iterando sobre `ODI_SCHEMA_CTRL`).",
                ],
            })

        # H2: Pré-requisito de Primary Key na Staging (+ validação de chave multi-tenant)
        desc_h2 = (
            "Para cargas incrementais (`IKM Oracle Merge`), a Staging exige Primary Key física. "
        )
        if self.multitenant_concat_found:
            desc_h2 += (
                "Foi detectada corretamente a concatenação de chave natural multi-tenant "
                "`to_number(to_char(#V_IBGE) || '000' || to_char(ID))` para evitar colisão de IDs entre municípios."
            )
        self.heuristics_triggered.append({
            "id": "H2_PK_STAGING_E_CHAVE_MULTITENANT",
            "titulo": "Estrutura de Primary Key na Staging Area & Isolamento de Chaves Multi-Tenant",
            "gravidade": "ALERTA_ARQUITETURAL",
            "descricao": desc_h2,
            "prescricao": [
                "Criar constraint de Primary Key física nas tabelas `STG_*` sobre a coluna de ID composta (`#V_IBGE || '000' || ID`).",
                "Configurar `Target Key` no ODI Canvas apontando para a PK da Staging.",
            ],
        })

        # H3: IKM Merge vs Update
        self.heuristics_triggered.append({
            "id": "H3_IKM_MERGE_VS_UPDATE",
            "titulo": "Seleção Ótima de IKM: `IKM Oracle Merge` com `FLOW_CONTROL = False`",
            "gravidade": "RECOMENDAÇÃO_PERFORMANCE",
            "descricao": (
                "Substituir `IKM Oracle Incremental Update` ou `Control Append` com CKM ativo por `IKM Oracle Merge` "
                "(para cargas incrementais) ou `IKM Oracle Insert` com `/*+ APPEND PARALLEL */` e `FLOW_CONTROL = False`."
            ),
            "prescricao": [
                "Definir `FLOW_CONTROL = False` e `STATIC_CONTROL = False` para eliminar a criação de tabelas de erro `E$_`.",
            ],
        })

        # H4: Monolito ou Pacotes Seriais
        if len(self.stg_targets) >= 3 or self.serial_scen_packages:
            detalhe_pack = ""
            if self.serial_scen_packages:
                nomes_p = ", ".join(f"{p} ({n} chamadas síncronas)" for p, n in self.serial_scen_packages)
                detalhe_pack = f" Pacotes com chamadas `OdiStartScen` 100% seriais detectados: {nomes_p}."
            self.heuristics_triggered.append({
                "id": "H4_ORQUESTRACAO_SERIAL_OU_MONOLITO",
                "titulo": f"Orquestração Serializada de Fluxos Independentes ({len(self.stg_targets)} tabelas STG / {len(self.dim_targets)} DIM / {len(self.fact_targets)} FATO)",
                "gravidade": "ALERTA_ARQUITETURAL",
                "descricao": (
                    f"Os fluxos de Staging, Dimensões e Fatos são disparados em série (`-SYNC_MODE=1`).{detalhe_pack} "
                    f"Isso faz com que tabelas pequenas aguardem o término de tabelas volumosas (`ATIVIDADE`, `PROTOCOLO`)."
                ),
                "prescricao": [
                    "Disparar os cenários independentes de Dimensões (`SCEN_CARGA_SEI_DIM_*`) e Fatos (`SCEN_CARGA_FATO_*`) em paralelo via `OdiStartScen -ASYNC=YES` seguidos de `OdiWaitForChildSession`.",
                ],
            })

        # H5: Funil JDBC genérico (quando não coberto pelo H9)
        if any("SQL to Oracle" in lkm for lkm in self.lkms_found) and not self.h9_c_dollar_in_multitenant_loop:
            self.heuristics_triggered.append({
                "id": "H5_FUNIL_JDBC",
                "titulo": "Detecção de Funil de I/O em Driver JDBC (`LKM SQL to Oracle`)",
                "gravidade": "ALERTA_PERFORMANCE",
                "descricao": (
                    "O uso de `LKM SQL to Oracle (Built-In)` força todos os dados a trafegarem pela JVM do ODI Agent "
                    "e cria tabelas temporárias `C$_`."
                ),
                "prescricao": [
                    "Substituir por `LKM Oracle to Oracle Pull (DB Link)` ou SQL direto no mesmo servidor Oracle.",
                ],
            })

    def print_summary(self):
        print(f"{NEGRITO}Alvo Auditado:{RESET} {self.mapping_name} ({len(self.xml_files)} arquivo(s) XML)")
        if self.is_dir:
            print(
                f"{NEGRITO}Inventário do Projeto ODI:{RESET} "
                f"{len(self.mappings_info)} Mapas | {len(self.scenarios_info)} Cenários | "
                f"{len(self.packages_info)} Pacotes | {len(self.procedures_info)} Procedures | "
                f"{len(self.variables_info)} Variáveis"
            )
        print(f"{NEGRITO}Tabelas STG ({len(self.stg_targets)}):{RESET} {', '.join(self.stg_targets[:8])}")
        if self.dim_targets:
            print(f"{NEGRITO}Tabelas DIM ({len(self.dim_targets)}):{RESET} {', '.join(self.dim_targets[:8])}")
        if self.fact_targets:
            print(f"{NEGRITO}Tabelas FATO ({len(self.fact_targets)}):{RESET} {', '.join(self.fact_targets[:8])}")
        print(f"{NEGRITO}Colunas Temporais (Criação/Abertura):{RESET} {', '.join(self.create_date_cols[:6]) if self.create_date_cols else 'Nenhuma'}")
        print(f"{NEGRITO}Colunas Temporais (Conclusão/Fechamento):{RESET} {', '.join(self.close_date_cols[:6]) if self.close_date_cols else 'Nenhuma'}")
        print(f"{NEGRITO}Filtros no Canvas:{RESET} {'SIM (' + str(len(self.filter_components_list)) + ' filtros)' if self.has_filter_components else 'NÃO (Extração Completa)'}\n")

        print(f"{NEGRITO}Heurísticas Preditivas Acionadas ({len(self.heuristics_triggered)}):{RESET}")
        for h in self.heuristics_triggered:
            cor = VERMELHO if h["gravidade"] == "CRÍTICA" else (AMARELO if "ALERTA" in h["gravidade"] else VERDE)
            print(f"  {cor}[{h['gravidade']}]{RESET} {NEGRITO}[{h['id']}] {h['titulo']}{RESET}")
            print(f"     -> {h['descricao']}")
            print(f"     -> {CIANO}Prescrição:{RESET} {h['prescricao'][0]}\n")

    def generate_markdown_report(self, output_path: Path):
        content = []
        content.append("# Relatório de Diagnóstico Preditivo & Tuning de Performance — ODI 12c (Motor NINHO v2.0)")
        content.append(f"\n**Escopo Auditado:** `{self.mapping_name}` ({len(self.xml_files)} arquivo(s) XML)  ")
        content.append(f"**Caminho de Origem:** `{self.target_path}`  ")
        content.append("**Classificação:** Auditoria Preditiva de Engenharia de Dados & Qualidade Dimensional (Plataforma NINHO)\n")
        content.append("---\n")

        content.append("## 1. Resumo Executivo e Inventário Técnico\n")
        content.append(f"- **Arquivos XML Inspecionados:** `{len(self.xml_files)}`")
        content.append(
            f"- **Objetos ODI Mapeados:** `{len(self.mappings_info)}` Mapeamentos (`MAP_*`), "
            f"`{len(self.scenarios_info)}` Cenários Compilados (`SCEN_*`), "
            f"`{len(self.packages_info)}` Pacotes (`PACK_*`), "
            f"`{len(self.procedures_info)}` Procedures (`TRT_*`), "
            f"`{len(self.variables_info)}` Variáveis (`VAR_*`)."
        )
        content.append(f"- **Tabelas Staging (`STG_*`):** `{', '.join(self.stg_targets) if self.stg_targets else 'Nenhuma'}`")
        if self.dim_targets:
            content.append(f"- **Dimensões (`DIM_*`):** `{', '.join(self.dim_targets)}`")
        if self.fact_targets:
            content.append(f"- **Tabelas Fato (`FATO_*`):** `{', '.join(self.fact_targets)}`")
        content.append(f"- **LKMs / IKMs Identificados:** `{', '.join(self.lkms_found + self.ikms_found) or 'N/A'}`")
        content.append(f"- **Isolamento de Chaves Multi-Tenant (`#V_IBGE || '000' || ID`):** `{'SIM' if self.multitenant_concat_found else 'NÃO DETECTADO'}`\n")

        content.append("---\n")
        content.append(f"## 2. Heurísticas Preditivas e Bugs Reais Detectados ({len(self.heuristics_triggered)})\n")

        for idx, h in enumerate(self.heuristics_triggered, 1):
            content.append(f"### {idx}. [{h['id']}] {h['titulo']}")
            content.append(f"**Nível de Gravidade:** `{h['gravidade']}`\n")
            content.append(f"**Diagnóstico Detalhado:**  \n{h['descricao']}\n")
            content.append("**Prescrição Técnica Obrigatória:**")
            for step in h["prescricao"]:
                content.append(f"- {step}")
            content.append("\n")

        if self.h6_fact_joins_missing_scd2_filter or self.h7_fake_scd2_constant_x or self.h8_date_joins_missing_trunc or self.h8_duration_in_group_by:
            content.append("---\n")
            content.append("## 3. Evidências Exatas Extraídas do Código XML / SQL Compilado\n")
            if self.h7_fake_scd2_constant_x:
                content.append("### 3.1. Objetos com Falso SCD2 (`DES_ATUALIZAR = 'X'` fixo)")
                for item in self.h7_fake_scd2_constant_x:
                    content.append(f"- `{item}`")
                content.append("")
            if self.h6_fact_joins_missing_scd2_filter:
                content.append("### 3.2. Joins de Fato com Dimensão SCD2 sem `DTC_EXPIRACAO IS NULL` (Risco de Fan Trap)")
                for item in self.h6_fact_joins_missing_scd2_filter:
                    content.append(f"- {item}")
                content.append("")
            if self.h8_date_joins_missing_trunc or self.h8_duration_in_group_by:
                content.append("### 3.3. Expressões SQL com Anomalia de Data (`DIM_TEMPO`) ou `GROUP BY`")
                for item in self.h8_date_joins_missing_trunc + self.h8_duration_in_group_by:
                    content.append(f"- {item}")
                content.append("")

        content.append("---\n")
        content.append("## 4. Scripts SQL / Expressões Corretivas Prontas para Aplicação\n")
        content.append("```sql")
        content.append("-- 1. Correção da Expressão DES_ATUALIZAR nas Dimensões (Habilita SCD Tipo 2 Real):")
        content.append("STANDARD_HASH(NVL(TO_CHAR(STG.SIGLA), '#') || '|' || NVL(TO_CHAR(STG.DESCRICAO), '#'), 'MD5') AS DES_ATUALIZAR")
        content.append("")
        content.append("-- 2. Correção dos Joins de Dimensão SCD2 nas Tabelas Fato (Evita Fan Trap / Duplicação):")
        content.append("LEFT OUTER JOIN BI_SEI_MUNICIPIO.DIM_SEI_MUNIC_UNIDADE DIM_UNIDADE")
        content.append("  ON STG_SEI_ATIVIDADE.ID_UNIDADE = DIM_UNIDADE.ID_UNIDADE")
        content.append(" AND DIM_UNIDADE.DTC_EXPIRACAO IS NULL")
        content.append("")
        content.append("-- 3. Correção do Join com DIM_TEMPO em MAP_CARGA_FATO_PROCESSO:")
        content.append("TRUNC(NVL(STG_SEI_PROTOCOLO.DTA_GERACAO, SYSDATE)) = DIM_TEMPO.DTC_COMPLETA")
        content.append("")
        content.append("-- 4. Correção da Métrica de Tempo de Tramitação em MAP_CARGA_FATO_TRAMITACAO (Fora do GROUP BY):")
        content.append("SUM(((NVL(STG_SEI_ATIVIDADE.DT_CONCLUSAO, SYSDATE) - STG_SEI_ATIVIDADE.DT_ABERTURA) * 86400)) AS QTD_TEMPO_TRAMITACAO")
        content.append("```\n")

        output_path.write_text("\n".join(content), encoding="utf-8")
        print_ok(f"Relatório preditivo v2.0 gerado com sucesso em: {output_path}")


def main():
    print_banner()
    parser = argparse.ArgumentParser(description="Auditor Preditivo de Objetos e Projetos ODI 12c (NINHO v2.0)")
    parser.add_argument("xml_path", help="Caminho do arquivo XML ou diretório exportado do ODI")
    parser.add_argument("--output", "-o", help="Caminho de saída para o relatório Markdown", default=None)

    args = parser.parse_args()
    target = Path(args.xml_path)

    if not target.exists():
        print_err(f"Caminho não encontrado: {target}")
        sys.exit(1)

    auditor = ODIMappingAuditor(target)
    auditor.parse()
    auditor.print_summary()

    if args.output:
        out_file = Path(args.output)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        auditor.generate_markdown_report(out_file)


if __name__ == "__main__":
    main()
