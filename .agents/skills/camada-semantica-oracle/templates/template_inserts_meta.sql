-- =============================================================================
-- TEMPLATE OFICIAL: CARGA IDEMPOTENTE (MERGE INTO) DAS 8 TABELAS META_*
-- =============================================================================
-- REGRAS OBRIGATÓRIAS:
-- 1. Gere 8 arquivos separados em saida/camada_semantica/meta_projeto/:
--    01_meta_glossario.sql
--    02_meta_metrica.sql
--    03_meta_objeto.sql
--    04_meta_relacionamento.sql
--    05_meta_regra_negocio.sql
--    06_meta_consulta_negocio.sql
--    07_meta_orientacao_ia.sql
--    08_meta_valor_dominio.sql
-- 2. Respeite ESTRITAMENTE os nomes de colunas e constraints de 01_create_meta_tables.sql.
-- 3. Sempre utilize MERGE INTO para garantir reexecução segura (idempotência) em
--    schemas compartilhados por múltiplos projetos.
-- 4. Finalize cada arquivo com COMMIT;
-- =============================================================================

-- =============================================================================
-- 1. ARQUIVO: 01_meta_glossario.sql (Tabela: META_GLOSSARIO)
--    PK: (PROJETO, IDENTIFICADOR)
--    CLASSIFICACAO sugerida: 'CONCEITO_DE_NEGOCIO', 'INDICADOR', 'OBJETO_SEMANTICO',
--                            'REGRA_TECNICA', 'CONCEITO_DE_MODELAGEM'
-- =============================================================================
MERGE INTO META_GLOSSARIO T
USING (
    SELECT
        '<PROJETO>'                                         AS PROJETO,
        '<DOMINIO>'                                         AS DOMINIO,
        '<IDENTIFICADOR>'                                   AS IDENTIFICADOR,
        '<DESCRICAO_FUNCIONAL_DO_CONCEITO>'                 AS DESCRICAO,
        '<SINONIMO_1>, <SINONIMO_2>, <SIGLA>'               AS SINONIMOS,
        '<EXEMPLO_1>, <EXEMPLO_2>'                          AS EXEMPLOS_VALORES,
        '<ORIENTACAO_PARA_FILTROS_E_AGRUPAMENTOS>'          AS REGRA_USO,
        'CONCEITO_DE_NEGOCIO'                               AS CLASSIFICACAO
    FROM DUAL
) S
ON (T.PROJETO = S.PROJETO AND T.IDENTIFICADOR = S.IDENTIFICADOR)
WHEN MATCHED THEN
    UPDATE SET
        T.DOMINIO          = S.DOMINIO,
        T.DESCRICAO        = S.DESCRICAO,
        T.SINONIMOS        = S.SINONIMOS,
        T.EXEMPLOS_VALORES = S.EXEMPLOS_VALORES,
        T.REGRA_USO        = S.REGRA_USO,
        T.CLASSIFICACAO    = S.CLASSIFICACAO
WHEN NOT MATCHED THEN
    INSERT (
        PROJETO, DOMINIO, IDENTIFICADOR, DESCRICAO,
        SINONIMOS, EXEMPLOS_VALORES, REGRA_USO, CLASSIFICACAO
    )
    VALUES (
        S.PROJETO, S.DOMINIO, S.IDENTIFICADOR, S.DESCRICAO,
        S.SINONIMOS, S.EXEMPLOS_VALORES, S.REGRA_USO, S.CLASSIFICACAO
    );

COMMIT;


-- =============================================================================
-- 2. ARQUIVO: 02_meta_metrica.sql (Tabela: META_METRICA)
--    PK: (PROJETO, NOME_METRICA)
--    CHK_META_METRICA_ADIT: TIPO_ADITIVIDADE IN ('ADITIVA', 'SEMI_ADITIVA', 'NAO_ADITIVA')
--    ATENÇÃO: NUNCA use hífen ou acento ('SEMI-ADITIVA' / 'NÃO-ADITIVA' são inválidos!).
-- =============================================================================
MERGE INTO META_METRICA T
USING (
    SELECT
        '<PROJETO>'                                         AS PROJETO,
        'QT_TOTAL_EVENTOS'                                  AS NOME_METRICA,
        'Quantidade total de eventos válidos no período.'   AS DESCRICAO_NEGOCIO,
        q'[SUM(E.QT_EVENTO)]'                               AS FORMULA_SQL,
        'ADITIVA'                                           AS TIPO_ADITIVIDADE,
        'DT_EVENTO (Competência Mensal CD_COMPETENCIA)'     AS DATA_REFERENCIA,
        'DS_STATUS_EVENTO <> ''CANCELADO'''                 AS FILTROS_OBRIGATORIOS,
        'Órgão, Unidade, Competência, Tipo de Evento'       AS DIMENSOES_PERMITIDAS,
        'Unidades'                                          AS UNIDADE
    FROM DUAL
) S
ON (T.PROJETO = S.PROJETO AND T.NOME_METRICA = S.NOME_METRICA)
WHEN MATCHED THEN
    UPDATE SET
        T.DESCRICAO_NEGOCIO    = S.DESCRICAO_NEGOCIO,
        T.FORMULA_SQL          = S.FORMULA_SQL,
        T.TIPO_ADITIVIDADE     = S.TIPO_ADITIVIDADE,
        T.DATA_REFERENCIA      = S.DATA_REFERENCIA,
        T.FILTROS_OBRIGATORIOS = S.FILTROS_OBRIGATORIOS,
        T.DIMENSOES_PERMITIDAS = S.DIMENSOES_PERMITIDAS,
        T.UNIDADE              = S.UNIDADE
WHEN NOT MATCHED THEN
    INSERT (
        PROJETO, NOME_METRICA, DESCRICAO_NEGOCIO, FORMULA_SQL,
        TIPO_ADITIVIDADE, DATA_REFERENCIA, FILTROS_OBRIGATORIOS,
        DIMENSOES_PERMITIDAS, UNIDADE
    )
    VALUES (
        S.PROJETO, S.NOME_METRICA, S.DESCRICAO_NEGOCIO, S.FORMULA_SQL,
        S.TIPO_ADITIVIDADE, S.DATA_REFERENCIA, S.FILTROS_OBRIGATORIOS,
        S.DIMENSOES_PERMITIDAS, S.UNIDADE
    );

COMMIT;


-- =============================================================================
-- 3. ARQUIVO: 03_meta_objeto.sql (Tabela: META_OBJETO)
--    PK: (PROJETO, NOME_OBJETO)
--    CHK_META_OBJ_TIPO: TIPO_OBJETO IN ('DIMENSAO', 'EVENTO', 'KPI', 'ALERTA')
--    CHK_META_OBJ_GOV / ATIVO: IND_GOVERNADO, IND_ATIVO IN ('S', 'N')
--    ATENÇÃO: NOME_OBJETO deve ser IDÊNTICO ao nome da View/Tabela em MAIÚSCULAS.
-- =============================================================================
MERGE INTO META_OBJETO T
USING (
    SELECT
        '<PROJETO>'                                         AS PROJETO,
        'VW_<PROJETO>_EVENTO'                               AS NOME_OBJETO,
        'EVENTO'                                            AS TIPO_OBJETO,
        '<DOMINIO>'                                         AS DOMINIO,
        'Uma linha representa um evento individual de <FATO>.' AS GRAO,
        '<SCHEMA_ALVO>'                                     AS SCHEMA_ORIGEM,
        'FATO_<FATO>'                                       AS OBJETO_FISICO,
        'S'                                                 AS IND_GOVERNADO,
        'S'                                                 AS IND_ATIVO,
        TRUNC(SYSDATE)                                      AS DT_INICIO_VIGENCIA,
        CAST(NULL AS DATE)                                  AS DT_FIM_VIGENCIA
    FROM DUAL
) S
ON (T.PROJETO = S.PROJETO AND T.NOME_OBJETO = S.NOME_OBJETO)
WHEN MATCHED THEN
    UPDATE SET
        T.TIPO_OBJETO        = S.TIPO_OBJETO,
        T.DOMINIO            = S.DOMINIO,
        T.GRAO               = S.GRAO,
        T.SCHEMA_ORIGEM      = S.SCHEMA_ORIGEM,
        T.OBJETO_FISICO      = S.OBJETO_FISICO,
        T.IND_GOVERNADO      = S.IND_GOVERNADO,
        T.IND_ATIVO          = S.IND_ATIVO,
        T.DT_FIM_VIGENCIA    = S.DT_FIM_VIGENCIA
WHEN NOT MATCHED THEN
    INSERT (
        PROJETO, NOME_OBJETO, TIPO_OBJETO, DOMINIO, GRAO,
        SCHEMA_ORIGEM, OBJETO_FISICO, IND_GOVERNADO, IND_ATIVO,
        DT_INICIO_VIGENCIA, DT_FIM_VIGENCIA
    )
    VALUES (
        S.PROJETO, S.NOME_OBJETO, S.TIPO_OBJETO, S.DOMINIO, S.GRAO,
        S.SCHEMA_ORIGEM, S.OBJETO_FISICO, S.IND_GOVERNADO, S.IND_ATIVO,
        S.DT_INICIO_VIGENCIA, S.DT_FIM_VIGENCIA
    );

COMMIT;


-- =============================================================================
-- 4. ARQUIVO: 04_meta_relacionamento.sql (Tabela: META_RELACIONAMENTO)
--    PK: ID_RELACIONAMENTO (IDENTITY)
--    UK: (PROJETO, OBJETO_ORIGEM, COLUNA_ORIGEM, OBJETO_DESTINO, COLUNA_DESTINO)
--    CHK: TIPO_JOIN IN ('LEFT', 'INNER', 'RIGHT', 'FULL')
--    CHK: CARDINALIDADE IN ('N:1', '1:1', '1:N', 'N:M')
--    ATENÇÃO: OBJETO_ORIGEM e OBJETO_DESTINO devem existir em META_OBJETO.NOME_OBJETO!
-- =============================================================================
MERGE INTO META_RELACIONAMENTO T
USING (
    SELECT
        '<PROJETO>'                                         AS PROJETO,
        'VW_<PROJETO>_EVENTO'                               AS OBJETO_ORIGEM,
        'SK_<DIMENSAO>'                                     AS COLUNA_ORIGEM,
        'VW_<PROJETO>_DIM_<DIMENSAO>_ATUAL'                 AS OBJETO_DESTINO,
        'SK_<DIMENSAO>'                                     AS COLUNA_DESTINO,
        'LEFT'                                              AS TIPO_JOIN,
        'N:1'                                               AS CARDINALIDADE,
        'Join padrão pela Surrogate Key com fallback para SK -1 (NÃO INFORMADO).' AS OBSERVACAO
    FROM DUAL
) S
ON (
    T.PROJETO        = S.PROJETO
    AND T.OBJETO_ORIGEM  = S.OBJETO_ORIGEM
    AND T.COLUNA_ORIGEM  = S.COLUNA_ORIGEM
    AND T.OBJETO_DESTINO = S.OBJETO_DESTINO
    AND T.COLUNA_DESTINO = S.COLUNA_DESTINO
)
WHEN MATCHED THEN
    UPDATE SET
        T.TIPO_JOIN     = S.TIPO_JOIN,
        T.CARDINALIDADE = S.CARDINALIDADE,
        T.OBSERVACAO    = S.OBSERVACAO
WHEN NOT MATCHED THEN
    INSERT (
        PROJETO, OBJETO_ORIGEM, COLUNA_ORIGEM,
        OBJETO_DESTINO, COLUNA_DESTINO, TIPO_JOIN,
        CARDINALIDADE, OBSERVACAO
    )
    VALUES (
        S.PROJETO, S.OBJETO_ORIGEM, S.COLUNA_ORIGEM,
        S.OBJETO_DESTINO, S.COLUNA_DESTINO, S.TIPO_JOIN,
        S.CARDINALIDADE, S.OBSERVACAO
    );

COMMIT;


-- =============================================================================
-- 5. ARQUIVO: 05_meta_regra_negocio.sql (Tabela: META_REGRA_NEGOCIO)
--    PK: ID_REGRA (IDENTITY) — Chave natural p/ MERGE: (PROJETO, REGRA)
--    CHK_META_REGRA_SEV: SEVERIDADE IN ('CRITICA', 'ALERTA', 'INFORMATIVA')
--    CHK_META_REGRA_STATUS: STATUS_REGRA IN ('HOMOLOGADA', 'PROVISORIA', 'PENDENTE', 'INATIVA')
-- =============================================================================
MERGE INTO META_REGRA_NEGOCIO T
USING (
    SELECT
        '<PROJETO>'                                         AS PROJETO,
        'Excluir eventos com DS_STATUS_EVENTO = ''CANCELADO'' do cômputo oficial de KPIs.' AS REGRA,
        'CRITICA'                                           AS SEVERIDADE,
        'HOMOLOGADA'                                        AS STATUS_REGRA,
        'VW_<PROJETO>_EVENTO / Views KPI'                   AS CONTEXTO,
        'Eventos cancelados permanecem na view de evento apenas para auditoria operacional.' AS OBSERVACAO
    FROM DUAL
) S
ON (T.PROJETO = S.PROJETO AND T.REGRA = S.REGRA)
WHEN MATCHED THEN
    UPDATE SET
        T.SEVERIDADE   = S.SEVERIDADE,
        T.STATUS_REGRA = S.STATUS_REGRA,
        T.CONTEXTO     = S.CONTEXTO,
        T.OBSERVACAO   = S.OBSERVACAO
WHEN NOT MATCHED THEN
    INSERT (
        PROJETO, REGRA, SEVERIDADE, STATUS_REGRA, CONTEXTO, OBSERVACAO
    )
    VALUES (
        S.PROJETO, S.REGRA, S.SEVERIDADE, S.STATUS_REGRA, S.CONTEXTO, S.OBSERVACAO
    );

COMMIT;


-- =============================================================================
-- 6. ARQUIVO: 06_meta_consulta_negocio.sql (Tabela: META_CONSULTA_NEGOCIO)
--    PK: (PROJETO, ID_CONSULTA)
--    REGRAS:
--    - Usar literal q'[...]' para armazenar SQL_VALIDADO_INTERPRETACAO.
--    - Usar sintaxe Oracle 12c+ (FETCH FIRST n ROWS ONLY, nunca LIMIT).
--    - Usar CTE PARAMETROS com CAST explícito de bind variables (:P_DT_INICIO, etc.).
-- =============================================================================
MERGE INTO META_CONSULTA_NEGOCIO T
USING (
    SELECT
        '<PROJETO>'                                         AS PROJETO,
        'Q001'                                              AS ID_CONSULTA,
        'Qual o total de eventos concluídos e o percentual dentro do prazo por órgão nos últimos 12 meses?' AS PERGUNTA_LINGUAGEM_NATURAL,
        'Painel Executivo <PROJETO>'                        AS PAINEL_RELACIONADO,
        'Utiliza a view pré-agregada de KPI mensal. Recalcula o percentual global da razão (NAO_ADITIVA).' AS OBSERVACOES,
        q'[WITH PARAMETROS AS (
    SELECT
        NVL(CAST(:P_ANO_INICIO AS NUMBER), EXTRACT(YEAR FROM ADD_MONTHS(SYSDATE, -12))) AS ANO_INICIO
    FROM DUAL
)
SELECT
    K.CD_<DIMENSAO>,
    K.NM_<DIMENSAO>,
    SUM(K.QT_TOTAL_EVENTOS)      AS QT_TOTAL_EVENTOS,
    SUM(K.QT_EVENTOS_CONCLUIDOS) AS QT_EVENTOS_CONCLUIDOS,
    ROUND(
        100.0 * SUM(K.QT_EVENTOS_CONCLUIDOS)
        / NULLIF(SUM(K.QT_TOTAL_EVENTOS), 0),
        2
    )                            AS PCT_CONCLUIDOS
FROM
    VW_<PROJETO>_KPI_<MEDIDA>_POR_<DIMENSAO> K
    CROSS JOIN PARAMETROS P
WHERE
    K.NR_ANO_EVENTO >= P.ANO_INICIO
GROUP BY
    K.CD_<DIMENSAO>,
    K.NM_<DIMENSAO>
ORDER BY
    QT_EVENTOS_CONCLUIDOS DESC
FETCH FIRST 20 ROWS ONLY]'                                  AS SQL_VALIDADO_INTERPRETACAO,
        'VW_<PROJETO>_KPI_<MEDIDA>_POR_<DIMENSAO>'          AS OBJETOS_CHAVE
    FROM DUAL
) S
ON (T.PROJETO = S.PROJETO AND T.ID_CONSULTA = S.ID_CONSULTA)
WHEN MATCHED THEN
    UPDATE SET
        T.PERGUNTA_LINGUAGEM_NATURAL = S.PERGUNTA_LINGUAGEM_NATURAL,
        T.PAINEL_RELACIONADO         = S.PAINEL_RELACIONADO,
        T.OBSERVACOES                = S.OBSERVACOES,
        T.SQL_VALIDADO_INTERPRETACAO = S.SQL_VALIDADO_INTERPRETACAO,
        T.OBJETOS_CHAVE              = S.OBJETOS_CHAVE
WHEN NOT MATCHED THEN
    INSERT (
        PROJETO, ID_CONSULTA, PERGUNTA_LINGUAGEM_NATURAL,
        PAINEL_RELACIONADO, OBSERVACOES, SQL_VALIDADO_INTERPRETACAO, OBJETOS_CHAVE
    )
    VALUES (
        S.PROJETO, S.ID_CONSULTA, S.PERGUNTA_LINGUAGEM_NATURAL,
        S.PAINEL_RELACIONADO, S.OBSERVACOES, S.SQL_VALIDADO_INTERPRETACAO, S.OBJETOS_CHAVE
    );

COMMIT;


-- =============================================================================
-- 7. ARQUIVO: 07_meta_orientacao_ia.sql (Tabela: META_ORIENTACAO_IA)
--    PK: ID_ORIENTACAO (IDENTITY) | UK: (PROJETO, SECAO, ORDEM)
--    CHK_META_ORIA_SECAO: SECAO IN ('WORKFLOW', 'PRINCIPIO', 'VALIDACAO', 'DESVIO', 'RESPOSTA')
--    NOTA: As 36 diretrizes universais usam PROJETO = 'GLOBAL' (ver references/catalogo_orientacoes_ia.md).
--          Diretrizes exclusivas do projeto usam PROJETO = '<PROJETO>'.
-- =============================================================================
MERGE INTO META_ORIENTACAO_IA T
USING (
    SELECT
        '<PROJETO>'                                         AS PROJETO,
        'PRINCIPIO'                                         AS SECAO,
        101                                                 AS ORDEM,
        'Prioridade de Uso das Views do Projeto <PROJETO>'  AS TITULO,
        q'[Para perguntas agregadas mensais por <DIMENSAO>, consulte prioritariamente VW_<PROJETO>_KPI_<MEDIDA>_POR_<DIMENSAO>. Utilize VW_<PROJETO>_EVENTO apenas quando o usuário solicitar detalhamento por protocolo ou data exata.]' AS CONTEUDO
    FROM DUAL
) S
ON (T.PROJETO = S.PROJETO AND T.SECAO = S.SECAO AND T.ORDEM = S.ORDEM)
WHEN MATCHED THEN
    UPDATE SET
        T.TITULO   = S.TITULO,
        T.CONTEUDO = S.CONTEUDO
WHEN NOT MATCHED THEN
    INSERT (PROJETO, SECAO, ORDEM, TITULO, CONTEUDO)
    VALUES (S.PROJETO, S.SECAO, S.ORDEM, S.TITULO, S.CONTEUDO);

COMMIT;


-- =============================================================================
-- 8. ARQUIVO: 08_meta_valor_dominio.sql (Tabela: META_VALOR_DOMINIO)
--    PK: ID_VALOR_DOMINIO (IDENTITY) — Chave natural p/ MERGE: (PROJETO, NOME_OBJETO, NOME_COLUNA, VALOR)
--    CHK_META_VD_ATIVO: IND_ATIVO IN ('S', 'N')
--    ATENÇÃO: NOME_OBJETO deve existir em META_OBJETO.NOME_OBJETO!
-- =============================================================================
MERGE INTO META_VALOR_DOMINIO T
USING (
    SELECT
        '<PROJETO>'                                         AS PROJETO,
        'VW_<PROJETO>_EVENTO'                               AS NOME_OBJETO,
        'DS_STATUS_EVENTO'                                  AS NOME_COLUNA,
        'CONCLUÍDO'                                         AS VALOR,
        'Evento finalizado com decisão administrativa ou atendimento encerrado.' AS DESCRICAO,
        'S'                                                 AS IND_ATIVO
    FROM DUAL
) S
ON (
    T.PROJETO         = S.PROJETO
    AND T.NOME_OBJETO = S.NOME_OBJETO
    AND T.NOME_COLUNA = S.NOME_COLUNA
    AND T.VALOR       = S.VALOR
)
WHEN MATCHED THEN
    UPDATE SET
        T.DESCRICAO = S.DESCRICAO,
        T.IND_ATIVO = S.IND_ATIVO
WHEN NOT MATCHED THEN
    INSERT (
        PROJETO, NOME_OBJETO, NOME_COLUNA, VALOR, DESCRICAO, IND_ATIVO
    )
    VALUES (
        S.PROJETO, S.NOME_OBJETO, S.NOME_COLUNA, S.VALOR, S.DESCRICAO, S.IND_ATIVO
    );

COMMIT;

