#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gerador Dinâmico de Dados Sintéticos / Mock para o Analista de BI
Inspeciona automaticamente os DDLs reais do projeto (DIM_* e FATO_*) ou a
Blueprint aprovada (SIMULACAO_BLUEPRINT_DW.md) para gerar arquivos CSV
100% aderentes às colunas reais do modelo Star Schema, incluindo ~3% de
chaves técnicas -1 (Não Informado - Kimball) para validação no Power BI.

Uso:
    python core/scripts_comuns/gerar_mock_dados.py --linhas 150
    python core/scripts_comuns/gerar_mock_dados.py --linhas 100 --saida saida/planejador_dw/08_datasets_bi/mock_dados_bi.csv
    python core/scripts_comuns/gerar_mock_dados.py --linhas 100 --separar-tabelas
"""

import logging as _logging_ninho

_LOG = _logging_ninho.getLogger("ninho.gerar_mock_dados")

import argparse
import csv
import os
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Configura encoding do stdout para UTF-8 no Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception as _exc:
        _LOG.debug("Exceção tratada (gerar_mock_dados.py:29): %r", _exc)

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from modular_semantica import (
    _obter_nk_dim,
    _obter_sk_dim,
    carregar_tabelas_dw,
    classificar_tabela_dw,
    identificar_fks_fato,
    localizar_ddls_para_semantica,
)
from simular_projeto import BLUEPRINT_DW_PATH, parse_tabelas_editadas_blueprint_dw


DOMINIOS_TEXTO_POR_SUFIXO = {
    "STATUS": ["DEFERIDO", "INDEFERIDO", "EM ANALISE", "CONCLUIDO", "CANCELADO"],
    "SITUACAO": ["ATIVO", "SUSPENSO", "REGULAR", "PENDENTE", "ENCERRADO"],
    "TIPO": ["ORDINARIO", "EXTRAORDINARIO", "ESPECIAL", "CONVENIO", "EMERGENCIAL"],
    "CATEGORIA": ["CATEGORIA A", "CATEGORIA B", "CATEGORIA C", "ESPECIAL"],
    "MODALIDADE": ["PRESENCIAL", "DIGITAL", "HIBRIDO", "AUTOMATICO"],
    "ORGAO": ["SAEB", "SEFAZ", "SESAB", "SEC", "SEINFRA", "SSP"],
    "SECRETARIA": ["ADMINISTRACAO", "FAZENDA", "SAUDE", "EDUCACAO", "INFRAESTRUTURA"],
    "UNIDADE": ["UNIDADE CENTRAL", "REGIONAL NORTE", "REGIONAL SUL", "REGIONAL LESTE", "POSTO SAC"],
    "DEPARTAMENTO": ["DIRETORIA GERAL", "RECURSOS HUMANOS", "TECNOLOGIA DA INFORMACAO", "OPERACIONAL", "FINANCEIRO"],
    "MUNICIPIO": ["SALVADOR", "FEIRA DE SANTANA", "VITORIA DA CONQUISTA", "CAMACARI", "ITABUNA", "JUAZEIRO"],
    "FORNECEDOR": [" CONSORCIO BAHIA TECH", "SERVICOS INTEGRADOS LTDA", " BRASILDATA S/A", "NORDESTE SUPRIMENTOS"],
    "CREDOR": ["CONSORCIO BAHIA TECH", "SERVICOS INTEGRADOS LTDA", "BRASILDATA S/A", "NORDESTE SUPRIMENTOS"],
    "CARGO": ["ANALISTA TECNICO", "ESPECIALISTA EM GESTAO", "COORDENADOR", "AUDITOR", "TECNICO ADMINISTRATIVO"],
}


def descubrir_esquema_projeto(caminho_custom: Optional[str] = None) -> List[dict]:
    """Localiza as tabelas DIM_* e FATO_* do projeto via argumento, DDLs gerados ou Blueprint editada."""
    alvo = Path(caminho_custom) if caminho_custom else None
    arqs, _ = localizar_ddls_para_semantica(alvo)
    tabelas: List[dict] = carregar_tabelas_dw(arqs) if arqs else []

    if not tabelas and BLUEPRINT_DW_PATH.exists():
        # Se só houver os DDLs transacionais TB_* em entrega/planejador_dw/ddl/, carrega via simular_projeto
        from simular_projeto import carregar_ou_projetar_modelo_dw

        tabelas, _, _, _ = carregar_ou_projetar_modelo_dw("dw")

    if tabelas and BLUEPRINT_DW_PATH.exists() and not caminho_custom:
        # Caso os DDLs em saida/planejador_dw já existam, eles já refletem a Blueprint;
        # caso estejamos lendo antes da execução física, aplica as edições da Blueprint DW:
        tabelas = parse_tabelas_editadas_blueprint_dw(BLUEPRINT_DW_PATH, tabelas)

    return tabelas


def _gerar_valor_coluna(
    col_nome: str,
    col_tipo: str,
    indice_linha: int,
    data_ini: datetime,
    eh_sentinela: bool = False,
) -> object:
    """Gera um valor sintético realista baseado no nome e tipo da coluna."""
    c_up = col_nome.upper()
    t_up = col_tipo.upper()

    # Colunas de auditoria SCD2 / controle
    if c_up in ("FLG_ATUAL", "IND_ATUAL", "IND_ATIVO", "FLG_ATIVO"):
        return 1
    if c_up in ("DTC_INICIO", "DAT_INICIO", "DT_INICIO_VIGENCIA", "DTC_EFETIVACAO"):
        return "1900-01-01"
    if c_up in ("DTC_FIM", "DAT_FIM", "DT_FIM_VIGENCIA", "DTC_EXPIRACAO"):
        return ""
    if c_up in ("DTC_CARGA", "DAT_CARGA", "DH_CARGA", "DT_ATUALIZACAO"):
        return datetime.now().strftime("%Y-%m-%d")

    if eh_sentinela:
        if c_up.startswith(("SK_", "ID_", "COD_", "NUM_", "SEQ_")) or "NUMBER" in t_up or "INT" in t_up:
            if c_up.startswith(("VAL_", "VLR_", "QTD_", "QT_")):
                return 0
            return -1
        if "DATE" in t_up or "TIMESTAMP" in t_up or c_up.startswith(("DTC_", "DAT_", "DT_")):
            return "1900-01-01"
        return "NAO INFORMADO"

    # Chaves primárias / técnicas / naturais
    if c_up.startswith("SK_"):
        return indice_linha
    if c_up.startswith("ID_"):
        return 1000 + indice_linha
    if c_up.startswith("COD_") or c_up.startswith("CD_"):
        if "CHAR" in t_up:
            return f"COD-{indice_linha:04d}"
        return 100 + indice_linha
    if c_up.startswith(("NUM_", "NR_", "SEQ_")):
        if "CHAR" in t_up:
            return f"{datetime.now().year}.{indice_linha:06d}"
        return indice_linha

    # Datas e atributos de calendário (DIM_TEMPO)
    if c_up in ("NUM_ANO", "NR_ANO", "ANO"):
        return (data_ini + timedelta(days=max(0, indice_linha * 10))).year if not eh_sentinela else 1900
    if c_up in ("NUM_MES", "NR_MES", "MES"):
        return ((indice_linha - 1) % 12) + 1 if not eh_sentinela else 1
    if c_up in ("NUM_DIA", "NR_DIA", "DIA"):
        return ((indice_linha - 1) % 28) + 1 if not eh_sentinela else 1
    if c_up in ("NUM_TRIMESTRE", "TRIMESTRE"):
        return ((indice_linha - 1) % 4) + 1 if not eh_sentinela else 1
    if c_up in ("NUM_SEMESTRE", "SEMESTRE"):
        return ((indice_linha - 1) % 2) + 1 if not eh_sentinela else 1
    if c_up in ("NOM_MES", "DES_MES", "NM_MES"):
        meses = [
            "JANEIRO", "FEVEREIRO", "MARCO", "ABRIL", "MAIO", "JUNHO",
            "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO",
        ]
        return meses[(indice_linha - 1) % 12] if not eh_sentinela else "NAO INFORMADO"
    if "DATE" in t_up or "TIMESTAMP" in t_up or c_up.startswith(("DTC_", "DAT_", "DT_")):
        dt_ev = data_ini + timedelta(days=random.randint(0, 90))
        return dt_ev.strftime("%Y-%m-%d")

    # Flags / Indicadores binários
    if c_up.startswith(("IND_", "FLG_", "IC_")):
        if "CHAR" in t_up and "(1" in t_up:
            return random.choice(["S", "N"])
        return random.choice([1, 1, 1, 0])

    # UF / Siglas
    if c_up in ("SIG_UF", "UF", "COD_UF", "SG_UF"):
        return random.choice(["BA", "SP", "RJ", "MG", "PE", "DF"])
    if c_up.startswith(("SIG_", "SG_")):
        return random.choice(["SAEB", "SEFAZ", "SESAB", "SEC", "SSP", "PGE"])

    # Métricas de quantidade
    if c_up.startswith(("QTD_", "QT_")):
        return random.randint(1, 50)

    # Métricas monetárias / percentuais / valores
    if c_up.startswith(("VAL_", "VLR_", "VL_", "PER_", "PCT_", "TAXA_")):
        if "PER_" in c_up or "PCT_" in c_up or "TAXA_" in c_up:
            return round(random.uniform(0.5, 99.5), 2)
        return round(random.uniform(50.0, 25000.0), 2)

    # Descrições / Nomes com busca inteligente por domínio semântico
    for sufixo, opcoes in DOMINIOS_TEXTO_POR_SUFIXO.items():
        if sufixo in c_up:
            return opcoes[(indice_linha - 1) % len(opcoes)]

    if c_up.startswith(("NOM_", "NM_", "DES_", "DS_")):
        entidade = (
            c_up.replace("NOM_", "")
            .replace("NM_", "")
            .replace("DES_", "")
            .replace("DS_", "")
            .replace("_", " ")
            .strip()
        )
        return f"{entidade} {indice_linha:02d}"

    if "NUMBER" in t_up or "INT" in t_up or "DECIMAL" in t_up:
        return random.randint(1, 100)

    return f"VALOR_{col_nome}_{indice_linha:02d}"


def _escolher_coluna_descritiva_dim(tinfo_dim: dict, sk_col: str, nk_col: str) -> Optional[str]:
    """Escolhe a melhor coluna descritiva (DES_* / NOM_*) de uma dimensão para enriquecer o CSV de BI."""
    for col in tinfo_dim.get("colunas", []):
        cn = col["nome_dw"].upper()
        if cn in (sk_col.upper(), nk_col.upper()):
            continue
        if cn.startswith(("NOM_", "DES_", "NM_", "DS_")):
            return col["nome_dw"]
    for col in tinfo_dim.get("colunas", []):
        cn = col["nome_dw"].upper()
        if cn not in (
            sk_col.upper(),
            nk_col.upper(),
            "DTC_INICIO",
            "DTC_FIM",
            "DTC_EFETIVACAO",
            "DTC_EXPIRACAO",
            "FLG_ATUAL",
            "IND_ATUAL",
            "DTC_CARGA",
        ):
            return col["nome_dw"]
    return None


def gerar_dados_mock_dinamico(
    tabelas: List[dict],
    num_linhas: int,
    caminho_saida: str,
    separar_tabelas: bool = False,
) -> dict:
    """Gera CSV(s) sintéticos baseados nas tabelas reais DIM_* e FATO_* do projeto."""
    random.seed(42)
    data_fim = datetime.now()
    data_ini = data_fim - timedelta(days=90)

    dims = {
        t["nome_tabela"].upper(): t
        for t in tabelas
        if classificar_tabela_dw(t) == "DIM"
    }
    fatos = {
        t["nome_tabela"].upper(): t
        for t in tabelas
        if classificar_tabela_dw(t) == "FATO"
    }
    nomes_dims = set(dims.keys())

    # 1. Gera registros para cada DIM_* (incluindo linha sentinela -1)
    catalogo_dims: Dict[str, dict] = {}
    qtd_membros_dim = 8

    for d_nome, d_info in sorted(dims.items()):
        sk_col = _obter_sk_dim(d_info)
        nk_col = _obter_nk_dim(d_info)
        desc_col = _escolher_coluna_descritiva_dim(d_info, sk_col, nk_col)
        col_names = [c["nome_dw"] for c in d_info.get("colunas", [])]

        registros_dim: Dict[int, Dict[str, object]] = {}
        # Linha -1 (Não Informado Kimball)
        reg_menos_um = {}
        for c in d_info.get("colunas", []):
            reg_menos_um[c["nome_dw"]] = _gerar_valor_coluna(
                c["nome_dw"], c.get("tipo_oracle", "VARCHAR2(100)"), -1, data_ini, eh_sentinela=True
            )
        reg_menos_um[sk_col] = -1
        registros_dim[-1] = reg_menos_um

        for idx in range(1, qtd_membros_dim + 1):
            reg = {}
            for c in d_info.get("colunas", []):
                reg[c["nome_dw"]] = _gerar_valor_coluna(
                    c["nome_dw"], c.get("tipo_oracle", "VARCHAR2(100)"), idx, data_ini, eh_sentinela=False
                )
            reg[sk_col] = idx
            registros_dim[idx] = reg

        catalogo_dims[d_nome] = {
            "sk_col": sk_col,
            "nk_col": nk_col,
            "desc_col": desc_col,
            "col_names": col_names,
            "registros": registros_dim,
        }

    if not fatos and dims:
        fatos = {next(iter(dims.keys())): next(iter(dims.values()))}

    fato_principal_nome, fato_principal_info = next(iter(fatos.items()))
    fks_list = identificar_fks_fato(fato_principal_info, nomes_dims)
    fks_map = {fk["coluna"]: fk["tabela_ref"].upper() for fk in fks_list}

    # Monta cabeçalho do CSV principal (colunas da Fato + descrições das Dimensões associadas)
    colunas_saida: List[str] = []
    enriquecimento_pos_fk: Dict[str, Tuple[str, str, str]] = {}

    for c in fato_principal_info.get("colunas", []):
        c_name = c["nome_dw"]
        colunas_saida.append(c_name)
        if c_name in fks_map:
            dim_ref = fks_map[c_name]
            desc_col = catalogo_dims.get(dim_ref, {}).get("desc_col")
            if desc_col:
                alias_desc = desc_col
                if alias_desc in colunas_saida:
                    entidade = dim_ref.replace("DIM_", "")
                    alias_desc = f"{desc_col}_{entidade}"
                colunas_saida.append(alias_desc)
                enriquecimento_pos_fk[c_name] = (dim_ref, desc_col, alias_desc)

    linhas_csv: List[List[object]] = []
    qtd_sentinelas_geradas = 0
    primeira_fk_processada = False

    for i in range(1, num_linhas + 1):
        linha_dict: Dict[str, object] = {}
        dt_linha = data_ini + timedelta(days=random.randint(0, 90))
        cod_data = int(dt_linha.strftime("%Y%m%d"))

        for c in fato_principal_info.get("colunas", []):
            c_name = c["nome_dw"]
            c_up = c_name.upper()
            c_type = c.get("tipo_oracle", "VARCHAR2(100)")

            if c_name in fks_map:
                dim_ref = fks_map[c_name]
                # Garante ~3% de chaves -1 (e pelo menos 1 na primeira linha se num_linhas >= 5)
                forcar_sentinela = (i == 1 and not primeira_fk_processada and num_linhas >= 5)
                primeira_fk_processada = True
                usar_sentinela = forcar_sentinela or (random.random() < 0.03)
                if usar_sentinela:
                    sk_val = -1
                    qtd_sentinelas_geradas += 1
                else:
                    sk_val = random.randint(1, qtd_membros_dim)

                linha_dict[c_name] = sk_val
                if c_name in enriquecimento_pos_fk:
                    _, desc_col, alias_desc = enriquecimento_pos_fk[c_name]
                    reg_dim = catalogo_dims[dim_ref]["registros"].get(sk_val, {})
                    linha_dict[alias_desc] = reg_dim.get(desc_col, "NAO INFORMADO")
            elif ("TEMPO" in c_up or "DATA" in c_up) and c_up.startswith(("SK_", "ID_", "DIM_")):
                linha_dict[c_name] = cod_data
            elif "DATE" in c_type.upper() or c_up.startswith(("DTC_", "DAT_", "DT_")):
                linha_dict[c_name] = dt_linha.strftime("%Y-%m-%d")
            else:
                linha_dict[c_name] = _gerar_valor_coluna(c_name, c_type, i, data_ini, eh_sentinela=False)

        linhas_csv.append([linha_dict.get(col, "") for col in colunas_saida])

    os.makedirs(os.path.dirname(os.path.abspath(caminho_saida)), exist_ok=True)
    with open(caminho_saida, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(colunas_saida)
        writer.writerows(linhas_csv)

    arquivos_gerados = [caminho_saida]
    pasta_destino = Path(os.path.abspath(caminho_saida)).parent

    # Se houver múltiplas tabelas Fato no DW, gera também um CSV dedicado por Fato adicional
    if len(fatos) > 1:
        for f_nome_extra, f_info_extra in fatos.items():
            if f_nome_extra == fato_principal_nome and not separar_tabelas:
                continue
            fks_extra = {fk["coluna"]: fk["tabela_ref"].upper() for fk in identificar_fks_fato(f_info_extra, nomes_dims)}
            cols_extra = [c["nome_dw"] for c in f_info_extra.get("colunas", [])]
            arq_fato_extra = pasta_destino / f"mock_{f_nome_extra.lower()}.csv"
            with open(arq_fato_extra, mode="w", newline="", encoding="utf-8") as ff:
                w_fato = csv.writer(ff, delimiter=";")
                w_fato.writerow(cols_extra)
                for idx_f in range(1, num_linhas + 1):
                    dt_f = data_ini + timedelta(days=random.randint(0, 90))
                    row_f = []
                    for c in f_info_extra.get("colunas", []):
                        cn = c["nome_dw"]
                        ct = c.get("tipo_oracle", "VARCHAR2(100)")
                        if cn in fks_extra:
                            row_f.append(-1 if (idx_f == 1 or random.random() < 0.03) else random.randint(1, qtd_membros_dim))
                        else:
                            row_f.append(_gerar_valor_coluna(cn, ct, idx_f, dt_f, eh_sentinela=False))
                    w_fato.writerow(row_f)
            if str(arq_fato_extra) not in arquivos_gerados:
                arquivos_gerados.append(str(arq_fato_extra))

    if separar_tabelas:
        for d_nome, d_meta in catalogo_dims.items():
            arq_dim = pasta_destino / f"mock_{d_nome.lower()}.csv"
            with open(arq_dim, mode="w", newline="", encoding="utf-8") as fd:
                w_dim = csv.writer(fd, delimiter=";")
                w_dim.writerow(d_meta["col_names"])
                for sk_k in sorted(d_meta["registros"].keys()):
                    reg = d_meta["registros"][sk_k]
                    w_dim.writerow([reg.get(cn, "") for cn in d_meta["col_names"]])
            arquivos_gerados.append(str(arq_dim))

    print(f"[OK] Mock dinâmico gerado a partir do modelo real ({fato_principal_nome} + {len(dims)} DIMs): {caminho_saida}")
    print(f"     Colunas geradas ({len(colunas_saida)}): {', '.join(colunas_saida)}")
    print(f"     Total de linhas: {len(linhas_csv)} (Ocorrências de chave -1 Kimball: {qtd_sentinelas_geradas})")
    print("     Separador: ';' (Padrão para Power BI / Excel pt-BR)")

    return {
        "modo": "dinamico",
        "tabela_fato": fato_principal_nome,
        "dimensoes": list(dims.keys()),
        "colunas": colunas_saida,
        "linhas": len(linhas_csv),
        "sentinelas": qtd_sentinelas_geradas,
        "arquivos": arquivos_gerados,
    }


def gerar_dados_mock_legado(num_linhas: int, caminho_saida: str) -> dict:
    """Fallback padrão quando não há DDLs ou Blueprints no workspace."""
    random.seed(42)
    print(f"Gerando {num_linhas} registros de mock (template genérico) para BI...")

    data_fim = datetime.now()
    data_ini = data_fim - timedelta(days=90)

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
        "VAL_LIQUIDO",
    ]

    linhas = []
    qtd_sentinelas = 0

    for i in range(1, num_linhas + 1):
        if i == 1 or random.random() < 0.03:
            sk_dep = -1
            nom_dep = "NAO INFORMADO"
            qtd_sentinelas += 1
        else:
            sk_dep = random.randint(1, len(departamentos))
            nom_dep = departamentos[sk_dep - 1]

        if random.random() < 0.03:
            sk_cat = -1
            nom_cat = "NAO INFORMADO"
            qtd_sentinelas += 1
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
            val_liq,
        ])

    os.makedirs(os.path.dirname(os.path.abspath(caminho_saida)), exist_ok=True)
    with open(caminho_saida, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(colunas)
        writer.writerows(linhas)

    print(f"[OK] Arquivo gerado com sucesso em: {caminho_saida}")
    print(f"     Total de linhas: {len(linhas)}")
    print("     Separador: ';' (Padrão para Power BI / Excel pt-BR)")

    return {
        "modo": "legado",
        "tabela_fato": "FATO_GENERICA",
        "dimensoes": ["DIM_DEPARTAMENTO", "DIM_CATEGORIA"],
        "colunas": colunas,
        "linhas": len(linhas),
        "sentinelas": qtd_sentinelas,
        "arquivos": [caminho_saida],
    }


def gerar_dados_mock(
    num_linhas: int,
    caminho_saida: str,
    caminho_ddls: Optional[str] = None,
    separar_tabelas: bool = False,
) -> dict:
    """Ponto de entrada unificado: usa esquema dinâmico do projeto se disponível, ou fallback legado."""
    tabelas = descubrir_esquema_projeto(caminho_ddls)
    if tabelas:
        return gerar_dados_mock_dinamico(
            tabelas=tabelas,
            num_linhas=num_linhas,
            caminho_saida=caminho_saida,
            separar_tabelas=separar_tabelas,
        )
    return gerar_dados_mock_legado(num_linhas=num_linhas, caminho_saida=caminho_saida)


def main():
    parser = argparse.ArgumentParser(description="Gerador Dinâmico de Dados Mock para Power BI")
    parser.add_argument("--linhas", type=int, default=150, help="Quantidade de linhas sintéticas a gerar (padrão: 150)")
    parser.add_argument(
        "--saida",
        type=str,
        default="saida/planejador_dw/08_datasets_bi/mock_dados_bi.csv",
        help="Caminho do arquivo CSV de saída (padrão: saida/planejador_dw/08_datasets_bi/mock_dados_bi.csv)",
    )
    parser.add_argument(
        "--caminho",
        type=str,
        default=None,
        help="Pasta opcional contendo os DDLs do DW para geração dinâmica",
    )
    parser.add_argument(
        "--separar-tabelas",
        action="store_true",
        help="Gera também arquivos mock_<dim>.csv separados para cada dimensão do modelo",
    )

    args = parser.parse_args()
    gerar_dados_mock(
        num_linhas=args.linhas,
        caminho_saida=args.saida,
        caminho_ddls=args.caminho,
        separar_tabelas=args.separar_tabelas,
    )


if __name__ == "__main__":
    main()


