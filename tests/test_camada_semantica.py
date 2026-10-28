"""Testes das views semânticas (Evento/KPI) e do RLS gerado por modular_semantica.py."""

import re

from inspecionar_ddl_origem import parse_ddl_text
from modular_semantica import (
    alias_oracle_seguro,
    construir_script_rls,
    construir_views_eventos,
    construir_views_kpis,
)

DDL_DW = """
CREATE TABLE DIM_ORGAO (
    DIMENSION_KEY NUMBER(38) NOT NULL,
    COD_ORGAO VARCHAR2(20),
    DES_UNIDADE_ORGANIZACIONAL_ORCAMENTARIA_COMPLETA VARCHAR2(200),
    DES_UNIDADE_ORGANIZACIONAL_ORCAMENTARIA_RESUMIDA VARCHAR2(100),
    DTC_EFETIVACAO DATE, DTC_EXPIRACAO DATE, SIN_ATIVO CHAR(1),
    CONSTRAINT PK_DIM_ORGAO PRIMARY KEY (DIMENSION_KEY)
);
CREATE TABLE FATO_CONTRATO (
    DIM_ORGAO NUMBER(38) NOT NULL,
    DTC_ASSINATURA DATE NOT NULL,
    DES_STATUS_CONTRATO VARCHAR2(40),
    VAL_CONTRATO NUMBER(18,2),
    CONSTRAINT FK_FATO_ORGAO FOREIGN KEY (DIM_ORGAO) REFERENCES DIM_ORGAO (DIMENSION_KEY)
);
"""


def _tabelas():
    return parse_ddl_text(DDL_DW, "dw.sql")


def test_alias_nunca_termina_com_underscore_nem_colide():
    usados = set()
    a1 = alias_oracle_seguro("DES_UNIDADE_ORGANIZACIONAL_OR_ALGO", usados)
    a2 = alias_oracle_seguro("DES_UNIDADE_ORGANIZACIONAL_OR_OUTRO", usados)
    assert len(a1) <= 30 and len(a2) <= 30
    assert not a1.endswith("_") and not a2.endswith("_")
    assert a1 != a2


def test_view_evento_deriva_situacao_de_coluna_real():
    sql = construir_views_eventos(_tabelas(), "DW", "CTR")
    assert "CASE WHEN 1 = 1" not in sql
    assert "NVL(TO_CHAR(f.DES_STATUS_CONTRATO), 'Não Informado') AS IND_SITUACAO_EVENTO" in sql
    aliases = re.findall(r" AS (\w+)", sql)
    assert all(len(a) <= 30 and not a.endswith("_") for a in aliases)
    assert len(aliases) == len(set(aliases))


def test_view_kpi_tem_eixo_temporal_e_participacao_por_periodo():
    sql = construir_views_kpis(_tabelas(), "DW", "CTR")
    assert "TRUNC(e.DTC_ASSINATURA, 'MM') AS DTC_MES_REFERENCIA" in sql
    assert "GROUP BY e.DIM_ORGAO, TRUNC(e.DTC_ASSINATURA, 'MM');" in sql
    assert "OVER (PARTITION BY TRUNC(e.DTC_ASSINATURA, 'MM'))" in sql


def test_rls_resolve_identidade_no_banco_sem_concatenar_entrada():
    sql = construir_script_rls(_tabelas(), "DW", "CTR")
    assert "RLS_CONTAS_SERVICO" in sql
    assert "DBMS_ASSERT.ENQUOTE_LITERAL" in sql
    assert "DBMS_RLS.DYNAMIC" in sql
    assert "LISTAGG" not in sql
    assert "p_acesso_total" not in sql and "VALOR_FILTRO" not in sql
    assert "RETURN '1 = 0';  -- Fail-closed" in sql
