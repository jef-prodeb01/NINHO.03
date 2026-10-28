"""Testes unitários do parser de DDL de origem (inspecionar_ddl_origem.py)."""

from inspecionar_ddl_origem import detectar_ctas, parse_ddl_text

DDL_CONTRATOS = """
CREATE TABLE TB_ORGAO (
    ID_ORGAO NUMBER(10) NOT NULL,
    NOM_ORGAO VARCHAR2(150),
    CONSTRAINT PK_TB_ORGAO PRIMARY KEY (ID_ORGAO)
);
CREATE TABLE TB_CONTRATO (
    ID_CONTRATO NUMBER(15) NOT NULL,
    ID_ORGAO NUMBER(10) NOT NULL REFERENCES TB_ORGAO (ID_ORGAO),
    VAL_CONTRATO NUMBER(18,2),
    CONSTRAINT PK_TB_CONTRATO PRIMARY KEY (ID_CONTRATO)
);
"""


def _por_nome(tabelas):
    return {t["nome_tabela"].upper(): t for t in tabelas}


def test_extrai_todas_as_tabelas_e_colunas():
    tabs = _por_nome(parse_ddl_text(DDL_CONTRATOS, "contratos.sql"))
    assert set(tabs) == {"TB_ORGAO", "TB_CONTRATO"}
    colunas = [c["nome_dw"] for c in tabs["TB_CONTRATO"]["colunas"]]
    assert colunas == ["ID_CONTRATO", "ID_ORGAO", "VAL_CONTRATO"]


def test_reconhece_pk_e_fk_inline():
    tab = _por_nome(parse_ddl_text(DDL_CONTRATOS, "contratos.sql"))["TB_CONTRATO"]
    assert "ID_CONTRATO" in [p.upper() for p in tab["pks"]]
    assert "ID_ORGAO" in [fk["coluna"].upper() for fk in tab["fks"]]


def test_comentarios_nao_viram_colunas_e_identificadores_especiais_sao_normalizados():
    sql = """
    CREATE TABLE TB_X (
        KEY_CLIENTE VARCHAR2(20), -- comentario, com virgula
        /* bloco, comentado */
        [Cod Pedido] NUMBER(10),
        "Valor Total" NUMBER(15, 2) DEFAULT 0
    );
    """
    colunas = [c["nome_dw"] for c in parse_ddl_text(sql, "x.sql")[0]["colunas"]]
    assert colunas == ["KEY_CLIENTE", "COD_PEDIDO", "VALOR_TOTAL"]


def test_ctas_e_detectado_e_nao_extraido_como_tabela():
    sql = "CREATE TABLE TB_CTAS AS SELECT ID, NOME FROM TB_ORIGEM;"
    assert parse_ddl_text(sql, "ctas.sql") == []
    assert detectar_ctas(sql) == ["TB_CTAS"]


def test_ddl_vazio_retorna_lista_vazia():
    assert parse_ddl_text("", "vazio.sql") == []
