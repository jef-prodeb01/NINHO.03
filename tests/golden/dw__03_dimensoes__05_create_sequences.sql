-- =============================================================================
-- NINHO — 05_create_sequences.sql (SCHEMA: DW_GLD)
-- Regra Corporativa: CACHE 1000 NOORDER NOCYCLE para performance de carga SCD2/Fato
-- =============================================================================

CREATE SEQUENCE DW_GLD.SEQ_DIM_ORGAO_PUBLICO START WITH 1 INCREMENT BY 1 CACHE 1000 NOORDER NOCYCLE;
CREATE SEQUENCE DW_GLD.SEQ_DIM_FORNECEDOR START WITH 1 INCREMENT BY 1 CACHE 1000 NOORDER NOCYCLE;
