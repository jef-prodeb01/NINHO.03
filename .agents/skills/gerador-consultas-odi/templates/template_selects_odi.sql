-- ============================================================================
-- PROJETO: <NOME_PROJETO>
-- ESQUEMA: <SCHEMA_ALVO>
-- DESCRICAO: CONSULTAS DE EXTRACAO E TRANSFORMACAO PARA ODI 12c (INTERFACES/MAPPINGS)
-- ORIGEM: STG_<NOME_PROJETO>
-- DESTINO: ODI_DIM_* (OU DIM_*) E FATO_<NOME_FATO>
-- ============================================================================

-- ============================================================================
-- 1. SELECT PARA CARGA DE DIMENSAO (EXEMPLO: DIM_ENTIDADE)
--    Granularidade: 1 linha por Chave Natural de Negocio
-- ============================================================================
SELECT 
    "<SCHEMA_ALVO>"."SEQ_DIM_<ENTIDADE>".NEXTVAL AS DIMENSION_KEY,
    COD_NATURAL_ORIGEM                           AS COD_<ENTIDADE>,
    MAX(NVL(NOM_ORIGEM, 'NAO INFORMADO'))        AS NOM_<ENTIDADE>,
    CASE 
        WHEN UPPER(MAX(NVL(DES_TIPO, ''))) LIKE '%EXTERNO%' THEN 'EXTERNO'
        ELSE 'INTERNO'
    END                                          AS DES_TIPO_<ENTIDADE>,
    -- Atributos de Controle SCD Tipo 2
    TRUNC(SYSDATE)                               AS DTC_EFETIVACAO,
    TO_DATE('2999-12-31', 'YYYY-MM-DD')          AS DTC_EXPIRACAO,
    'S'                                          AS DES_ATUALIZA
FROM "<SCHEMA_ALVO>"."STG_<TABELA_ORIGEM>"
WHERE COD_NATURAL_ORIGEM IS NOT NULL
GROUP BY COD_NATURAL_ORIGEM;


-- ============================================================================
-- 2. SELECT PARA CARGA DA FATO PRINCIPAL COM LOOKUPS E FALLBACK -1
--    Granularidade: <GRAO_DECLARADO_DA_FATO>
-- ============================================================================
SELECT 
    -- ------------------------------------------------------------------------
    -- CHAVES ESTRANGEIRAS RESOLVIDAS COM FALLBACK -1 (PROIBIDO FK NULA)
    -- ------------------------------------------------------------------------
    NVL(de.DIMENSION_KEY, -1)                    AS DIM_<ENTIDADE>,
    NVL(dt.DIMENSION_KEY, -1)                    AS DIM_TEMPO,

    -- ------------------------------------------------------------------------
    -- DEGENERATED DIMENSIONS (IDENTIFICADORES TRANSACIONAIS)
    -- ------------------------------------------------------------------------
    stg.NUM_TRANSACAO                            AS NUM_PROTOCOLO_DEGENERADA,

    -- ------------------------------------------------------------------------
    -- DATAS TRANSACIONAIS DO NEGOCIO
    -- ------------------------------------------------------------------------
    stg.DTC_REGISTRO                             AS DTC_EVENTO,

    -- ------------------------------------------------------------------------
    -- METRICAS E INDICADORES (NUMERICOS)
    -- ------------------------------------------------------------------------
    NVL(stg.VALOR_TOTAL, 0)                      AS VAL_TOTAL,
    NVL(stg.QUANTIDADE, 1)                       AS QTD_ITEM

FROM "<SCHEMA_ALVO>"."STG_<TABELA_ORIGEM>" stg

-- Lookups com dimensoes ativas (SCD Tipo 2)
LEFT JOIN "<SCHEMA_ALVO>"."DIM_<ENTIDADE>" de
    ON stg.COD_NATURAL_ORIGEM = de.COD_<ENTIDADE>
   AND de.DES_ATUALIZA = 'S'

LEFT JOIN "<SCHEMA_ALVO>"."DIM_TEMPO" dt
    ON TRUNC(stg.DTC_REGISTRO) = dt.DATA_COMPLETA;

