-- =============================================================================
-- CONSULTAS ANALÍTICAS SQL PARA O ODI 12c (CARGA_DIM_* / MAP_001) — PROJETO GLD
-- Schema Alvo: DW_GLD | Stage Origem: STG_GLD | Gerado em: <DATA_HORA>
-- Instrução  : No padrão Dimension Pattern (CARGA_DIM_*), aplique UPPER(TRIM(NK))
--              no componente EXPRESSION; ou cole este SELECT na aba Custom SQL.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Dimensão Alvo: DW_GLD.DIM_ORGAO_PUBLICO (Tabela Auxiliar: DW_GLD.ODI_DIM_ORGAO_PUBLICO)
-- Origem Stage : STG_GLD.STG_ORGAO_PUBLICO | Chave Natural (NK): ID_ORGAO
-- -----------------------------------------------------------------------------
WITH BASE_DEDUP AS (
    SELECT
        S.ID_ORGAO AS ID_ORGAO,
        S.SIG_ORGAO,
        S.NOM_ORGAO,
        S.DES_ESFERA,
        SYSDATE AS DTC_MOVIMENTO,
        ROW_NUMBER() OVER (PARTITION BY S.ID_ORGAO ORDER BY S.ID_ORGAO) AS NR_VERSAO,
        LEAD(SYSDATE, 1) OVER (PARTITION BY S.ID_ORGAO ORDER BY S.ID_ORGAO) AS PROX_DTC_INICIO
    FROM STG_GLD.STG_ORGAO_PUBLICO S
    WHERE S.ID_ORGAO IS NOT NULL
)
SELECT
    B.ID_ORGAO,
    B.SIG_ORGAO,
    B.NOM_ORGAO,
    B.DES_ESFERA,
    CASE WHEN B.PROX_DTC_INICIO IS NULL THEN 'S' ELSE 'N' END AS SIN_ATIVO,
    CASE WHEN B.NR_VERSAO = 1 THEN TO_DATE('<DATA>', 'YYYY-MM-DD') ELSE B.DTC_MOVIMENTO END AS DTC_EFETIVACAO,
    B.PROX_DTC_INICIO AS DTC_EXPIRACAO,
    CASE WHEN B.PROX_DTC_INICIO IS NULL THEN 'S' ELSE 'N' END AS DES_ATUALIZAR
FROM BASE_DEDUP B;

-- -----------------------------------------------------------------------------
-- Dimensão Alvo: DW_GLD.DIM_FORNECEDOR (Tabela Auxiliar: DW_GLD.ODI_DIM_FORNECEDOR)
-- Origem Stage : STG_GLD.STG_FORNECEDOR | Chave Natural (NK): ID_FORNECEDOR
-- -----------------------------------------------------------------------------
WITH BASE_DEDUP AS (
    SELECT
        S.ID_FORNECEDOR AS ID_FORNECEDOR,
        S.NUM_CNPJ,
        S.NOM_FORNECEDOR,
        S.SIG_UF,
        S.DES_PORTE_EMPRESA,
        SYSDATE AS DTC_MOVIMENTO,
        ROW_NUMBER() OVER (PARTITION BY S.ID_FORNECEDOR ORDER BY S.ID_FORNECEDOR) AS NR_VERSAO,
        LEAD(SYSDATE, 1) OVER (PARTITION BY S.ID_FORNECEDOR ORDER BY S.ID_FORNECEDOR) AS PROX_DTC_INICIO
    FROM STG_GLD.STG_FORNECEDOR S
    WHERE S.ID_FORNECEDOR IS NOT NULL
)
SELECT
    B.ID_FORNECEDOR,
    B.NUM_CNPJ,
    B.NOM_FORNECEDOR,
    B.SIG_UF,
    B.DES_PORTE_EMPRESA,
    CASE WHEN B.PROX_DTC_INICIO IS NULL THEN 'S' ELSE 'N' END AS SIN_ATIVO,
    CASE WHEN B.NR_VERSAO = 1 THEN TO_DATE('<DATA>', 'YYYY-MM-DD') ELSE B.DTC_MOVIMENTO END AS DTC_EFETIVACAO,
    B.PROX_DTC_INICIO AS DTC_EXPIRACAO,
    CASE WHEN B.PROX_DTC_INICIO IS NULL THEN 'S' ELSE 'N' END AS DES_ATUALIZAR
FROM BASE_DEDUP B;
