#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
Script: auditar_esteira_hop.py
Módulo: Core / Scripts Comuns (NINHO)
Finalidade: Motor determinístico de auditoria estática, segurança e qualidade
            para esteiras Apache Hop 2.x (.hpl, .hwf, .json) e scripts (.py, .sh).
            Aplica as heurísticas corporativas HOP-H1 a HOP-H8 extraídas de
            projetos reais (DGO, GESTAODIS/COST_MGMT, Indicadores_servico).
Uso:
  python core/scripts_comuns/auditar_esteira_hop.py <caminho_pasta_ou_arquivo> [--saida relatorio.md]
==============================================================================
"""

import os
import re
import sys
import json
import hashlib
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Tuple, Any, Set

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


KNOWN_PROJECT_TOKENS = [
    "CFPC_BLASTER", "CFPC_FISC", "CFPC", "CPFC",
    "DRACO", "DHPP", "DEIC", "DIP", "VOCRIM",
    "COST_MGMT", "INDICADORES_SERVICO", "RH_BAHIA",
]


class Finding:
    def __init__(
        self,
        rule_id: str,
        severity: str,
        file_path: str,
        title: str,
        detail: str,
        recommendation: str,
    ):
        self.rule_id = rule_id
        self.severity = severity  # CRITICO | ALTO | MEDIO | INFO
        self.file_path = file_path
        self.title = title
        self.detail = detail
        self.recommendation = recommendation


def find_project_root(file_path: Path, base_dir: Path) -> Path:
    """Encontra a raiz do projeto Hop (onde fica project-config.json) ou subpasta imediata."""
    cur = file_path.parent
    while cur != base_dir and cur.parent != cur:
        if (cur / "project-config.json").exists():
            return cur
        cur = cur.parent
    # Fallback: primeira subpasta abaixo de base_dir
    try:
        rel = file_path.relative_to(base_dir)
        if len(rel.parts) >= 2:
            if rel.parts[0].upper() in ("DGO", "GESTAODIS") and len(rel.parts) >= 3:
                return base_dir / rel.parts[0] / rel.parts[1]
            return base_dir / rel.parts[0]
    except ValueError:
        pass
    return file_path.parent


def get_project_tokens_to_ignore(proj_name: str) -> Set[str]:
    """Retorna tokens que pertencem legitimamente ao próprio projeto."""
    up = proj_name.upper()
    own = {up}
    if "CFPC" in up or "CPFC" in up:
        own.update({"CFPC", "CPFC", "CFPC_BLASTER", "CFPC_FISC"})
    if "INDICADORES" in up or "RH_BAHIA" in up or "SDM" in up:
        own.update({"INDICADORES_SERVICO", "RH_BAHIA"})
    return own


def audit_hop_directory(target_path: Path) -> Tuple[Dict[str, Any], List[Finding]]:
    files: List[Path] = []
    if target_path.is_file():
        files = [target_path]
        base_dir = target_path.parent
    else:
        base_dir = target_path
        for root_dir, _, filenames in os.walk(target_path):
            for fn in sorted(filenames):
                if fn.endswith((".hpl", ".hwf", ".json", ".py", ".sh")):
                    files.append(Path(root_dir) / fn)

    stats: Dict[str, Any] = {
        "hpl_count": 0,
        "hwf_count": 0,
        "json_count": 0,
        "py_count": 0,
        "sh_count": 0,
        "projects": set(),
        "transforms": {},
        "actions": {},
        "target_tables": set(),
        "features_found": {
            "eta_etapas_carga": False,
            "controle_modificacao_arquivos": False,
            "workflow_logging": False,
            "hop_pwd_resolver": False,
            "data_quality_error_table": False,
            "atomic_tmp_python": False,
        },
    }
    findings: List[Finding] = []

    # Agrupar arquivos por projeto Hop
    project_files: Dict[Path, List[Path]] = {}
    for f in files:
        proj_root = find_project_root(f, base_dir)
        project_files.setdefault(proj_root, []).append(f)
        stats["projects"].add(proj_root.name)
        if f.suffix == ".hpl":
            stats["hpl_count"] += 1
        elif f.suffix == ".hwf":
            stats["hwf_count"] += 1
        elif f.suffix == ".json":
            stats["json_count"] += 1
        elif f.suffix == ".py":
            stats["py_count"] += 1
        elif f.suffix == ".sh":
            stats["sh_count"] += 1

    # Para cada projeto, coletar variáveis de ambiente definidas em JSONs
    for proj_root, pfiles in sorted(project_files.items()):
        proj_name = proj_root.name
        own_tokens = get_project_tokens_to_ignore(proj_name)
        env_vars_defined: Dict[str, str] = {}
        hpl_hashes: Dict[str, List[Path]] = {}

        for f in pfiles:
            rel_str = str(f.relative_to(base_dir) if f.is_relative_to(base_dir) else f)
            try:
                raw_text = f.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            # Detectar features corporativas positivas
            if "ETA_ETAPAS_CARGA" in raw_text.upper():
                stats["features_found"]["eta_etapas_carga"] = True
            if "CONTROLE_MODIFICACAO_ARQUIVOS" in raw_text.upper():
                stats["features_found"]["controle_modificacao_arquivos"] = True
            if "<type>WorkflowLogging</type>" in raw_text or "workflow-log" in rel_str.replace("\\", "/"):
                stats["features_found"]["workflow_logging"] = True
            if "hop-pwd" in raw_text or "HopPassword" in raw_text:
                stats["features_found"]["hop_pwd_resolver"] = True
            if re.search(r"TAB_[A-Z0-9_]*ERRO", raw_text.upper()):
                stats["features_found"]["data_quality_error_table"] = True
            if ".tmp" in raw_text and ".replace(" in raw_text:
                stats["features_found"]["atomic_tmp_python"] = True

            # ------------------------------------------------------------------
            # Auditoria de arquivos JSON
            # ------------------------------------------------------------------
            if f.suffix == ".json":
                try:
                    data = json.loads(raw_text)
                except Exception as e:
                    findings.append(
                        Finding(
                            "HOP-H8",
                            "ALTO",
                            rel_str,
                            "Arquivo JSON inválido ou corrompido",
                            f"Falha ao fazer parse do JSON: {e}",
                            "Corrigir a sintaxe JSON do arquivo de configuração/metadado.",
                        )
                    )
                    continue

                # Checar variáveis de ambiente em ambiente_*.json / *-config.json
                if isinstance(data, dict) and isinstance(data.get("variables"), list):
                    for var_obj in data["variables"]:
                        if not isinstance(var_obj, dict):
                            continue
                        vname = str(var_obj.get("name", ""))
                        vval = str(var_obj.get("value", ""))
                        if vname:
                            env_vars_defined[vname] = vval

                        # HOP-H1 em JSON: senha em texto aberto
                        if any(k in vname.upper() for k in ("PASS", "SECRET", "PWD", "TOKEN")):
                            if (
                                vval
                                and not vval.startswith("Encrypted ")
                                and not vval.startswith("${")
                                and not vval.startswith("#{")
                            ):
                                findings.append(
                                    Finding(
                                        "HOP-H1",
                                        "CRITICO",
                                        rel_str,
                                        f"Segredo/Senha em texto puro na variável '{vname}'",
                                        f"Valor '{vval}' não está criptografado com 'Encrypted ...' nem referenciado via Variable Resolver.",
                                        "Criptografar a senha usando `hop-encrypt.sh -hop <senha>` ou `#{hop-pwd:" + vname + "}`.",
                                    )
                                )

                        # HOP-H2 em JSON: caminho de outro projeto em ENV_DIR_*
                        for tok in KNOWN_PROJECT_TOKENS:
                            if tok not in own_tokens and re.search(r"\b" + re.escape(tok) + r"\b", vval, re.I):
                                findings.append(
                                    Finding(
                                        "HOP-H2",
                                        "CRITICO",
                                        rel_str,
                                        f"Contaminação de Copy-Paste na variável '{vname}' (referência a '{tok}')",
                                        f"No projeto '{proj_name}', a variável '{vname}' aponta para '{vval}'.",
                                        f"Atualizar o caminho/valor da variável '{vname}' para usar o diretório do projeto '{proj_name}' ou `${{PROJECT_HOME}}`.",
                                    )
                                )

                # HOP-H8: Schema Definition JSON corrompido (ex: decimalSymbol="binary-string")
                if isinstance(data, dict) and isinstance(data.get("fieldDefinitions"), list):
                    for fd in data["fieldDefinitions"]:
                        if not isinstance(fd, dict):
                            continue
                        dec = str(fd.get("decimalSymbol", ""))
                        grp = str(fd.get("groupingSymbol", ""))
                        if dec == "binary-string" or grp == "R$":
                            findings.append(
                                Finding(
                                    "HOP-H8",
                                    "MEDIO",
                                    rel_str,
                                    f"Schema Definition '{data.get('name', f.stem)}' com propriedades deslocadas",
                                    f"O campo '{fd.get('name')}' possui decimalSymbol='{dec}' e groupingSymbol='{grp}', indicando desalinhamento de atributos na exportação do Hop.",
                                    "Recriar ou corrigir o arquivo JSON de Schema Definition em `metadata/schema-definition/`.",
                                )
                            )
                            break

        # Segunda passagem: auditar .hpl e .hwf com contexto das variáveis do projeto
        for f in pfiles:
            if f.suffix not in (".hpl", ".hwf"):
                continue
            rel_str = str(f.relative_to(base_dir) if f.is_relative_to(base_dir) else f)
            try:
                raw_text = f.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            # HOP-H1: Senhas hardcoded em XML (<auth_password>, <password>, <httpPassword>)
            for m in re.finditer(
                r"<(auth_password|password|httpPassword|trustStorePassword|keyStorePassword)>(.*?)</\1>",
                raw_text,
            ):
                tag_name = m.group(1)
                pwd_val = m.group(2).strip()
                if (
                    pwd_val
                    and not pwd_val.startswith("Encrypted")
                    and not pwd_val.startswith("${")
                    and not pwd_val.startswith("#{")
                ):
                    findings.append(
                        Finding(
                            "HOP-H1",
                            "CRITICO",
                            rel_str,
                            f"Senha hardcoded em texto aberto na tag <{tag_name}>",
                            f"Tag `<{tag_name}>{pwd_val[:4]}***</{tag_name}>` expõe credencial corporativa diretamente no XML versionado.",
                            "Substituir por variável de ambiente criptografada (ex: `${ENV_SMTP_PASS}`) ou Variable Resolver (`#{hop-pwd:ENV_SMTP_PASS}`).",
                        )
                    )

            # HOP-H2: Contaminação de Copy-Paste entre projetos no XML
            for tok in KNOWN_PROJECT_TOKENS:
                if tok not in own_tokens:
                    matches = list(re.finditer(r"\b" + re.escape(tok) + r"\b", raw_text, re.I))
                    if matches:
                        # Extrair linha aproximada do primeiro match
                        line_no = raw_text[: matches[0].start()].count("\n") + 1
                        snippet = raw_text.splitlines()[line_no - 1].strip()
                        findings.append(
                            Finding(
                                "HOP-H2",
                                "CRITICO",
                                rel_str,
                                f"Vazamento de Copy-Paste: menção a '{tok}' dentro do projeto '{proj_name}' (linha {line_no})",
                                f"Trecho encontrado: `{snippet[:140]}`",
                                f"Substituir a referência hardcoded a '{tok}' pela referência correta do projeto '{proj_name}' ou por `${{HOP_PROJECT_NAME}}`.",
                            )
                        )

            # HOP-H5: Concatenação de variáveis de diretório + arquivo sem barra '/'
            for m in re.finditer(r"(\$\{[^}]+\})(\$\{[^}]+\})", raw_text):
                v1, v2 = m.group(1), m.group(2)
                # Ignorar casos legítimos onde FTP_DIR já começa com / ou em expressões shell ${VAR%/}
                if "PORT" in v1.upper() and "DIR" in v2.upper():
                    continue
                if any(k in v1.upper() for k in ("DIR", "PATH", "HOME", "FOLDER")):
                    line_no = raw_text[: m.start()].count("\n") + 1
                    findings.append(
                        Finding(
                            "HOP-H5",
                            "ALTO",
                            rel_str,
                            f"Concatenação de variáveis de caminho sem barra '/' (linha {line_no})",
                            f"Expressão `{v1}{v2}` falha caso `{v1}` seja definido sem `/` no final no arquivo de ambiente.",
                            f"Padronizar com barra separadora explícita: `{v1}/{v2}`.",
                        )
                    )
                    break

            # HOP-H5b: Referências ${PROJECT_HOME}/... para arquivos .hpl/.hwf/.py/.sh inexistentes
            for m in re.finditer(r"<filename>\$\{PROJECT_HOME\}/([^<$]+\.(?:hpl|hwf|py|sh))</filename>", raw_text):
                rel_ref = m.group(1).strip()
                target_file = proj_root / rel_ref.replace("/", os.sep)
                if not target_file.exists():
                    line_no = raw_text[: m.start()].count("\n") + 1
                    findings.append(
                        Finding(
                            "HOP-H5",
                            "CRITICO",
                            rel_str,
                            f"Referência quebrada a arquivo inexistente no projeto (linha {line_no})",
                            f"O caminho `${{PROJECT_HOME}}/{rel_ref}` não existe dentro de `{proj_root.name}`.",
                            "Corrigir o caminho em `<filename>` para apontar para o pipeline/workflow real do projeto.",
                        )
                    )

            # Parse XML para inspeção estrutural de .hpl e .hwf
            try:
                root = ET.fromstring(raw_text)
            except Exception as e:
                findings.append(
                    Finding(
                        "HOP-H8",
                        "CRITICO",
                        rel_str,
                        "XML inválido em arquivo Hop",
                        f"Erro ao parsear XML: {e}",
                        "Verificar fechamento de tags no arquivo .hpl/.hwf.",
                    )
                )
                continue

            if f.suffix == ".hpl":
                # Calcular hash canônico sem <name> e datas para detectar duplicação exata (HOP-H4)
                normalized_lines = [
                    ln.strip()
                    for ln in raw_text.splitlines()
                    if not any(
                        tag in ln
                        for tag in ("<name>", "<created_date>", "<modified_date>")
                    )
                ]
                h_digest = hashlib.sha256("\n".join(normalized_lines).encode("utf-8")).hexdigest()
                hpl_hashes.setdefault(h_digest, []).append(f)

                for tx in root.findall("transform"):
                    tx_type = tx.findtext("type", "")
                    tx_name = tx.findtext("name", "")
                    stats["transforms"][tx_type] = stats["transforms"].get(tx_type, 0) + 1

                    # Coletar tabelas alvo
                    if tx_type in ("TableOutput", "InsertUpdate"):
                        tbl = tx.findtext("table", "") or tx.findtext("lookup/table", "")
                        sch = tx.findtext("schema", "") or tx.findtext("lookup/schema", "")
                        if tbl:
                            stats["target_tables"].add(f"{sch}.{tbl}" if sch else tbl)

                    # HOP-H6: PipelineExecutor / WorkflowExecutor com inherit_all_vars=N
                    if tx_type in ("PipelineExecutor", "WorkflowExecutor"):
                        inh = tx.findtext("inherit_all_vars", "Y")
                        if inh == "N":
                            findings.append(
                                Finding(
                                    "HOP-H6",
                                    "MEDIO",
                                    rel_str,
                                    f"{tx_type} '{tx_name}' com <inherit_all_vars>N</inherit_all_vars>",
                                    "Variáveis do workflow/pipeline pai (como `${V_SEQ}` ou variáveis de ambiente em memória) não são repassadas automaticamente ao sub-executor.",
                                    "Habilitar `<inherit_all_vars>Y</inherit_all_vars>` no transform executor.",
                                )
                            )

                    # HOP-H4b: Hardcode de arquivo em ExcelInput/CSVInput quando ENV_NOM_ARQUIVO existe
                    if tx_type in ("ExcelInput", "CSVInput", "TextFileInput2") and "ENV_NOM_ARQUIVO" in env_vars_defined:
                        file_nodes = [tx.findtext("filename", "")] + [
                            fn.text or "" for fn in tx.findall(".//file/name")
                        ]
                        for fn_val in file_nodes:
                            fn_val = fn_val.strip()
                            if (
                                fn_val
                                and "ENV_NOM_ARQUIVO" not in fn_val
                                and fn_val.lower().endswith((".xlsx", ".xls"))
                            ):
                                findings.append(
                                    Finding(
                                        "HOP-H4",
                                        "ALTO",
                                        rel_str,
                                        f"Transform '{tx_name}' ignora variável ENV_NOM_ARQUIVO definida no ambiente",
                                        f"Caminho configurado como `{fn_val}`, enquanto o ambiente do projeto define `ENV_NOM_ARQUIVO={env_vars_defined['ENV_NOM_ARQUIVO']}`.",
                                        "Parametrizar o caminho do arquivo usando `${ENV_DIR_TARGET}/${ENV_NOM_ARQUIVO}`.",
                                    )
                                )

                    # HOP-H7: TableOutput / InsertUpdate boas práticas
                    if tx_type == "TableOutput":
                        use_batch = tx.findtext("use_batch", "Y")
                        spec_fields = tx.findtext("specify_fields", "Y")
                        if use_batch == "N" or spec_fields == "N":
                            findings.append(
                                Finding(
                                    "HOP-H7",
                                    "MEDIO",
                                    rel_str,
                                    f"TableOutput '{tx_name}' sem batch insert ou sem specify_fields",
                                    f"Configuração atual: use_batch={use_batch}, specify_fields={spec_fields}.",
                                    "Definir `<use_batch>Y</use_batch>` e `<specify_fields>Y</specify_fields>` para evitar quebra por alteração de ordem de colunas no Oracle.",
                                )
                            )
                    elif tx_type == "InsertUpdate":
                        tbl = tx.findtext("lookup/table", "")
                        sch = tx.findtext("lookup/schema", "")
                        if '"' in tbl or '"' in sch:
                            findings.append(
                                Finding(
                                    "HOP-H7",
                                    "BAIXO",
                                    rel_str,
                                    f"InsertUpdate '{tx_name}' com aspas duplas hardcoded em schema/tabela ({sch}.{tbl})",
                                    "O uso de identificadores entre aspas no Oracle força case-sensitivity estrito e dificulta parametrização.",
                                    "Remover aspas duplas do nome do schema e da tabela no transform InsertUpdate.",
                                )
                            )

            elif f.suffix == ".hwf":
                wname = root.findtext("name", "")
                if (
                    wname
                    and wname not in (f.stem, "New workflow")
                    and not f.stem.endswith("_old")
                    and not f.stem.endswith("_modificado")
                ):
                    findings.append(
                        Finding(
                            "HOP-H2",
                            "MEDIO",
                            rel_str,
                            f"Divergência entre <name>{wname}</name> interno e nome do arquivo '{f.name}'",
                            f"O workflow `{f.name}` está registrado internamente como `{wname}` (indício de clonagem sem atualização de metadado).",
                            f"Alinhar `<name>{f.stem}</name>` com `<name_sync_with_filename>Y</name_sync_with_filename>`.",
                        )
                    )

                for act in root.findall(".//action"):
                    act_type = act.findtext("type", "")
                    stats["actions"][act_type] = stats["actions"].get(act_type, 0) + 1

                # HOP-H3: Hop condicional invertido (evaluation=N apontando para etapa produtiva)
                for hop in root.findall(".//hop"):
                    fr = hop.findtext("from", "")
                    to = hop.findtext("to", "")
                    ev = hop.findtext("evaluation", "Y")
                    un = hop.findtext("unconditional", "N")
                    en = hop.findtext("enabled", "Y")
                    if (
                        en == "Y"
                        and ev == "N"
                        and un == "N"
                        and not any(
                            k in to.upper()
                            for k in ("ERRO", "EMAIL", "ABORT", "LOG", "FALHA", "FAIL", "EXCECAO")
                        )
                    ):
                        findings.append(
                            Finding(
                                "HOP-H3",
                                "CRITICO",
                                rel_str,
                                f"Hop condicional invertido (evaluation=N em fluxo produtivo): '{fr}' -> '{to}'",
                                f"O hop entre '{fr}' e '{to}' está configurado como caminho de FALHA (`evaluation=N`, `unconditional=N`), fazendo com que '{to}' só execute quando '{fr}' falhar!",
                                "Corrigir o hop no workflow para `<evaluation>Y</evaluation>` (caminho verde de sucesso).",
                            )
                        )

        # Verificar duplicação exata de pipelines no mesmo projeto (HOP-H4)
        for h_digest, dup_files in hpl_hashes.items():
            if len(dup_files) > 1:
                names = ", ".join(df.name for df in dup_files)
                rel0 = str(
                    dup_files[0].relative_to(base_dir)
                    if dup_files[0].is_relative_to(base_dir)
                    else dup_files[0]
                )
                findings.append(
                    Finding(
                        "HOP-H4",
                        "ALTO",
                        rel0,
                        f"Pipelines 100% duplicados dentro do projeto '{proj_name}': {names}",
                        f"Os arquivos ({names}) possuem exatamente o mesmo grafo de transforms e lógica XML, gerando retrabalho de manutenção e execução redundante.",
                        "Unificar os pipelines duplicados ou parametrizar a diferença via variáveis.",
                    )
                )

    return stats, findings


def format_markdown_report(target_path: Path, stats: Dict[str, Any], findings: List[Finding]) -> str:
    lines: List[str] = []
    lines.append("# 🦅 Relatório de Auditoria Preditiva — Esteira Apache Hop & Python/FTPS")
    lines.append("")
    lines.append(f"- **Diretório/Alvo Inspecionado:** `{target_path}`")
    lines.append(
        f"- **Inventário:** `{stats['hpl_count']}` Pipelines (`.hpl`) | "
        f"`{stats['hwf_count']}` Workflows (`.hwf`) | "
        f"`{stats['json_count']}` Configs/Metadados (`.json`) | "
        f"`{stats['py_count']}` Scripts Python (`.py`) | "
        f"`{stats['sh_count']}` Scripts Shell (`.sh`)"
    )
    lines.append(f"- **Projetos Mapeados ({len(stats['projects'])}):** `{', '.join(sorted(stats['projects']))}`")
    lines.append("")

    # Resumo de Padrões Corporativos Detectados
    lines.append("## 🏆 1. Conformidade com Padrões Corporativos (PRODEB / NINHO)")
    lines.append("")
    feat_labels = [
        ("eta_etapas_carga", "Auditoria de Ciclo de Vida no Oracle (`ETA_ETAPAS_CARGA`)"),
        ("controle_modificacao_arquivos", "Controle de Manifesto FTPS (`CONTROLE_MODIFICACAO_ARQUIVOS`)"),
        ("workflow_logging", "Captura Nativa de Erros de Workflow (`WorkflowLogging`)"),
        ("hop_pwd_resolver", "Resolução Segura de Senhas (`HopPassword` Variable Resolver `#{hop-pwd:...}`)"),
        ("data_quality_error_table", "Gate de Qualidade com Quarentena (`TAB_*_ERRO`) e Devolução por E-mail"),
        ("atomic_tmp_python", "Escrita Atômica de CSV em Python (`.tmp` + `.replace()`)"),
    ]
    for key, label in feat_labels:
        status = "✅ Detectado" if stats["features_found"].get(key) else "⚪ Não detectado neste escopo"
        lines.append(f"- **{label}:** {status}")
    lines.append("")

    # Contagem por severidade
    sev_order = {"CRITICO": 0, "ALTO": 1, "MEDIO": 2, "BAIXO": 3}
    findings_sorted = sorted(findings, key=lambda x: (sev_order.get(x.severity, 9), x.rule_id, x.file_path))
    crit = sum(1 for f in findings_sorted if f.severity == "CRITICO")
    alto = sum(1 for f in findings_sorted if f.severity == "ALTO")
    medio = sum(1 for f in findings_sorted if f.severity == "MEDIO")
    baixo = sum(1 for f in findings_sorted if f.severity == "BAIXO")

    lines.append("## 🚨 2. Diagnóstico de Heurísticas (`HOP-H1` a `HOP-H8`)")
    lines.append("")
    lines.append(
        f"**Total de Apontamentos:** `{len(findings_sorted)}` "
        f"(🔴 Críticos: `{crit}` | 🟠 Altos: `{alto}` | 🟡 Médios: `{medio}` | 🔵 Baixos: `{baixo}`)"
    )
    lines.append("")

    if not findings_sorted:
        lines.append("> ✅ **Nenhum problema estrutural ou vulnerabilidade detectada!**")
    else:
        lines.append("| Regra | Severidade | Arquivo | Diagnóstico | Recomendação Técnica |")
        lines.append("| :--- | :---: | :--- | :--- | :--- |")
        for fn in findings_sorted:
            icon = {"CRITICO": "🔴 CRÍTICO", "ALTO": "🟠 ALTO", "MEDIO": "🟡 MÉDIO", "BAIXO": "🔵 BAIXO"}.get(
                fn.severity, fn.severity
            )
            detail_clean = fn.detail.replace("|", "\\|").replace("\n", " ")
            title_clean = fn.title.replace("|", "\\|")
            rec_clean = fn.recommendation.replace("|", "\\|")
            lines.append(f"| `{fn.rule_id}` | {icon} | `{fn.file_path}` | **{title_clean}**<br/>{detail_clean} | {rec_clean} |")
    lines.append("")

    # Top Transforms e Actions
    if stats["transforms"]:
        top_tx = ", ".join(f"`{k}` ({v})" for k, v in sorted(stats["transforms"].items(), key=lambda x: -x[1])[:10])
        lines.append(f"- **Top Transforms (`.hpl`):** {top_tx}")
    if stats["actions"]:
        top_act = ", ".join(f"`{k}` ({v})" for k, v in sorted(stats["actions"].items(), key=lambda x: -x[1])[:10])
        lines.append(f"- **Top Actions (`.hwf`):** {top_act}")
    if stats["target_tables"]:
        tbls = ", ".join(f"`{t}`" for t in sorted(stats["target_tables"])[:20])
        lines.append(f"- **Tabelas Staging/Alvo Mapeadas ({len(stats['target_tables'])}):** {tbls}")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Auditor de Esteiras Apache Hop 2.x e Extratores Python/FTPS")
    parser.add_argument("alvo", help="Caminho da pasta do projeto Hop ou arquivo (.hpl/.hwf)")
    parser.add_argument("--saida", "-o", help="Arquivo Markdown de saída opcional", default=None)
    args = parser.parse_args()

    target = Path(args.alvo)
    if not target.exists():
        print(f"[ERRO] Caminho não encontrado: {target}", file=sys.stderr)
        sys.exit(1)

    stats, findings = audit_hop_directory(target)
    report = format_markdown_report(target, stats, findings)
    print(report)

    if args.saida:
        out_path = Path(args.saida)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report, encoding="utf-8")
        print(f"\n[OK] Relatório salvo em: {out_path}")


if __name__ == "__main__":
    main()

