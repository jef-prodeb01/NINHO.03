-- =============================================================================
-- NINHO — 04_create_fato_tables.sql (SCHEMA: DW_GLD)
-- =============================================================================

CREATE TABLE DW_GLD.FATO_LICITACAO_CONTRATO (
    DIM_ORGAO_PUBLICO NUMBER(38,0) NOT NULL,
    DIM_FORNECEDOR NUMBER(38,0) NOT NULL,
    QTD_ITENS_CONTRATO NUMBER(8,0),
    VAL_ESTIMADO NUMBER(18,2),
    VAL_CONTRATO NUMBER(18,2) NOT NULL,
    VAL_PAGO_ACUMULADO NUMBER(18,2),
    DIM_TEMPO NUMBER(38,0) NOT NULL
) TABLESPACE GLD_DATA;

-- RECOMENDAÇÃO DBA (opcional, avaliar pelo volume — sugerido acima de ~20 milhões de linhas):
-- particionamento por faixa numérica (YYYYMMDD) em DIM_TEMPO habilita partition pruning nas consultas por
-- período e troca de partição (Partition Exchange) na carga. Requer a opção Oracle Partitioning
-- (Enterprise Edition) e Oracle 12.2+ para a conversão ONLINE.
-- ALTER TABLE DW_GLD.FATO_LICITACAO_CONTRATO MODIFY
--     PARTITION BY RANGE (DIM_TEMPO) INTERVAL (100)
--     (PARTITION P_INICIAL VALUES LESS THAN (20000101)) ONLINE;
-- Compressão: COMPRESS BASIC (cargas direct-path) ou ROW STORE COMPRESS ADVANCED (licença
-- Advanced Compression). COMPRESS FOR QUERY HIGH (HCC) só existe em Exadata/ZFS.

-- =============================================================================
-- PATCH FAST-TRACK NÃO-DESTRUTIVO: INTEGRIDADE REFERENCIAL E AJUSTES (FATOS)
-- Schema Alvo: DW_GLD | Cláusula ENABLE NOVALIDATE (não bloqueia dados históricos)
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Fato: DW_GLD.FATO_LICITACAO_CONTRATO
-- -----------------------------------------------------------------------------
ALTER TABLE DW_GLD.FATO_LICITACAO_CONTRATO ADD CONSTRAINT FK_FATO_LICITACAO_1_DIM_ORGA
    FOREIGN KEY (DIM_ORGAO_PUBLICO) REFERENCES DW_GLD.DIM_ORGAO_PUBLICO (DIMENSION_KEY)
    ENABLE NOVALIDATE;

ALTER TABLE DW_GLD.FATO_LICITACAO_CONTRATO ADD CONSTRAINT FK_FATO_LICITACAO_2_DIM_FORN
    FOREIGN KEY (DIM_FORNECEDOR) REFERENCES DW_GLD.DIM_FORNECEDOR (DIMENSION_KEY)
    ENABLE NOVALIDATE;

ALTER TABLE DW_GLD.FATO_LICITACAO_CONTRATO ADD CONSTRAINT FK_FATO_LICITACAO_3_DIM_TEMP
    FOREIGN KEY (DIM_TEMPO) REFERENCES DW_GLD.DIM_TEMPO (DIMENSION_KEY)
    ENABLE NOVALIDATE;



-- =============================================================================
-- PATCH FAST-TRACK: COMENTÁRIOS DE TABELAS E COLUNAS (TABELAS FATO (FATO_*))
-- Schema Alvo: DW_GLD | Gerado em: <DATA_HORA>
-- Nota: Script 100% não-destrutivo. Não altera estrutura nem esteira de carga.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Tabela: DW_GLD.FATO_LICITACAO_CONTRATO (FATO)
-- -----------------------------------------------------------------------------
COMMENT ON TABLE DW_GLD.FATO_LICITACAO_CONTRATO IS 'Tabela Fato de Licitacao Contrato do projeto DW_GLD. Uma linha representa uma ocorrência/medição analítica de Licitacao Contrato cruzado por Órgão Publico, Fornecedor, Tempo.';

COMMENT ON COLUMN DW_GLD.FATO_LICITACAO_CONTRATO.DIM_ORGAO_PUBLICO IS 'Chave estrangeira (FK) referenciando DIM_ORGAO_PUBLICO(DIMENSION_KEY).';
COMMENT ON COLUMN DW_GLD.FATO_LICITACAO_CONTRATO.DIM_FORNECEDOR IS 'Chave estrangeira (FK) referenciando DIM_FORNECEDOR(DIMENSION_KEY).';
COMMENT ON COLUMN DW_GLD.FATO_LICITACAO_CONTRATO.QTD_ITENS_CONTRATO IS 'Quantidade apurada ou contagem de Itens Contrato. Métrica Aditiva (SUM) na tabela Fato.';
COMMENT ON COLUMN DW_GLD.FATO_LICITACAO_CONTRATO.VAL_ESTIMADO IS 'Valor monetário ou quantitativo de Estimado. Métrica Aditiva (SUM) na tabela Fato.';
COMMENT ON COLUMN DW_GLD.FATO_LICITACAO_CONTRATO.VAL_CONTRATO IS 'Valor monetário ou quantitativo de Contrato. Métrica Aditiva (SUM) na tabela Fato.';
COMMENT ON COLUMN DW_GLD.FATO_LICITACAO_CONTRATO.VAL_PAGO_ACUMULADO IS 'Valor monetário ou quantitativo de Pago Acumulado. Métrica Aditiva (SUM) na tabela Fato.';
COMMENT ON COLUMN DW_GLD.FATO_LICITACAO_CONTRATO.DIM_TEMPO IS 'Chave estrangeira (FK) para a dimensão calendário conformada DIM_TEMPO(DIMENSION_KEY).';
