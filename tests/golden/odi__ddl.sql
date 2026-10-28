-- =============================================================================
-- TABELAS AUXILIARES DE PREPARAÇÃO SCD2 DO ODI (ODI_DIM_*) — PROJETO GLD
-- Schema Alvo: DW_GLD | Gerado em: <DATA_HORA>
-- Padrão ODI : Utilizadas como 'Armazenamento de Dados de Teste' (STG_DIM_*)
--              no componente nativo de Dimensão (Dimension Pattern / Asterisco).
--              ATENÇÃO: Todas as colunas (inclusive DIMENSION_KEY, DTC_EFETIVACAO
--              e DTC_EXPIRACAO) DEVEM ser NULLABLE e sem PK para evitar ORA-01400
--              na etapa intermediária STG_DIM antes do disparo da Sequence no Target.
-- =============================================================================

-- Tabela Auxiliar ODI para DIM_ORGAO_PUBLICO (100% NULLABLE para STG_DIM do Dimension Pattern)
CREATE TABLE DW_GLD.ODI_DIM_ORGAO_PUBLICO (
    DIMENSION_KEY                NUMBER(38,0),
    ID_ORGAO                     NUMBER(10,0),
    SIG_ORGAO                    VARCHAR2(20 CHAR),
    NOM_ORGAO                    VARCHAR2(150 CHAR),
    DES_ESFERA                   VARCHAR2(50 CHAR),
    SIN_ATIVO                    CHAR(1 CHAR) DEFAULT 'S',
    DTC_EFETIVACAO               DATE,
    DTC_EXPIRACAO                DATE,
    DES_ATUALIZAR                CHAR(1 CHAR) DEFAULT 'S',
    DES_STATUS_REGISTRO          CHAR(1 CHAR)
);
CREATE INDEX DW_GLD.IDX_ODI_DIM_ORGAO_PUBL_NK ON DW_GLD.ODI_DIM_ORGAO_PUBLICO (ID_ORGAO, DTC_EFETIVACAO DESC);
COMMENT ON TABLE DW_GLD.ODI_DIM_ORGAO_PUBLICO IS 'Tabela intermediária de stage analítico (Armazenamento de Dados de Teste) do ODI 12c para cálculo de versão e vigência SCD2 de DIM_ORGAO_PUBLICO.';

-- Tabela Auxiliar ODI para DIM_FORNECEDOR (100% NULLABLE para STG_DIM do Dimension Pattern)
CREATE TABLE DW_GLD.ODI_DIM_FORNECEDOR (
    DIMENSION_KEY                NUMBER(38,0),
    ID_FORNECEDOR                NUMBER(12,0),
    NUM_CNPJ                     VARCHAR2(18 CHAR),
    NOM_FORNECEDOR               VARCHAR2(200 CHAR),
    SIG_UF                       CHAR(2 CHAR),
    DES_PORTE_EMPRESA            VARCHAR2(60 CHAR),
    SIN_ATIVO                    CHAR(1 CHAR) DEFAULT 'S',
    DTC_EFETIVACAO               DATE,
    DTC_EXPIRACAO                DATE,
    DES_ATUALIZAR                CHAR(1 CHAR) DEFAULT 'S',
    DES_STATUS_REGISTRO          CHAR(1 CHAR)
);
CREATE INDEX DW_GLD.IDX_ODI_DIM_FORNECEDOR_NK ON DW_GLD.ODI_DIM_FORNECEDOR (ID_FORNECEDOR, DTC_EFETIVACAO DESC);
COMMENT ON TABLE DW_GLD.ODI_DIM_FORNECEDOR IS 'Tabela intermediária de stage analítico (Armazenamento de Dados de Teste) do ODI 12c para cálculo de versão e vigência SCD2 de DIM_FORNECEDOR.';
