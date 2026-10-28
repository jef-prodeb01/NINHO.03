#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gerar_artefatos_governanca.py — Esteira determinística de Governança de Dados (/executar-governanca)

Fluxo:
  1. Gate 0.5  — inspeciona os insumos do cliente em `entrega/governanca_dados/` (planilha + amostras),
                 cruza Dicionário x Amostras e classifica cada campo nos 4 níveis LGPD.
                 Reprovado -> grava `relatorio_devolucao_cliente_<ORGAO>.md` e encerra (exit 1).
  2. Gate 0    — lê `modulos/governanca_dados/INTAKE_GOVERNANCA.md` (Seção 0 e tecnologias marcadas).
                 Sem código de dataset válido -> gera só relatório + matriz e encerra (exit 2).
  3. Geração   — sempre: matriz DE/PARA + LGPD (.csv) e `relatorio_governanca_<DATASET>.md`.
                 MongoDB marcado: `schemas_mongo/` (coleções centrais, documento do tb_dataset,
                 coleção trusted com $jsonSchema estrito, barreira de quarentena e evento de auditoria).
                 AWS marcado: `aws_sagemaker_catalog/` (Metadata Form, payload do ativo, tabela Glue e
                 script boto3 de publicação em modo dry-run).

Nenhum dado é inventado: o que não vem do cliente nem do Intake sai como `<INFORMAR: ...>` e é listado
como pendência do engenheiro no relatório (e reprovado por `validar_entrega.py saida`).

Uso:
  python core/scripts_comuns/gerar_artefatos_governanca.py [caminho_insumos] [--intake caminho] [--json]
"""

import argparse
import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import inspecionar_insumos_governanca as gate  # noqa: E402
from ninho_core.console import configurar_saida_utf8  # noqa: E402
from ninho_core.paths import BASE_DIR, ENTREGA_DIR, SAIDA_DIR  # noqa: E402

configurar_saida_utf8()

SAIDA_GOV = SAIDA_DIR / "governanca_dados"
INTAKE_PADRAO = BASE_DIR / "modulos" / "governanca_dados" / "INTAKE_GOVERNANCA.md"
REFERENCIAS = BASE_DIR / ".agents" / "skills" / "governanca-dados-corporativa" / "references"
PADRAO_COD_DATASET = re.compile(r"^[A-Z0-9]+_[A-Z0-9]+_[A-Z0-9_]+_V[0-9]+$")
NIVEIS = ["PUBLICO", "INTERNO", "CONFIDENCIAL", "RESTRITO"]
TIPO_GLUE = {"string": "string", "int": "int", "long": "bigint", "decimal": "decimal(18,2)",
             "double": "double", "date": "timestamp", "bool": "boolean"}


def pendente(o_que: str) -> str:
    return f"<INFORMAR: {o_que}>"


# ----------------------------------------------------------------------------
# Leitura do Intake e dos metadados da planilha
# ----------------------------------------------------------------------------
def _valor_intake(texto: str, rotulo: str) -> str:
    m = re.search(rf"^-\s*\*\*{re.escape(rotulo)}.*?:\*\*\s*(.+)$", texto, re.MULTILINE)
    if not m:
        return ""
    valor = m.group(1).strip().strip("`").strip()
    return "" if valor.startswith("[") else valor


def _marcado(texto: str, rotulo: str) -> bool:
    return bool(re.search(rf"-\s*\[x\]\s*\*\*{rotulo}", texto, re.IGNORECASE))


def ler_intake(caminho: Path) -> dict:
    texto = caminho.read_text(encoding="utf-8", errors="replace") if caminho.exists() else ""
    ctx = {
        "sigla": _valor_intake(texto, "Sigla do Órgão / Cliente").upper(),
        "unidade": _valor_intake(texto, "Unidade / Coordenação / Sistema").upper(),
        "tema": _valor_intake(texto, "Tema de Negócio").upper(),
        "versao": _valor_intake(texto, "Versão do Esquema").upper(),
        "cod_dataset": _valor_intake(texto, "Código Canônico do Dataset").upper(),
        "data_owner": _valor_intake(texto, "Data Owner"),
        "data_steward": _valor_intake(texto, "Data Steward"),
        "engenheiro": _valor_intake(texto, "Engenheiro de Dados Responsável"),
        "mongo": _marcado(texto, "MongoDB"),
        "aws": _marcado(texto, "Amazon SageMaker"),
        "ferramentas": [
            nome for nome, rotulo in (
                ("ODI_12C", "Oracle Data Integrator"),
                ("APACHE_HOP", "Apache Hop"),
                ("PYTHON_EXTRACTOR", "Extratores e Automação Python"),
            ) if _marcado(texto, rotulo)
        ],
    }
    if not ctx["cod_dataset"] and all(ctx[k] for k in ("sigla", "unidade", "tema", "versao")):
        ctx["cod_dataset"] = f"{ctx['sigla']}_{ctx['unidade']}_{ctx['tema']}_{ctx['versao']}"
    return ctx


def _meta(metadados: dict, *palavras: str) -> str:
    """Valor da aba 'Dados - Insumos' cuja pergunta contém todas as palavras informadas."""
    for chave, valor in metadados.items():
        norm = gate.remover_acentos(chave).lower()
        if all(p in norm for p in palavras) and str(valor).strip():
            return str(valor).strip()
    return ""


def _enum(valor: str, mapa: dict, o_que: str) -> str:
    norm = gate.remover_acentos(valor).lower()
    for trecho, enum in mapa.items():
        if trecho in norm:
            return enum
    return pendente(o_que)


def _numero(valor: str):
    m = re.search(r"\d+(?:[.,]\d+)?", valor or "")
    return float(m.group(0).replace(",", ".")) if m else None


# ----------------------------------------------------------------------------
# Modelo do dataset (tb_dataset) a partir da inspeção + Intake
# ----------------------------------------------------------------------------
def _sim(valor) -> bool:
    return gate._sim_nao(valor) is True


def montar_campos(resultados: list) -> list:
    campos = []
    for r in resultados:
        for item in r.get("de_para_campos", []):
            if not re.match(r"^[a-z]{3}_[a-z0-9_]+$", item["campo_mongo"]):
                continue
            campos.append(item)
    return campos


def derivar_regras_qualidade(campos: list) -> list:
    """Regras da Barreira de 4 Etapas derivadas do dicionário (dimensões DAMA)."""
    regras = [{
        "cod_regra": "DQ_00_ESQUEMA",
        "nom_regra": "Documento aderente ao $jsonSchema da coleção trusted",
        "tip_dimensao_dama": "CONFORMIDADE",
        "des_severidade": "CRITICA",
        "prc_meta_conformidade": 100.0,
        "des_acao_falha": "ENVIAR_QUARENTENA_E_NOTIFICAR_CLIENTE",
    }]
    formatos = {"cpf": r"^\d{11}$", "cnpj": r"^\d{14}$", "cep": r"^\d{8}$"}
    for item in campos:
        campo = item["campo_mongo"]
        sufixo = campo.upper()
        if _sim(item.get("obrigatorio_cliente")) or _sim(item.get("chave_cliente")):
            regras.append({
                "cod_regra": f"DQ_COMPL_{sufixo}", "nom_regra": f"{campo} obrigatório (não nulo e não vazio)",
                "tip_dimensao_dama": "COMPLETUDE", "nom_campo_alvo": campo, "des_severidade": "CRITICA",
                "prc_meta_conformidade": 100.0, "des_acao_falha": "ENVIAR_QUARENTENA_E_NOTIFICAR_CLIENTE",
            })
        if _sim(item.get("chave_cliente")):
            regras.append({
                "cod_regra": f"DQ_UNIC_{sufixo}", "nom_regra": f"{campo} único no lote (chave de negócio)",
                "tip_dimensao_dama": "UNICIDADE", "nom_campo_alvo": campo, "des_severidade": "ALTA",
                "prc_meta_conformidade": 100.0, "des_acao_falha": "ENVIAR_QUARENTENA_E_NOTIFICAR_CLIENTE",
            })
        for doc, padrao in formatos.items():
            if re.search(rf"(^|_){doc}($|_)", campo):
                regras.append({
                    "cod_regra": f"DQ_CONF_{sufixo}", "nom_regra": f"{campo} com {doc.upper()} higienizado ({padrao})",
                    "tip_dimensao_dama": "CONFORMIDADE", "nom_campo_alvo": campo, "des_expressao_validacao": padrao,
                    "des_severidade": "ALTA", "prc_meta_conformidade": 100.0,
                    "des_acao_falha": "ENVIAR_QUARENTENA_E_NOTIFICAR_CLIENTE",
                })
        if item["tipo_bson"] == "date" and re.search(r"nascimento|obito|emissao|admissao", campo):
            regras.append({
                "cod_regra": f"DQ_VALID_{sufixo}", "nom_regra": f"{campo} não pode estar no futuro",
                "tip_dimensao_dama": "VALIDADE", "nom_campo_alvo": campo, "des_expressao_validacao": "<= data da carga",
                "des_severidade": "MEDIA", "prc_meta_conformidade": 100.0,
                "des_acao_falha": "ENVIAR_QUARENTENA_E_NOTIFICAR_CLIENTE",
            })
    return regras


def montar_documento_dataset(ctx: dict, metadados: dict, campos: list) -> dict:
    cod = ctx["cod_dataset"]
    cod_min = cod.lower()
    niveis = [c["classificacao_lgpd"]["des_nivel_sensibilidade"] for c in campos] or ["INTERNO"]
    nivel_global = max(niveis, key=NIVEIS.index)
    volume = _numero(_meta(metadados, "volume", "atualmente"))
    crescimento = _numero(_meta(metadados, "volume", "novos"))

    governanca = {
        "des_cargo_data_owner": pendente("cargo/unidade do Data Owner"),
        "nom_titular_data_owner": ctx["data_owner"] or _meta(metadados, "responsavel") or pendente("Data Owner (Seção 0 do Intake)"),
        "des_area_data_steward": pendente("área do Data Steward"),
        "nom_titular_data_steward": ctx["data_steward"] or pendente("Data Steward (Seção 0 do Intake)"),
        "des_equipe_engenharia_transporte": ctx["engenheiro"] or pendente("engenheiro responsável"),
        "des_criticidade": _enum(_meta(metadados, "criticidade"), {"critic": "CRITICA", "alta": "ALTA", "medi": "MEDIA", "baixa": "BAIXA"}, "criticidade ALTA/MEDIA/BAIXA/CRITICA"),
        "des_nivel_acesso_padrao": nivel_global,
        "des_frequencia_atualizacao": _meta(metadados, "frequencia") or pendente("frequência de atualização"),
        "des_janela_sla": _meta(metadados, "janela") or pendente("janela de disponibilização"),
    }
    if volume is not None:
        governanca["val_volume_estimado_gb"] = volume
    if crescimento is not None:
        governanca["val_crescimento_mensal_gb"] = crescimento

    metadados_campos = []
    for idx, item in enumerate(campos, start=1):
        classif = {k: v for k, v in item["classificacao_lgpd"].items() if k.startswith(("des_", "ind_")) and v != ""}
        metadados_campos.append({
            "cod_campo": f"{cod}_C{idx:03d}",
            "nom_campo_origem": item["campo_origem"],
            "nom_campo_mongo": item["campo_mongo"],
            "des_campo": item.get("descricao") or pendente(f"descrição de {item['campo_origem']}"),
            "tip_dado_origem": item.get("tipo_origem") or pendente(f"tipo de {item['campo_origem']}"),
            "tip_bson_mongo": item["tipo_bson"],
            "ind_obrigatorio": _sim(item.get("obrigatorio_cliente")) or _sim(item.get("chave_cliente")),
            "ind_chave_negocio": _sim(item.get("chave_cliente")),
            "classificacao_lgpd": classif,
        })

    jobs = {"ODI_12C": f"SCEN_CARGA_{cod}", "APACHE_HOP": f"wf_carga_{cod_min}", "PYTHON_EXTRACTOR": f"extrator_{cod_min}.py"}
    return {
        "cod_dataset": cod,
        "nom_dataset": _meta(metadados, "nome da tabela") or cod,
        "des_finalidade": pendente("finalidade do dataset"),
        "sts_dataset": "EM_HOMOLOGACAO",
        "num_versao_schema": ctx["versao"] or "V1",
        "orgao_responsavel": {
            "cod_orgao": ctx["sigla"] or pendente("sigla do órgão"),
            "sig_orgao": ctx["sigla"] or pendente("sigla do órgão"),
            "nom_orgao": pendente("nome por extenso do órgão"),
            "nom_unidade_responsavel": ctx["unidade"] or pendente("unidade responsável"),
        },
        "sistema_origem": {
            "cod_sistema": ctx["unidade"] or pendente("código do sistema"),
            "nom_sistema": _meta(metadados, "sistema de origem") or pendente("nome do sistema de origem"),
            "des_versao_origem": _meta(metadados, "versao da origem") or pendente("versão da origem"),
            "tip_fonte": _enum(_meta(metadados, "tipo de origem"), {"banco": "BANCO_DADOS", "api": "API_REST", "ftp": "ARQUIVO_FTP", "arquivo": "ARQUIVO_FTP", "file": "ARQUIVO_FTP", "nosql": "NOSQL", "mongo": "NOSQL", "sap": "SAP_ERP"}, "tipo de fonte"),
            "des_ambiente": _enum(_meta(metadados, "hospedagem"), {"hibrid": "HIBRIDO", "prodeb": "NUVEM_PRODEB", "aws": "NUVEM_AWS", "on-prem": "ON_PREMISE", "on prem": "ON_PREMISE", "local": "ON_PREMISE"}, "ambiente de hospedagem"),
            "des_metodo_autenticacao": _meta(metadados, "autenticacao") or pendente("método de autenticação"),
        },
        "governanca": governanca,
        "metadados_campos": metadados_campos,
        "regras_qualidade": derivar_regras_qualidade(campos),
        "linhagem_origem": [
            {
                "cod_linhagem": f"LIN_{cod}_{ferr}",
                "nom_objeto_origem": _meta(metadados, "nome da tabela") or pendente("objeto de origem"),
                "des_ferramenta_transporte": ferr,
                "nom_job_transporte": jobs[ferr],
                "nom_colecao_raw": f"raw_{cod_min}",
                "nom_colecao_trusted": f"trusted_{cod_min}",
                **({"nom_ativo_aws_sagemaker_catalog": cod_min} if ctx["aws"] else {}),
            }
            for ferr in ctx["ferramentas"]
        ],
    }


# ----------------------------------------------------------------------------
# Renderização dos artefatos
# ----------------------------------------------------------------------------
def extrair_script_referencia(nome_script: str) -> str:
    """Script oficial `// Script: <nome>` mantido nas referências da skill (fonte única)."""
    for doc in REFERENCIAS.glob("*.md"):
        for bloco in re.findall(r"```javascript\n(.*?)```", doc.read_text(encoding="utf-8"), re.DOTALL):
            if f"// Script: {nome_script}" in bloco:
                return bloco
    raise FileNotFoundError(f"Script de referência '{nome_script}' não encontrado em {REFERENCIAS}")


def extrair_json_referencia(marcador: str) -> dict:
    texto = (REFERENCIAS / "integracao_aws_sagemaker_glue.md").read_text(encoding="utf-8")
    for bloco in re.findall(r"```json\n(.*?)```", texto, re.DOTALL):
        if marcador in bloco:
            return json.loads(bloco)
    raise FileNotFoundError(f"Bloco JSON '{marcador}' não encontrado nas referências AWS")


def _js(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


def render_documento_dataset_js(doc: dict) -> str:
    return (
        f"// Script: 06_documento_tb_dataset_{doc['cod_dataset'].lower()}.js\n"
        "// Gerado pelo NINHO (/executar-governanca). Idempotente: atualiza o catálogo sem perder dth_cadastro.\n"
        "// Antes de executar, substitua todos os valores <INFORMAR: ...> (o $jsonSchema rejeita enums inválidos).\n\n"
        f"const doc = {_js(doc)};\n\n"
        "doc.dth_atualizacao = new Date();\n"
        "db.tb_dataset.updateOne(\n"
        "  { cod_dataset: doc.cod_dataset },\n"
        "  { $set: doc, $setOnInsert: { dth_cadastro: new Date() } },\n"
        "  { upsert: true }\n"
        ");\n"
    )


def render_colecao_trusted_js(cod: str, campos: list) -> str:
    colecao = f"trusted_{cod.lower()}"
    propriedades = {
        "_id": {"bsonType": ["objectId", "string"]},
        "sts_registro": {"enum": ["ATIVO", "INATIVO"]},
        "num_versao": {"bsonType": "string"},
        "dth_criacao": {"bsonType": "date"},
        "dth_atualizacao": {"bsonType": "date"},
        "cod_job_ingestao": {"bsonType": "string"},
    }
    obrigatorios = ["sts_registro", "dth_criacao", "cod_job_ingestao"]
    chaves = []
    for item in campos:
        classif = item["classificacao_lgpd"]
        descricao = item.get("descricao") or item["campo_origem"]
        if classif["ind_anonimizar"]:
            propriedades[item["campo_mongo"]] = {"bsonType": "string", "description": f"{descricao} — armazenar pseudonimizado (SHA-256 + SALT)"}
        else:
            propriedades[item["campo_mongo"]] = {"bsonType": item["tipo_bson"], "description": descricao}
        if _sim(item.get("obrigatorio_cliente")) or _sim(item.get("chave_cliente")):
            obrigatorios.append(item["campo_mongo"])
        if _sim(item.get("chave_cliente")):
            chaves.append(item["campo_mongo"])
    validador = {"$jsonSchema": {"bsonType": "object", "required": obrigatorios,
                                 "additionalProperties": False, "properties": propriedades}}
    linhas = [
        f"// Script: 07_colecao_{colecao}.js",
        "// Coleção TRUSTED (Silver) com validação estrita: só entram registros aprovados na Barreira de 4 Etapas.",
        "",
        f'db.createCollection("{colecao}", {{',
        f"  validator: {_js(validador)},",
        '  validationLevel: "strict",',
        '  validationAction: "error"',
        "});",
        "",
        f'db.{colecao}.createIndex({{ "dth_criacao": -1 }}, {{ name: "idx_{colecao}_dth_criacao" }});',
    ]
    if chaves:
        indice = ", ".join(f'"{c}": 1' for c in chaves)
        linhas.append(f'db.{colecao}.createIndex({{ {indice} }}, {{ unique: true, name: "uk_{colecao}_chave_negocio" }});')
    return "\n".join(linhas) + "\n"


def render_barreira_js(cod: str, regras: list) -> str:
    regras_exec = []
    for r in regras:
        campo = r.get("nom_campo_alvo")
        if not campo:
            continue
        if r["tip_dimensao_dama"] == "COMPLETUDE":
            filtro = f'{{ $or: [ {{ "{campo}": null }}, {{ "{campo}": "" }} ] }}'
        elif r["tip_dimensao_dama"] == "CONFORMIDADE":
            filtro = f'{{ "{campo}": {{ $exists: true, $not: /{r["des_expressao_validacao"]}/ }} }}'
        elif r["tip_dimensao_dama"] == "VALIDADE":
            filtro = f'{{ "{campo}": {{ $gt: new Date() }} }}'
        else:
            continue
        regras_exec.append(f'  {{ cod_regra: "{r["cod_regra"]}", filtro: {filtro}, motivo: {json.dumps(r["nom_regra"], ensure_ascii=False)} }}')
    return (
        f"// Script: 05_regras_barreira_quarentena_{cod.lower()}.js\n"
        "// Barreira de Qualidade (Etapa 3): move registros reprovados da RAW para a quarentena do dia,\n"
        "// com o motivo exato para devolução ao Data Owner. Registros reprovados NUNCA chegam à TRUSTED.\n"
        "// Pré-requisito: CPF/CNPJ/CEP higienizados (só dígitos) na RAW antes de rodar a barreira.\n\n"
        f'const COD_DATASET = "{cod}";\n'
        f'const colRaw = "raw_{cod.lower()}";\n'
        'const hoje = new Date().toISOString().slice(0, 10).replace(/-/g, "");\n'
        f'const colQuarentena = "tb_quarentena_{cod.lower()}_" + hoje;\n\n'
        "const regras = [\n" + ",\n".join(regras_exec) + "\n];\n\n"
        "let totalQuarentena = 0;\n"
        "regras.forEach((regra) => {\n"
        "  db.getCollection(colRaw).find(regra.filtro).forEach((registro) => {\n"
        "    db.getCollection(colQuarentena).insertOne({\n"
        "      cod_dataset: COD_DATASET,\n"
        "      dth_rejeicao: new Date(),\n"
        "      cod_regra_violada: regra.cod_regra,\n"
        "      des_motivo_devolucao_cliente: regra.motivo + \" — saneamento na origem é responsabilidade do órgão.\",\n"
        "      jsn_registro_original_bruto: registro\n"
        "    });\n"
        "    db.getCollection(colRaw).deleteOne({ _id: registro._id });\n"
        "    totalQuarentena += 1;\n"
        "  });\n"
        "});\n"
        'print(`Barreira concluída: ${totalQuarentena} registro(s) enviados para ${colQuarentena}.`);\n'
    )


def render_evento_auditoria_js(cod: str, resumo: str) -> str:
    evento = {
        "cod_evento": f"EVT_{cod}_CATALOGACAO",
        "cod_dataset": cod,
        "tip_categoria_evento": "ALTERACAO_METADADOS",
        "des_evento": resumo,
        "des_usuario_ou_job": "NINHO /executar-governanca",
    }
    return (
        f"// Script: 08_evento_auditoria_{cod.lower()}.js\n"
        "// Trilha de auditoria: registra a catalogação/atualização de metadados (retenção TTL de 5 anos).\n\n"
        f"const evento = {_js(evento)};\n"
        "evento.cod_evento = evento.cod_evento + \"_\" + Date.now();\n"
        "evento.dth_evento = new Date();\n"
        "db.tb_auditoria_eventos.insertOne(evento);\n"
    )


def montar_tabela_glue(doc: dict) -> dict:
    colunas = []
    for c in doc["metadados_campos"]:
        nivel = c["classificacao_lgpd"]["des_nivel_sensibilidade"]
        colunas.append({
            "Name": c["nom_campo_mongo"],
            "Type": TIPO_GLUE.get(c["tip_bson_mongo"], "string"),
            "Comment": f"[{nivel}] {c['des_campo']}"[:255],
            "Parameters": {"lgpd_nivel": nivel, "lgpd_anonimizar": str(c["classificacao_lgpd"]["ind_anonimizar"]).lower()},
        })
    return {
        "TableInput": {
            "Name": f"trusted_{doc['cod_dataset'].lower()}",
            "Description": doc["des_finalidade"],
            "TableType": "EXTERNAL_TABLE",
            "Parameters": {
                "classification": "mongodb",
                "cod_dataset": doc["cod_dataset"],
                "lgpd_nivel_global": doc["governanca"]["des_nivel_acesso_padrao"],
                "data_owner": doc["governanca"]["nom_titular_data_owner"],
            },
            "StorageDescriptor": {"Columns": colunas},
        }
    }


def montar_payload_ativo(doc: dict, ctx: dict) -> dict:
    lgpd = [c["classificacao_lgpd"] for c in doc["metadados_campos"]]
    bases = sorted({c["des_base_legal"] for c in lgpd if c["ind_dado_pessoal"]})
    return {
        "platform": "AMAZON_SAGEMAKER_UNIFIED_STUDIO_CATALOG",
        "assetName": f"trusted_{doc['cod_dataset'].lower()}",
        "domainUnit": ctx["sigla"] or pendente("sigla do órgão"),
        "formName": "FormGovernancaLgpdLaiBahia",
        "formValues": {
            "cod_dataset_prodeb": doc["cod_dataset"],
            "sig_orgao_proprietario": ctx["sigla"] or pendente("sigla do órgão"),
            "nom_data_owner_origem": doc["governanca"]["nom_titular_data_owner"],
            "des_nivel_sensibilidade_global": doc["governanca"]["des_nivel_acesso_padrao"],
            "des_grau_sigilo_lai": pendente("grau de sigilo LAI: OSTENSIVO/RESERVADO_5_ANOS/SECRETO_15_ANOS/ULTRASSECRETO_25_ANOS"),
            "ind_contem_dados_pessoais_lgpd": any(c["ind_dado_pessoal"] for c in lgpd),
            "ind_contem_dados_sensiveis_art11": any(c["ind_dado_sensivel"] for c in lgpd),
            "des_base_legal_lgpd": "; ".join(bases) or "Não se aplica (sem dados pessoais)",
            "sts_validacao_origem_cliente": "APROVADO_SEM_REGISTROS_VAZIOS",
        },
        "glossaryTerms": [c["nom_campo_mongo"] for c in doc["metadados_campos"]],
    }


SCRIPT_PUBLICACAO_AWS = '''#!/usr/bin/env python3
"""
Publica a tabela do dataset {cod} no AWS Glue Data Catalog (base do SageMaker Catalog).
Gerado pelo NINHO. Por padrão roda em DRY-RUN: só mostra o que faria. Use --aplicar para publicar.

Variáveis de ambiente: AWS_REGION, GLUE_DATABASE (credenciais AWS pelo perfil/role padrão do boto3).
"""
import argparse
import json
import os
from pathlib import Path

PASTA = Path(__file__).resolve().parent
TABELA = json.loads((PASTA / "glue_table_{cod_min}.json").read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--aplicar", action="store_true", help="Publica de fato (sem esta flag é dry-run).")
    args = parser.parse_args()
    database = os.environ.get("GLUE_DATABASE")
    if not database:
        raise SystemExit("Defina GLUE_DATABASE com o nome do database do Glue Catalog.")
    texto = json.dumps(TABELA, ensure_ascii=False)
    if "<INFORMAR" in texto:
        raise SystemExit("Há valores <INFORMAR: ...> pendentes em glue_table_{cod_min}.json. Corrija antes de publicar.")
    if not args.aplicar:
        print(f"[DRY-RUN] Publicaria {{TABELA['TableInput']['Name']}} em {{database}} "
              f"com {{len(TABELA['TableInput']['StorageDescriptor']['Columns'])}} colunas.")
        return 0

    import boto3

    glue = boto3.client("glue", region_name=os.environ.get("AWS_REGION"))
    try:
        glue.update_table(DatabaseName=database, **TABELA)
        print("Tabela atualizada no Glue Catalog.")
    except glue.exceptions.EntityNotFoundException:
        glue.create_table(DatabaseName=database, **TABELA)
        print("Tabela criada no Glue Catalog.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def gravar_matriz_csv(destino: Path, campos: list) -> None:
    cabecalho = [
        "campo_origem", "tipo_origem", "descricao", "campo_mongo", "tipo_bson", "nivel_lgpd",
        "dado_pessoal", "dado_sensivel", "anonimizar", "tecnica_anonimizacao", "base_legal",
        "cliente_sensivel", "cliente_anonimizar", "cliente_sensibilidade", "divergente_do_cliente",
    ]
    with destino.open("w", encoding="utf-8-sig", newline="") as arq:
        escritor = csv.writer(arq, delimiter=";")
        escritor.writerow(cabecalho)
        for item in campos:
            c = item["classificacao_lgpd"]
            escritor.writerow([
                item["campo_origem"], item.get("tipo_origem", ""), item.get("descricao", ""), item["campo_mongo"],
                item["tipo_bson"], c["des_nivel_sensibilidade"], c["ind_dado_pessoal"], c["ind_dado_sensivel"],
                c["ind_anonimizar"], c["des_tecnica_anonimizacao"], c["des_base_legal"],
                item.get("sensivel_cliente", ""), item.get("anonimizar_cliente", ""),
                item.get("sensibilidade_cliente", ""), c["divergente_do_cliente"],
            ])


def coletar_pendencias(*objetos) -> list:
    texto = "\n".join(json.dumps(o, ensure_ascii=False) for o in objetos)
    return sorted(set(re.findall(r"<INFORMAR: ([^>]+)>", texto)))


# Sugestões do Radar para tb_sem_conceitos (camada_semantica_mongodb.md): padrão no nome do campo
# -> (conceito canônico, domínio). São só sugestões para aprovação; nada é gravado no catálogo.
CONCEITOS_SUGERIDOS = [
    (r"(^|_)(cpf|rg|nis|nascimento|mae|filiacao|nome_social)($|_)", "CNC_CIDADAO", "DOM_CIDADANIA_IDENTIFICACAO"),
    (r"(^|_)(matricula|servidor|cargo|lotacao|pernr)($|_)", "CNC_SERVIDOR_PUBLICO", "DOM_GESTAO_PESSOAS_PREVIDENCIA"),
    (r"(^|_)(placa|renavam|chassi|cnh|renach)($|_)", "CNC_VEICULO_CONDUTOR", "DOM_MOBILIDADE_TRANSITO"),
    (r"(^|_)(cid|beneficiario|prontuario|deficiencia)($|_)", "CNC_BENEFICIARIO_SAUDE", "DOM_SAUDE_ASSISTENCIA"),
    (r"(^|_)(cnpj|fornecedor|empresa)($|_)", "CNC_PESSOA_JURIDICA", "—"),
    (r"(^|_)(municipio|ibge|cep|uf)($|_)", "CNC_LOCALIDADE", "—"),
]


def sugerir_conceitos(campos: list) -> dict:
    """{(conceito, domínio): [campos_mongo]} a partir do nome dos campos."""
    sugestoes: dict = {}
    for item in campos:
        for padrao, conceito, dominio in CONCEITOS_SUGERIDOS:
            if re.search(padrao, item["campo_mongo"]):
                sugestoes.setdefault((conceito, dominio), []).append(item["campo_mongo"])
                break
    return sugestoes


def render_relatorio(ctx: dict, campos: list, artefatos: list, pendencias: list, avisos: list) -> str:
    por_nivel = {n: sum(1 for c in campos if c["classificacao_lgpd"]["des_nivel_sensibilidade"] == n) for n in NIVEIS}
    divergentes = [c["campo_origem"] for c in campos if c["classificacao_lgpd"]["divergente_do_cliente"]]
    restritos = [c["campo_mongo"] for c in campos if c["classificacao_lgpd"]["des_nivel_sensibilidade"] == "RESTRITO"]
    pessoais_sem_anon = [
        c["campo_mongo"] for c in campos
        if c["classificacao_lgpd"]["des_nivel_sensibilidade"] == "CONFIDENCIAL" and not c["classificacao_lgpd"]["ind_anonimizar"]
    ]
    linhas = [
        f"# Relatório de Governança — `{ctx['cod_dataset'] or 'DATASET SEM CÓDIGO'}`",
        "",
        f"- **Gerado em:** {datetime.now().strftime('%Y-%m-%d %H:%M')} pelo `/executar-governanca`",
        f"- **Órgão:** {ctx['sigla'] or '—'} · **Data Owner:** {ctx['data_owner'] or '—'} · **Data Steward:** {ctx['data_steward'] or '—'}",
        f"- **Tecnologias no Intake:** MongoDB {'✅' if ctx['mongo'] else '—'} · AWS SageMaker/Glue {'✅' if ctx['aws'] else '—'}"
        f" · Transporte: {', '.join(ctx['ferramentas']) or '—'}",
        "",
        "## Classificação LGPD dos campos",
        "",
        "| Nível | Campos |",
        "| --- | ---: |",
        *[f"| `{n}` | {por_nivel[n]} |" for n in NIVEIS],
        "",
    ]
    if avisos:
        linhas += ["## Avisos", "", *[f"- ⚠️ {a}" for a in avisos], ""]
    if pendencias:
        linhas += [
            "## Pendências do engenheiro antes do deploy",
            "",
            "Os artefatos contêm `<INFORMAR: ...>` nestes pontos. O `$jsonSchema` e o `validar_entrega.py saida` rejeitam até serem preenchidos:",
            "",
            *[f"- [ ] {p}" for p in pendencias],
            "",
        ]
    linhas += ["## 💡 Radar Consultivo da IA", ""]
    if divergentes:
        linhas.append(f"- Campos com classificação do cliente abaixo da detectada (retificar com o Data Owner): {', '.join(divergentes)}.")
    if restritos:
        linhas.append(f"- Campos RESTRITOS (Art. 11) exigem Termo de Compartilhamento `TC_*` e anonimização no transporte: {', '.join(restritos)}.")
    if pessoais_sem_anon:
        linhas.append(f"- Dados pessoais sem anonimização declarada; avaliar pseudonimização SHA-256 para consumo analítico: {', '.join(pessoais_sem_anon)}.")
    if not (divergentes or restritos or pessoais_sem_anon):
        linhas.append("- Nenhum risco LGPD adicional identificado além do declarado pelo cliente.")
    conceitos = sugerir_conceitos(campos)
    if conceitos:
        linhas += [
            "",
            "### Conceitos canônicos sugeridos para `tb_sem_conceitos` (aprovar antes de cadastrar)",
            "",
            "| Conceito | Domínio | Campos do dataset |",
            "| --- | --- | --- |",
            *[f"| `{c}` | `{d}` | {', '.join(f'`{x}`' for x in cs)} |" for (c, d), cs in conceitos.items()],
        ]
    linhas += ["", "## Artefatos gerados", "", *[f"- `{a}`" for a in artefatos], ""]
    return "\n".join(linhas)


# ----------------------------------------------------------------------------
# Orquestração
# ----------------------------------------------------------------------------
def _rel(caminho: Path) -> str:
    try:
        return caminho.relative_to(BASE_DIR).as_posix()
    except ValueError:
        return caminho.as_posix()


def _gravar(caminho: Path, conteudo: str, artefatos: list) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(conteudo, encoding="utf-8")
    artefatos.append(_rel(caminho))


def executar(alvo: Path, intake: Path, saida: Path = SAIDA_GOV, simular: bool = False) -> dict:
    """
    Executa a esteira. Com `simular=True` (/simular-governanca) roda o Gate 0.5 e a classificação,
    grava só o relatório (prévia) e a matriz LGPD, e não gera scripts MongoDB nem artefatos AWS.
    """
    if simular:
        ctx_original = ler_intake(intake)
        resultado = _executar(alvo, intake, saida, ctx_forcado={**ctx_original, "mongo": False, "aws": False})
        if resultado["status"] == "GERADO":
            resultado["status"] = "SIMULADO"
            resultado["avisos"] = [
                a for a in resultado.get("avisos", []) if "Nenhuma tecnologia marcada" not in a
            ] + ["Simulação: scripts MongoDB e AWS não foram gravados. Rode /executar-governanca para gerá-los."]
        return resultado
    return _executar(alvo, intake, saida)


def _executar(alvo: Path, intake: Path, saida: Path, ctx_forcado: dict | None = None) -> dict:
    resultados = gate.executar_inspecao(alvo) if alvo.exists() else []
    if not resultados:
        return {"status": "SEM_INSUMOS", "codigo_saida": 0, "artefatos": [],
                "mensagem": f"Nenhum insumo encontrado em {alvo}. Deposite a planilha (.xlsx/.ods) e amostras (.csv)."}

    ctx = ctx_forcado or ler_intake(intake)
    artefatos: list = []
    total_bloqueios = sum(len(r["bloqueios_devolucao"]) for r in resultados)
    if total_bloqueios:
        orgao = ctx["sigla"] or "CLIENTE"
        _gravar(saida / f"relatorio_devolucao_cliente_{orgao}.md", gate.gerar_markdown_relatorio(resultados), artefatos)
        return {"status": "DEVOLVIDO_AO_CLIENTE", "codigo_saida": 1, "artefatos": artefatos,
                "total_bloqueios": total_bloqueios}

    campos = montar_campos(resultados)
    metadados = {}
    for r in resultados:
        metadados.update(r.get("metadados_insumos", {}))
    avisos = []
    cod = ctx["cod_dataset"]
    if not cod or not PADRAO_COD_DATASET.match(cod):
        avisos.append(
            "Gate 0: preencha a Seção 0 do INTAKE_GOVERNANCA.md (código SIGLA_ORGAO_UNIDADE_TEMA_VERSAO). "
            "Sem ele, só o relatório e a matriz LGPD foram gerados."
        )
        ctx["cod_dataset"] = ""
    if not (ctx["mongo"] or ctx["aws"]):
        avisos.append("Nenhuma tecnologia marcada na Seção 1 do Intake: scripts MongoDB e AWS não foram gerados (geração condicional).")

    sufixo = (ctx["cod_dataset"] or "SEM_CODIGO").lower()
    matriz = saida / f"matriz_de_para_lgpd_{sufixo}.csv"
    matriz.parent.mkdir(parents=True, exist_ok=True)
    gravar_matriz_csv(matriz, campos)
    artefatos.append(_rel(matriz))

    pendencias = []
    if ctx["cod_dataset"] and campos:
        doc = montar_documento_dataset(ctx, metadados, campos)
        pendencias = coletar_pendencias(doc)
        if ctx["mongo"]:
            pasta = saida / "schemas_mongo"
            for nome in ("01_schema_tb_dataset.js", "02_schema_tb_sem_dominios.js",
                         "03_schema_tb_sem_conceitos.js", "04_schema_tb_auditoria_eventos.js"):
                _gravar(pasta / nome, extrair_script_referencia(nome), artefatos)
            _gravar(pasta / f"05_regras_barreira_quarentena_{sufixo}.js", render_barreira_js(cod, doc["regras_qualidade"]), artefatos)
            _gravar(pasta / f"06_documento_tb_dataset_{sufixo}.js", render_documento_dataset_js(doc), artefatos)
            _gravar(pasta / f"07_colecao_trusted_{sufixo}.js", render_colecao_trusted_js(cod, campos), artefatos)
            _gravar(pasta / f"08_evento_auditoria_{sufixo}.js",
                    render_evento_auditoria_js(cod, f"Catalogação de {len(campos)} campos gerada pelo NINHO."), artefatos)
        if ctx["aws"]:
            pasta = saida / "aws_sagemaker_catalog"
            tabela = montar_tabela_glue(doc)
            payload = montar_payload_ativo(doc, ctx)
            pendencias = coletar_pendencias(doc, payload)
            _gravar(pasta / "form_lgpd_lai_sagemaker.json", _js(extrair_json_referencia("FormGovernancaLgpdLaiBahia")), artefatos)
            _gravar(pasta / f"asset_payload_{sufixo}.json", _js(payload), artefatos)
            _gravar(pasta / f"glue_table_{sufixo}.json", _js(tabela), artefatos)
            _gravar(pasta / f"publicar_catalogo_{sufixo}.py",
                    SCRIPT_PUBLICACAO_AWS.format(cod=cod, cod_min=sufixo), artefatos)

    relatorio = saida / f"relatorio_governanca_{sufixo}.md"
    artefatos.append(_rel(relatorio))
    _gravar(relatorio, render_relatorio(ctx, campos, artefatos, pendencias, avisos), [])
    return {
        "status": "GERADO" if ctx["cod_dataset"] else "GATE_0_PENDENTE",
        "codigo_saida": 0 if ctx["cod_dataset"] else 2,
        "artefatos": artefatos,
        "pendencias": pendencias,
        "avisos": avisos,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Esteira de Governança: Gate 0.5 + MongoDB PRODEB + AWS SageMaker/Glue.")
    parser.add_argument("caminho", nargs="?", default=str(ENTREGA_DIR / "governanca_dados"),
                        help="Arquivo ou pasta de insumos (padrão: entrega/governanca_dados/).")
    parser.add_argument("--intake", default=str(INTAKE_PADRAO), help="Caminho do INTAKE_GOVERNANCA.md.")
    parser.add_argument("--json", action="store_true", help="Imprime o resultado em JSON.")
    parser.add_argument("--simular", action="store_true", help="Prévia: Gate 0.5 + classificação LGPD, sem gravar scripts MongoDB/AWS.")
    args = parser.parse_args()

    resultado = executar(Path(args.caminho), Path(args.intake), simular=args.simular)
    if args.json:
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
        return resultado["codigo_saida"]

    titulos = {
        "SEM_INSUMOS": "ℹ️  Nenhum insumo de governança encontrado",
        "DEVOLVIDO_AO_CLIENTE": "❌ Gate 0.5 REPROVADO — insumos devolvidos ao cliente",
        "GATE_0_PENDENTE": "🟡 Gate 0 pendente — Intake sem código de dataset",
        "GERADO": "✅ Artefatos de governança gerados",
        "SIMULADO": "🧪 Simulação de governança concluída (prévia, sem scripts MongoDB/AWS)",
    }
    print(f"# {titulos[resultado['status']]}\n")
    if resultado.get("mensagem"):
        print(resultado["mensagem"])
    for aviso in resultado.get("avisos", []):
        print(f"- ⚠️ {aviso}")
    if resultado.get("pendencias"):
        print(f"- 📝 {len(resultado['pendencias'])} pendência(s) <INFORMAR> para o engenheiro (ver relatório).")
    for artefato in resultado["artefatos"]:
        print(f"- `{artefato}`")
    print(
        "\n### 🧭 O que você pode fazer agora:\n"
        "- `/inspecionar-governanca` — ver o detalhe da auditoria do Gate 0.5\n"
        "- `/validar-entrega saida` — auditar os artefatos gerados (inclui pendências <INFORMAR>)\n"
        "- `/onde-estou` — ver o progresso do projeto"
    )
    return resultado["codigo_saida"]


if __name__ == "__main__":
    sys.exit(main())
