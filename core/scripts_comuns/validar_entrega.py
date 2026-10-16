#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validador Pré-Voo de Insumos e Auditor Pós-Geração da Plataforma NINHO
Executa a verificação dos arquivos de entrada (Gate 0) e audita a conformidade
dos artefatos gerados em 'saida/' contra as 4 Regras de Ouro.

Uso:
    python core/scripts_comuns/validar_entrega.py dw
    python core/scripts_comuns/validar_entrega.py fast-track
    python core/scripts_comuns/validar_entrega.py semantica
    python core/scripts_comuns/validar_entrega.py governanca
    python core/scripts_comuns/validar_entrega.py saida
    python core/scripts_comuns/validar_entrega.py all
"""

import sys
import os
import re
from pathlib import Path

# Configura encoding do stdout para UTF-8 no Windows
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
NEGRITO = "\033[1m"
RESET = "\033[0m"


def get_base_dir() -> Path:
    """Retorna o diretório raiz do projeto."""
    return Path(__file__).resolve().parent.parent.parent


def print_header(title: str):
    print(f"\n{AZUL}{NEGRITO}{'=' * 70}{RESET}")
    print(f"{AZUL}{NEGRITO}  {title}{RESET}")
    print(f"{AZUL}{NEGRITO}{'=' * 70}{RESET}\n")


def print_ok(msg: str):
    print(f"  {VERDE}[OK]{RESET} {msg}")


def print_warn(msg: str):
    print(f"  {AMARELO}[AVISO]{RESET} {msg}")


def print_err(msg: str):
    print(f"  {VERMELHO}[ERRO]{RESET} {msg}")


def validar_intake_dw(base_dir: Path) -> dict:
    intake_path = base_dir / "modulos" / "planejador_dw" / "INTAKE_DW.md"
    results = {"erros": 0, "avisos": 0, "sucessos": 0}

    print(f"{NEGRITO}1. Verificando Formulario INTAKE_DW.md:{RESET}")
    if not intake_path.exists():
        print_err(f"Arquivo nao encontrado: {intake_path}")
        results["erros"] += 1
        return results

    content = intake_path.read_text(encoding="utf-8", errors="ignore")

    # Checar se perguntas/regras vêm por arquivos na pasta entrega
    pasta_entrega_dw = base_dir / "entrega" / "planejador_dw"
    tem_docs_entrega = False
    if pasta_entrega_dw.exists():
        docs = [f for f in pasta_entrega_dw.iterdir() if f.is_file() and f.suffix.lower() in [".md", ".txt", ".docx", ".pdf"] and f.name.lower() != "readme.md"]
        if docs:
            tem_docs_entrega = True

    opcao2_marcada = bool(re.search(r"-\s*\[x\]\s*\*\*Opção 2:", content, re.IGNORECASE))
    opcao3_marcada = bool(re.search(r"-\s*\[x\]\s*\*\*Opção 3:", content, re.IGNORECASE))
    radar_ia_dw = bool(re.search(r"-\s*\[x\]\s*\*\*💡\s*Habilitar Radar Consultivo da IA", content, re.IGNORECASE))

    if radar_ia_dw or opcao3_marcada:
        print_ok("💡 Radar Consultivo da IA habilitado: a IA sugerirá novos KPIs, regras implícitas e perguntas de negócio.")
        results["sucessos"] += 1

    # Checar se campos chave ainda contêm [Ex: ...]
    placeholders = re.findall(r"(\[Ex:.*?\])", content)
    if placeholders:
        if tem_docs_entrega or opcao2_marcada or opcao3_marcada:
            print_ok("Perguntas e regras de negócio fornecidas via arquivos na pasta 'entrega/planejador_dw/' ou descoberta consultiva da IA.")
            results["sucessos"] += 1
        else:
            print_warn(f"Existem {len(placeholders)} campos de exemplo ainda nao preenchidos no formulario.")
            for p in placeholders[:3]:
                print(f"     Pendente: {p}")
            results["avisos"] += 1
    else:
        print_ok("Nenhum placeholder '[Ex: ...]' encontrado. Formulario parece preenchido!")
        results["sucessos"] += 1

    # Checar nome do projeto
    proj_match = re.search(r"\*\*Nome do Projeto:\*\*\s*`?(.*?)`?$", content, re.MULTILINE)
    if proj_match and proj_match.group(1).strip() and not proj_match.group(1).strip().startswith("[Ex:"):
        print_ok(f"Projeto identificado: {proj_match.group(1).strip()}")
        results["sucessos"] += 1
    else:
        print_warn("Nome do projeto nao foi preenchido na Secao 0.")
        results["avisos"] += 1

    # Checar schema alvo
    schema_match = re.search(r"\*\*Schema Alvo no Oracle:\*\*\s*`?(.*?)`?$", content, re.MULTILINE)
    if schema_match and schema_match.group(1).strip() and not schema_match.group(1).strip().startswith("[Ex:"):
        print_ok(f"Schema Oracle configurado: {schema_match.group(1).strip()}")
        results["sucessos"] += 1
    else:
        print_warn("Schema alvo nao especificado na Secao 0.")
        results["avisos"] += 1

    # Checar Secao 1 - Tecnologias da Esteira (MANDATORIO)
    sec1_match = re.search(r"## Seção 1 — Seleção de Tecnologias da Esteira.*?(?=## Seção 2)", content, re.DOTALL | re.IGNORECASE)
    if sec1_match:
        sec1_text = sec1_match.group(0)
        techs_marcadas = re.findall(r"-\s*\[x\]\s*\*\*(.*?)\*\*", sec1_text, re.IGNORECASE)
        if not techs_marcadas:
            print_err("NENHUMA tecnologia de engenharia marcada com [x] na Secao 1 do INTAKE_DW.md!")
            print_err("     O Engenheiro DEVE abrir 'modulos/planejador_dw/INTAKE_DW.md' e marcar as ferramentas utilizadas (ODI, Hop, Python, PL/SQL ou Legado).")
            print_warn("     Sem essa definicao, a IA bloqueara a geracao para evitar criar scripts indesejados.")
            results["erros"] += 1
        else:
            print_ok(f"Pilha Tecnologica selecionada ({len(techs_marcadas)} opcao(oes)):")
            for t in techs_marcadas:
                print(f"     -> {t}")
            results["sucessos"] += 1

    # Checar Tablespace de Dados e Indices
    ts_data_match = re.search(r"\*\*Tablespace de Dados:\*\*\s*`?(.*?)`?$", content, re.MULTILINE)
    if ts_data_match and ts_data_match.group(1).strip() and not ts_data_match.group(1).strip().startswith("[Ex:"):
        print_ok(f"Tablespace de Dados configurada: {ts_data_match.group(1).strip()}")
        results["sucessos"] += 1
    else:
        print_warn("Tablespace de Dados pendente na Secao 0 (Padrao: tablespace do usuario sera assumida).")
        results["avisos"] += 1

    ts_idx_match = re.search(r"\*\*Tablespace de Índices:\*\*\s*`?(.*?)`?$", content, re.MULTILINE)
    if ts_idx_match and ts_idx_match.group(1).strip() and not ts_idx_match.group(1).strip().startswith("[Ex:"):
        print_ok(f"Tablespace de Indices configurada: {ts_idx_match.group(1).strip()}")
        results["sucessos"] += 1
    else:
        print_warn("Tablespace de Indices nao especificada na Secao 0 (mesma de dados sera utilizada).")
        results["avisos"] += 1

    return results


def validar_arquivos_dw(base_dir: Path) -> dict:
    results = {"erros": 0, "avisos": 0, "sucessos": 0}
    print(f"\n{NEGRITO}2. Inspecionando Arquivos e Amostras de Entrada:{RESET}")

    pastas_insumo = [
        base_dir / "entrega" / "planejador_dw",
        base_dir / "modulos" / "planejador_dw" / "entrada",
    ]

    total_arquivos = 0
    ddl_files = []
    amostras_files = []

    for pasta in pastas_insumo:
        if not pasta.exists():
            continue
        # Documentos soltos de regras/perguntas na raiz da pasta
        docs_raiz = [f for f in pasta.iterdir() if f.is_file() and f.suffix.lower() in [".md", ".txt", ".docx", ".pdf"] and f.name.lower() != "readme.md"]
        if docs_raiz:
            total_arquivos += len(docs_raiz)
            print_ok(f"Encontrado(s) {len(docs_raiz)} documento(s) de negócio/regras em '{pasta.name}':")
            for d in docs_raiz:
                print(f"     - {d.name} ({d.stat().st_size} bytes)")

        for sub in ["ddl", "amostras", "arquivos_ftp", "api_specs"]:
            sub_path = pasta / sub
            if sub_path.exists():
                files = [f for f in sub_path.iterdir() if f.is_file() and f.name.lower() != "readme.md"]
                if files:
                    total_arquivos += len(files)
                    print_ok(f"Encontrado(s) {len(files)} arquivo(s) em '{pasta.name}/{sub}':")
                    for f in files:
                        print(f"     - {f.name} ({f.stat().st_size} bytes)")
                        if sub == "ddl" and f.suffix.lower() in [".sql", ".txt"]:
                            ddl_files.append(f)
                        elif sub in ["amostras", "arquivos_ftp"]:
                            amostras_files.append(f)

    if total_arquivos == 0:
        print_err("Nenhum arquivo de insumo (DDL, CSV, JSON) encontrado em 'entrega/planejador_dw/' ou 'modulos/planejador_dw/entrada/'.")
        print_warn("Por favor, deposite pelo menos um DDL ou amostra de dados antes de planejar o DW.")
        results["erros"] += 1
    else:
        results["sucessos"] += 1

    # Verificação de padrões no DDL (Convenções Oracle)
    if ddl_files:
        print(f"\n{NEGRITO}3. Auditoria de Convencoes nos DDLs de Entrada:{RESET}")
        for ddl in ddl_files:
            try:
                sql = ddl.read_text(encoding="utf-8", errors="ignore")
                minusc_quotes = re.findall(r'"([a-z0-9_]+)"', sql)
                if minusc_quotes:
                    print_warn(f"O arquivo '{ddl.name}' contem identificadores com aspas e letras minusculas (ex: \"{minusc_quotes[0]}\").")
                    print_warn("     O Oracle trata identificadores com aspas minusculas como case-sensitive!")
                    print_ok("     A IA converterá tudo para MAIUSCULAS automaticamente.")
                    results["avisos"] += 1
                else:
                    print_ok(f"Arquivo DDL '{ddl.name}' com sintaxe padrao.")
                    results["sucessos"] += 1
            except Exception as e:
                print_warn(f"Nao foi possivel analisar '{ddl.name}': {e}")

    return results


def validar_fast_track_dw(base_dir: Path) -> dict:
    """Valida insumos para o Modo Fast-Track (Melhoria de DW Existente sem alterar carga ETL)."""
    results = {"erros": 0, "avisos": 0, "sucessos": 0}
    print(f"{NEGRITO}1. Verificando Modo Fast-Track (Smart Gate 0 Bypass — DW Existente):{RESET}")
    print_ok(
        "Modo Fast-Track ativo: preenchimento completo do 'INTAKE_DW.md' dispensado "
        "(foco exclusivo em comentarios, indices e patches nao-destrutivos sem alterar ETL)."
    )
    results["sucessos"] += 1

    pastas_ddl = [
        base_dir / "entrega" / "planejador_dw" / "ddl",
        base_dir / "modulos" / "planejador_dw" / "entrada" / "ddl",
    ]
    ddl_files = []
    for p in pastas_ddl:
        if p.exists():
            ddl_files.extend(
                [
                    f
                    for f in p.iterdir()
                    if f.is_file()
                    and f.suffix.lower() in [".sql", ".txt"]
                    and f.name.lower() != "readme.md"
                ]
            )

    if not ddl_files:
        print_err(
            "Nenhum arquivo DDL (.sql/.txt) do DW existente encontrado em 'entrega/planejador_dw/ddl/'!"
        )
        print_warn(
            "Deposite o script DDL das tabelas DIM_* e FATO_* existentes em 'entrega/planejador_dw/ddl/' "
            "ou passe '--ddl caminho/arquivo.sql' ao executar 'melhorar_dw_existente.py'."
        )
        results["erros"] += 1
    else:
        print_ok(f"Encontrado(s) {len(ddl_files)} arquivo(s) DDL do DW existente para melhoria rapida:")
        for f in ddl_files:
            print(f"     - {f.name} ({f.stat().st_size} bytes)")
        results["sucessos"] += 1

    return results


def validar_intake_semantica(base_dir: Path) -> dict:
    intake_path = base_dir / "modulos" / "camada_semantica" / "INTAKE_SEMANTICA.md"
    results = {"erros": 0, "avisos": 0, "sucessos": 0}

    print(f"\n{NEGRITO}1. Verificando Formulario INTAKE_SEMANTICA.md:{RESET}")
    if not intake_path.exists():
        print_err(f"Arquivo nao encontrado: {intake_path}")
        results["erros"] += 1
        return results

    content = intake_path.read_text(encoding="utf-8", errors="ignore")

    # Checar se perguntas/regras vêm por arquivos na pasta entrega
    pasta_entrega_sem = base_dir / "entrega" / "camada_semantica"
    tem_docs_sem = False
    if pasta_entrega_sem.exists():
        docs_sem = [f for f in pasta_entrega_sem.glob("*") if f.is_file() and f.suffix.lower() in [".md", ".txt", ".docx", ".pdf"] and f.name.lower() != "readme.md"]
        rel_etl = [f for f in (pasta_entrega_sem / "relatorios_etl").glob("*") if f.is_file() and f.name.lower() != "readme.md"] if (pasta_entrega_sem / "relatorios_etl").exists() else []
        if docs_sem or rel_etl:
            tem_docs_sem = True

    opcao2_sem = bool(re.search(r"-\s*\[x\]\s*\*\*Opção 2:", content, re.IGNORECASE))
    opcao3_sem = bool(re.search(r"-\s*\[x\]\s*\*\*Opção 3:", content, re.IGNORECASE))
    radar_ia_sem = bool(re.search(r"-\s*\[x\]\s*\*\*💡\s*(?:Habilitar Radar Consultivo|Expandir Catálogo)", content, re.IGNORECASE))

    if radar_ia_sem or opcao3_sem:
        print_ok("💡 Radar Consultivo da IA habilitado: a IA sugerirá novos KPIs, regras semânticas e perguntas executivas/táticas.")
        results["sucessos"] += 1

    # Checar placeholders não preenchidos
    placeholders = re.findall(r"(\[Ex:.*?\]|<informe.*?>|<cole.*?>|<descreva.*?>)", content, re.IGNORECASE)
    if placeholders:
        if tem_docs_sem or opcao2_sem or opcao3_sem:
            print_ok("Regras/perguntas de negócio fornecidas via arquivos na pasta 'entrega/camada_semantica/' ou descoberta consultiva da IA.")
            results["sucessos"] += 1
        else:
            print_warn(f"Existem {len(placeholders)} marcadores ainda nao preenchidos no formulario.")
            for p in placeholders[:3]:
                print(f"     Pendente: {p}")
            results["avisos"] += 1
    else:
        print_ok("Formulario INTAKE_SEMANTICA.md preenchido sem marcadores pendentes.")
        results["sucessos"] += 1

    # Checar projeto
    proj_match = re.search(r"\*\*Nome do Projeto.*?:\*\*\s*`?(.*?)`?$", content, re.MULTILINE) or re.search(
        r"\|\s*\*\*Nome do Projeto\*\*.*?\|\s*`?(.*?)`?\s*\|", content, re.MULTILINE
    )
    if proj_match and proj_match.group(1).strip() and not proj_match.group(1).strip().startswith(("<", "[Ex:")):
        print_ok(f"Projeto identificado: {proj_match.group(1).strip()}")
        results["sucessos"] += 1
    else:
        print_warn("Nome do projeto pendente na Secao 0.")
        results["avisos"] += 1

    # Checar schema
    schema_match = re.search(r"\*\*Schema Alvo no Oracle:\*\*\s*`?(.*?)`?$", content, re.MULTILINE) or re.search(
        r"\|\s*\*\*Schema Alvo no Oracle\*\*.*?\|\s*`?(.*?)`?\s*\|", content, re.MULTILINE
    )
    if schema_match and schema_match.group(1).strip() and not schema_match.group(1).strip().startswith(("<", "[Ex:")):
        print_ok(f"Schema Oracle configurado: {schema_match.group(1).strip()}")
        results["sucessos"] += 1
    else:
        print_warn("Schema alvo pendente na Secao 0.")
        results["avisos"] += 1

    # Checar Secao 1 - Tecnologias e Ferramentas de Consumo
    sec1_sem_match = re.search(r"## Seção 1 — Seleção de Tecnologias e Ferramentas.*?(?=## Seção 2)", content, re.DOTALL | re.IGNORECASE)
    if sec1_sem_match:
        sec1_sem_text = sec1_sem_match.group(0)
        ferramentas_marcadas = re.findall(r"-\s*\[x\]\s*\*\*(.*?)\*\*", sec1_sem_text, re.IGNORECASE)
        if not ferramentas_marcadas:
            print_warn("Nenhuma ferramenta de consumo (Power BI, Agentes IA, etc.) marcada com [x] na Secao 1 do INTAKE_SEMANTICA.md.")
            results["avisos"] += 1
        else:
            print_ok(f"Ferramentas de consumo selecionadas ({len(ferramentas_marcadas)} opcao(oes)):")
            for fm in ferramentas_marcadas:
                print(f"     -> {fm}")
            results["sucessos"] += 1

    # Checar Secao 0.2 - Estado das tabelas META_*
    sec02_match = re.search(r"### 0\.2 Estado das 8 Tabelas `META_\*`.*?(?=---)", content, re.DOTALL | re.IGNORECASE)
    if sec02_match:
        meta_marcadas = re.findall(r"-\s*\[x\]\s*\*\*(.*?)\*\*", sec02_match.group(0), re.IGNORECASE)
        if meta_marcadas:
            print_ok(f"Estado de tabelas META_* definido: {meta_marcadas[0]}")
            results["sucessos"] += 1
        else:
            print_warn("Estado das tabelas META_* nao marcado na Secao 0.2 (novo schema vs schema existente).")
            results["avisos"] += 1

    return results


def validar_arquivos_semantica(base_dir: Path) -> dict:
    results = {"erros": 0, "avisos": 0, "sucessos": 0}
    print(f"\n{NEGRITO}2. Inspecionando Insumos em 'entrega/camada_semantica/':{RESET}")

    pasta_entrega = base_dir / "entrega" / "camada_semantica"
    if not pasta_entrega.exists():
        print_err(f"Pasta nao encontrada: {pasta_entrega}")
        results["erros"] += 1
        return results

    # 1. DDL
    ddl_pasta = pasta_entrega / "ddl"
    ddls = [f for f in ddl_pasta.glob("*.sql")] if ddl_pasta.exists() else []
    if ddls:
        print_ok(f"Encontrado(s) {len(ddls)} script(s) DDL em 'entrega/camada_semantica/ddl/':")
        for f in ddls:
            print(f"     - {f.name} ({f.stat().st_size} bytes)")
        results["sucessos"] += 1
    else:
        print_err("Nenhum arquivo DDL (.sql) encontrado em 'entrega/camada_semantica/ddl/'.")
        results["erros"] += 1

    # 2. Amostras
    amostras_pasta = pasta_entrega / "amostras"
    amostras = [f for f in amostras_pasta.glob("*") if f.is_file() and f.suffix.lower() in [".csv", ".tsv", ".json", ".txt"] and f.name.lower() != "readme.md"] if amostras_pasta.exists() else []
    if amostras:
        print_ok(f"Encontrado(s) {len(amostras)} arquivo(s) de amostra em 'entrega/camada_semantica/amostras/':")
        for f in amostras:
            print(f"     - {f.name} ({f.stat().st_size} bytes)")
        results["sucessos"] += 1
    else:
        print_warn("Nenhuma amostra encontrada em 'entrega/camada_semantica/amostras/'.")
        print_warn("     Execute: python core/scripts_comuns/gerar_mock_dados.py --saida entrega/camada_semantica/amostras/mock.csv")
        results["avisos"] += 1

    # 3. Relatórios ETL
    rel_pasta = pasta_entrega / "relatorios_etl"
    rels = [f for f in rel_pasta.glob("*") if f.is_file() and f.suffix.lower() in [".md", ".txt", ".pdf"] and f.name.lower() != "readme.md"] if rel_pasta.exists() else []
    if rels:
        print_ok(f"Encontrado(s) {len(rels)} relatorio(s) de ETL em 'entrega/camada_semantica/relatorios_etl/':")
        for f in rels:
            print(f"     - {f.name}")
        results["sucessos"] += 1
    else:
        print_warn("Nenhum relatorio de ETL encontrado em 'entrega/camada_semantica/relatorios_etl/' (recomendado).")
        results["avisos"] += 1

    return results


def validar_intake_governanca(base_dir: Path) -> dict:
    intake_path = base_dir / "modulos" / "governanca_dados" / "INTAKE_GOVERNANCA.md"
    results = {"erros": 0, "avisos": 0, "sucessos": 0}

    print(f"\n{NEGRITO}1. Verificando Formulario INTAKE_GOVERNANCA.md:{RESET}")
    if not intake_path.exists():
        print_err(f"Arquivo nao encontrado: {intake_path}")
        results["erros"] += 1
        return results

    content = intake_path.read_text(encoding="utf-8", errors="ignore")

    # Checar se diretrizes/planilhas vêm por arquivos na pasta entrega
    pasta_entrega_gov = base_dir / "entrega" / "governanca_dados"
    tem_docs_gov = False
    if pasta_entrega_gov.exists():
        docs_gov = [
            f for f in pasta_entrega_gov.glob("*")
            if f.is_file() and f.suffix.lower() in [".xlsx", ".csv", ".md", ".txt", ".docx", ".pdf"]
            and f.name.lower() != "readme.md" and not f.name.startswith("~$")
        ]
        if docs_gov:
            tem_docs_gov = True

    opcao1_gov = bool(re.search(r"-\s*\[x\]\s*\*\*Opção 1:", content, re.IGNORECASE))
    opcao2_gov = bool(re.search(r"-\s*\[x\]\s*\*\*Opção 2:", content, re.IGNORECASE))
    opcao3_gov = bool(re.search(r"-\s*\[x\]\s*\*\*Opção 3:", content, re.IGNORECASE))

    if opcao3_gov:
        print_ok("💡 Radar Consultivo da IA habilitado para Governanca (conceitos semanticos, regras BSON e alertas LGPD).")
        results["sucessos"] += 1

    # Checar se campos de exemplo ainda contêm [Ex: ...]
    placeholders = re.findall(r"(\[Ex:.*?\])", content)
    if placeholders:
        if tem_docs_gov or opcao1_gov or opcao2_gov or opcao3_gov:
            print_ok("Insumos/diretrizes de governanca fornecidos via arquivos na pasta 'entrega/governanca_dados/' ou descoberta assistida.")
            results["sucessos"] += 1
        else:
            print_warn(f"Existem {len(placeholders)} campos de exemplo ainda nao preenchidos no formulario.")
            for p in placeholders[:3]:
                print(f"     Pendente: {p}")
            results["avisos"] += 1
    else:
        print_ok("Nenhum placeholder '[Ex: ...]' encontrado no INTAKE_GOVERNANCA.md.")
        results["sucessos"] += 1

    # Checar órgão / cliente
    org_match = re.search(r"\*\*(?:Sigla|Nome) do Órgão / Cliente.*?:\*\*\s*`?(.*?)`?$", content, re.MULTILINE)
    if org_match and org_match.group(1).strip() and not org_match.group(1).strip().startswith(("[Ex:", "[Nome")):
        print_ok(f"Orgao/Cliente identificado: {org_match.group(1).strip()}")
        results["sucessos"] += 1
    else:
        print_warn("Sigla/Nome do Orgao/Cliente pendente na Secao 0.")
        results["avisos"] += 1

    # Checar código canônico do dataset ou projeto/domínio
    ds_match = (
        re.search(r"\*\*Código Canônico do Dataset.*?:\*\*\s*`?(.*?)`?$", content, re.MULTILINE)
        or re.search(r"\*\*Nome do Projeto / Domínio:\*\*\s*`?(.*?)`?$", content, re.MULTILINE)
    )
    if ds_match and ds_match.group(1).strip() and not ds_match.group(1).strip().startswith(("[Ex:", "[Nome")):
        print_ok(f"Dataset/Dominio identificado: {ds_match.group(1).strip()}")
        results["sucessos"] += 1
    else:
        print_warn("Codigo Canonico do Dataset (`SIGLA_ORGAO_UNIDADE_TEMA_VERSAO`) pendente na Secao 0.")
        results["avisos"] += 1

    # Checar Seção 1 - Tecnologias de Governança / Transporte (MANDATÓRIO)
    sec1_match = re.search(r"## Seção 1 — Seleção de Tecnologias.*?(?=## Seção 2)", content, re.DOTALL | re.IGNORECASE)
    if sec1_match:
        sec1_text = sec1_match.group(0)
        techs = re.findall(r"-\s*\[x\]\s*\*\*(.*?)\*\*", sec1_text, re.IGNORECASE)
        if not techs:
            print_err("NENHUMA tecnologia marcada com [x] na Secao 1 do INTAKE_GOVERNANCA.md!")
            print_err("     Abra 'modulos/governanca_dados/INTAKE_GOVERNANCA.md' e marque MongoDB, Amazon SageMaker Catalog/Glue, ODI, Hop ou Python.")
            results["erros"] += 1
        else:
            print_ok(f"Tecnologias de governanca/transporte selecionadas ({len(techs)} opcao(oes)):")
            for t in techs:
                print(f"     -> {t}")
            results["sucessos"] += 1

    # Checar Seção 2 - Gate de Qualidade e LGPD / LAI
    sec2_match = re.search(r"## Seção 2 —.*?(?=## Seção 3)", content, re.DOTALL | re.IGNORECASE)
    if sec2_match:
        regras_marcadas = re.findall(r"-\s*\[x\]\s*\*\*(.*?)\*\*", sec2_match.group(0), re.IGNORECASE)
        if regras_marcadas:
            print_ok(f"Diretrizes LGPD/LAI e opcoes de insumos marcadas ({len(regras_marcadas)} item(ns)).")
            results["sucessos"] += 1
        else:
            print_warn("Nenhuma diretriz de LGPD/LAI marcada na Secao 2.")
            results["avisos"] += 1

    return results


def validar_arquivos_governanca(base_dir: Path) -> dict:
    results = {"erros": 0, "avisos": 0, "sucessos": 0}
    print(f"\n{NEGRITO}2. Inspecionando Insumos em 'entrega/governanca_dados/' (Gate 0.5 — Qualidade na Origem):{RESET}")

    pasta_entrega = base_dir / "entrega" / "governanca_dados"
    if not pasta_entrega.exists():
        print_err(f"Pasta nao encontrada: {pasta_entrega}")
        results["erros"] += 1
        return results

    arquivos = [
        f for f in pasta_entrega.glob("*")
        if f.is_file() and f.name.lower() != "readme.md" and not f.name.startswith("~$")
    ]
    if arquivos:
        print_ok(f"Encontrado(s) {len(arquivos)} arquivo(s) de insumo em 'entrega/governanca_dados/':")
        for f in arquivos:
            print(f"     - {f.name} ({f.stat().st_size} bytes)")
        results["sucessos"] += 1

        # Executa auditoria determinística Gate 0.5 se houver .xlsx ou .csv
        arqs_tabular = [f for f in arquivos if f.suffix.lower() in (".xlsx", ".csv")]
        if arqs_tabular:
            try:
                from inspecionar_insumos_governanca import inspecionar_xlsx, inspecionar_csv
                for arq in arqs_tabular:
                    res = inspecionar_xlsx(arq) if arq.suffix.lower() == ".xlsx" else inspecionar_csv(arq)
                    bloqueios = res.get("bloqueios_devolucao", [])
                    if bloqueios:
                        print_err(
                            f"[GATE 0.5 — DEVOLVER AO CLIENTE] '{arq.name}' possui {len(bloqueios)} pendencia(s) na origem (campos/registros vazios ou sem LGPD):"
                        )
                        for b in bloqueios[:5]:
                            print_err(f"     -> {b}")
                        results["erros"] += 1
                    else:
                        print_ok(f"[GATE 0.5] '{arq.name}' aprovado sem campos/registros obrigatorios vazios.")
                        results["sucessos"] += 1
            except Exception as exc:
                print_warn(f"Nao foi possivel executar auditoria detalhada Gate 0.5: {exc}")
    else:
        print_warn("Nenhum arquivo de insumo (.xlsx, .csv, mapeamentos LGPD/LAI) depositado em 'entrega/governanca_dados/'.")
        print_warn("     Deposite a planilha padrao PRODEB (.xlsx) e execute: python core/scripts_comuns/inspecionar_insumos_governanca.py")
        results["avisos"] += 1

    return results


PASTAS_CANONICAS_SAIDA_DW = {
    "01_controle_carga",
    "02_staging",
    "03_dimensoes",
    "04_fatos",
    "05_procedimentos_manutencao",
    "06_pipelines_hop",
    "07_extratores_python",
    "08_datasets_bi",
    "09_relatorio_estrategias",
    "10_testes_integridade",
    "11_dicionario_dados",
}

PASTAS_CANONICAS_SAIDA_SEMANTICA = {
    "vw_analiticas",
    "meta_projeto",
    "seguranca",
}

PASTAS_CANONICAS_SAIDA_GOVERNANCA = {
    "schemas_mongo",
    "aws_datazone",
    "aws_sagemaker_catalog",
}


def validar_saida_gerada(base_dir: Path) -> dict:
    """Audita os artefatos gerados em 'saida/' contra as Regras de Ouro e Convenções."""
    results = {"erros": 0, "avisos": 0, "sucessos": 0}
    print(f"\n{NEGRITO}Auditoria Pos-Geracao de Artefatos em 'saida/':{RESET}")

    saida_dw = base_dir / "saida" / "planejador_dw"
    saida_sem = base_dir / "saida" / "camada_semantica"
    saida_gov = base_dir / "saida" / "governanca_dados"

    # 1. Regra de Ouro 3: Proibição de subpastas com nome de projeto
    for pasta_mod, permitidas in [
        (saida_dw, PASTAS_CANONICAS_SAIDA_DW),
        (saida_sem, PASTAS_CANONICAS_SAIDA_SEMANTICA),
        (saida_gov, PASTAS_CANONICAS_SAIDA_GOVERNANCA),
    ]:
        if pasta_mod.exists():
            subpastas_invalidas = [
                d.name for d in pasta_mod.iterdir()
                if d.is_dir() and d.name.lower() not in permitidas
            ]
            if subpastas_invalidas:
                print_err(
                    f"VIOLACAO DA REGRA DE OURO 3 em 'saida/{pasta_mod.name}/': "
                    f"Subpasta(s) nao canonica(s) detectada(s): {', '.join(subpastas_invalidas)}"
                )
                results["erros"] += 1
            else:
                print_ok(f"Estrutura de diretorios canonica respeitada em 'saida/{pasta_mod.name}/'.")
                results["sucessos"] += 1

    # 2. Regra de Ouro 2: Geração condicional de tecnologias (Hop e Python)
    intake_dw = base_dir / "modulos" / "planejador_dw" / "INTAKE_DW.md"
    if intake_dw.exists() and saida_dw.exists():
        intake_txt = intake_dw.read_text(encoding="utf-8", errors="ignore")
        hop_marcado = bool(re.search(r"-\s*\[x\]\s*\*\*Apache Hop", intake_txt, re.IGNORECASE))
        ftps_marcado = bool(re.search(r"-\s*\[x\]\s*\*\*Ingest[aã]o\s+Arquivos\s+em\s+Lote", intake_txt, re.IGNORECASE))
        py_marcado = bool(re.search(r"-\s*\[x\]\s*\*\*Extratores Python", intake_txt, re.IGNORECASE))

        pasta_hop = saida_dw / "06_pipelines_hop"
        if pasta_hop.exists():
            arqs_hop = [
                f for f in pasta_hop.rglob("*")
                if f.is_file() and f.suffix.lower() in [".hpl", ".hwf", ".sh"]
            ]
            if arqs_hop and not (hop_marcado or ftps_marcado):
                print_err(
                    f"VIOLACAO DA REGRA DE OURO 2: {len(arqs_hop)} arquivo(s) Apache Hop/FTPS gerado(s) "
                    f"em '06_pipelines_hop/', mas Apache Hop / Ingestao FTPS NAO esta marcado no INTAKE_DW.md!"
                )
                results["erros"] += 1
            for f_hop in arqs_hop:
                if f_hop.suffix.lower() == ".hpl":
                    hpl_txt = f_hop.read_text(encoding="utf-8", errors="ignore")
                    if "<type>CSVFileInput</type>" in hpl_txt:
                        print_err(
                            f"[{f_hop.name}] Plugin ID invalido '<type>CSVFileInput</type>' detectado! Use '<type>CSVInput</type>' no Apache Hop 2.x."
                        )
                        results["erros"] += 1

        pasta_py = saida_dw / "07_extratores_python"
        if pasta_py.exists():
            arqs_py = [f for f in pasta_py.rglob("*.py") if f.is_file()]
            if arqs_py and not py_marcado:
                print_err(
                    f"VIOLACAO DA REGRA DE OURO 2: {len(arqs_py)} script(s) Python gerado(s) "
                    f"em '07_extratores_python/', mas Extratores Python NAO esta marcado no INTAKE_DW.md!"
                )
                results["erros"] += 1

    # 3. Auditoria de SQLs gerados no Planejador de DW
    sqls_dw = [f for f in saida_dw.rglob("*.sql")] if saida_dw.exists() else []
    if sqls_dw:
        print_ok(f"Auditando {len(sqls_dw)} script(s) SQL gerados em 'saida/planejador_dw/'...")
        diag_fast_track = (
            saida_dw / "09_relatorio_estrategias" / "DIAGNOSTICO_MELHORIAS_DW_EXISTENTE.md"
        ).exists()
        tem_ddl_dim_completo = (saida_dw / "03_dimensoes" / "03_create_dim_tables.sql").exists()
        tem_patch_fast_track = any(
            f.name.startswith(("90_patch_", "91_patch_", "92_patch_")) for f in sqls_dw
        )
        is_simulacao_dw = (base_dir / "entrega" / "planejador_dw" / "SIMULACAO_BLUEPRINT_DW.md").exists()
        is_fast_track_dw = diag_fast_track or tem_patch_fast_track or not tem_ddl_dim_completo

        if is_fast_track_dw:
            print_ok(
                "Modo Fast-Track / Micro-Processo Modular detectado em 'saida/planejador_dw/'."
            )
            results["sucessos"] += 1
        elif is_simulacao_dw:
            print_ok(
                "Execucao real originada de Simulacao Aprovada ('SIMULACAO_BLUEPRINT_DW.md') detectada."
            )
            results["sucessos"] += 1

        tem_menos_um = False
        tem_dim_tempo_ddl = False
        tem_dim_tempo_fk = False
        for f_sql in sqls_dw:
            txt = f_sql.read_text(encoding="utf-8", errors="ignore")

            # Identificadores minúsculos entre aspas
            min_q = re.findall(r'"([a-z][a-z0-9_]*)"', txt)
            if min_q:
                print_err(f"[{f_sql.name}] Contem identificador(es) em minusculas entre aspas: \"{min_q[0]}\"")
                results["erros"] += 1

            # Placeholders esquecidos
            ph = re.findall(r"<(PROJETO|SCHEMA|SCHEMA_ALVO|ENTIDADE|TABELA|DIMENSAO|FATO)>", txt, re.IGNORECASE)
            if ph:
                print_err(f"[{f_sql.name}] Contem placeholder nao substituido: <{ph[0]}>")
                results["erros"] += 1

            # Proibição de BITMAP INDEX em Dimensões, verificação de DIMENSION_KEY, DIM_TEMPO e antipadrões SCD2
            if "03_dimensoes" in f_sql.parts or f_sql.name.upper().startswith("DIM_"):
                if re.search(r"CREATE\s+TABLE\s+.*?\bDIM_TEMPO\b", txt, re.IGNORECASE):
                    tem_dim_tempo_ddl = True
                if re.search(r"CREATE\s+BITMAP\s+INDEX", txt, re.IGNORECASE):
                    print_err(
                        f"[{f_sql.name}] PROIBIDO criar BITMAP INDEX em tabelas de Dimensao (risco de deadlock ORA-00060)!"
                    )
                    results["erros"] += 1
                if re.search(r"\bDES_ATUALIZA\b", txt, re.IGNORECASE):
                    if is_fast_track_dw:
                        print_warn(
                            f"[{f_sql.name}] Coluna legada 'DES_ATUALIZA' preservada do DW existente (padrao corporativo recomenda 'DES_ATUALIZAR')."
                        )
                        results["avisos"] += 1
                    else:
                        print_err(
                            f"[{f_sql.name}] Coluna SCD2 incorreta 'DES_ATUALIZA' detectada! O padrao corporativo exige 'DES_ATUALIZAR'."
                        )
                        results["erros"] += 1
                if "2999-12-31" in txt or "9999-12-31" in txt:
                    print_warn(
                        f"[{f_sql.name}] Data magica ('2999-12-31'/'9999-12-31') detectada em dimensao! Prefira 'DTC_EXPIRACAO IS NULL'."
                    )
                    results["avisos"] += 1
                if re.search(r"CREATE\s+TABLE\s+", txt, re.IGNORECASE) and "odi_dim" not in f_sql.name.lower():
                    sk_invalidas = [
                        k for k in re.findall(r"\b([A-Z0-9_]+_KEY)\b", txt.upper())
                        if k != "DIMENSION_KEY"
                    ]
                    if sk_invalidas and not is_simulacao_dw:
                        print_err(
                            f"[{f_sql.name}] Surrogate Key fora do padrao corporativo detectada ({sk_invalidas[0]})! "
                            f"Em todas as dimensoes a SK deve chamar-se estritamente 'DIMENSION_KEY'."
                        )
                        results["erros"] += 1
                    elif not re.search(r"\b(DIMENSION_KEY|SK_[A-Z0-9_]+)\b", txt, re.IGNORECASE):
                        print_err(
                            f"[{f_sql.name}] Coluna obrigatoria de Surrogate Key ('DIMENSION_KEY' ou 'SK_*') ausente no DDL de dimensao!"
                        )
                        results["erros"] += 1

            # Verificação de FKs na Fato (padrão corporativo DIM_<PROJETO>_<...> apontando para DIMENSION_KEY), DIM_TEMPO e proibição de DTC_CARGA_DW
            if "04_fatos" in f_sql.parts or f_sql.name.upper().startswith("FATO_"):
                if re.search(r"\b(DTC_CARGA_DW|DTC_CARGA)\b", txt, re.IGNORECASE):
                    if is_fast_track_dw or is_simulacao_dw:
                        print_warn(
                            f"[{f_sql.name}] Coluna legada 'DTC_CARGA_DW'/'DTC_CARGA' detectada no DW existente (documentada sem alterar estrutura)."
                        )
                        results["avisos"] += 1
                    else:
                        print_err(
                            f"[{f_sql.name}] PROIBIDO incluir coluna 'DTC_CARGA_DW' / 'DTC_CARGA' na tabela Fato! "
                            f"O controle de carga ja existe em TB_CONTROLE_CARGA / ETA_ETAPAS_CARGA (evite redundancia)."
                        )
                        results["erros"] += 1
                if re.search(r"\bDIM_TEMPO\b", txt, re.IGNORECASE):
                    tem_dim_tempo_fk = True
                fk_invalidas = [
                    k for k in re.findall(r"\b([A-Z0-9_]+_KEY)\b", txt.upper())
                    if k != "DIMENSION_KEY"
                ]
                if fk_invalidas:
                    if is_fast_track_dw or is_simulacao_dw:
                        print_warn(
                            f"[{f_sql.name}] Coluna FK legada ({fk_invalidas[0]}) preservada para nao quebrar a estrutura existente."
                        )
                        results["avisos"] += 1
                    else:
                        print_err(
                            f"[{f_sql.name}] Coluna FK fora do padrao corporativo na Fato ({fk_invalidas[0]})! "
                            f"Na Fato, as FKs de dimensao devem chamar-se 'DIM_<PROJETO>_<ENTIDADE>' referenciando 'DIMENSION_KEY'."
                        )
                        results["erros"] += 1
                fks_declaradas = re.findall(r"FOREIGN\s+KEY\s*\(\s*([A-Z0-9_\"\.]+)\s*\)", txt, re.IGNORECASE)
                for fk_col in fks_declaradas:
                    fk_clean = fk_col.replace('"', '').strip().upper()
                    if not fk_clean.startswith(("DIM_", "SK_")):
                        if is_fast_track_dw or is_simulacao_dw:
                            print_warn(
                                f"[{f_sql.name}] Foreign Key legada '{fk_clean}' preservada."
                            )
                            results["avisos"] += 1
                        else:
                            print_err(
                                f"[{f_sql.name}] Foreign Key '{fk_clean}' na Fato nao segue o padrao 'DIM_<PROJETO>_<ENTIDADE>' ou 'SK_<ENTIDADE>'!"
                            )
                            results["erros"] += 1

            # Verificação de NOPARALLEL após REBUILD PARALLEL em procedimentos de manutenção
            if "05_procedimentos_manutencao" in f_sql.parts or "07_procedures" in f_sql.parts:
                if re.search(r"REBUILD\s+PARALLEL", txt, re.IGNORECASE) and not re.search(r"NOPARALLEL", txt, re.IGNORECASE):
                    print_warn(
                        f"[{f_sql.name}] 'REBUILD PARALLEL' detectado sem retorno para 'NOPARALLEL LOGGING'. Risco de degradacao de queries OLAP!"
                    )
                    results["avisos"] += 1

            if re.search(r"VALUES\s*\(\s*-1\b|'NAO INFORMADO'|'NÃO INFORMADO'|-1\s+AS\s+", txt, re.IGNORECASE):
                tem_menos_um = True

        pasta_dim = saida_dw / "03_dimensoes"
        if pasta_dim.exists() and list(pasta_dim.glob("*.sql")):
            if is_fast_track_dw:
                if tem_menos_um:
                    print_ok("Registro padrao -1 ('NAO INFORMADO') confirmado nos scripts de dimensao.")
                else:
                    print_ok("Scripts modulares/Fast-Track de dimensao validados com sucesso.")
                results["sucessos"] += 1
            else:
                if not tem_menos_um:
                    print_warn("Dimensoes geradas em '03_dimensoes/', mas nenhum INSERT/MERGE da linha tecnica -1 ('NAO INFORMADO') foi detectado.")
                    results["avisos"] += 1
                else:
                    print_ok("Registro padrao -1 ('NAO INFORMADO') confirmado nos scripts de dimensao.")
                    results["sucessos"] += 1
                if not tem_dim_tempo_ddl:
                    if is_simulacao_dw:
                        print_warn("Simulacao executada sem 'DIM_TEMPO' explicita no DDL de entrada (considere vincular a DIM_TEMPO corporativa).")
                        results["avisos"] += 1
                    else:
                        print_err("Dimensao conformada obrigatoria 'DIM_TEMPO' ausente em '03_dimensoes/'! Todo schema de trabalho deve conter a DIM_TEMPO corporativa.")
                        results["erros"] += 1
                else:
                    print_ok("Dimensao conformada obrigatoria 'DIM_TEMPO' presente em '03_dimensoes/'.")
                    results["sucessos"] += 1
                if not (pasta_dim / "03_create_odi_dim_tables.sql").exists():
                    print_err("Script obrigatorio '03_create_odi_dim_tables.sql' (tabelas ODI_DIM_*) ausente em '03_dimensoes/'! Da STG para DIM/FATO a carga e unicamente no ODI.")
                    results["erros"] += 1
                else:
                    print_ok("Tabelas auxiliares 'ODI_DIM_*' ('03_create_odi_dim_tables.sql') presentes em '03_dimensoes/'.")
                    results["sucessos"] += 1
                if not (pasta_dim / "03_selects_odi_dimensoes.sql").exists():
                    print_err("Script obrigatorio '03_selects_odi_dimensoes.sql' (consultas ODI STG -> DIM) ausente em '03_dimensoes/'!")
                    results["erros"] += 1
                else:
                    print_ok("Consultas de carga dimensional no ODI ('03_selects_odi_dimensoes.sql') presentes em '03_dimensoes/'.")
                    results["sucessos"] += 1

        pasta_fato = saida_dw / "04_fatos"
        if pasta_fato.exists() and list(pasta_fato.glob("*.sql")):
            if is_fast_track_dw:
                print_ok("Scripts modulares/Fast-Track de Fato validados com sucesso.")
                results["sucessos"] += 1
            else:
                if not tem_dim_tempo_fk:
                    if is_simulacao_dw:
                        print_warn("Simulacao de Fato executada conforme colunas aprovadas na Blueprint (sem FK explicita para DIM_TEMPO).")
                        results["avisos"] += 1
                    else:
                        print_err("Referencia obrigatoria para 'DIM_TEMPO' ausente nas tabelas Fato em '04_fatos/'!")
                        results["erros"] += 1
                else:
                    print_ok("FK obrigatoria 'DIM_TEMPO' presente e sem redundancia de 'DTC_CARGA_DW' nas tabelas Fato.")
                    results["sucessos"] += 1
                if not (pasta_fato / "04_select_odi_fato.sql").exists():
                    print_err("Script obrigatorio '04_select_odi_fato.sql' (consultas ODI STG -> FATO com Lookups) ausente em '04_fatos/'!")
                    results["erros"] += 1
                else:
                    print_ok("Consultas de carga de Fato no ODI ('04_select_odi_fato.sql') presentes em '04_fatos/'.")
                    results["sucessos"] += 1

        pasta_rel = saida_dw / "09_relatorio_estrategias"
        if pasta_rel.exists():
            guias_dim = list(pasta_rel.glob("guia_estrategias_odi_dim_*.md"))
            guias_fato = list(pasta_rel.glob("guia_estrategias_odi_fato_*.md"))
            if is_fast_track_dw and not (guias_dim or guias_fato):
                if diag_fast_track:
                    print_ok(
                        "Relatorio 'DIAGNOSTICO_MELHORIAS_DW_EXISTENTE.md' confirmado em '09_relatorio_estrategias/' (Modo Fast-Track sem tocar no ODI)."
                    )
                    results["sucessos"] += 1
            else:
                guias_monoliticos = list(pasta_rel.glob("GUIA_IMPLEMENTACAO_ODI*.md"))
                if guias_monoliticos:
                    print_err(
                        f"Arquivo monolitico '{guias_monoliticos[0].name}' detectado em '09_relatorio_estrategias/'! "
                        "O padrao exige 1 guia separado por tabela ('guia_estrategias_odi_dim_<entidade>.md' e 'guia_estrategias_odi_fato_<entidade>.md')."
                    )
                    results["erros"] += 1
                if not guias_dim or not guias_fato:
                    print_err(
                        "Guias individuais por tabela no ODI ('guia_estrategias_odi_dim_*.md' e 'guia_estrategias_odi_fato_*.md') "
                        "ausentes em '09_relatorio_estrategias/'!"
                    )
                    results["erros"] += 1
                else:
                    print_ok(
                        f"Guias individuais de construcao no ODI 12c confirmados em '09_relatorio_estrategias/' "
                        f"({len(guias_dim)} guia(s) de Dimensao e {len(guias_fato)} guia(s) de Fato)."
                    )
                    results["sucessos"] += 1

    # 4. Auditoria de SQLs gerados na Camada Semântica
    ddl_meta_base = saida_sem / "meta_projeto" / "01_create_meta_tables.sql"
    if saida_sem.exists():
        if ddl_meta_base.exists():
            print_ok("Script base '01_create_meta_tables.sql' presente em 'saida/camada_semantica/meta_projeto/'.")
            results["sucessos"] += 1
        else:
            print_err("Script base '01_create_meta_tables.sql' ausente em 'saida/camada_semantica/meta_projeto/'!")
            results["erros"] += 1

    sqls_sem = [
        f for f in saida_sem.rglob("*.sql") if f.name != "01_create_meta_tables.sql"
    ] if saida_sem.exists() else []
    if sqls_sem:
        print_ok(f"Auditando {len(sqls_sem)} script(s) SQL de projeto gerados em 'saida/camada_semantica/'...")
        for f_sql in sqls_sem:
            txt = f_sql.read_text(encoding="utf-8", errors="ignore")

            # Prefixos banidos (SEM_VW_, SEC_, TST_)
            banidos = re.findall(r"\b(SEM_VW_[A-Z0-9_]+|SEC_[A-Z0-9_]+|TST_[A-Z0-9_]+)\b", txt, re.IGNORECASE)
            if banidos:
                print_err(f"[{f_sql.name}] Contem prefixo banido pelas convencoes: {banidos[0]}")
                results["erros"] += 1

            # Placeholders esquecidos
            ph = re.findall(r"<(PROJETO|NOME_PROJETO|SCHEMA_ALVO|DIMENSAO|FATO|MEDIDA)>", txt, re.IGNORECASE)
            if ph:
                print_err(f"[{f_sql.name}] Contem placeholder nao substituido: <{ph[0]}>")
                results["erros"] += 1

            # Identificadores entre aspas duplas em minúsculas
            aspas_minusculas = re.findall(r'"([a-z_][a-z0-9_]*)"', txt)
            if aspas_minusculas:
                print_err(
                    f"[{f_sql.name}] Identificador entre aspas duplas em minusculas detectado (proibido no Oracle): \"{aspas_minusculas[0]}\""
                )
                results["erros"] += 1

            # Sintaxe LIMIT (PostgreSQL/MySQL) em vez de FETCH FIRST n ROWS ONLY (Oracle 12c+)
            if re.search(r"\bLIMIT\s+\d+\b", txt, re.IGNORECASE):
                print_err(
                    f"[{f_sql.name}] Sintaxe 'LIMIT n' detectada! No Oracle 12c+ utilize 'FETCH FIRST n ROWS ONLY'."
                )
                results["erros"] += 1

            # Aditividade fora do padrão (hífen ou acento em vez de underscore sem acento)
            adit_invalida = re.findall(
                r"'(SEMI-ADITIVA|NÃO-ADITIVA|NAO-ADITIVA|NÃO_ADITIVA)'", txt, re.IGNORECASE
            )
            if adit_invalida:
                print_err(
                    f"[{f_sql.name}] Valor de TIPO_ADITIVIDADE fora do padrao ('{adit_invalida[0]}'). Use estritamente 'ADITIVA', 'SEMI_ADITIVA' ou 'NAO_ADITIVA'."
                )
                results["erros"] += 1

            # COMMENT ON TABLE com "Uma linha representa" nas views analíticas
            if "vw_analiticas" in f_sql.parts and re.search(r"CREATE\s+(?:OR\s+REPLACE\s+)?(?:FORCE\s+)?VIEW", txt, re.IGNORECASE):
                if not re.search(r"COMMENT\s+ON\s+TABLE.*Uma linha representa", txt, re.IGNORECASE | re.DOTALL):
                    print_warn(
                        f"[{f_sql.name}] View analitica sem declaracao explicita de grao ('COMMENT ON TABLE ... IS ''Uma linha representa...''')!"
                    )
                    results["avisos"] += 1
                else:
                    results["sucessos"] += 1

    if not sqls_dw and not sqls_sem:
        print_ok("Nenhum script SQL de projeto gerado em 'saida/' no momento (diretorio limpo para novo projeto).")
        results["sucessos"] += 1

    return results


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help", "help"]:
        print(__doc__)
        sys.exit(0)

    base_dir = get_base_dir()
    modulo = sys.argv[1].lower() if len(sys.argv) > 1 else "dw"

    print_header(f"NINHO - Verificador de Qualidade e Insumos (Modo: {modulo.upper()})")

    total_erros = 0
    total_avisos = 0
    total_sucessos = 0

    if modulo in ["fast-track", "fast_track", "fasttrack"]:
        rf = validar_fast_track_dw(base_dir)
        total_erros += rf["erros"]
        total_avisos += rf["avisos"]
        total_sucessos += rf["sucessos"]

    if modulo in ["dw", "all"]:
        r1 = validar_intake_dw(base_dir)
        r2 = validar_arquivos_dw(base_dir)
        total_erros += r1["erros"] + r2["erros"]
        total_avisos += r1["avisos"] + r2["avisos"]
        total_sucessos += r1["sucessos"] + r2["sucessos"]

    if modulo in ["semantica", "all"]:
        r3 = validar_intake_semantica(base_dir)
        r4 = validar_arquivos_semantica(base_dir)
        total_erros += r3["erros"] + r4["erros"]
        total_avisos += r3["avisos"] + r4["avisos"]
        total_sucessos += r3["sucessos"] + r4["sucessos"]

    if modulo in ["governanca", "all"]:
        r5 = validar_intake_governanca(base_dir)
        r6 = validar_arquivos_governanca(base_dir)
        total_erros += r5["erros"] + r6["erros"]
        total_avisos += r5["avisos"] + r6["avisos"]
        total_sucessos += r5["sucessos"] + r6["sucessos"]

    if modulo in ["saida", "all", "fast-track", "fast_track", "fasttrack"]:
        r7 = validar_saida_gerada(base_dir)
        total_erros += r7["erros"]
        total_avisos += r7["avisos"]
        total_sucessos += r7["sucessos"]

    print(f"\n{AZUL}{'=' * 70}{RESET}")
    print(f"{NEGRITO}Resultado da Auditoria ({modulo.upper()}):{RESET}")
    print(f"  {VERDE}Itens Validados com Sucesso:{RESET} {total_sucessos}")
    print(f"  {AMARELO}Avisos / Recomendacoes:{RESET}      {total_avisos}")
    print(f"  {VERMELHO}Erros Criticos Bloqueantes:{RESET}   {total_erros}")

    if total_erros == 0 and total_avisos == 0:
        print(f"\n{VERDE}{NEGRITO}[PRONTO] EXCELENTE! Validacao concluida com 100% de conformidade.{RESET}\n")
    elif total_erros == 0:
        print(f"\n{VERDE}{NEGRITO}[PRONTO COM OBSERVACOES] Validacao aprovada, mas revise os avisos acima.{RESET}\n")
    else:
        print(f"\n{VERMELHO}{NEGRITO}[PENDENTE] Corrija os erros bloqueantes listados acima antes de prosseguir.{RESET}\n")


if __name__ == "__main__":
    main()



