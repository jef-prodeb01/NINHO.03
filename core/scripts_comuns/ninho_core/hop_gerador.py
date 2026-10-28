"""
Geração e migração Apache Hop 2.x: pacote completo (wf_*.hwf, ppl_*.hpl com TableOutput ou
OraBulkLoader, hop-lint.yml, hop-pwd.json) e migrador Pentaho Kettle (.ktr/.kjb/shared.xml) -> Hop.

Extraído de auditar_esteira_hop.py (que mantém uma fachada de reimportação).
"""

import logging as _logging_ninho

_LOG = _logging_ninho.getLogger("ninho.core.hop_gerador")

import os
import re
import json
import xml.etree.ElementTree as ET
from ninho_core import xml_seguro
from pathlib import Path
from typing import Dict, List, Tuple, Any, Set


KETTLE_ELEMENT_REPLACEMENTS: Dict[str, str] = {
    "transformation": "pipeline",
    "trans_type": "pipeline_type",
    "trans_version": "pipeline_version",
    "trans_status": "pipeline_status",
    "step": "transform",
    "step_error_handling": "transform_error_handling",
    "capture_step_performance": "capture_transform_performance",
    "step_performance_capturing_size_limit": "transform_performance_capturing_size_limit",
    "target_step_name": "target_transform_name",
    "step_performance_capturing_delay": "transform_performance_capturing_delay",
    "transformationPath": "pipelinePath",
    "SUB_STEP": "subTransform",
    "job": "workflow",
    "job_version": "workflow_version",
    "entries": "actions",
    "entry": "action",
    "source_step": "source_transform",
    "target_step": "target_transform",
    "step1": "transform1",
    "step2": "transform2",
    "step3": "transform3",
    "step4": "transform4",
    "step5": "transform5",
    "step6": "transform6",
    "step7": "transform7",
    "step8": "transform8",
    "step9": "transform9",
    "step0": "transform0",
    "accept_stepname": "accept_transform_name",
    "steps": "transforms",
    "default_target_step": "default_target_transform",
    "input_step": "input_transform",
    "output_step": "output_transform",
    "info_steps": "info_transforms",
    "info_step": "info_transform",
    "target_steps": "target_transforms",
    "step_tag": "transform_tag",
    "step_name": "transform_name",
    "step_description": "transform_description",
    "extention": "extension",
    "formula_string": "formula",
    "targetXMLstep": "targetXMLTransform",
    "sourceXMLstep": "sourceXMLTransform",
    "stepRequired": "transformRequired",
    "stepnamefield": "transformnamefield",
    "stepidfield": "transformidfield",
    "steplinesinputfield": "transformlinesinputfield",
    "steplinesoutputfield": "transformlinesoutputfield",
    "steplinesreadfield": "transformlinesreadfield",
    "steplinesupdatedfield": "transformlinesupdatedfield",
    "steplineswrittentfield": "transformlineswrittenfield",
    "steplineserrorsfield": "transformlineserrorsfield",
    "stepsecondsfield": "transformsecondsfield",
    "execution_result_target_step": "execution_result_target_transform",
}


KETTLE_ELEMENTS_TO_REMOVE: Set[str] = {
    "size_rowset", "sleep_time_empty", "sleep_time_full", "unique_connections",
    "feedback_shown", "feedback_size", "using_thread_priorities",
    "shared_objects_file", "dependencies", "partitionschemas", "slaveservers",
    "remotesteps", "clusterschemas", "maxdate", "log",
    "slave-step-copy-partition-distribution", "slave_transformation",
    "trans_object_id", "job_object_id", "specification_method",
    "job-log-table", "jobentry-log-table", "channel-log-table", "checkpoint-log-table",
}


KETTLE_TYPE_REPLACEMENTS: Dict[str, str] = {
    "JOB": "WORKFLOW",
    "TRANS": "PIPELINE",
    "PARENT_JOB": "PARENT_WORKFLOW",
    "GP_JOB": "GP_WORKFLOW",
    "ROOT_JOB": "ROOT_WORKFLOW",
    "BlockingStep": "BlockingTransform",
    "BlockUntilStepsFinish": "BlockUntilTransformsFinish",
    "StepsMetrics": "TransformsMetrics",
    "TypeExitExcelWriterStep": "TypeExitExcelWriterTransform",
    "StepMetastructure": "TransformMetaStructure",
    "JobExecutor": "WorkflowExecutor",
    "TransExecutor": "PipelineExecutor",
    "Mapping": "SimpleMapping",
    "TextFileInput": "TextFileInput2",
    "HTTP": "Http",
    "KafkaConsumerInput": "KafkaConsumer",
    "KettleKafkaConsumerInput": "KafkaConsumer",
    "PentahoGoogleSheetsPluginOutputMeta": "GoogleSheetsOutput",
    "PentahoGoogleSheetsPluginInputMeta": "GoogleSheetsInput",
}


KETTLE_TEXT_REPLACEMENTS: List[Tuple[str, str]] = [
    (".kjb", ".hwf"),
    (".ktr", ".hpl"),
    ("Internal.Job.Filename.Directory", "Internal.Workflow.Filename.Folder"),
    ("Internal.Job.Filename.Name", "Internal.Workflow.Filename.Name"),
    ("Internal.Entry.Current.Directory", "Internal.Entry.Current.Folder"),
    ("Internal.Job", "Internal.Workflow"),
    ("Internal.Transformation", "Internal.Pipeline"),
    ("Filename.Directory", "Filename.Folder"),
    ("Repository.Directory", "Repository.Folder"),
    ("Current.Directory", "Current.Folder"),
    ("CONTINUE_TRANSFORMATION", "CONTINUE_PIPELINE"),
    ("SKIP_TRANSFORMATION", "SKIP_PIPELINE"),
    ("ERROR_TRANSFORMATION", "ERROR_PIPELINE"),
    ("ABORT_TRANSFORMATION", "ABORT_PIPELINE"),
    ("CURRENT_JOB", "CURRENT_WORKFLOW"),
    ("PARENT_JOB", "PARENT_WORKFLOW"),
    ("ROOT_JOB", "ROOT_WORKFLOW"),
]


def gerar_hop_lint_yml(pasta_destino: Path) -> Path:
    """
    Gera o arquivo oficial `hop-lint.yml` (compatível com hop-lint-core.yml do Apache Hop)
    na raiz do projeto Hop para governança contínua e CI/CD.
    """
    pasta_destino.mkdir(parents=True, exist_ok=True)
    yml_path = pasta_destino / "hop-lint.yml"
    yml_content = """# ==============================================================================
# Apache Hop Project Linter Configuration (hop-lint.yml) — Padrão NINHO / PRODEB
# Baseado em hop-lint-core.yml & THREAT_MODEL.md
# ==============================================================================
version: "1.0"
settings:
  fail_on_severity: "ERROR"
  ignore_patterns:
    - "**/tmp/**"
    - "**/*_old.hpl"

rules:
  # Naming & Documentation
  NAMING-001:
    enabled: true
    severity: WARNING
    pattern: "^(ppl|stg|dim|fat)_[a-z0-9_]+$"
    description: "Nomes de pipelines devem seguir o padrão snake_case com prefixo semântico."
  NAMING-002:
    enabled: true
    severity: WARNING
    pattern: "^(wf|job)_[a-z0-9_]+$"
    description: "Nomes de workflows devem iniciar com wf_ em snake_case."
  NAMING-004:
    enabled: true
    severity: INFO
    description: "Transforms não devem manter nomes genéricos padrão da GUI (ex: 'Table input', 'Select values 2')."
  DOC-001:
    enabled: true
    severity: INFO
    description: "Pipelines e Workflows devem possuir <description> ou <notepad> documentando seu propósito."

  # Graph Integrity & Disconnected Nodes
  TRANS-002:
    enabled: true
    severity: ERROR
    description: "Proibido manter transforms órfãos (desconectados de hops) dentro de pipelines."
  WORKFLOW-002:
    enabled: true
    severity: ERROR
    description: "Proibido manter actions órfãs (desconectadas de hops) dentro de workflows."
  STRUCT-003:
    enabled: true
    severity: WARNING
    description: "Hops desabilitados (<enabled>N</enabled>) devem ser removidos antes do deploy."

  # Database, Security & Performance (THREAT_MODEL.md)
  DB-001:
    enabled: true
    severity: ERROR
    description: "Proibido hardcode de senhas em texto puro ou 'Encrypted ...' estático em XML/RDBMS JSON. Use #{hop-pwd:...}."
  SEC-002:
    enabled: true
    severity: ERROR
    description: "Credenciais HTTP/REST/SMTP/TrustStore devem usar variáveis ou Variable Resolver."
  SQL-002:
    enabled: true
    severity: WARNING
    description: "Evitar 'SELECT *' sem projeção explícita ou limite em transforms TableInput."
  META-001:
    enabled: true
    severity: ERROR
    description: "Subpastas de metadata/ devem usar exclusivamente kebab-case (rdbms, variable-resolver, workflow-log)."
"""
    yml_path.write_text(yml_content, encoding="utf-8")
    return yml_path


def gerar_hop_pwd_resolver_json(
    pasta_destino: Path,
    arquivo_segredos: str = "${PROJECT_HOME}/config/segredos_hop.json",
) -> Path:
    """
    Gera o metadado `metadata/variable-resolver/hop-pwd.json` (HopPasswordVariableResolver)
    para resolução segura via expressão `#{hop-pwd:ENV_PASS_ORACLE}`.
    """
    vr_dir = pasta_destino / "metadata" / "variable-resolver"
    vr_dir.mkdir(parents=True, exist_ok=True)
    vr_path = vr_dir / "hop-pwd.json"
    payload = {
        "name": "hop-pwd",
        "description": "Resolução segura de credenciais corporativas via HopPasswordVariableResolver (Padrão NINHO)",
        "PluginMetadata": {
            "HopPasswordVariableResolver": {
                "filename": arquivo_segredos,
                "passwordVariable": "HOP_SHARED_KEY_PASS",
            }
        },
    }
    vr_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return vr_path


def _converter_elemento_kettle_recursivo(elem: ET.Element, is_workflow: bool = False) -> None:
    """Renomeia tags, tipos de plugins e variáveis internas de Kettle (.ktr/.kjb) para Apache Hop 2.x (.hpl/.hwf)."""
    # 1. Remover filhos obsoletos do Kettle
    for child in list(elem):
        if child.tag in KETTLE_ELEMENTS_TO_REMOVE:
            elem.remove(child)
            continue
        if child.tag == "connection" and elem.tag in ("transformation", "pipeline", "job", "workflow"):
            elem.remove(child)
            continue

    # 2. Renomear a própria tag se mapeada em KettleConst
    if elem.tag in KETTLE_ELEMENT_REPLACEMENTS:
        elem.tag = KETTLE_ELEMENT_REPLACEMENTS[elem.tag]

    # 3. Se for <action> (antigo <entry>) em workflow, converter <special><start>Y</start> ou <dummy>Y</dummy>
    if is_workflow and elem.tag == "action":
        t_el = elem.find("type")
        if t_el is not None and (t_el.text or "").strip() == "SPECIAL":
            is_dummy = (elem.findtext("dummy") or "N").strip().upper() == "Y"
            t_el.text = "DUMMY" if is_dummy else "START"
            for obsolete_tag in ("start", "dummy", "draw", "nr"):
                ob = elem.find(obsolete_tag)
                if ob is not None:
                    elem.remove(ob)
        elif t_el is not None and (t_el.text or "").strip() in KETTLE_TYPE_REPLACEMENTS:
            t_el.text = KETTLE_TYPE_REPLACEMENTS[(t_el.text or "").strip()]
        # Converter coordenadas xloc/yloc diretas em <gui><xloc>... se ainda não tiver <gui>
        if elem.find("gui") is None and (elem.find("xloc") is not None or elem.find("yloc") is not None):
            x_val = elem.findtext("xloc", "120")
            y_val = elem.findtext("yloc", "120")
            for k_rm in ("xloc", "yloc", "draw", "nr"):
                node_rm = elem.find(k_rm)
                if node_rm is not None:
                    elem.remove(node_rm)
            gui_el = ET.SubElement(elem, "gui")
            ET.SubElement(gui_el, "xloc").text = x_val
            ET.SubElement(gui_el, "yloc").text = y_val

    # 4. Se for <transform> (antigo <step>) em pipeline, converter <type> e <GUI> -> <gui>
    if not is_workflow and elem.tag == "transform":
        t_el = elem.find("type")
        if t_el is not None and (t_el.text or "").strip() in KETTLE_TYPE_REPLACEMENTS:
            t_el.text = KETTLE_TYPE_REPLACEMENTS[(t_el.text or "").strip()]
        gui_upper = elem.find("GUI")
        if gui_upper is not None:
            gui_upper.tag = "gui"
            draw_node = gui_upper.find("draw")
            if draw_node is not None:
                gui_upper.remove(draw_node)

    # 5. Substituir textos internos (.ktr -> .hpl, .kjb -> .hwf, Internal.Transformation -> Internal.Pipeline, etc.)
    if elem.text:
        txt = elem.text
        for old_s, new_s in KETTLE_TEXT_REPLACEMENTS:
            if old_s in txt:
                txt = txt.replace(old_s, new_s)
        elem.text = txt

    for child in list(elem):
        _converter_elemento_kettle_recursivo(child, is_workflow=is_workflow)


def migrar_kettle_para_hop(caminho_origem: Path, pasta_destino: Path) -> Dict[str, Any]:
    """
    Migra arquivos ou diretórios legados do Pentaho Data Integration / Kettle (.ktr, .kjb, shared.xml)
    para um projeto Apache Hop 2.x (.hpl, .hwf, metadata/rdbms/*.json, hop-lint.yml, hop-pwd.json e Diagrama SVG).
    """
    pasta_destino.mkdir(parents=True, exist_ok=True)
    rdbms_dir = pasta_destino / "metadata" / "rdbms"
    rdbms_dir.mkdir(parents=True, exist_ok=True)

    source_files: List[Path] = []
    if caminho_origem.is_file():
        source_files = [caminho_origem]
        base_src = caminho_origem.parent
    else:
        base_src = caminho_origem
        for root_d, _, fnames in os.walk(caminho_origem):
            for fn in sorted(fnames):
                if fn.lower().endswith((".ktr", ".kjb")) or fn.lower() == "shared.xml":
                    source_files.append(Path(root_d) / fn)

    migrated_hpl: List[str] = []
    migrated_hwf: List[str] = []
    connections_extracted: Dict[str, str] = {}

    for src_f in source_files:
        try:
            raw_xml = src_f.read_text(encoding="utf-8", errors="ignore")
            root = xml_seguro.fromstring(raw_xml)
        except Exception:
            continue

        # 1. Extrair blocos <connection> embutidos para metadata/rdbms/<CONN>.json
        for conn_el in root.findall(".//connection"):
            cname = (conn_el.findtext("name") or "").strip()
            if not cname or cname in connections_extracted:
                continue
            ctype = (conn_el.findtext("type") or "ORACLE").strip().upper()
            host = (conn_el.findtext("server") or "${ENV_DB_HOST}").strip()
            db_name = (conn_el.findtext("database") or "${ENV_DB_SERVICE}").strip()
            port = (conn_el.findtext("port") or "1521").strip()
            user = (conn_el.findtext("username") or "${ENV_DB_USER}").strip()
            safe_env = re.sub(r"[^A-Z0-9_]", "_", cname.upper())
            conn_json = {
                "name": cname,
                "rdbms": {
                    ctype: {
                        "databaseName": db_name,
                        "pluginId": ctype,
                        "accessType": 0,
                        "hostname": host,
                        "password": f"#{{hop-pwd:ENV_PASS_{safe_env}}}",
                        "pluginName": f"{ctype} Database",
                        "port": str(port),
                        "username": user,
                        "attributes": {
                            "SUPPORTS_TIMESTAMP_DATA_TYPE": "Y",
                            "SUPPORTS_BOOLEAN_DATA_TYPE": "Y",
                        },
                    }
                },
            }
            conn_file = rdbms_dir / f"{cname}.json"
            conn_file.write_text(json.dumps(conn_json, indent=2, ensure_ascii=False), encoding="utf-8")
            connections_extracted[cname] = str(conn_file)

        if src_f.name.lower() == "shared.xml":
            continue

        is_kjb = src_f.suffix.lower() == ".kjb" or root.tag.lower() == "job"
        _converter_elemento_kettle_recursivo(root, is_workflow=is_kjb)

        rel_sub = src_f.relative_to(base_src) if src_f.is_relative_to(base_src) else Path(src_f.name)
        new_ext = ".hwf" if is_kjb else ".hpl"
        out_file = pasta_destino / rel_sub.with_suffix(new_ext)
        out_file.parent.mkdir(parents=True, exist_ok=True)

        if hasattr(ET, "indent"):
            ET.indent(root, space="  ")
        xml_str = ET.tostring(root, encoding="unicode")
        out_file.write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_str}\n', encoding="utf-8")
        if is_kjb:
            migrated_hwf.append(str(out_file))
        else:
            migrated_hpl.append(str(out_file))

    # Criar project-config.json se não existir
    proj_cfg = pasta_destino / "project-config.json"
    if not proj_cfg.exists():
        proj_cfg.write_text(
            json.dumps(
                {
                    "description": f"Projeto Apache Hop 2.x migrado automaticamente pelo NINHO a partir de {caminho_origem.name}",
                    "company": "PRODEB / Plataforma NINHO",
                    "metadataBaseFolder": "${PROJECT_HOME}/metadata",
                    "unitTestsBasePath": "${PROJECT_HOME}",
                    "dataSetsCsvFolder": "${PROJECT_HOME}/datasets",
                    "enforcingExecutionInHome": True,
                    "config": {"variables": []},
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    lint_path = gerar_hop_lint_yml(pasta_destino)
    vr_path = gerar_hop_pwd_resolver_json(pasta_destino)

    doc_res: Dict[str, str] = {}
    try:
        from ninho_core.diagramas import gerar_documentacao_esteira_hop
        doc_res = gerar_documentacao_esteira_hop(str(pasta_destino), str(pasta_destino))
    except Exception as _exc:
        _LOG.debug("Exceção tratada (hop_gerador.py:405): %r", _exc)

    return {
        "hpl_migrados": migrated_hpl,
        "hwf_migrados": migrated_hwf,
        "conexoes_rdbms": list(connections_extracted.values()),
        "hop_lint_yml": str(lint_path),
        "hop_pwd_json": str(vr_path),
        **doc_res,
    }


def gerar_pacote_hop_completo(
    pasta_destino: Path,
    projeto: str = "DW_CORPORATIVO",
    schema_stg: str = "STG_DW",
    tabelas: List[str] = None,
    usar_orabulkloader: bool = False,
) -> Dict[str, Any]:
    """
    Gera um pacote completo Apache Hop 2.x em `pasta_destino` (por padrão `saida/planejador_dw/06_pipelines_hop`):
      - `project-config.json` + `hop-lint.yml`
      - `metadata/rdbms/ORACLE_STG.json` (com `#{hop-pwd:ENV_PASS_ORACLE_STG}`)
      - `metadata/variable-resolver/hop-pwd.json`
      - `metadata/workflow-log/LOG_EXECUCAO_HOP.json`
      - `wf_carga_stg_<projeto>.hwf` (com auditoria `ETA_ETAPAS_CARGA` e rota de erro `MAIL_ALERTA_ERRO`)
      - `ppl_stg_<tabela>.hpl` (usando `TableOutput` JDBC batch ou `OraBulkLoader` SQL*Loader DIRECT=TRUE)
      - `ppl_log_auditoria_workflow.hpl` (`WorkflowLogging` -> `ETA_ETAPAS_CARGA`)
      - `diagrama_esteira_hop.svg` e `DOCUMENTACAO_HOP.md`
    """
    pasta_destino.mkdir(parents=True, exist_ok=True)
    proj_slug = re.sub(r"[^a-z0-9_]", "_", projeto.lower()).strip("_") or "dw"
    if not tabelas:
        tabelas = [f"STG_{proj_slug.upper()}_PRINCIPAL"]

    # 1. project-config.json
    (pasta_destino / "project-config.json").write_text(
        json.dumps(
            {
                "description": f"Esteira Corporativa Apache Hop 2.x — Projeto {projeto.upper()}",
                "company": "PRODEB / Plataforma NINHO",
                "metadataBaseFolder": "${PROJECT_HOME}/metadata",
                "unitTestsBasePath": "${PROJECT_HOME}",
                "dataSetsCsvFolder": "${PROJECT_HOME}/datasets",
                "enforcingExecutionInHome": True,
                "config": {
                    "variables": [
                        {"name": "ENV_DB_SCHEMA_STG", "value": schema_stg, "description": "Schema Oracle de Staging"},
                        {"name": "ENV_DIR_INPUT", "value": "${PROJECT_HOME}/input", "description": "Diretório de entrada"},
                        {"name": "ENV_SQLPLUS_BIN", "value": "/u01/app/oracle/product/19.0.0/client_1/bin/sqlldr", "description": "Binário SQL*Loader"},
                    ]
                },
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    # 2. metadata/rdbms/ORACLE_STG.json & variable-resolver/hop-pwd.json & workflow-log
    rdbms_dir = pasta_destino / "metadata" / "rdbms"
    rdbms_dir.mkdir(parents=True, exist_ok=True)
    (rdbms_dir / "ORACLE_STG.json").write_text(
        json.dumps(
            {
                "name": "ORACLE_STG",
                "rdbms": {
                    "ORACLE": {
                        "databaseName": "${ENV_DB_SERVICE}",
                        "pluginId": "ORACLE",
                        "accessType": 0,
                        "hostname": "${ENV_DB_HOST}",
                        "password": "#{hop-pwd:ENV_PASS_ORACLE_STG}",
                        "pluginName": "Oracle",
                        "port": "${ENV_DB_PORT}",
                        "username": "${ENV_DB_USER}",
                        "attributes": {
                            "SUPPORTS_TIMESTAMP_DATA_TYPE": "Y",
                            "SUPPORTS_BOOLEAN_DATA_TYPE": "Y",
                        },
                    }
                },
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    vr_path = gerar_hop_pwd_resolver_json(pasta_destino)
    wflog_dir = pasta_destino / "metadata" / "workflow-log"
    wflog_dir.mkdir(parents=True, exist_ok=True)
    (wflog_dir / "LOG_EXECUCAO_HOP.json").write_text(
        json.dumps(
            {
                "name": "LOG_EXECUCAO_HOP",
                "enabled": True,
                "loggingParentsOnly": False,
                "pipelineFilename": "${PROJECT_HOME}/ppl_log_auditoria_workflow.hpl",
                "executingAtStart": False,
                "executingAtEnd": True,
                "executingPeriodically": False,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    lint_path = gerar_hop_lint_yml(pasta_destino)

    # 3. Pipelines de carga por tabela (TableOutput ou OraBulkLoader)
    hpl_gerados: List[str] = []
    for tbl in tabelas:
        tbl_upper = tbl.upper()
        tbl_slug = re.sub(r"[^a-z0-9_]", "_", tbl.lower()).strip("_")
        hpl_name = f"ppl_{tbl_slug}"
        hpl_path = pasta_destino / f"{hpl_name}.hpl"

        if usar_orabulkloader:
            target_tx_xml = f"""  <transform>
    <name>BULK_{tbl_upper}</name>
    <type>OraBulkLoader</type>
    <connection>ORACLE_STG</connection>
    <schema>${{ENV_DB_SCHEMA_STG}}</schema>
    <table>{tbl_upper}</table>
    <sqlldr>${{ENV_SQLPLUS_BIN}}</sqlldr>
    <control_file>${{java.io.tmpdir}}/{tbl_slug}_${{Internal.Pipeline.Run.Id}}.ctl</control_file>
    <data_file>${{java.io.tmpdir}}/{tbl_slug}_${{Internal.Pipeline.Run.Id}}.dat</data_file>
    <log_file>${{java.io.tmpdir}}/{tbl_slug}_${{Internal.Pipeline.Run.Id}}.log</log_file>
    <bad_file>${{java.io.tmpdir}}/{tbl_slug}_${{Internal.Pipeline.Run.Id}}.bad</bad_file>
    <discard_file>${{java.io.tmpdir}}/{tbl_slug}_${{Internal.Pipeline.Run.Id}}.dsc</discard_file>
    <load_method>AUTO_CONCURRENT</load_method>
    <load_action>TRUNCATE</load_action>
    <direct_path>Y</direct_path>
    <erase_files>Y</erase_files>
    <encoding>UTF-8</encoding>
    <max_errors>0</max_errors>
    <commit>100000</commit>
    <bind_size>0</bind_size>
    <read_size>0</read_size>
    <fail_on_warning>N</fail_on_warning>
    <fail_on_error>Y</fail_on_error>
    <parallel>Y</parallel>
    <gui>
      <xloc>620</xloc>
      <yloc>180</yloc>
    </gui>
  </transform>"""
            target_tx_name = f"BULK_{tbl_upper}"
        else:
            target_tx_xml = f"""  <transform>
    <name>OUT_{tbl_upper}</name>
    <type>TableOutput</type>
    <connection>ORACLE_STG</connection>
    <schema>${{ENV_DB_SCHEMA_STG}}</schema>
    <table>{tbl_upper}</table>
    <commit>5000</commit>
    <truncate>Y</truncate>
    <use_batch>Y</use_batch>
    <specify_fields>Y</specify_fields>
    <gui>
      <xloc>620</xloc>
      <yloc>180</yloc>
    </gui>
  </transform>"""
            target_tx_name = f"OUT_{tbl_upper}"

        hpl_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<pipeline>
  <info>
    <name>{hpl_name}</name>
    <name_sync_with_filename>Y</name_sync_with_filename>
    <description>Pipeline corporativo de ingestão em {schema_stg}.{tbl_upper} ({'OraBulkLoader SQL*Loader DIRECT=TRUE' if usar_orabulkloader else 'JDBC Batch TableOutput'})</description>
    <pipeline_type>Normal</pipeline_type>
    <parameters>
      <parameter>
        <name>PRM_DATA_REFERENCIA</name>
        <default_value>SYSDATE</default_value>
        <description>Data de referência do lote de extração</description>
      </parameter>
    </parameters>
  </info>
  <notepads>
    <notepad>
      <note>Pipeline: {hpl_name}
Alvo: {schema_stg}.{tbl_upper}
Modo: {'Alta Volumetria (OraBulkLoader DIRECT=TRUE)' if usar_orabulkloader else 'Transacional Batch (TableOutput + Quarentena TAB_ERRO)'}</note>
      <xloc>80</xloc>
      <yloc>40</yloc>
      <width>520</width>
      <heigth>72</heigth>
    </notepad>
  </notepads>
  <order>
    <hop>
      <from>IN_ORIGEM_{tbl_upper}</from>
      <to>META_HIGIENIZACAO_{tbl_upper}</to>
      <enabled>Y</enabled>
    </hop>
    <hop>
      <from>META_HIGIENIZACAO_{tbl_upper}</from>
      <to>{target_tx_name}</to>
      <enabled>Y</enabled>
    </hop>
    <hop>
      <from>{target_tx_name}</from>
      <to>QUARENTENA_TAB_{tbl_upper}_ERRO</to>
      <enabled>Y</enabled>
    </hop>
  </order>
  <transform_error_handling>
    <error>
      <source_transform>{target_tx_name}</source_transform>
      <target_transform>QUARENTENA_TAB_{tbl_upper}_ERRO</target_transform>
      <is_enabled>Y</is_enabled>
      <nr_valuename>NUM_ERROS_HOP</nr_valuename>
      <descriptions_valuename>DES_ERRO_ORACLE</descriptions_valuename>
      <fields_valuename>NOM_COLUNA_ERRO</fields_valuename>
      <codes_valuename>COD_ORA_ERRO</codes_valuename>
    </error>
  </transform_error_handling>
  <transform>
    <name>IN_ORIGEM_{tbl_upper}</name>
    <type>TableInput</type>
    <connection>ORACLE_STG</connection>
    <sql>SELECT COD_REGISTRO, DES_CONTEUDO, DTC_EXTRACAO FROM {schema_stg}.VW_FONTE_{tbl_upper}</sql>
    <limit>0</limit>
    <replace_variables>N</replace_variables>
    <gui>
      <xloc>120</xloc>
      <yloc>180</yloc>
    </gui>
  </transform>
  <transform>
    <name>META_HIGIENIZACAO_{tbl_upper}</name>
    <type>SelectValues</type>
    <gui>
      <xloc>360</xloc>
      <yloc>180</yloc>
    </gui>
  </transform>
{target_tx_xml}
  <transform>
    <name>QUARENTENA_TAB_{tbl_upper}_ERRO</name>
    <type>TableOutput</type>
    <connection>ORACLE_STG</connection>
    <schema>${{ENV_DB_SCHEMA_STG}}</schema>
    <table>TAB_{tbl_upper}_ERRO</table>
    <commit>1000</commit>
    <truncate>N</truncate>
    <use_batch>Y</use_batch>
    <specify_fields>Y</specify_fields>
    <gui>
      <xloc>620</xloc>
      <yloc>330</yloc>
    </gui>
  </transform>
</pipeline>
"""
        hpl_path.write_text(hpl_xml, encoding="utf-8")
        hpl_gerados.append(str(hpl_path))

    # 4. Pipeline de auditoria WorkflowLogging -> ETA_ETAPAS_CARGA
    log_hpl_path = pasta_destino / "ppl_log_auditoria_workflow.hpl"
    log_hpl_path.write_text(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<pipeline>
  <info>
    <name>ppl_log_auditoria_workflow</name>
    <name_sync_with_filename>Y</name_sync_with_filename>
    <description>Captura telemetria nativa do WorkflowLogging e persiste em {schema_stg}.ETA_ETAPAS_CARGA</description>
    <pipeline_type>Normal</pipeline_type>
  </info>
  <notepads>
    <notepad>
      <note>Telemetria de Auditoria: WorkflowLogging -> {schema_stg}.ETA_ETAPAS_CARGA</note>
      <xloc>80</xloc>
      <yloc>40</yloc>
      <width>460</width>
      <heigth>56</heigth>
    </notepad>
  </notepads>
  <order>
    <hop>
      <from>CAPTURA_WORKFLOW_LOGGING</from>
      <to>GRAVA_ETA_ETAPAS_CARGA</to>
      <enabled>Y</enabled>
    </hop>
  </order>
  <transform>
    <name>CAPTURA_WORKFLOW_LOGGING</name>
    <type>WorkflowLogging</type>
    <gui>
      <xloc>140</xloc>
      <yloc>160</yloc>
    </gui>
  </transform>
  <transform>
    <name>GRAVA_ETA_ETAPAS_CARGA</name>
    <type>TableOutput</type>
    <connection>ORACLE_STG</connection>
    <schema>${{ENV_DB_SCHEMA_STG}}</schema>
    <table>ETA_ETAPAS_CARGA</table>
    <commit>100</commit>
    <use_batch>Y</use_batch>
    <specify_fields>Y</specify_fields>
    <gui>
      <xloc>440</xloc>
      <yloc>160</yloc>
    </gui>
  </transform>
</pipeline>
""",
        encoding="utf-8",
    )
    hpl_gerados.append(str(log_hpl_path))

    # 5. Workflow Orquestrador Principal (.hwf)
    first_hpl_name = Path(hpl_gerados[0]).name
    wf_name = f"wf_carga_stg_{proj_slug}"
    hwf_path = pasta_destino / f"{wf_name}.hwf"
    hwf_path.write_text(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<workflow>
  <name>{wf_name}</name>
  <name_sync_with_filename>Y</name_sync_with_filename>
  <description>Workflow Mestre de Orquestração Staging ({projeto.upper()}) com controle ETA_ETAPAS_CARGA</description>
  <notepads>
    <notepad>
      <note>Orquestrador Apache Hop 2.x — {projeto.upper()}
Registra início/fim em {schema_stg}.ETA_ETAPAS_CARGA e notifica equipe em caso de falha.</note>
      <xloc>80</xloc>
      <yloc>40</yloc>
      <width>560</width>
      <heigth>64</heigth>
    </notepad>
  </notepads>
  <actions>
    <action>
      <name>START</name>
      <type>START</type>
      <gui><xloc>100</xloc><yloc>180</yloc></gui>
    </action>
    <action>
      <name>SQL_INICIO_ETA_CARGA</name>
      <type>SQL</type>
      <connection>ORACLE_STG</connection>
      <sql>UPDATE {schema_stg}.ETA_ETAPAS_CARGA SET COD_STATUS = 'EM_EXECUCAO', DTC_INICIO = SYSDATE WHERE NOM_ETAPA = 'STG_{proj_slug.upper()}';</sql>
      <gui><xloc>280</xloc><yloc>180</yloc></gui>
    </action>
    <action>
      <name>EXEC_{Path(first_hpl_name).stem.upper()}</name>
      <type>PIPELINE</type>
      <filename>${{PROJECT_HOME}}/{first_hpl_name}</filename>
      <gui><xloc>500</xloc><yloc>180</yloc></gui>
    </action>
    <action>
      <name>SQL_SUCESSO_ETA_CARGA</name>
      <type>SQL</type>
      <connection>ORACLE_STG</connection>
      <sql>UPDATE {schema_stg}.ETA_ETAPAS_CARGA SET COD_STATUS = 'CONCLUIDO', DTC_FIM = SYSDATE WHERE NOM_ETAPA = 'STG_{proj_slug.upper()}';</sql>
      <gui><xloc>720</xloc><yloc>180</yloc></gui>
    </action>
    <action>
      <name>SUCCESS_FIM</name>
      <type>SUCCESS</type>
      <gui><xloc>920</xloc><yloc>180</yloc></gui>
    </action>
    <action>
      <name>MAIL_ALERTA_ERRO</name>
      <type>MAIL</type>
      <auth_password>#{{hop-pwd:ENV_SMTP_PASS}}</auth_password>
      <gui><xloc>500</xloc><yloc>340</yloc></gui>
    </action>
    <action>
      <name>ABORT_WORKFLOW</name>
      <type>ABORT</type>
      <gui><xloc>720</xloc><yloc>340</yloc></gui>
    </action>
  </actions>
  <hops>
    <hop>
      <from>START</from>
      <to>SQL_INICIO_ETA_CARGA</to>
      <enabled>Y</enabled>
      <evaluation>Y</evaluation>
      <unconditional>Y</unconditional>
    </hop>
    <hop>
      <from>SQL_INICIO_ETA_CARGA</from>
      <to>EXEC_{Path(first_hpl_name).stem.upper()}</to>
      <enabled>Y</enabled>
      <evaluation>Y</evaluation>
      <unconditional>N</unconditional>
    </hop>
    <hop>
      <from>EXEC_{Path(first_hpl_name).stem.upper()}</from>
      <to>SQL_SUCESSO_ETA_CARGA</to>
      <enabled>Y</enabled>
      <evaluation>Y</evaluation>
      <unconditional>N</unconditional>
    </hop>
    <hop>
      <from>SQL_SUCESSO_ETA_CARGA</from>
      <to>SUCCESS_FIM</to>
      <enabled>Y</enabled>
      <evaluation>Y</evaluation>
      <unconditional>N</unconditional>
    </hop>
    <hop>
      <from>EXEC_{Path(first_hpl_name).stem.upper()}</from>
      <to>MAIL_ALERTA_ERRO</to>
      <enabled>Y</enabled>
      <evaluation>N</evaluation>
      <unconditional>N</unconditional>
    </hop>
    <hop>
      <from>MAIL_ALERTA_ERRO</from>
      <to>ABORT_WORKFLOW</to>
      <enabled>Y</enabled>
      <evaluation>Y</evaluation>
      <unconditional>Y</unconditional>
    </hop>
  </hops>
</workflow>
""",
        encoding="utf-8",
    )

    doc_res: Dict[str, str] = {}
    try:
        from ninho_core.diagramas import gerar_documentacao_esteira_hop
        doc_res = gerar_documentacao_esteira_hop(str(pasta_destino), str(pasta_destino))
    except Exception as _exc:
        _LOG.debug("Exceção tratada (hop_gerador.py:838): %r", _exc)

    return {
        "pasta_destino": str(pasta_destino),
        "hwf_principal": str(hwf_path),
        "hpl_gerados": hpl_gerados,
        "hop_lint_yml": str(lint_path),
        "hop_pwd_json": str(vr_path),
        **doc_res,
    }
