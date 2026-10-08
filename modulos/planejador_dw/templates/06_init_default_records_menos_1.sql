-- ==============================================================================
-- SCRIPT DML: CARGA INICIAL DO REGISTRO PADRÃO DESCONHECIDO (LINHA -1)
-- ==============================================================================
-- Objetivo:    Garantir que fatos com chaves nulas ou registros ainda não cadastrados
--              nas fontes dimensionais não quebrem a carga referencial (Early Arriving Facts).
-- Padrão:      DIMENSION_KEY = -1, ID = -1, SIN_ATIVO = 'N', DTC_EFETIVACAO = 1900-01-01,
--              DTC_EXPIRACAO = NULL (vigente), DES_ATUALIZAR = 'N', texto 'NAO INFORMADO'.
-- Execução:    DEVE ser executado antes da criação de FKs ou da primeira carga da Fato.
-- ==============================================================================

-- 1. Dimensão Entidade 1
MERGE INTO "<SCHEMA_ALVO>"."DIM_<SISTEMA>_<DOMINIO>_<ENTIDADE_1>" T
USING (
  SELECT 
    -1 AS DIMENSION_KEY, 
    -1 AS ID_<ENTIDADE_1>, 
    'N/I' AS SIGLA_<ENTIDADE_1>, 
    'NAO INFORMADO / DESCONHECIDO' AS DS_<ENTIDADE_1>, 
    'N/A' AS TIPO_<ENTIDADE_1>,
    'N' AS SIN_ATIVO,
    -1 AS COD_IBGE,
    TO_DATE('1900-01-01', 'YYYY-MM-DD') AS DTC_EFETIVACAO, 
    NULL AS DTC_EXPIRACAO, 
    'N' AS DES_ATUALIZAR
  FROM DUAL
) S
ON (T.DIMENSION_KEY = S.DIMENSION_KEY)
WHEN NOT MATCHED THEN
  INSERT (
    DIMENSION_KEY, 
    ID_<ENTIDADE_1>, 
    SIGLA_<ENTIDADE_1>, 
    DS_<ENTIDADE_1>, 
    TIPO_<ENTIDADE_1>,
    SIN_ATIVO, 
    COD_IBGE,
    DTC_EFETIVACAO, 
    DTC_EXPIRACAO, 
    DES_ATUALIZAR
  )
  VALUES (
    S.DIMENSION_KEY, 
    S.ID_<ENTIDADE_1>, 
    S.SIGLA_<ENTIDADE_1>, 
    S.DS_<ENTIDADE_1>, 
    S.TIPO_<ENTIDADE_1>,
    S.SIN_ATIVO, 
    S.COD_IBGE,
    S.DTC_EFETIVACAO, 
    S.DTC_EXPIRACAO, 
    S.DES_ATUALIZAR
  );

-- 2. Dimensão Entidade 2
MERGE INTO "<SCHEMA_ALVO>"."DIM_<SISTEMA>_<DOMINIO>_<ENTIDADE_2>" T
USING (
  SELECT 
    -1 AS DIMENSION_KEY, 
    -1 AS ID_<ENTIDADE_2>, 
    'N/I' AS SIGLA_<ENTIDADE_2>, 
    'NAO INFORMADO / DESCONHECIDO' AS DS_<ENTIDADE_2>, 
    'N/A' AS TIPO_<ENTIDADE_2>,
    'N' AS SIN_ATIVO,
    TO_DATE('1900-01-01', 'YYYY-MM-DD') AS DTC_EFETIVACAO, 
    NULL AS DTC_EXPIRACAO, 
    'N' AS DES_ATUALIZAR
  FROM DUAL
) S
ON (T.DIMENSION_KEY = S.DIMENSION_KEY)
WHEN NOT MATCHED THEN
  INSERT (
    DIMENSION_KEY, 
    ID_<ENTIDADE_2>, 
    SIGLA_<ENTIDADE_2>, 
    DS_<ENTIDADE_2>, 
    TIPO_<ENTIDADE_2>,
    SIN_ATIVO, 
    DTC_EFETIVACAO, 
    DTC_EXPIRACAO, 
    DES_ATUALIZAR
  )
  VALUES (
    S.DIMENSION_KEY, 
    S.ID_<ENTIDADE_2>, 
    S.SIGLA_<ENTIDADE_2>, 
    S.DS_<ENTIDADE_2>, 
    S.TIPO_<ENTIDADE_2>,
    S.SIN_ATIVO, 
    S.DTC_EFETIVACAO, 
    S.DTC_EXPIRACAO, 
    S.DES_ATUALIZAR
  );

COMMIT;

