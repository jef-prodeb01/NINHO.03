#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validador Pré-Voo de Insumos da Plataforma NINHO
Executa a verificação dos arquivos de entrada antes de acionar a IA.

Uso:
    python core/scripts_comuns/validar_entrega.py dw
    python core/scripts_comuns/validar_entrega.py semantica
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

    opcao2_marcada = bool(re.search(r"-\s*\[x\]\s*\*\*Opção 2:\s*Detalhadas em arquivos", content, re.IGNORECASE))

    # Checar se campos chave ainda contêm [Ex: ...]
    placeholders = re.findall(r"(\[Ex:.*?\])", content)
    if placeholders:
        if tem_docs_entrega or opcao2_marcada:
            print_ok("Perguntas e regras de negócio fornecidas via arquivos na pasta 'entrega/planejador_dw/'.")
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

    opcao2_sem = bool(re.search(r"-\s*\[x\]\s*\*\*Opção 2:\s*Documentadas em arquivos", content, re.IGNORECASE))

    # Checar placeholders não preenchidos
    placeholders = re.findall(r"(<informe.*?>|<cole.*?>|<descreva.*?>)", content, re.IGNORECASE)
    if placeholders:
        if tem_docs_sem or opcao2_sem:
            print_ok("Regras/perguntas de negócio fornecidas via arquivos na pasta 'entrega/camada_semantica/'.")
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
    proj_match = re.search(r"\|\s*\*\*Nome do Projeto\*\*.*?\|\s*`?(.*?)`?\s*\|", content, re.MULTILINE)
    if proj_match and proj_match.group(1).strip() and not proj_match.group(1).strip().startswith("<"):
        print_ok(f"Projeto identificado: {proj_match.group(1).strip()}")
        results["sucessos"] += 1
    else:
        print_warn("Nome do projeto pendente na Secao 0.")
        results["avisos"] += 1

    # Checar schema
    schema_match = re.search(r"\|\s*\*\*Schema Alvo no Oracle\*\*.*?\|\s*`?(.*?)`?\s*\|", content, re.MULTILINE)
    if schema_match and schema_match.group(1).strip() and not schema_match.group(1).strip().startswith("<"):
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
            print_warn("Nenhuma ferramenta de consumo (Power BI, Superset, etc.) marcada com [x] na Secao 1 do INTAKE_SEMANTICA.md.")
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

    # Checar se diretrizes vêm por arquivos na pasta entrega
    pasta_entrega_gov = base_dir / "entrega" / "governanca_dados"
    tem_docs_gov = False
    if pasta_entrega_gov.exists():
        docs_gov = [f for f in pasta_entrega_gov.glob("*") if f.is_file() and f.suffix.lower() in [".md", ".txt", ".docx", ".pdf"] and f.name.lower() != "readme.md"]
        if docs_gov:
            tem_docs_gov = True

    opcao2_gov = bool(re.search(r"-\s*\[x\]\s*\*\*Opção 2:\s*Diretrizes documentadas", content, re.IGNORECASE))

    # Checar se campos de exemplo ainda contêm [Ex: ...]
    placeholders = re.findall(r"(\[Ex:.*?\])", content)
    if placeholders:
        if tem_docs_gov or opcao2_gov:
            print_ok("Diretrizes de governança fornecidas via arquivos na pasta 'entrega/governanca_dados/'.")
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
    org_match = re.search(r"\*\*Nome do Órgão / Cliente:\*\*\s*`?(.*?)`?$", content, re.MULTILINE)
    if org_match and org_match.group(1).strip() and not org_match.group(1).strip().startswith("[Ex:"):
        print_ok(f"Orgao/Cliente identificado: {org_match.group(1).strip()}")
        results["sucessos"] += 1
    else:
        print_warn("Nome do Orgao/Cliente pendente na Secao 0.")
        results["avisos"] += 1

    # Checar projeto / domínio
    proj_match = re.search(r"\*\*Nome do Projeto / Domínio:\*\*\s*`?(.*?)`?$", content, re.MULTILINE)
    if proj_match and proj_match.group(1).strip() and not proj_match.group(1).strip().startswith("[Ex:"):
        print_ok(f"Projeto/Dominio identificado: {proj_match.group(1).strip()}")
        results["sucessos"] += 1
    else:
        print_warn("Nome do Projeto/Dominio pendente na Secao 0.")
        results["avisos"] += 1

    # Checar Seção 1 - Tecnologias de Governança (MANDATÓRIO)
    sec1_match = re.search(r"## Seção 1 — Seleção de Tecnologias de Governança.*?(?=## Seção 2)", content, re.DOTALL | re.IGNORECASE)
    if sec1_match:
        sec1_text = sec1_match.group(0)
        techs = re.findall(r"-\s*\[x\]\s*\*\*(.*?)\*\*", sec1_text, re.IGNORECASE)
        if not techs:
            print_err("NENHUMA tecnologia de governanca marcada com [x] na Secao 1 do INTAKE_GOVERNANCA.md!")
            print_err("     Abra 'modulos/governanca_dados/INTAKE_GOVERNANCA.md' e marque MongoDB, DataZone/Glue, Hop ou Python.")
            results["erros"] += 1
        else:
            print_ok(f"Tecnologias de governanca selecionadas ({len(techs)} opcao(oes)):")
            for t in techs:
                print(f"     -> {t}")
            results["sucessos"] += 1

    # Checar Seção 2 - LGPD / LAI
    sec2_match = re.search(r"## Seção 2 — Diretrizes de Conformidade Legal.*?(?=## Seção 3)", content, re.DOTALL | re.IGNORECASE)
    if sec2_match:
        regras_marcadas = re.findall(r"-\s*\[x\]\s*\*\*(.*?)\*\*", sec2_match.group(0), re.IGNORECASE)
        if regras_marcadas:
            print_ok(f"Diretrizes LGPD/LAI marcadas ({len(regras_marcadas)} item(ns)).")
            results["sucessos"] += 1
        else:
            print_warn("Nenhuma diretriz de LGPD/LAI marcada na Secao 2.")
            results["avisos"] += 1

    return results


def validar_arquivos_governanca(base_dir: Path) -> dict:
    results = {"erros": 0, "avisos": 0, "sucessos": 0}
    print(f"\n{NEGRITO}2. Inspecionando Insumos em 'entrega/governanca_dados/':{RESET}")

    pasta_entrega = base_dir / "entrega" / "governanca_dados"
    if not pasta_entrega.exists():
        print_err(f"Pasta nao encontrada: {pasta_entrega}")
        results["erros"] += 1
        return results

    arquivos = [f for f in pasta_entrega.glob("*") if f.is_file() and f.name.lower() != "readme.md"]
    if arquivos:
        print_ok(f"Encontrado(s) {len(arquivos)} arquivo(s) de insumo em 'entrega/governanca_dados/':")
        for f in arquivos:
            print(f"     - {f.name} ({f.stat().st_size} bytes)")
        results["sucessos"] += 1
    else:
        print_warn("Nenhum arquivo de insumo adicional (DDL, CSV, JSON, mapeamentos LGPD/LAI) em 'entrega/governanca_dados/'.")
        print_warn("     (Opcional: catalogacao pode ser iniciada a partir do DW ou DDL corporativo).")
        results["avisos"] += 1

    return results


def main():
    base_dir = get_base_dir()
    modulo = sys.argv[1].lower() if len(sys.argv) > 1 else "dw"

    print_header(f"NINHO - Verificador Pre-Voo de Insumos (Modulo: {modulo.upper()})")

    total_erros = 0
    total_avisos = 0
    total_sucessos = 0

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

    print(f"\n{AZUL}{'=' * 70}{RESET}")
    print(f"{NEGRITO}Resultado da Auditoria Pre-Voo:{RESET}")
    print(f"  {VERDE}Itens Validados com Sucesso:{RESET} {total_sucessos}")
    print(f"  {AMARELO}Avisos / Recomendacoes:{RESET}      {total_avisos}")
    print(f"  {VERMELHO}Erros Criticos Bloqueantes:{RESET}   {total_erros}")

    if total_erros == 0 and total_avisos == 0:
        print(f"\n{VERDE}{NEGRITO}[PRONTO] EXCELENTE! Tudo pronto para acionar a IA no chat.{RESET}\n")
    elif total_erros == 0:
        print(f"\n{VERDE}{NEGRITO}[PRONTO COM OBSERVACOES] Voce pode chamar a IA, mas revise os avisos acima.{RESET}\n")
    else:
        print(f"\n{VERMELHO}{NEGRITO}[PENDENTE] Deposite os insumos ou preencha o INTAKE antes de acionar a IA.{RESET}\n")


if __name__ == "__main__":
    main()


