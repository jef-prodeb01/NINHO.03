"""Testes unitários da classificação OLTP -> Star Schema e das regras de nomes do ODI 12c."""

import pytest

from inspecionar_ddl_origem import parse_ddl_text
from melhorar_dw_existente import (
    abreviar_identificador_odi,
    derivar_sigla_curta_odi,
    validar_tamanho_identificador_odi,
)
from simular_projeto import _converter_oltp_para_dw_se_necessario

DDL_VENDAS = """
CREATE TABLE TB_VENDA (
    ID_VENDA NUMBER PRIMARY KEY,
    ID_CLIENTE NUMBER,
    ID_PRODUTO NUMBER,
    VAL_TOTAL NUMBER(12,2),
    QTD_ITENS NUMBER(5)
);
CREATE TABLE TB_CLIENTE (ID_CLIENTE NUMBER PRIMARY KEY, NOM_CLIENTE VARCHAR2(100));
CREATE TABLE TB_PRODUTO (ID_PRODUTO NUMBER PRIMARY KEY, DES_PRODUTO VARCHAR2(100));
"""


def test_tabela_com_metricas_e_fks_vira_fato_e_cadastros_viram_dimensoes():
    propostas = _converter_oltp_para_dw_se_necessario(parse_ddl_text(DDL_VENDAS, "vendas.sql"))
    nomes = {t["nome_tabela"] for t in propostas}
    assert {"FATO_VENDA", "DIM_CLIENTE", "DIM_PRODUTO"} <= nomes


def test_dimensoes_recebem_colunas_corporativas_scd2():
    propostas = _converter_oltp_para_dw_se_necessario(parse_ddl_text(DDL_VENDAS, "vendas.sql"))
    dim = next(t for t in propostas if t["nome_tabela"] == "DIM_CLIENTE")
    colunas = {c["nome_dw"] for c in dim["colunas"]}
    assert {"SIN_ATIVO", "DTC_EFETIVACAO", "DTC_EXPIRACAO"} <= colunas


@pytest.mark.parametrize(
    "prefixo,nome,limite",
    [
        ("DIM", "MUNICIPIO_RESIDENCIA_BENEFICIARIO_PROGRAMA", 22),
        ("FATO", "TRAMITACAO_PROCESSOS_ADMINISTRATIVOS_ESTADUAIS", 26),
        ("ODI_DIM", "UNIDADE_ORGANIZACIONAL_SECRETARIA", 26),
    ],
)
def test_abreviacao_odi_respeita_limite(prefixo, nome, limite):
    resultado = abreviar_identificador_odi(prefixo, nome, "SEI", max_len=limite)
    assert len(resultado) <= limite
    assert resultado.startswith(f"{prefixo}_")


def test_sigla_curta_tem_ate_4_caracteres():
    sigla = derivar_sigla_curta_odi("SISTEMA_ELETRONICO_DE_INFORMACOES")
    assert 2 <= len(sigla) <= 4
    assert sigla.isalnum()


def test_validacao_de_tamanho_usa_limite_22_para_dimensoes_e_26_para_demais():
    aprovado, _, limite = validar_tamanho_identificador_odi("DIM_" + "X" * 30)
    assert not aprovado and limite == 22
    aprovado, _, limite = validar_tamanho_identificador_odi("FATO_CONTRATO")
    assert aprovado and limite == 26
