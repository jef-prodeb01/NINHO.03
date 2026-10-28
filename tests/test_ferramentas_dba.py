"""Fase 3 — /comparar-modelo e /estimar-volumetria."""

from inspecionar_ddl_origem import parse_ddl_text
from ninho_core.comparador_modelo import alargamento_seguro, comparar, gerar_script_alter
from ninho_core.volumetria import LIMIAR_PARTICIONAMENTO, bytes_coluna, estimar, relatorio_markdown

ATUAL = """
CREATE TABLE DIM_ORGAO (DIMENSION_KEY NUMBER(38) NOT NULL, NOM_ORGAO VARCHAR2(100), COD_LEGADO VARCHAR2(10));
CREATE TABLE FATO_CONTRATO (DIM_ORGAO NUMBER(38) NOT NULL, VAL_CONTRATO NUMBER(12,2), DES_STATUS VARCHAR2(40));
CREATE TABLE TB_ANTIGA (ID NUMBER);
"""
NOVO = """
CREATE TABLE DIM_ORGAO (DIMENSION_KEY NUMBER(38) NOT NULL, NOM_ORGAO VARCHAR2(200), SIG_ORGAO VARCHAR2(20) NOT NULL);
CREATE TABLE FATO_CONTRATO (DIM_ORGAO NUMBER(38) NOT NULL, VAL_CONTRATO NUMBER(18,2), DES_STATUS VARCHAR2(10), DTC_ASSINATURA DATE);
CREATE TABLE DIM_FORNECEDOR (DIMENSION_KEY NUMBER(38) NOT NULL, NOM_FORNECEDOR VARCHAR2(200));
"""


def test_alargamento_seguro():
    assert alargamento_seguro("VARCHAR2(100)", "VARCHAR2(200)")
    assert not alargamento_seguro("VARCHAR2(40)", "VARCHAR2(10)")
    assert alargamento_seguro("NUMBER(12,2)", "NUMBER(18,2)")
    assert not alargamento_seguro("NUMBER(12,2)", "NUMBER(18,4)")
    assert not alargamento_seguro("DATE", "TIMESTAMP")


def test_alter_incremental_seguro():
    atual, novo = parse_ddl_text(ATUAL, "a.sql"), parse_ddl_text(NOVO, "n.sql")
    sql = gerar_script_alter(comparar(atual, novo), novo, "DW")
    assert "CREATE TABLE DW.DIM_FORNECEDOR (" in sql
    assert "ALTER TABLE DW.FATO_CONTRATO ADD (DTC_ASSINATURA DATE);" in sql
    assert "ALTER TABLE DW.DIM_ORGAO MODIFY (NOM_ORGAO VARCHAR2(200));" in sql
    assert "ALTER TABLE DW.FATO_CONTRATO MODIFY (VAL_CONTRATO NUMBER(18,2));" in sql
    assert "-- ALTER TABLE DW.FATO_CONTRATO MODIFY (DES_STATUS VARCHAR2(10));" in sql      # estreitamento comentado
    assert "-- ALTER TABLE DW.DIM_ORGAO MODIFY (SIG_ORGAO NOT NULL);" in sql                # NOT NULL via backfill
    assert "SET UNUSED (COD_LEGADO)" in sql and "-- [REMOÇÃO" in sql                     # remoção comentada
    assert "-- [TABELA AUSENTE NO MODELO NOVO — avaliar] DROP TABLE DW.TB_ANTIGA PURGE;" in sql
    linhas_ativas = [ln for ln in sql.splitlines() if ln.strip() and not ln.lstrip().startswith("--")]
    assert not any("DROP" in ln or "SET UNUSED" in ln for ln in linhas_ativas)


def test_volumetria_e_particionamento():
    assert bytes_coluna("DATE") == 8 and bytes_coluna("VARCHAR2(100)") == 51
    tabelas = parse_ddl_text(NOVO, "n.sql")
    est = {e.tabela: e for e in estimar(tabelas, {"FATO_CONTRATO": 50_000_000}, 0.02)}
    fato = est["FATO_CONTRATO"]
    assert fato.linhas_5_anos > LIMIAR_PARTICIONAMENTO and fato.particionar and not fato.premissa_padrao
    assert est["DIM_ORGAO"].premissa_padrao and not est["DIM_ORGAO"].particionar
    assert fato.mb_tabela > 1000
    relatorio = relatorio_markdown(list(est.values()), "GLD", 0.02)
    assert "Particionamento recomendado" in relatorio and "FATO_CONTRATO" in relatorio
