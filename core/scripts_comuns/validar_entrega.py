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

    # Checar se campos chave ainda contêm [Ex: ...]
    placeholders = re.findall(r"(\[Ex:.*?\])", content)
    if placeholders:
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

    # Checar placeholders não preenchidos
    placeholders = re.findall(r"(<informe.*?>|<cole.*?>|<descreva.*?>)", content, re.IGNORECASE)
    if placeholders:
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


