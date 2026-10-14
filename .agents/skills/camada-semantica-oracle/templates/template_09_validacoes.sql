-- =============================================================================
-- TEMPLATE OFICIAL: 09_validacoes.sql — AUDITORIA PÓS-IMPLANTAÇÃO (ORACLE 12c+)
-- =============================================================================
-- Destino: saida/camada_semantica/meta_projeto/09_validacoes.sql
-- Objetivo: Validar integridade referencial lógica entre as 8 tabelas META_*
--           e o dicionário de dados real do Oracle (USER_OBJECTS, USER_VIEWS,
--           USER_TAB_COMMENTS, USER_COL_COMMENTS), além de smoke test das views.
-- =============================================================================

PROMPT =========================================================================
PROMPT 1. VOLUMETRIA DAS 8 TABELAS META_* POR PROJETO (<PROJETO> E GLOBAL)
PROMPT =========================================================================
SELECT 'META_GLOSSARIO'        AS TABELA, PROJETO, COUNT(*) AS QTD_REGISTROS FROM META_GLOSSARIO        WHERE PROJETO IN ('GLOBAL', '<PROJETO>') GROUP BY PROJETO
UNION ALL
SELECT 'META_METRICA'          AS TABELA, PROJETO, COUNT(*) AS QTD_REGISTROS FROM META_METRICA          WHERE PROJETO IN ('GLOBAL', '<PROJETO>') GROUP BY PROJETO
UNION ALL
SELECT 'META_OBJETO'           AS TABELA, PROJETO, COUNT(*) AS QTD_REGISTROS FROM META_OBJETO           WHERE PROJETO IN ('GLOBAL', '<PROJETO>') GROUP BY PROJETO
UNION ALL
SELECT 'META_RELACIONAMENTO'   AS TABELA, PROJETO, COUNT(*) AS QTD_REGISTROS FROM META_RELACIONAMENTO   WHERE PROJETO IN ('GLOBAL', '<PROJETO>') GROUP BY PROJETO
UNION ALL
SELECT 'META_REGRA_NEGOCIO'    AS TABELA, PROJETO, COUNT(*) AS QTD_REGISTROS FROM META_REGRA_NEGOCIO    WHERE PROJETO IN ('GLOBAL', '<PROJETO>') GROUP BY PROJETO
UNION ALL
SELECT 'META_CONSULTA_NEGOCIO' AS TABELA, PROJETO, COUNT(*) AS QTD_REGISTROS FROM META_CONSULTA_NEGOCIO WHERE PROJETO IN ('GLOBAL', '<PROJETO>') GROUP BY PROJETO
UNION ALL
SELECT 'META_ORIENTACAO_IA'    AS TABELA, PROJETO, COUNT(*) AS QTD_REGISTROS FROM META_ORIENTACAO_IA    WHERE PROJETO IN ('GLOBAL', '<PROJETO>') GROUP BY PROJETO
UNION ALL
SELECT 'META_VALOR_DOMINIO'    AS TABELA, PROJETO, COUNT(*) AS QTD_REGISTROS FROM META_VALOR_DOMINIO    WHERE PROJETO IN ('GLOBAL', '<PROJETO>') GROUP BY PROJETO
ORDER BY 1, 2;

PROMPT =========================================================================
PROMPT 2. AUDITORIA DAS 36 ORIENTAÇÕES GLOBAIS DA IA (ESPERADO: 36 REGISTROS)
PROMPT =========================================================================
SELECT
    SECAO,
    COUNT(*) AS QTD_ITENS,
    CASE
        WHEN SECAO = 'WORKFLOW'  AND COUNT(*) >= 9  THEN 'OK'
        WHEN SECAO = 'PRINCIPIO' AND COUNT(*) >= 11 THEN 'OK'
        WHEN SECAO = 'VALIDACAO' AND COUNT(*) >= 8  THEN 'OK'
        WHEN SECAO = 'DESVIO'    AND COUNT(*) >= 3  THEN 'OK'
        WHEN SECAO = 'RESPOSTA'  AND COUNT(*) >= 5  THEN 'OK'
        ELSE 'ALERTA: CONTAGEM ABAIXO DO CATÁLOGO PADRÃO'
    END AS STATUS_CATALOGO
FROM
    META_ORIENTACAO_IA
WHERE
    PROJETO = 'GLOBAL'
GROUP BY
    SECAO
ORDER BY
    SECAO;

PROMPT =========================================================================
PROMPT 3. VERIFICAÇÃO DE OBJETOS ÓRFÃOS (META_RELACIONAMENTO -> META_OBJETO)
PROMPT    (Esperado: 0 linhas retornadas)
PROMPT =========================================================================
SELECT
    R.PROJETO,
    R.OBJETO_ORIGEM,
    R.OBJETO_DESTINO,
    'OBJETO_ORIGEM NÃO CADASTRADO EM META_OBJETO' AS DIAGNOSTICO
FROM
    META_RELACIONAMENTO R
WHERE
    R.PROJETO = '<PROJETO>'
    AND NOT EXISTS (
        SELECT 1 FROM META_OBJETO O
        WHERE O.PROJETO IN ('GLOBAL', R.PROJETO)
          AND O.NOME_OBJETO = R.OBJETO_ORIGEM
    )
UNION ALL
SELECT
    R.PROJETO,
    R.OBJETO_ORIGEM,
    R.OBJETO_DESTINO,
    'OBJETO_DESTINO NÃO CADASTRADO EM META_OBJETO' AS DIAGNOSTICO
FROM
    META_RELACIONAMENTO R
WHERE
    R.PROJETO = '<PROJETO>'
    AND NOT EXISTS (
        SELECT 1 FROM META_OBJETO O
        WHERE O.PROJETO IN ('GLOBAL', R.PROJETO)
          AND O.NOME_OBJETO = R.OBJETO_DESTINO
    );

PROMPT =========================================================================
PROMPT 4. VERIFICAÇÃO DE DOMÍNIOS ÓRFÃOS (META_VALOR_DOMINIO -> META_OBJETO)
PROMPT    (Esperado: 0 linhas retornadas)
PROMPT =========================================================================
SELECT
    V.PROJETO,
    V.NOME_OBJETO,
    V.NOME_COLUNA,
    'NOME_OBJETO NÃO CADASTRADO EM META_OBJETO' AS DIAGNOSTICO
FROM
    META_VALOR_DOMINIO V
WHERE
    V.PROJETO = '<PROJETO>'
    AND NOT EXISTS (
        SELECT 1 FROM META_OBJETO O
        WHERE O.PROJETO IN ('GLOBAL', V.PROJETO)
          AND O.NOME_OBJETO = V.NOME_OBJETO
    )
GROUP BY
    V.PROJETO, V.NOME_OBJETO, V.NOME_COLUNA;

PROMPT =========================================================================
PROMPT 5. ADERÊNCIA FÍSICA: META_OBJETO vs USER_OBJECTS (STATUS = VALID)
PROMPT    (Esperado: Todos os objetos com STATUS_FISICO = 'VALID')
PROMPT =========================================================================
SELECT
    O.PROJETO,
    O.NOME_OBJETO,
    O.TIPO_OBJETO,
    NVL(U.OBJECT_TYPE, 'NÃO ENCONTRADO NO SCHEMA') AS TIPO_FISICO,
    NVL(U.STATUS, 'INEXISTENTE')                   AS STATUS_FISICO
FROM
    META_OBJETO O
    LEFT JOIN USER_OBJECTS U
        ON U.OBJECT_NAME = O.NOME_OBJETO
       AND U.OBJECT_TYPE IN ('VIEW', 'MATERIALIZED VIEW', 'TABLE')
WHERE
    O.PROJETO = '<PROJETO>'
    AND O.IND_ATIVO = 'S'
ORDER BY
    O.TIPO_OBJETO, O.NOME_OBJETO;

PROMPT =========================================================================
PROMPT 6. AUDITORIA DE GRÃO CANÔNICO NAS VIEWS ('Uma linha representa%')
PROMPT    (Esperado: STATUS_GRAO = 'OK' para todas as views do projeto)
PROMPT =========================================================================
SELECT
    V.VIEW_NAME,
    CASE
        WHEN C.COMMENTS IS NULL THEN 'ERRO: SEM COMMENT ON TABLE'
        WHEN C.COMMENTS LIKE 'Uma linha representa%' THEN 'OK'
        ELSE 'ALERTA: COMENTÁRIO NÃO INICIA COM "Uma linha representa"'
    END AS STATUS_GRAO,
    SUBSTR(C.COMMENTS, 1, 120) AS RESUMO_COMENTARIO
FROM
    USER_VIEWS V
    LEFT JOIN USER_TAB_COMMENTS C
        ON C.TABLE_NAME = V.VIEW_NAME
WHERE
    V.VIEW_NAME LIKE 'VW_<PROJETO>_%'
ORDER BY
    V.VIEW_NAME;

PROMPT =========================================================================
PROMPT 7. AUDITORIA DE COLUNAS SEM COMENTÁRIO NAS VIEWS DO PROJETO
PROMPT    (Esperado: 0 linhas retornadas)
PROMPT =========================================================================
SELECT
    CC.TABLE_NAME AS VIEW_NAME,
    CC.COLUMN_NAME,
    'COLUNA SEM COMMENT ON COLUMN' AS DIAGNOSTICO
FROM
    USER_COL_COMMENTS CC
    INNER JOIN USER_VIEWS V
        ON V.VIEW_NAME = CC.TABLE_NAME
WHERE
    V.VIEW_NAME LIKE 'VW_<PROJETO>_%'
    AND (CC.COMMENTS IS NULL OR TRIM(CC.COMMENTS) IS NULL)
ORDER BY
    CC.TABLE_NAME, CC.COLUMN_NAME;

PROMPT =========================================================================
PROMPT 8. SMOKE TEST DE EXECUÇÃO DAS VIEWS ANALÍTICAS DO PROJETO
PROMPT =========================================================================
-- Substitua pelos nomes reais das views geradas para o projeto <PROJETO>:
SELECT 'VW_<PROJETO>_DIM_<DIMENSAO>_ATUAL'         AS OBJETO, COUNT(*) AS QTD_LINHAS FROM VW_<PROJETO>_DIM_<DIMENSAO>_ATUAL
UNION ALL
SELECT 'VW_<PROJETO>_EVENTO'                       AS OBJETO, COUNT(*) AS QTD_LINHAS FROM VW_<PROJETO>_EVENTO
UNION ALL
SELECT 'VW_<PROJETO>_KPI_<MEDIDA>_POR_<DIMENSAO>'  AS OBJETO, COUNT(*) AS QTD_LINHAS FROM VW_<PROJETO>_KPI_<MEDIDA>_POR_<DIMENSAO>;

