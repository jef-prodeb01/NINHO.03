-- =============================================================================
-- NINHO — 02_create_stg_tables.sql (SCHEMA: STG_GLD)
-- =============================================================================

CREATE TABLE STG_GLD.STG_ORGAO_PUBLICO (
    ID_ORGAO NUMBER(10,0),
    SIG_ORGAO VARCHAR2(20 CHAR),
    NOM_ORGAO VARCHAR2(150 CHAR),
    DES_ESFERA VARCHAR2(50 CHAR),
    DTC_EXTRACAO DATE DEFAULT SYSDATE,
    ID_LOTE NUMBER
) TABLESPACE GLD_DATA NOLOGGING;

CREATE TABLE STG_GLD.STG_FORNECEDOR (
    ID_FORNECEDOR NUMBER(12,0),
    NUM_CNPJ VARCHAR2(18 CHAR),
    NOM_FORNECEDOR VARCHAR2(200 CHAR),
    SIG_UF CHAR(2 CHAR),
    DES_PORTE_EMPRESA VARCHAR2(60 CHAR),
    DTC_EXTRACAO DATE DEFAULT SYSDATE,
    ID_LOTE NUMBER
) TABLESPACE GLD_DATA NOLOGGING;

CREATE TABLE STG_GLD.STG_LICITACAO_CONTRATO (
    ID_ORGAO NUMBER(10),
    ID_FORNECEDOR NUMBER(12),
    QTD_ITENS_CONTRATO NUMBER(8,0),
    VAL_ESTIMADO NUMBER(18,2),
    VAL_CONTRATO NUMBER(18,2),
    VAL_PAGO_ACUMULADO NUMBER(18,2),
    DTC_ASSINATURA DATE,
    DTC_EXTRACAO DATE DEFAULT SYSDATE,
    ID_LOTE NUMBER
) TABLESPACE GLD_DATA NOLOGGING;

-- =============================================================================
-- PATCH FAST-TRACK: COMENTÁRIOS DE TABELAS E COLUNAS (TABELAS DE STAGE (STG_*))
-- Schema Alvo: STG_GLD | Gerado em: <DATA_HORA>
-- Nota: Script 100% não-destrutivo. Não altera estrutura nem esteira de carga.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Tabela: STG_GLD.STG_ORGAO_PUBLICO (STG)
-- -----------------------------------------------------------------------------
COMMENT ON TABLE STG_GLD.STG_ORGAO_PUBLICO IS 'Tabela de Stage (área transitória NOLOGGING) para carga de DIM_ORGAO_PUBLICO — Uma linha representa um registro de Órgão Publico.';

COMMENT ON COLUMN STG_GLD.STG_ORGAO_PUBLICO.ID_ORGAO IS 'Identificador numérico ou chave natural na origem de Órgão.';
COMMENT ON COLUMN STG_GLD.STG_ORGAO_PUBLICO.SIG_ORGAO IS 'Sigla ou abreviação oficial de Órgão.';
COMMENT ON COLUMN STG_GLD.STG_ORGAO_PUBLICO.NOM_ORGAO IS 'Nome completo ou razão social de Órgão.';
COMMENT ON COLUMN STG_GLD.STG_ORGAO_PUBLICO.DES_ESFERA IS 'Descrição textual ou detalhamento de Esfera.';
COMMENT ON COLUMN STG_GLD.STG_ORGAO_PUBLICO.DTC_EXTRACAO IS 'Data e hora em que o registro foi extraído da origem para a Staging.';
COMMENT ON COLUMN STG_GLD.STG_ORGAO_PUBLICO.ID_LOTE IS 'Identificador do lote de execução da carga na área de Staging.';

-- -----------------------------------------------------------------------------
-- Tabela: STG_GLD.STG_FORNECEDOR (STG)
-- -----------------------------------------------------------------------------
COMMENT ON TABLE STG_GLD.STG_FORNECEDOR IS 'Tabela de Stage (área transitória NOLOGGING) para carga de DIM_FORNECEDOR — Uma linha representa um registro de Fornecedor.';

COMMENT ON COLUMN STG_GLD.STG_FORNECEDOR.ID_FORNECEDOR IS 'Identificador numérico ou chave natural na origem de Fornecedor.';
COMMENT ON COLUMN STG_GLD.STG_FORNECEDOR.NUM_CNPJ IS 'Número ou código numérico de Cnpj.';
COMMENT ON COLUMN STG_GLD.STG_FORNECEDOR.NOM_FORNECEDOR IS 'Nome completo ou razão social de Fornecedor.';
COMMENT ON COLUMN STG_GLD.STG_FORNECEDOR.SIG_UF IS 'Sigla ou abreviação oficial de UF.';
COMMENT ON COLUMN STG_GLD.STG_FORNECEDOR.DES_PORTE_EMPRESA IS 'Descrição textual ou detalhamento de Porte Empresa.';
COMMENT ON COLUMN STG_GLD.STG_FORNECEDOR.DTC_EXTRACAO IS 'Data e hora em que o registro foi extraído da origem para a Staging.';
COMMENT ON COLUMN STG_GLD.STG_FORNECEDOR.ID_LOTE IS 'Identificador do lote de execução da carga na área de Staging.';

-- -----------------------------------------------------------------------------
-- Tabela: STG_GLD.STG_LICITACAO_CONTRATO (STG)
-- -----------------------------------------------------------------------------
COMMENT ON TABLE STG_GLD.STG_LICITACAO_CONTRATO IS 'Tabela de Stage (área transitória NOLOGGING) para carga de FATO_LICITACAO_CONTRATO — Uma linha representa um registro de Licitacao Contrato.';

COMMENT ON COLUMN STG_GLD.STG_LICITACAO_CONTRATO.ID_ORGAO IS 'Chave estrangeira (FK) referenciando DIM_ORGAO_PUBLICO(DIMENSION_KEY).';
COMMENT ON COLUMN STG_GLD.STG_LICITACAO_CONTRATO.ID_FORNECEDOR IS 'Chave estrangeira (FK) referenciando DIM_FORNECEDOR(DIMENSION_KEY).';
COMMENT ON COLUMN STG_GLD.STG_LICITACAO_CONTRATO.QTD_ITENS_CONTRATO IS 'Quantidade apurada ou contagem de Itens Contrato.';
COMMENT ON COLUMN STG_GLD.STG_LICITACAO_CONTRATO.VAL_ESTIMADO IS 'Valor monetário ou quantitativo de Estimado.';
COMMENT ON COLUMN STG_GLD.STG_LICITACAO_CONTRATO.VAL_CONTRATO IS 'Valor monetário ou quantitativo de Contrato.';
COMMENT ON COLUMN STG_GLD.STG_LICITACAO_CONTRATO.VAL_PAGO_ACUMULADO IS 'Valor monetário ou quantitativo de Pago Acumulado.';
COMMENT ON COLUMN STG_GLD.STG_LICITACAO_CONTRATO.DTC_ASSINATURA IS 'Chave estrangeira (FK) para a dimensão calendário conformada DIM_TEMPO(DIMENSION_KEY).';
COMMENT ON COLUMN STG_GLD.STG_LICITACAO_CONTRATO.DTC_EXTRACAO IS 'Data e hora em que o registro foi extraído da origem para a Staging.';
COMMENT ON COLUMN STG_GLD.STG_LICITACAO_CONTRATO.ID_LOTE IS 'Identificador do lote de execução da carga na área de Staging.';
