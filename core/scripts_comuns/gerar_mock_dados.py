#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gerador de Dados Sintéticos / Mock para o Analista de BI
Gera arquivos CSV com dados de teste para acelerar o desenvolvimento
de relatórios no Power BI antes da conclusão do pipeline de produção.

Uso:
    python core/scripts_comuns/gerar_mock_dados.py --linhas 100 --saida mock_fato.csv
"""

import sys
import os
import csv
import random
import argparse
from datetime import datetime, timedelta

# Configura encoding do stdout para UTF-8 no Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def gerar_dados_mock(num_linhas: int, caminho_saida: str):
    print(f"Gerando {num_linhas} registros de mock para BI...")

    # Data base para simulação (últimos 90 dias)
    data_fim = datetime.now()
    data_ini = data_fim - timedelta(days=90)

    # Entidades simuladas
    departamentos = ["DIRETORIA GERAL", "RECURSOS HUMANOS", "TECNOLOGIA DA INFORMACAO", "OPERACIONAL", "FINANCEIRO", "LOGISTICA"]
    status_opcoes = ["DEFERIDO", "INDEFERIDO", "EM ANALISE", "CANCELADO"]
    categorias = ["CATEGORIA A", "CATEGORIA B", "CATEGORIA C", "NAO INFORMADO"]

    colunas = [
        "ID_TRANSACAO",
        "DTC_COMPLETA",
        "DIM_TEMPO",
        "DIM_DEPARTAMENTO",
        "DES_DEPARTAMENTO",
        "DIM_CATEGORIA",
        "DES_CATEGORIA",
        "DES_STATUS",
        "IND_DEFERIDO",
        "QTD_ITENS",
        "VAL_UNITARIO",
        "VAL_TOTAL_BRUTO",
        "VAL_DESCONTO",
        "VAL_LIQUIDO"
    ]

    linhas = []

    for i in range(1, num_linhas + 1):
        # 3% de chance de gerar a chave técnica -1 (não informado Kimball)
        if random.random() < 0.03:
            sk_dep = -1
            nom_dep = "NAO INFORMADO"
        else:
            sk_dep = random.randint(1, len(departamentos))
            nom_dep = departamentos[sk_dep - 1]

        if random.random() < 0.03:
            sk_cat = -1
            nom_cat = "NAO INFORMADO"
        else:
            sk_cat = random.randint(1, len(categorias))
            nom_cat = categorias[sk_cat - 1]

        dias_aleatorios = random.randint(0, 90)
        dt_evento = data_ini + timedelta(days=dias_aleatorios)
        cod_data = int(dt_evento.strftime("%Y%m%d"))

        status = random.choice(status_opcoes)
        ind_deferido = 1 if status == "DEFERIDO" else 0

        qtd = random.randint(1, 20)
        val_unit = round(random.uniform(15.0, 450.0), 2)
        val_bruto = round(qtd * val_unit, 2)
        val_desc = round(val_bruto * random.choice([0.0, 0.05, 0.10]), 2)
        val_liq = round(val_bruto - val_desc, 2)

        linhas.append([
            i,
            dt_evento.strftime("%Y-%m-%d"),
            cod_data,
            sk_dep,
            nom_dep,
            sk_cat,
            nom_cat,
            status,
            ind_deferido,
            qtd,
            val_unit,
            val_bruto,
            val_desc,
            val_liq
        ])

    os.makedirs(os.path.dirname(os.path.abspath(caminho_saida)), exist_ok=True)
    with open(caminho_saida, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(colunas)
        writer.writerows(linhas)

    print(f"[OK] Arquivo gerado com sucesso em: {caminho_saida}")
    print(f"     Total de linhas: {len(linhas)}")
    print(f"     Separador: ';' (Padrão para Power BI / Excel pt-BR)")


def main():
    parser = argparse.ArgumentParser(description="Gerador de Dados Mock para Power BI")
    parser.add_argument("--linhas", type=int, default=150, help="Quantidade de linhas sintéticas a gerar (padrão: 150)")
    parser.add_argument("--saida", type=str, default="saida/mock_dados_bi.csv", help="Caminho do arquivo CSV de saída")

    args = parser.parse_args()
    gerar_dados_mock(args.linhas, args.saida)


if __name__ == "__main__":
    main()

