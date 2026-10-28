-- =============================================================================
-- CONSULTAS DE RESOLUÇÃO DE SKs PARA TABELAS FATO (CARGA_FATO_*) — PROJETO GLD
-- Schema Alvo: DW_GLD | Stage Origem: STG_GLD | Estratégia: A | Gerado em: <DATA_HORA>
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Tabela Fato Alvo: DW_GLD.FATO_LICITACAO_CONTRATO | Stage Origem: STG_GLD.STG_LICITACAO_CONTRATO
-- -----------------------------------------------------------------------------
SELECT
    NVL(D1.DIMENSION_KEY, -1) AS DIM_ORGAO_PUBLICO,
    NVL(D2.DIMENSION_KEY, -1) AS DIM_FORNECEDOR,
    NVL(S.QTD_ITENS_CONTRATO, 0) AS QTD_ITENS_CONTRATO,
    NVL(S.VAL_ESTIMADO, 0) AS VAL_ESTIMADO,
    NVL(S.VAL_CONTRATO, 0) AS VAL_CONTRATO,
    NVL(S.VAL_PAGO_ACUMULADO, 0) AS VAL_PAGO_ACUMULADO,
    NVL(D3.DIMENSION_KEY, -1) AS DIM_TEMPO
FROM STG_GLD.STG_LICITACAO_CONTRATO S
LEFT JOIN DW_GLD.DIM_ORGAO_PUBLICO D1
    ON S.ID_ORGAO = D1.ID_ORGAO
   AND D1.DTC_EXPIRACAO IS NULL
LEFT JOIN DW_GLD.DIM_FORNECEDOR D2
    ON S.ID_FORNECEDOR = D2.ID_FORNECEDOR
   AND D2.DTC_EXPIRACAO IS NULL
LEFT JOIN DW_GLD.DIM_TEMPO D3
    ON TRUNC(S.DTC_ASSINATURA) = D3.DTC_COMPLETA;
