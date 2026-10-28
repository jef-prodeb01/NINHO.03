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

import logging as _logging_ninho

_LOG = _logging_ninho.getLogger("ninho.auditar_esteira_hop")

import os
import re
import sys
import json
import hashlib
import argparse

from ninho_core import xml_seguro  # noqa: E402
from ninho_core.hop_gerador import (  # noqa: E402,F401 — fachada de compatibilidade
    KETTLE_ELEMENTS_TO_REMOVE,
    KETTLE_ELEMENT_REPLACEMENTS,
    KETTLE_TEXT_REPLACEMENTS,
    KETTLE_TYPE_REPLACEMENTS,
    _converter_elemento_kettle_recursivo,
    gerar_hop_lint_yml,
    gerar_hop_pwd_resolver_json,
    gerar_pacote_hop_completo,
    migrar_kettle_para_hop,
)
from pathlib import Path
from typing import Dict, List, Tuple, Any, Set

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


KNOWN_PROJECT_TOKENS = [
    "CFPC_BLASTER", "CFPC_FISC", "CFPC", "CPFC",
    "DRACO", "DHPP", "DEIC", "DIP", "VOCRIM",
    "COST_MGMT", "INDICADORES_SERVICO", "RH_BAHIA",
]

# Semente estática oficial do HopTwoWayPasswordEncoder.java (Apache Hop / Pentaho Kettle)
HOP_ENCODER_SEED_STR = "0933910847463829827159347601486730416058"
HOP_ENCODER_SEED_INT = int(HOP_ENCODER_SEED_STR)
HOP_PASSWORD_PREFIX = "Encrypted "

# Nomes padrão de transforms do Hop GUI (regra oficial NAMING-004 do hop-lint-core.yml)
DEFAULT_HOP_TRANSFORM_NAMES = {
    "Table input", "Table output", "Insert / update", "Select values",
    "Filter rows", "Sort rows", "Merge join", "Stream lookup",
    "Database lookup", "Add constants", "Add sequence", "Calculator",
    "Row denormaliser", "Row flattener", "Split fields", "String operations",
    "Switch / case", "Unique rows", "Value mapper", "Dummy (do nothing)",
    "Write to log", "Set variables", "Get variables", "Text file input",
    "Text file output", "CSV file input", "Microsoft Excel input",
    "Microsoft Excel writer", "Oracle bulk loader", "Execute SQL script",
}

# Tipos de pastas oficiais de metadata do Apache Hop 2.x (sempre kebab-case)
VALID_HOP_METADATA_FOLDERS = {
    "rdbms", "dataset", "variable-resolver", "workflow-log", "pipeline-log",
    "pipeline-run-configuration", "workflow-run-configuration", "hop-server",
    "partition-schema", "schema-definition", "cassandra-connection",
    "mongodb-connection", "neo4j-connection", "neo4j-graph-model",
    "splunk-connection", "web-service", "async-web-service",
    "execution-info-location", "execution-data-profile", "unit-test",
    "file-definition", " beam-file-definition", "rest-connection",
}

# Tabelas de mapeamento Kettle (.ktr/.kjb) -> Apache Hop 2.x (.hpl/.hwf) extraídas de KettleConst.java

def hop_encrypt_password(password: str, include_prefix: bool = True, seed: str = HOP_ENCODER_SEED_STR) -> str:
    """
    Port exato de HopTwoWayPasswordEncoder.java (Apache Hop 2.x / Pentaho Kettle).
    Se a string já contiver variáveis (${...} ou #{...}), preserva sem alterar.
    """
    if not password:
        return ""
    if "${" in password or "#{" in password:
        return password
    raw_bytes = password.encode("utf-8")
    bi_passwd = int.from_bytes(raw_bytes, byteorder="big", signed=True)
    bi_r0 = int(seed)
    bi_r1 = bi_r0 ^ bi_passwd
    hex_str = format(bi_r1, "x")
    return f"{HOP_PASSWORD_PREFIX}{hex_str}" if include_prefix else hex_str


def hop_decrypt_password(encrypted: str, seed: str = HOP_ENCODER_SEED_STR) -> str:
    """
    Decodifica strings 'Encrypted 2be98afc86aa7f2e...' usando o XOR estático do HopTwoWayPasswordEncoder.
    Demonstra porque THREAT_MODEL.md classifica 'Encrypted ...' como ofuscação reversível (não criptografia forte).
    """
    if not encrypted:
        return ""
    clean = encrypted.strip()
    if clean.startswith(HOP_PASSWORD_PREFIX):
        clean = clean[len(HOP_PASSWORD_PREFIX):].strip()
    if not clean or "${" in clean or "#{" in clean:
        return ""
    try:
        bi_r1 = int(clean, 16)
        bi_confuse = int(seed)
        bi_r0 = bi_r1 ^ bi_confuse
        if bi_r0 == 0:
            return "\x00"
        byte_len = (bi_r0.bit_length() + 8) // 8
        raw_bytes = bi_r0.to_bytes(byte_len, byteorder="big", signed=True)
        # BigInteger.toByteArray() pode incluir byte 0x00 inicial de sinal se MSB >= 0x80
        if len(raw_bytes) > 1 and raw_bytes[0] == 0:
            raw_bytes = raw_bytes[1:]
        return raw_bytes.decode("utf-8", errors="replace")
    except Exception:
        return ""


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
    except ValueError as _exc:
        _LOG.debug("Exceção tratada (auditar_esteira_hop.py:155): %r", _exc)
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

                # HOP-SEC-01 (DB-001 / THREAT_MODEL.md): Conexão RDBMS JSON com senha em texto puro ou Encrypted estático
                rel_posix = rel_str.replace("\\", "/")
                if "/metadata/" in f"/{rel_posix}" and isinstance(data, dict):
                    pwd_candidates: List[str] = []
                    if "password" in data and isinstance(data.get("password"), str):
                        pwd_candidates.append(str(data.get("password") or "").strip())
                    for _db_type, db_cfg in data.items():
                        if isinstance(db_cfg, dict):
                            if "password" in db_cfg and isinstance(db_cfg.get("password"), str):
                                pwd_candidates.append(str(db_cfg.get("password") or "").strip())
                            for _sub_k, sub_cfg in db_cfg.items():
                                if isinstance(sub_cfg, dict) and "password" in sub_cfg:
                                    pwd_candidates.append(str(sub_cfg.get("password") or "").strip())
                    for db_pwd in pwd_candidates:
                        if db_pwd and not db_pwd.startswith("${") and not db_pwd.startswith("#{"):
                            if db_pwd.startswith("Encrypted "):
                                dec_preview = hop_decrypt_password(db_pwd)
                                masked = (dec_preview[:2] + "***") if len(dec_preview) > 2 else "***"
                                findings.append(
                                    Finding(
                                        "HOP-SEC-01",
                                        "ALTO",
                                        rel_str,
                                        f"Ofuscação reversível 'Encrypted' em conexão RDBMS '{f.stem}' (DB-001 / THREAT_MODEL)",
                                        f"A senha em `{rel_str}` usa XOR com semente estática pública (`HopTwoWayPasswordEncoder`, decodificável instantaneamente: `{masked}`).",
                                        f"Substituir por Variable Resolver `\"password\": \"#{{hop-pwd:ENV_PASS_{f.stem.upper()}}}\"` ou `${{ENV_PASS_{f.stem.upper()}}}`.",
                                    )
                                )
                            else:
                                findings.append(
                                    Finding(
                                        "HOP-H1",
                                        "CRITICO",
                                        rel_str,
                                        f"Senha em texto aberto na conexão RDBMS '{f.stem}' (DB-001)",
                                        f"O atributo `password` da conexão `{f.stem}` expõe credencial de banco em texto puro.",
                                        f"Substituir por `\"password\": \"#{{hop-pwd:ENV_PASS_{f.stem.upper()}}}\"`.",
                                    )
                                )

        # META-001: Validar subpastas de metadata/<kebab-case> (FileMetadataFolderProvider)
        meta_dir = proj_root / "metadata"
        if meta_dir.exists() and meta_dir.is_dir():
            for child_dir in sorted(meta_dir.iterdir()):
                if child_dir.is_dir():
                    folder_name = child_dir.name
                    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", folder_name):
                        findings.append(
                            Finding(
                                "META-001",
                                "ALTO",
                                str(child_dir.relative_to(base_dir) if child_dir.is_relative_to(base_dir) else child_dir),
                                f"Subpasta de metadata fora do padrão kebab-case: 'metadata/{folder_name}'",
                                f"O `FileMetadataFolderProvider` do Apache Hop 2.x exige nomes de pastas em `kebab-case` (ex: `rdbms`, `variable-resolver`, `workflow-log`). Pastas como `{folder_name}` são ignoradas em runtime.",
                                f"Renomear `metadata/{folder_name}` para `{folder_name.lower().replace('_', '-')}`.",
                            )
                        )

        # Segunda passagem: auditar .hpl e .hwf com contexto das variáveis do projeto
        for f in pfiles:
            if f.suffix not in (".hpl", ".hwf"):
                continue
            rel_str = str(f.relative_to(base_dir) if f.is_relative_to(base_dir) else f)
            try:
                raw_text = f.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            # HOP-H1 & HOP-SEC-01: Senhas hardcoded ou Encrypted reversível em XML (<auth_password>, <password>, <httpPassword>)
            for m in re.finditer(
                r"<(auth_password|password|httpPassword|trustStorePassword|keyStorePassword)>(.*?)</\1>",
                raw_text,
            ):
                tag_name = m.group(1)
                pwd_val = m.group(2).strip()
                if not pwd_val:
                    continue
                if (
                    not pwd_val.startswith("Encrypted")
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
                elif pwd_val.startswith("Encrypted "):
                    dec_preview = hop_decrypt_password(pwd_val)
                    masked = (dec_preview[:2] + "***") if len(dec_preview) > 2 else "***"
                    findings.append(
                        Finding(
                            "HOP-SEC-01",
                            "ALTO",
                            rel_str,
                            f"Ofuscação reversível 'Encrypted' hardcoded na tag <{tag_name}> (SEC-002 / THREAT_MODEL)",
                            f"Tag `<{tag_name}>{pwd_val[:22]}...</{tag_name}>` usa semente estática do Hop (`HopTwoWayPasswordEncoder`, reversível para `{masked}`).",
                            f"Externalizar a senha do XML para Variable Resolver (`#{{hop-pwd:ENV_{tag_name.upper()}}}`) ou variável de ambiente (`${{ENV_{tag_name.upper()}}}`).",
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
                root = xml_seguro.fromstring(raw_text)
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

                # DOC-001 (hop-lint): Verificar se há <description> em <info> ou <notepad>
                info_desc = (root.findtext("info/description") or "").strip()
                has_notepads = bool(root.findall(".//notepad"))
                if not info_desc and not has_notepads:
                    findings.append(
                        Finding(
                            "DOC-001",
                            "BAIXO",
                            rel_str,
                            f"Pipeline '{f.stem}' sem <description> nem <notepad> explicativo (hop-lint DOC-001)",
                            "A ausência de descrição e notas de canvas dificulta a governança e a geração automática via DocBuilder.",
                            "Preencher `<info><description>` ou adicionar um `<notepad>` com objetivo, origem e tabela alvo do pipeline.",
                        )
                    )

                # Mapear conexões de hops e error handling para detectar órfãos (TRANS-002) e hops desabilitados (STRUCT-003)
                connected_transforms: Set[str] = set()
                for hop_el in root.findall(".//order/hop"):
                    fr_tx = (hop_el.findtext("from") or "").strip()
                    to_tx = (hop_el.findtext("to") or "").strip()
                    en_tx = (hop_el.findtext("enabled") or "Y").strip().upper()
                    if fr_tx:
                        connected_transforms.add(fr_tx)
                    if to_tx:
                        connected_transforms.add(to_tx)
                    if en_tx == "N":
                        findings.append(
                            Finding(
                                "STRUCT-003",
                                "MEDIO",
                                rel_str,
                                f"Hop desabilitado no pipeline: '{fr_tx}' -> '{to_tx}' (hop-lint STRUCT-003)",
                                "Hops desabilitados deixados em produção geram código morto e confusão visual no canvas.",
                                "Remover o hop desabilitado e os transforms de teste associados antes do deploy.",
                            )
                        )
                for err_el in root.findall(".//transform_error_handling/error"):
                    src_tx = (err_el.findtext("source_transform") or "").strip()
                    tgt_tx = (err_el.findtext("target_transform") or "").strip()
                    if src_tx:
                        connected_transforms.add(src_tx)
                    if tgt_tx:
                        connected_transforms.add(tgt_tx)

                all_tx_elements = root.findall("transform")
                vars_set_in_pipeline: Set[str] = set()
                for tx in all_tx_elements:
                    if (tx.findtext("type") or "").strip() == "SetVariable":
                        for fn_node in tx.findall(".//fields/field/variable_name"):
                            if fn_node.text and fn_node.text.strip():
                                vars_set_in_pipeline.add(fn_node.text.strip())

                for tx in all_tx_elements:
                    tx_type = tx.findtext("type", "")
                    tx_name = tx.findtext("name", "")
                    stats["transforms"][tx_type] = stats["transforms"].get(tx_type, 0) + 1

                    # TRANS-002 (hop-lint): Transform órfão quando há múltiplos transforms no pipeline
                    if len(all_tx_elements) > 1 and tx_name and tx_name not in connected_transforms:
                        findings.append(
                            Finding(
                                "TRANS-002",
                                "ALTO",
                                rel_str,
                                f"Transform órfão desconectado no canvas: '{tx_name}' ({tx_type}) (hop-lint TRANS-002)",
                                f"O transform `{tx_name}` não possui nenhum `<hop>` de entrada ou saída ativo, mas é inicializado pelo motor Hop.",
                                "Conectar o transform ao fluxo principal ou removê-lo do pipeline.",
                            )
                        )

                    # NAMING-004 (hop-lint): Nome padrão de GUI não renomeado ("Table input", "Select values 2", etc.)
                    base_tx_name = re.sub(r"\s+\d+$", "", tx_name.strip())
                    if base_tx_name in DEFAULT_HOP_TRANSFORM_NAMES:
                        findings.append(
                            Finding(
                                "NAMING-004",
                                "BAIXO",
                                rel_str,
                                f"Transform com nome genérico padrão do Hop GUI: '{tx_name}' (hop-lint NAMING-004)",
                                f"O nome `{tx_name}` não descreve a regra de negócio nem a entidade manipulada.",
                                f"Renomear para padrão semântico (ex: `IN_{f.stem.upper()}`, `OUT_STG_...`, `FLT_...`).",
                            )
                        )

                    # SQL-002 (hop-lint) & HOP-SEC-02 (THREAT_MODEL §4.5): TableInput / ExecSQL
                    if tx_type in ("TableInput", "ExecSQL", "DynamicSQLRow"):
                        sql_txt = (tx.findtext("sql") or "").strip()
                        limit_val = (tx.findtext("limit") or "0").strip()
                        repl_vars = (tx.findtext("replace_variables") or tx.findtext("VariableReplacementActive") or "N").strip().upper()
                        if (
                            tx_type == "TableInput"
                            and re.search(r"\bSELECT\s+\*\s+FROM\b", sql_txt, re.I)
                            and limit_val in ("", "0")
                            and not re.search(r"\b(ROWNUM|FETCH\s+FIRST)\b", sql_txt, re.I)
                        ):
                            findings.append(
                                Finding(
                                    "SQL-002",
                                    "MEDIO",
                                    rel_str,
                                    f"TableInput '{tx_name}' com 'SELECT *' irrestrito (hop-lint SQL-002)",
                                    "Consultas `SELECT *` sem filtro ou projeção explícita aumentam tráfego de rede JDBC e quebram se a origem mudar a ordem das colunas.",
                                    "Declarar explicitamente a lista de colunas necessárias no `<sql>`.",
                                )
                            )

                        # HOP-SEC-02: Interpolação direta de ${VAR} no SQL (especialmente com replace_variables=Y ou SetVariable)
                        vars_in_sql = re.findall(r"\$\{([A-Za-z0-9_.-]+)\}", sql_txt)
                        non_schema_vars = [
                            v for v in vars_in_sql
                            if not any(k in v.upper() for k in ("SCHEMA", "OWNER", "TABLE", "DB"))
                        ]
                        if non_schema_vars and (repl_vars == "Y" or any(v in vars_set_in_pipeline for v in non_schema_vars)):
                            findings.append(
                                Finding(
                                    "HOP-SEC-02",
                                    "ALTO",
                                    rel_str,
                                    f"Risco de SQL Injection via interpolação de variável ${{{non_schema_vars[0]}}} em '{tx_name}' (THREAT_MODEL §4.5)",
                                    f"A consulta SQL interpola diretamente `${{{', '.join(non_schema_vars)}}}` com substituição textual ativa.",
                                    "Usar bind parameters posicionais (`?`) com stream de parâmetros (`<lookup>`) em vez de interpolação `${VAR}`.",
                                )
                            )

                    # Coletar tabelas alvo e auditar sincronia com DDL de Staging (HOP-H9)
                    if tx_type in ("TableOutput", "InsertUpdate", "OraBulkLoader"):
                        tbl = (tx.findtext("table", "") or tx.findtext("lookup/table", "")).strip()
                        sch = (tx.findtext("schema", "") or tx.findtext("lookup/schema", "")).strip()
                        if tbl:
                            stats["target_tables"].add(f"{sch}.{tbl}" if sch else tbl)
                            # HOP-H9: Verificar se tabela STG_* existe no 02_create_stg_tables.sql do projeto
                            if tbl.upper().startswith("STG_"):
                                candidatos_stg_sql = [
                                    proj_root / "02_create_stg_tables.sql",
                                    proj_root.parent / "02_staging" / "02_create_stg_tables.sql",
                                    base_dir.parent / "02_staging" / "02_create_stg_tables.sql",
                                    proj_root.parent / "saida" / "planejador_dw" / "02_staging" / "02_create_stg_tables.sql",
                                    base_dir / "saida" / "planejador_dw" / "02_staging" / "02_create_stg_tables.sql",
                                ]
                                for cand_sql in candidatos_stg_sql:
                                    if cand_sql.exists():
                                        try:
                                            txt_stg = cand_sql.read_text(encoding="utf-8", errors="ignore").upper()
                                            tabelas_ddl_stg = set(
                                                re.findall(r"CREATE\s+TABLE\s+(?:[A-Z0-9_]+\.)?(STG_[A-Z0-9_]+)", txt_stg)
                                            )
                                            if tabelas_ddl_stg and tbl.upper() not in tabelas_ddl_stg:
                                                findings.append(
                                                    Finding(
                                                        "HOP-H9",
                                                        "CRITICO",
                                                        rel_str,
                                                        f"Dessincronia de Tabela Staging: '{tbl}' no Hop vs DDL ({ ', '.join(sorted(tabelas_ddl_stg)) })",
                                                        f"O transform '{tx_name}' tenta gravar em `{tbl}`, mas o DDL `{cand_sql.name}` declara `{', '.join(sorted(tabelas_ddl_stg))}` (causa `ORA-00942: table or view does not exist`).",
                                                        f"Alinhar a tag `<table>` em `{f.name}` para `{sorted(tabelas_ddl_stg)[0]}`.",
                                                    )
                                                )
                                        except Exception as _exc:
                                            _LOG.debug("Exceção tratada (auditar_esteira_hop.py:679): %r", _exc)
                                        break

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

                # DOC-001 (hop-lint): Verificar se há <description> ou <notepad> no workflow
                wf_desc = (root.findtext("description") or "").strip()
                wf_notepads = bool(root.findall(".//notepad"))
                if not wf_desc and not wf_notepads:
                    findings.append(
                        Finding(
                            "DOC-001",
                            "BAIXO",
                            rel_str,
                            f"Workflow '{f.stem}' sem <description> nem <notepad> explicativo (hop-lint DOC-001)",
                            "A ausência de descrição ou nota de canvas no workflow dificulta o entendimento da orquestração.",
                            "Preencher `<description>` ou adicionar um `<notepad>` descrevendo o fluxo e o SLA.",
                        )
                    )

                all_act_elements = root.findall(".//action")
                connected_actions: Set[str] = set()
                for hop in root.findall(".//hop"):
                    fr = (hop.findtext("from") or "").strip()
                    to = (hop.findtext("to") or "").strip()
                    ev = hop.findtext("evaluation", "Y")
                    un = hop.findtext("unconditional", "N")
                    en = hop.findtext("enabled", "Y")
                    if fr:
                        connected_actions.add(fr)
                    if to:
                        connected_actions.add(to)
                    if en == "N":
                        findings.append(
                            Finding(
                                "STRUCT-003",
                                "MEDIO",
                                rel_str,
                                f"Hop desabilitado no workflow: '{fr}' -> '{to}' (hop-lint STRUCT-003)",
                                "Hops desabilitados no workflow podem mascarar rotas de erro ou etapas órfãs.",
                                "Remover o hop desabilitado ou reativar a rota pretendida.",
                            )
                        )
                    # HOP-H3: Hop condicional invertido (evaluation=N apontando para etapa produtiva)
                    if (
                        en == "Y"
                        and ev == "N"
                        and un == "N"
                        and not any(
                            k in to.upper()
                            for k in ("ERRO", "EMAIL", "ABORT", "LOG", "FALHA", "FAIL", "EXCECAO", "MAIL", "ROLLBACK")
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

                for act in all_act_elements:
                    act_type = act.findtext("type", "")
                    act_name = (act.findtext("name") or "").strip()
                    stats["actions"][act_type] = stats["actions"].get(act_type, 0) + 1
                    # WORKFLOW-002 (hop-lint): Action órfã desconectada no workflow
                    if len(all_act_elements) > 1 and act_name and act_name not in connected_actions:
                        findings.append(
                            Finding(
                                "WORKFLOW-002",
                                "ALTO",
                                rel_str,
                                f"Action órfã desconectada no workflow: '{act_name}' ({act_type}) (hop-lint WORKFLOW-002)",
                                f"A action `{act_name}` não possui nenhum `<hop>` de entrada ou saída no workflow.",
                                "Conectar a action ao fluxo de orquestração ou removê-la do workflow.",
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

    lines.append("## 🚨 2. Diagnóstico de Heurísticas (`HOP-H1..H9`, `hop-lint` & `THREAT_MODEL`)")
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
    parser = argparse.ArgumentParser(
        description="Motor Apache Hop 2.x do NINHO: Auditoria (HOP-H1..H9 + hop-lint + THREAT_MODEL), Canvas SVG, Migrador Kettle (.ktr/.kjb -> .hpl/.hwf) e Gerador de Pacotes."
    )
    parser.add_argument(
        "alvo",
        nargs="?",
        default=None,
        help="Caminho da pasta do projeto Hop/Kettle ou arquivo (.hpl/.hwf/.ktr/.kjb)",
    )
    parser.add_argument("--saida", "-o", help="Arquivo Markdown de saída ou pasta de destino", default=None)
    parser.add_argument("--svg-doc", action="store_true", help="Gera também diagrama_esteira_hop.svg e DOCUMENTACAO_HOP.md")
    parser.add_argument("--gerar-lint-yml", action="store_true", help="Gera o arquivo hop-lint.yml na pasta alvo")
    parser.add_argument("--migrar-kettle", metavar="PASTA_DESTINO", help="Migra projeto legado Pentaho Kettle (.ktr/.kjb/shared.xml) para Apache Hop 2.x", default=None)
    parser.add_argument("--gerar-pacote-hop", action="store_true", help="Gera um pacote completo Apache Hop 2.x em saida/planejador_dw/06_pipelines_hop")
    parser.add_argument("--orabulkloader", action="store_true", help="Usa OraBulkLoader (SQL*Loader DIRECT=TRUE) no pacote Hop gerado")
    parser.add_argument("--projeto", default="DW_CORPORATIVO", help="Nome do projeto para geração de pacote Hop")
    parser.add_argument("--schema-stg", default="STG_DW", help="Schema Oracle de Staging para geração de pacote Hop")
    parser.add_argument("--encrypt", metavar="SENHA", help="Codifica senha usando HopTwoWayPasswordEncoder", default=None)
    parser.add_argument("--decrypt", metavar="HASH", help="Decodifica hash 'Encrypted ...' usando HopTwoWayPasswordEncoder", default=None)
    args = parser.parse_args()

    if args.encrypt is not None:
        print(hop_encrypt_password(args.encrypt))
        return
    if args.decrypt is not None:
        print(hop_decrypt_password(args.decrypt))
        return

    if args.gerar_pacote_hop:
        dest = Path(args.saida or args.alvo or "saida/planejador_dw/06_pipelines_hop")
        res = gerar_pacote_hop_completo(
            pasta_destino=dest,
            projeto=args.projeto,
            schema_stg=args.schema_stg,
            usar_orabulkloader=args.orabulkloader,
        )
        print(f"[OK] Pacote Apache Hop 2.x gerado em: {res['pasta_destino']}")
        print(f"  - Workflow Mestre: {res['hwf_principal']}")
        print(f"  - Pipelines (.hpl): {len(res['hpl_gerados'])}")
        print(f"  - Linter Config: {res['hop_lint_yml']}")
        print(f"  - Variable Resolver: {res['hop_pwd_json']}")
        if res.get("svg_esteira_hop"):
            print(f"  - Canvas SVG: {res['svg_esteira_hop']}")
        if res.get("doc_esteira_hop"):
            print(f"  - Auto-Documentação: {res['doc_esteira_hop']}")
        return

    if args.migrar_kettle:
        if not args.alvo:
            print("[ERRO] Informe o caminho de origem (.ktr/.kjb ou pasta) para migrar.", file=sys.stderr)
            sys.exit(1)
        src = Path(args.alvo)
        if not src.exists():
            print(f"[ERRO] Caminho de origem não encontrado: {src}", file=sys.stderr)
            sys.exit(1)
        dest = Path(args.migrar_kettle)
        res = migrar_kettle_para_hop(src, dest)
        print(f"[OK] Migração Kettle -> Apache Hop 2.x concluída em: {dest}")
        print(f"  - Pipelines convertidos (.ktr -> .hpl): {len(res['hpl_migrados'])}")
        print(f"  - Workflows convertidos (.kjb -> .hwf): {len(res['hwf_migrados'])}")
        print(f"  - Conexões extraídas para metadata/rdbms/: {len(res['conexoes_rdbms'])}")
        if res.get("svg_esteira_hop"):
            print(f"  - Canvas SVG: {res['svg_esteira_hop']}")
        if res.get("doc_esteira_hop"):
            print(f"  - Auto-Documentação: {res['doc_esteira_hop']}")
        return

    target = Path(args.alvo) if args.alvo else Path("saida/planejador_dw/06_pipelines_hop")
    if not target.exists():
        print(f"[ERRO] Caminho não encontrado: {target}", file=sys.stderr)
        sys.exit(1)

    if args.gerar_lint_yml:
        lint_dir = target if target.is_dir() else target.parent
        yml_p = gerar_hop_lint_yml(lint_dir)
        print(f"[OK] hop-lint.yml gerado em: {yml_p}")

    if args.svg_doc:
        try:
            from ninho_core.diagramas import gerar_documentacao_esteira_hop
            out_dir = Path(args.saida).parent if args.saida else (target if target.is_dir() else target.parent)
            doc_res = gerar_documentacao_esteira_hop(str(target), str(out_dir))
            if doc_res.get("svg_esteira_hop"):
                print(f"[OK] Diagrama SVG Hop salvo em: {doc_res['svg_esteira_hop']}")
            if doc_res.get("doc_esteira_hop"):
                print(f"[OK] Documentação Técnica Hop salva em: {doc_res['doc_esteira_hop']}")
        except Exception as exc:
            print(f"[AVISO] Falha ao gerar SVG/Doc Hop: {exc}", file=sys.stderr)

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

