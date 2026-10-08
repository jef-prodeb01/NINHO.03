-- ============================================================================
-- SUÍTE DE TESTES DE INTEGRIDADE & SANIDADE ANALÍTICA PÓS-CARGA (SMOKE TESTS)
-- PROJETO: <NOME_PROJETO> | SCHEMA: <SCHEMA_OWNER>
-- OBJETIVO: Validar a integridade referencial, presença da linha -1,
--           ausência de nulos em FKs e status dos índices após o ETL.
-- ============================================================================

SET SERVEROUTPUT ON;
SET LINESIZE 200;
SET PAGESIZE 100;

PROMPT ========================================================================
PROMPT INICIANDO AUDITORIA DE INTEGRIDADE PÓS-CARGA: <NOME_PROJETO>
PROMPT ========================================================================

-- ----------------------------------------------------------------------------
-- TESTE 1: Auditoria da Última Execução na TB_CONTROLE_CARGA
-- Esperado: DES_STATUS_EXECUCAO = 'SUCESSO' e QTD_REGISTROS_ERRO = 0
-- ----------------------------------------------------------------------------
PROMPT [TESTE 1] Verificando status da última execução na TB_CONTROLE_CARGA...

SELECT 
    ID_CARGA,
    NOME_PROJETO,
    NOME_TABELA_ALVO,
    TIPO_CARGA,
    DATA_INICIO,
    DATA_FIM,
    ROUND((DATA_FIM - DATA_INICIO) * 86400, 2) AS TEMPO_SEGUNDOS,
    STATUS_EXECUCAO,
    QTD_LINHAS_PROCESSADAS,
    DES_MENSAGEM_ERRO
FROM "<SCHEMA_OWNER>"."TB_CONTROLE_CARGA"
WHERE NOME_PROJETO LIKE '%<NOME_PROJETO>%'
ORDER BY DATA_INICIO DESC
FETCH FIRST 5 ROWS ONLY;


-- ----------------------------------------------------------------------------
-- TESTE 2: Presença Obrigatória da Linha Técnica -1 em TODAS as Dimensões
-- Esperado: Exatamente 1 linha retornada por dimensão
-- ----------------------------------------------------------------------------
PROMPT [TESTE 2] Validando presença do registro padrão -1 nas dimensões...

SELECT 'DIM_TEMPO' AS TABELA, COUNT(*) AS QTD_MENOS_1 
FROM "<SCHEMA_OWNER>"."DIM_TEMPO" 
WHERE "DIMENSION_KEY" = -1
UNION ALL
SELECT '<DIM_ENTIDADE_1>', COUNT(*) 
FROM "<SCHEMA_OWNER>"."<DIM_ENTIDADE_1>" 
WHERE "DIMENSION_KEY" = -1
UNION ALL
SELECT '<DIM_ENTIDADE_2>', COUNT(*) 
FROM "<SCHEMA_OWNER>"."<DIM_ENTIDADE_2>" 
WHERE "DIMENSION_KEY" = -1;


-- ----------------------------------------------------------------------------
-- TESTE 3: Verificação de Chaves Estrangeiras NULAS na Tabela Fato
-- Esperado: ZERO linhas retornadas (FKs devem ser NOT NULL com NVL -> -1)
-- ----------------------------------------------------------------------------
PROMPT [TESTE 3] Verificando ocorrência de FKs NULAS na Fato...

SELECT 
    COUNT(*) AS TOTAL_LINHAS_FATO,
    SUM(CASE WHEN "<FK_DIM_TEMPO>" IS NULL THEN 1 ELSE 0 END) AS NULOS_TEMPO,
    SUM(CASE WHEN "<FK_DIM_ENTIDADE_1>" IS NULL THEN 1 ELSE 0 END) AS NULOS_DIM1,
    SUM(CASE WHEN "<FK_DIM_ENTIDADE_2>" IS NULL THEN 1 ELSE 0 END) AS NULOS_DIM2
FROM "<SCHEMA_OWNER>"."<FATO_TABELA>";


-- ----------------------------------------------------------------------------
-- TESTE 4: Verificação de Chaves Órfãs (Integridade Referencial Kimball)
-- Esperado: ZERO linhas retornadas em todas as checagens
-- ----------------------------------------------------------------------------
PROMPT [TESTE 4] Checando existência de Chaves Órfãs na Fato...

-- Checagem Fato -> Dimensão 1
SELECT '<DIM_ENTIDADE_1>' AS DIMENSAO_FALHA, COUNT(*) AS QTD_CHAVES_ORFAS
FROM "<SCHEMA_OWNER>"."<FATO_TABELA>" F
LEFT JOIN "<SCHEMA_OWNER>"."<DIM_ENTIDADE_1>" D 
    ON F."<FK_DIM_ENTIDADE_1>" = D."DIMENSION_KEY"
WHERE D."DIMENSION_KEY" IS NULL
UNION ALL
-- Checagem Fato -> Dimensão 2
SELECT '<DIM_ENTIDADE_2>', COUNT(*)
FROM "<SCHEMA_OWNER>"."<FATO_TABELA>" F
LEFT JOIN "<SCHEMA_OWNER>"."<DIM_ENTIDADE_2>" D 
    ON F."<FK_DIM_ENTIDADE_2>" = D."DIMENSION_KEY"
WHERE D."DIMENSION_KEY" IS NULL;


-- ----------------------------------------------------------------------------
-- TESTE 5: Status dos Índices pós PRC_POS_CARGA_FATO
-- Esperado: ZERO índices com status UNUSABLE ou INVALID
-- ----------------------------------------------------------------------------
PROMPT [TESTE 5] Validando status dos índices na Fato e Dimensões...

SELECT 
    TABLE_NAME,
    INDEX_NAME,
    INDEX_TYPE,
    STATUS
FROM USER_INDEXES
WHERE TABLE_NAME IN ('<FATO_TABELA>', '<DIM_ENTIDADE_1>', '<DIM_ENTIDADE_2>', 'DIM_TEMPO')
  AND STATUS <> 'VALID';


-- ----------------------------------------------------------------------------
-- TESTE 6: Reconciliação Quantitativa Staging vs. Fato (Lote Atual)
-- ----------------------------------------------------------------------------
PROMPT [TESTE 6] Comparando volumetria de Staging com Fato...

SELECT 
    (SELECT COUNT(*) FROM "<SCHEMA_OWNER>"."<STG_TABELA>") AS TOTAL_STAGING,
    (SELECT COUNT(*) FROM "<SCHEMA_OWNER>"."<FATO_TABELA>") AS TOTAL_FATO
FROM DUAL;

PROMPT ========================================================================
PROMPT AUDITORIA DE INTEGRIDADE CONCLUÍDA!
PROMPT ========================================================================

