-- =============================================================
-- INSERTS / MERGES — META_ORIENTACAO_IA
-- =============================================================
-- Catálogo de orientações e diretrizes de IA para geração de SQL
-- sobre a camada semântica (Oracle 12c+).
--
-- COMPORTAMENTO IDEMPOTENTE (INSERIR / ACRESCENTAR):
-- Utiliza MERGE INTO com base em (PROJETO, SECAO, ORDEM).
-- - Se o schema NÃO possuía os registros: insere todas as orientações.
-- - Se o schema JÁ possuía as orientações: atualiza o conteúdo sem duplicar
--   e apenas acrescenta as que faltarem.
--
-- O escopo padrão é 'GLOBAL' (diretrizes universais). Para regras
-- específicas de um projeto, substitua 'GLOBAL' pelo identificador do projeto.
-- =============================================================

-- =============================================================
-- SEÇÃO 1: WORKFLOW (Fluxo de raciocínio da IA)
-- =============================================================

MERGE INTO META_ORIENTACAO_IA T
USING (SELECT 'GLOBAL' AS PROJETO, 'WORKFLOW' AS SECAO, 1 AS ORDEM FROM DUAL) S
ON (T.PROJETO = S.PROJETO AND T.SECAO = S.SECAO AND T.ORDEM = S.ORDEM)
WHEN MATCHED THEN
    UPDATE SET T.TITULO = 'Identifique o escopo da pergunta',
               T.CONTEUDO = q'[Identifique o tema, as entidades, as métricas, o período e o nível de detalhamento solicitados. Não gere SQL antes de compreender esses elementos.]'
WHEN NOT MATCHED THEN
    INSERT (PROJETO, SECAO, ORDEM, TITULO, CONTEUDO)
    VALUES ('GLOBAL', 'WORKFLOW', 1, 'Identifique o escopo da pergunta',
            q'[Identifique o tema, as entidades, as métricas, o período e o nível de detalhamento solicitados. Não gere SQL antes de compreender esses elementos.]');

MERGE INTO META_ORIENTACAO_IA T
USING (SELECT 'GLOBAL' AS PROJETO, 'WORKFLOW' AS SECAO, 2 AS ORDEM FROM DUAL) S
ON (T.PROJETO = S.PROJETO AND T.SECAO = S.SECAO AND T.ORDEM = S.ORDEM)
WHEN MATCHED THEN
    UPDATE SET T.TITULO = 'Consulte o glossário',
               T.CONTEUDO = q'[Consulte META_GLOSSARIO para relacionar os termos e sinônimos usados pelo usuário aos conceitos, indicadores, objetos e colunas oficiais da camada semântica.]'
WHEN NOT MATCHED THEN
    INSERT (PROJETO, SECAO, ORDEM, TITULO, CONTEUDO)
    VALUES ('GLOBAL', 'WORKFLOW', 2, 'Consulte o glossário',
            q'[Consulte META_GLOSSARIO para relacionar os termos e sinônimos usados pelo usuário aos conceitos, indicadores, objetos e colunas oficiais da camada semântica.]');

MERGE INTO META_ORIENTACAO_IA T
USING (SELECT 'GLOBAL' AS PROJETO, 'WORKFLOW' AS SECAO, 3 AS ORDEM FROM DUAL) S
ON (T.PROJETO = S.PROJETO AND T.SECAO = S.SECAO AND T.ORDEM = S.ORDEM)
WHEN MATCHED THEN
    UPDATE SET T.TITULO = 'Procure uma consulta de negócio',
               T.CONTEUDO = q'[Consulte META_CONSULTA_NEGOCIO para verificar se existe uma pergunta semelhante já documentada. Quando existir, utilize o SQL de referência e respeite os parâmetros, observações e objetos-chave cadastrados.]'
WHEN NOT MATCHED THEN
    INSERT (PROJETO, SECAO, ORDEM, TITULO, CONTEUDO)
    VALUES ('GLOBAL', 'WORKFLOW', 3, 'Procure uma consulta de negócio',
            q'[Consulte META_CONSULTA_NEGOCIO para verificar se existe uma pergunta semelhante já documentada. Quando existir, utilize o SQL de referência e respeite os parâmetros, observações e objetos-chave cadastrados.]');

MERGE INTO META_ORIENTACAO_IA T
USING (SELECT 'GLOBAL' AS PROJETO, 'WORKFLOW' AS SECAO, 4 AS ORDEM FROM DUAL) S
ON (T.PROJETO = S.PROJETO AND T.SECAO = S.SECAO AND T.ORDEM = S.ORDEM)
WHEN MATCHED THEN
    UPDATE SET T.TITULO = 'Identifique os objetos adequados',
               T.CONTEUDO = q'[Consulte META_OBJETO para localizar as views governadas e ativas compatíveis com o domínio, o tipo de análise e o grão solicitado.]'
WHEN NOT MATCHED THEN
    INSERT (PROJETO, SECAO, ORDEM, TITULO, CONTEUDO)
    VALUES ('GLOBAL', 'WORKFLOW', 4, 'Identifique os objetos adequados',
            q'[Consulte META_OBJETO para localizar as views governadas e ativas compatíveis com o domínio, o tipo de análise e o grão solicitado.]');

MERGE INTO META_ORIENTACAO_IA T
USING (SELECT 'GLOBAL' AS PROJETO, 'WORKFLOW' AS SECAO, 5 AS ORDEM FROM DUAL) S
ON (T.PROJETO = S.PROJETO AND T.SECAO = S.SECAO AND T.ORDEM = S.ORDEM)
WHEN MATCHED THEN
    UPDATE SET T.TITULO = 'Consulte a definição da métrica',
               T.CONTEUDO = q'[Consulte META_METRICA antes de calcular qualquer indicador. Respeite a fórmula SQL, o tipo de aditividade, a data de referência, os filtros obrigatórios, as dimensões permitidas e a unidade de medida.]'
WHEN NOT MATCHED THEN
    INSERT (PROJETO, SECAO, ORDEM, TITULO, CONTEUDO)
    VALUES ('GLOBAL', 'WORKFLOW', 5, 'Consulte a definição da métrica',
            q'[Consulte META_METRICA antes de calcular qualquer indicador. Respeite a fórmula SQL, o tipo de aditividade, a data de referência, os filtros obrigatórios, as dimensões permitidas e a unidade de medida.]');

MERGE INTO META_ORIENTACAO_IA T
USING (SELECT 'GLOBAL' AS PROJETO, 'WORKFLOW' AS SECAO, 6 AS ORDEM FROM DUAL) S
ON (T.PROJETO = S.PROJETO AND T.SECAO = S.SECAO AND T.ORDEM = S.ORDEM)
WHEN MATCHED THEN
    UPDATE SET T.TITULO = 'Monte apenas relacionamentos documentados',
               T.CONTEUDO = q'[Quando a consulta exigir mais de uma view, consulte META_RELACIONAMENTO e utilize somente os caminhos de JOIN documentados. Não deduza relacionamentos apenas pela semelhança entre nomes de colunas.]'
WHEN NOT MATCHED THEN
    INSERT (PROJETO, SECAO, ORDEM, TITULO, CONTEUDO)
    VALUES ('GLOBAL', 'WORKFLOW', 6, 'Monte apenas relacionamentos documentados',
            q'[Quando a consulta exigir mais de uma view, consulte META_RELACIONAMENTO e utilize somente os caminhos de JOIN documentados. Não deduza relacionamentos apenas pela semelhança entre nomes de colunas.]');

MERGE INTO META_ORIENTACAO_IA T
USING (SELECT 'GLOBAL' AS PROJETO, 'WORKFLOW' AS SECAO, 7 AS ORDEM FROM DUAL) S
ON (T.PROJETO = S.PROJETO AND T.SECAO = S.SECAO AND T.ORDEM = S.ORDEM)
WHEN MATCHED THEN
    UPDATE SET T.TITULO = 'Valide os valores de filtro',
               T.CONTEUDO = q'[Consulte META_VALOR_DOMINIO antes de aplicar filtros sobre colunas categóricas. Utilize os valores exatos e ativos cadastrados para o objeto e a coluna correspondente.]'
WHEN NOT MATCHED THEN
    INSERT (PROJETO, SECAO, ORDEM, TITULO, CONTEUDO)
    VALUES ('GLOBAL', 'WORKFLOW', 7, 'Valide os valores de filtro',
            q'[Consulte META_VALOR_DOMINIO antes de aplicar filtros sobre colunas categóricas. Utilize os valores exatos e ativos cadastrados para o objeto e a coluna correspondente.]');

MERGE INTO META_ORIENTACAO_IA T
USING (SELECT 'GLOBAL' AS PROJETO, 'WORKFLOW' AS SECAO, 8 AS ORDEM FROM DUAL) S
ON (T.PROJETO = S.PROJETO AND T.SECAO = S.SECAO AND T.ORDEM = S.ORDEM)
WHEN MATCHED THEN
    UPDATE SET T.TITULO = 'Valide todas as regras aplicáveis',
               T.CONTEUDO = q'[Consulte META_REGRA_NEGOCIO e avalie todas as regras aplicáveis aos objetos e métricas utilizados. Reescreva o SQL quando houver violação de uma regra CRITICA.]'
WHEN NOT MATCHED THEN
    INSERT (PROJETO, SECAO, ORDEM, TITULO, CONTEUDO)
    VALUES ('GLOBAL', 'WORKFLOW', 8, 'Valide todas as regras aplicáveis',
            q'[Consulte META_REGRA_NEGOCIO e avalie todas as regras aplicáveis aos objetos e métricas utilizados. Reescreva o SQL quando houver violação de uma regra CRITICA.]');

MERGE INTO META_ORIENTACAO_IA T
USING (SELECT 'GLOBAL' AS PROJETO, 'WORKFLOW' AS SECAO, 9 AS ORDEM FROM DUAL) S
ON (T.PROJETO = S.PROJETO AND T.SECAO = S.SECAO AND T.ORDEM = S.ORDEM)
WHEN MATCHED THEN
    UPDATE SET T.TITULO = 'Defina a granularidade temporal',
               T.CONTEUDO = q'[Identifique se a pergunta solicita análise diária, mensal ou de um período maior. Para análise diária, priorize as views VW_<PROJETO>_KPI_%_DIA. Para análise mensal, priorize as views VW_<PROJETO>_KPI_%_MES. Para períodos maiores, verifique a aditividade da métrica antes de agregar os resultados.]'
WHEN NOT MATCHED THEN
    INSERT (PROJETO, SECAO, ORDEM, TITULO, CONTEUDO)
    VALUES ('GLOBAL', 'WORKFLOW', 9, 'Defina a granularidade temporal',
            q'[Identifique se a pergunta solicita análise diária, mensal ou de um período maior. Para análise diária, priorize as views VW_<PROJETO>_KPI_%_DIA. Para análise mensal, priorize as views VW_<PROJETO>_KPI_%_MES. Para períodos maiores, verifique a aditividade da métrica antes de agregar os resultados.]');

-- =============================================================
-- SEÇÃO 2: PRINCIPIO (Princípios de interpretação e modelagem)
-- =============================================================

MERGE INTO META_ORIENTACAO_IA T
USING (SELECT 'GLOBAL' AS PROJETO, 'PRINCIPIO' AS SECAO, 1 AS ORDEM FROM DUAL) S
ON (T.PROJETO = S.PROJETO AND T.SECAO = S.SECAO AND T.ORDEM = S.ORDEM)
WHEN MATCHED THEN
    UPDATE SET T.TITULO = 'Use somente objetos oficiais',
               T.CONTEUDO = q'[Utilize somente objetos registrados como governados e ativos na META_OBJETO. Nunca utilize objetos cujo nome termine em _BKP.]'
WHEN NOT MATCHED THEN
    INSERT (PROJETO, SECAO, ORDEM, TITULO, CONTEUDO)
    VALUES ('GLOBAL', 'PRINCIPIO', 1, 'Use somente objetos oficiais',
            q'[Utilize somente objetos registrados como governados e ativos na META_OBJETO. Nunca utilize objetos cujo nome termine em _BKP.]');

MERGE INTO META_ORIENTACAO_IA T
USING (SELECT 'GLOBAL' AS PROJETO, 'PRINCIPIO' AS SECAO, 2 AS ORDEM FROM DUAL) S
ON (T.PROJETO = S.PROJETO AND T.SECAO = S.SECAO AND T.ORDEM = S.ORDEM)
WHEN MATCHED THEN
    UPDATE SET T.TITULO = 'Priorize as views KPI',
               T.CONTEUDO = q'[Para consultas agregadas por mês, priorize as views VW_<PROJETO>_KPI_%. Utilize as views VW_<PROJETO>_EVENTO_% para detalhamento, auditoria, contagens distintas ou recálculo de métricas não aditivas.]'
WHEN NOT MATCHED THEN
    INSERT (PROJETO, SECAO, ORDEM, TITULO, CONTEUDO)
    VALUES ('GLOBAL', 'PRINCIPIO', 2, 'Priorize as views KPI',
            q'[Para consultas agregadas por mês, priorize as views VW_<PROJETO>_KPI_%. Utilize as views VW_<PROJETO>_EVENTO_% para detalhamento, auditoria, contagens distintas ou recálculo de métricas não aditivas.]');

MERGE INTO META_ORIENTACAO_IA T
USING (SELECT 'GLOBAL' AS PROJETO, 'PRINCIPIO' AS SECAO, 3 AS ORDEM FROM DUAL) S
ON (T.PROJETO = S.PROJETO AND T.SECAO = S.SECAO AND T.ORDEM = S.ORDEM)
WHEN MATCHED THEN
    UPDATE SET T.TITULO = 'Respeite o grão dos objetos',
               T.CONTEUDO = q'[Verifique o grão registrado na META_OBJETO antes de agregar dados. As views de evento mantêm o grão das respectivas fatos e podem conter mais de uma linha para a mesma entidade de negócio.]'
WHEN NOT MATCHED THEN
    INSERT (PROJETO, SECAO, ORDEM, TITULO, CONTEUDO)
    VALUES ('GLOBAL', 'PRINCIPIO', 3, 'Respeite o grão dos objetos',
            q'[Verifique o grão registrado na META_OBJETO antes de agregar dados. As views de evento mantêm o grão das respectivas fatos e podem conter mais de uma linha para a mesma entidade de negócio.]');

MERGE INTO META_ORIENTACAO_IA T
USING (SELECT 'GLOBAL' AS PROJETO, 'PRINCIPIO' AS SECAO, 4 AS ORDEM FROM DUAL) S
ON (T.PROJETO = S.PROJETO AND T.SECAO = S.SECAO AND T.ORDEM = S.ORDEM)
WHEN MATCHED THEN
    UPDATE SET T.TITULO = 'Use as medidas de quantidade',
               T.CONTEUDO = q'[Utilize SUM dos campos QTD_* quando a medida estiver disponível e for compatível com a métrica. Utilize COUNT DISTINCT somente quando for necessário contar entidades únicas ou eliminar duplicidades decorrentes do grão.]'
WHEN NOT MATCHED THEN
    INSERT (PROJETO, SECAO, ORDEM, TITULO, CONTEUDO)
    VALUES ('GLOBAL', 'PRINCIPIO', 4, 'Use as medidas de quantidade',
            q'[Utilize SUM dos campos QTD_* quando a medida estiver disponível e for compatível com a métrica. Utilize COUNT DISTINCT somente quando for necessário contar entidades únicas ou eliminar duplicidades decorrentes do grão.]');

MERGE INTO META_ORIENTACAO_IA T
USING (SELECT 'GLOBAL' AS PROJETO, 'PRINCIPIO' AS SECAO, 5 AS ORDEM FROM DUAL) S
ON (T.PROJETO = S.PROJETO AND T.SECAO = S.SECAO AND T.ORDEM = S.ORDEM)
WHEN MATCHED THEN
    UPDATE SET T.TITULO = 'Trate o registro desconhecido',
               T.CONTEUDO = q'[O valor de chave -1 representa registro desconhecido, não identificado ou não aplicável. Exclua-o das contagens de entidades identificadas, mas preserve-o quando for necessário reconciliar as medidas com os totais físicos.]'
WHEN NOT MATCHED THEN
    INSERT (PROJETO, SECAO, ORDEM, TITULO, CONTEUDO)
    VALUES ('GLOBAL', 'PRINCIPIO', 5, 'Trate o registro desconhecido',
            q'[O valor de chave -1 representa registro desconhecido, não identificado ou não aplicável. Exclua-o das contagens de entidades identificadas, mas preserve-o quando for necessário reconciliar as medidas com os totais físicos.]');

MERGE INTO META_ORIENTACAO_IA T
USING (SELECT 'GLOBAL' AS PROJETO, 'PRINCIPIO' AS SECAO, 6 AS ORDEM FROM DUAL) S
ON (T.PROJETO = S.PROJETO AND T.SECAO = S.SECAO AND T.ORDEM = S.ORDEM)
WHEN MATCHED THEN
    UPDATE SET T.TITULO = 'Respeite a aditividade',
               T.CONTEUDO = q'[Não some percentuais, taxas, médias, medianas, contagens distintas ou outras métricas não aditivas. Recalcule essas métricas no contexto solicitado utilizando seus componentes ou os registros detalhados.]'
WHEN NOT MATCHED THEN
    INSERT (PROJETO, SECAO, ORDEM, TITULO, CONTEUDO)
    VALUES ('GLOBAL', 'PRINCIPIO', 6, 'Respeite a aditividade',
            q'[Não some percentuais, taxas, médias, medianas, contagens distintas ou outras métricas não aditivas. Recalcule essas métricas no contexto solicitado utilizando seus componentes ou os registros detalhados.]');

MERGE INTO META_ORIENTACAO_IA T
USING (SELECT 'GLOBAL' AS PROJETO, 'PRINCIPIO' AS SECAO, 7 AS ORDEM FROM DUAL) S
ON (T.PROJETO = S.PROJETO AND T.SECAO = S.SECAO AND T.ORDEM = S.ORDEM)
WHEN MATCHED THEN
    UPDATE SET T.TITULO = 'Diferencie cadastro vigente de histórico',
               T.CONTEUDO = q'[As views VW_<PROJETO>_DIM_%_ATUAL representam o cadastro vigente. Não interprete seus registros como uma fotografia histórica do mês analisado e não some a mesma população cadastral entre meses.]'
WHEN NOT MATCHED THEN
    INSERT (PROJETO, SECAO, ORDEM, TITULO, CONTEUDO)
    VALUES ('GLOBAL', 'PRINCIPIO', 7, 'Diferencie cadastro vigente de histórico',
            q'[As views VW_<PROJETO>_DIM_%_ATUAL representam o cadastro vigente. Não interprete seus registros como uma fotografia histórica do mês analisado e não some a mesma população cadastral entre meses.]');

MERGE INTO META_ORIENTACAO_IA T
USING (SELECT 'GLOBAL' AS PROJETO, 'PRINCIPIO' AS SECAO, 8 AS ORDEM FROM DUAL) S
ON (T.PROJETO = S.PROJETO AND T.SECAO = S.SECAO AND T.ORDEM = S.ORDEM)
WHEN MATCHED THEN
    UPDATE SET T.TITULO = 'Escolha entre KPI diário e mensal',
               T.CONTEUDO = q'[Utilize as views VW_<PROJETO>_KPI_%_DIA quando o usuário solicitar informações por dia ou em uma data específica. Utilize as views VW_<PROJETO>_KPI_%_MES quando o usuário solicitar informações mensais ou quando for necessário manter compatibilidade com consultas e painéis existentes.]'
WHEN NOT MATCHED THEN
    INSERT (PROJETO, SECAO, ORDEM, TITULO, CONTEUDO)
    VALUES ('GLOBAL', 'PRINCIPIO', 8, 'Escolha entre KPI diário e mensal',
            q'[Utilize as views VW_<PROJETO>_KPI_%_DIA quando o usuário solicitar informações por dia ou em uma data específica. Utilize as views VW_<PROJETO>_KPI_%_MES quando o usuário solicitar informações mensais ou quando for necessário manter compatibilidade com consultas e painéis existentes.]');

MERGE INTO META_ORIENTACAO_IA T
USING (SELECT 'GLOBAL' AS PROJETO, 'PRINCIPIO' AS SECAO, 9 AS ORDEM FROM DUAL) S
ON (T.PROJETO = S.PROJETO AND T.SECAO = S.SECAO AND T.ORDEM = S.ORDEM)
WHEN MATCHED THEN
    UPDATE SET T.TITULO = 'Não agregue métricas não aditivas',
               T.CONTEUDO = q'[Não some contagens distintas, percentuais, taxas, médias ou medianas provenientes das views diárias para produzir resultados mensais ou de períodos maiores. Recalcule essas métricas utilizando seus componentes ou diretamente sobre as views VW_<PROJETO>_EVENTO_%.]'
WHEN NOT MATCHED THEN
    INSERT (PROJETO, SECAO, ORDEM, TITULO, CONTEUDO)
    VALUES ('GLOBAL', 'PRINCIPIO', 9, 'Não agregue métricas não aditivas',
            q'[Não some contagens distintas, percentuais, taxas, médias ou medianas provenientes das views diárias para produzir resultados mensais ou de períodos maiores. Recalcule essas métricas utilizando seus componentes ou diretamente sobre as views VW_<PROJETO>_EVENTO_%.]');

MERGE INTO META_ORIENTACAO_IA T
USING (SELECT 'GLOBAL' AS PROJETO, 'PRINCIPIO' AS SECAO, 10 AS ORDEM FROM DUAL) S
ON (T.PROJETO = S.PROJETO AND T.SECAO = S.SECAO AND T.ORDEM = S.ORDEM)
WHEN MATCHED THEN
    UPDATE SET T.TITULO = 'Interprete a data diária corretamente',
               T.CONTEUDO = q'[Nas views VW_<PROJETO>_KPI_%_DIA, DATA_REFERENCIA representa o dia do evento utilizado pelo indicador. Em documentos representa geração; em tramitações representa abertura; em eficiência processual representa conclusão; em processos pode reunir indicadores apurados pelas datas de criação e conclusão.]'
WHEN NOT MATCHED THEN
    INSERT (PROJETO, SECAO, ORDEM, TITULO, CONTEUDO)
    VALUES ('GLOBAL', 'PRINCIPIO', 10, 'Interprete a data diária corretamente',
            q'[Nas views VW_<PROJETO>_KPI_%_DIA, DATA_REFERENCIA representa o dia do evento utilizado pelo indicador. Em documentos representa geração; em tramitações representa abertura; em eficiência processual representa conclusão; em processos pode reunir indicadores apurados pelas datas de criação e conclusão.]');

MERGE INTO META_ORIENTACAO_IA T
USING (SELECT 'GLOBAL' AS PROJETO, 'PRINCIPIO' AS SECAO, 11 AS ORDEM FROM DUAL) S
ON (T.PROJETO = S.PROJETO AND T.SECAO = S.SECAO AND T.ORDEM = S.ORDEM)
WHEN MATCHED THEN
    UPDATE SET T.TITULO = 'Diferencie atividade diária de cadastro vigente',
               T.CONTEUDO = q'[Nas views diárias de usuários, unidades e estrutura processual, as quantidades cadastradas representam o cadastro vigente no último refresh. Não interprete essas quantidades como fotografia histórica da DATA_REFERENCIA e não as some entre dias.]'
WHEN NOT MATCHED THEN
    INSERT (PROJETO, SECAO, ORDEM, TITULO, CONTEUDO)
    VALUES ('GLOBAL', 'PRINCIPIO', 11, 'Diferencie atividade diária de cadastro vigente',
            q'[Nas views diárias de usuários, unidades e estrutura processual, as quantidades cadastradas representam o cadastro vigente no último refresh. Não interprete essas quantidades como fotografia histórica da DATA_REFERENCIA e não as some entre dias.]');

-- =============================================================
-- SEÇÃO 3: VALIDACAO (Regras de validação pré-execução)
-- =============================================================

MERGE INTO META_ORIENTACAO_IA T
USING (SELECT 'GLOBAL' AS PROJETO, 'VALIDACAO' AS SECAO, 1 AS ORDEM FROM DUAL) S
ON (T.PROJETO = S.PROJETO AND T.SECAO = S.SECAO AND T.ORDEM = S.ORDEM)
WHEN MATCHED THEN
    UPDATE SET T.TITULO = 'Valide período e data de referência',
               T.CONTEUDO = q'[Confirme se o filtro temporal utiliza a data de referência indicada na META_METRICA. Em análises mensais, normalize a competência para o primeiro dia do mês.]'
WHEN NOT MATCHED THEN
    INSERT (PROJETO, SECAO, ORDEM, TITULO, CONTEUDO)
    VALUES ('GLOBAL', 'VALIDACAO', 1, 'Valide período e data de referência',
            q'[Confirme se o filtro temporal utiliza a data de referência indicada na META_METRICA. Em análises mensais, normalize a competência para o primeiro dia do mês.]');

MERGE INTO META_ORIENTACAO_IA T
USING (SELECT 'GLOBAL' AS PROJETO, 'VALIDACAO' AS SECAO, 2 AS ORDEM FROM DUAL) S
ON (T.PROJETO = S.PROJETO AND T.SECAO = S.SECAO AND T.ORDEM = S.ORDEM)
WHEN MATCHED THEN
    UPDATE SET T.TITULO = 'Valide filtros obrigatórios',
               T.CONTEUDO = q'[Antes de executar a consulta, confirme que todos os filtros obrigatórios da métrica foram aplicados e que os valores categóricos correspondem aos valores ativos da META_VALOR_DOMINIO.]'
WHEN NOT MATCHED THEN
    INSERT (PROJETO, SECAO, ORDEM, TITULO, CONTEUDO)
    VALUES ('GLOBAL', 'VALIDACAO', 2, 'Valide filtros obrigatórios',
            q'[Antes de executar a consulta, confirme que todos os filtros obrigatórios da métrica foram aplicados e que os valores categóricos correspondem aos valores ativos da META_VALOR_DOMINIO.]');

MERGE INTO META_ORIENTACAO_IA T
USING (SELECT 'GLOBAL' AS PROJETO, 'VALIDACAO' AS SECAO, 3 AS ORDEM FROM DUAL) S
ON (T.PROJETO = S.PROJETO AND T.SECAO = S.SECAO AND T.ORDEM = S.ORDEM)
WHEN MATCHED THEN
    UPDATE SET T.TITULO = 'Valide agregações',
               T.CONTEUDO = q'[Confirme que as dimensões de agrupamento são permitidas para a métrica e que percentuais, médias, medianas, saldos e contagens distintas foram recalculados corretamente.]'
WHEN NOT MATCHED THEN
    INSERT (PROJETO, SECAO, ORDEM, TITULO, CONTEUDO)
    VALUES ('GLOBAL', 'VALIDACAO', 3, 'Valide agregações',
            q'[Confirme que as dimensões de agrupamento são permitidas para a métrica e que percentuais, médias, medianas, saldos e contagens distintas foram recalculados corretamente.]');

MERGE INTO META_ORIENTACAO_IA T
USING (SELECT 'GLOBAL' AS PROJETO, 'VALIDACAO' AS SECAO, 4 AS ORDEM FROM DUAL) S
ON (T.PROJETO = S.PROJETO AND T.SECAO = S.SECAO AND T.ORDEM = S.ORDEM)
WHEN MATCHED THEN
    UPDATE SET T.TITULO = 'Valide os relacionamentos',
               T.CONTEUDO = q'[Confirme que todos os JOINs existem na META_RELACIONAMENTO. Utilize LEFT JOIN quando essa for a recomendação cadastrada e preserve o lado de origem do relacionamento.]'
WHEN NOT MATCHED THEN
    INSERT (PROJETO, SECAO, ORDEM, TITULO, CONTEUDO)
    VALUES ('GLOBAL', 'VALIDACAO', 4, 'Valide os relacionamentos',
            q'[Confirme que todos os JOINs existem na META_RELACIONAMENTO. Utilize LEFT JOIN quando essa for a recomendação cadastrada e preserve o lado de origem do relacionamento.]');

MERGE INTO META_ORIENTACAO_IA T
USING (SELECT 'GLOBAL' AS PROJETO, 'VALIDACAO' AS SECAO, 5 AS ORDEM FROM DUAL) S
ON (T.PROJETO = S.PROJETO AND T.SECAO = S.SECAO AND T.ORDEM = S.ORDEM)
WHEN MATCHED THEN
    UPDATE SET T.TITULO = 'Valide regras provisórias e pendentes',
               T.CONTEUDO = q'[Quando a resposta depender de regra PROVISORIA ou PENDENTE, informe claramente a limitação. Não apresente como homologado um conceito que ainda depende de validação funcional.]'
WHEN NOT MATCHED THEN
    INSERT (PROJETO, SECAO, ORDEM, TITULO, CONTEUDO)
    VALUES ('GLOBAL', 'VALIDACAO', 5, 'Valide regras provisórias e pendentes',
            q'[Quando a resposta depender de regra PROVISORIA ou PENDENTE, informe claramente a limitação. Não apresente como homologado um conceito que ainda depende de validação funcional.]');

MERGE INTO META_ORIENTACAO_IA T
USING (SELECT 'GLOBAL' AS PROJETO, 'VALIDACAO' AS SECAO, 6 AS ORDEM FROM DUAL) S
ON (T.PROJETO = S.PROJETO AND T.SECAO = S.SECAO AND T.ORDEM = S.ORDEM)
WHEN MATCHED THEN
    UPDATE SET T.TITULO = 'Valide a granularidade temporal',
               T.CONTEUDO = q'[Antes de executar a consulta, confirme que o objeto selecionado possui a granularidade temporal solicitada. Não utilize uma view mensal para responder uma pergunta diária quando existir uma view correspondente terminada em _DIA.]'
WHEN NOT MATCHED THEN
    INSERT (PROJETO, SECAO, ORDEM, TITULO, CONTEUDO)
    VALUES ('GLOBAL', 'VALIDACAO', 6, 'Valide a granularidade temporal',
            q'[Antes de executar a consulta, confirme que o objeto selecionado possui a granularidade temporal solicitada. Não utilize uma view mensal para responder uma pergunta diária quando existir uma view correspondente terminada em _DIA.]');

MERGE INTO META_ORIENTACAO_IA T
USING (SELECT 'GLOBAL' AS PROJETO, 'VALIDACAO' AS SECAO, 7 AS ORDEM FROM DUAL) S
ON (T.PROJETO = S.PROJETO AND T.SECAO = S.SECAO AND T.ORDEM = S.ORDEM)
WHEN MATCHED THEN
    UPDATE SET T.TITULO = 'Valide a agregação das views diárias',
               T.CONTEUDO = q'[Ao consolidar vários dias, some somente métricas aditivas. Para usuários, unidades e tipos processuais distintos, recalcule a contagem no detalhe. Para percentuais e taxas, some os componentes e recalcule a razão. Para médias e medianas, utilize os registros das views de evento.]'
WHEN NOT MATCHED THEN
    INSERT (PROJETO, SECAO, ORDEM, TITULO, CONTEUDO)
    VALUES ('GLOBAL', 'VALIDACAO', 7, 'Valide a agregação das views diárias',
            q'[Ao consolidar vários dias, some somente métricas aditivas. Para usuários, unidades e tipos processuais distintos, recalcule a contagem no detalhe. Para percentuais e taxas, some os componentes e recalcule a razão. Para médias e medianas, utilize os registros das views de evento.]');

MERGE INTO META_ORIENTACAO_IA T
USING (SELECT 'GLOBAL' AS PROJETO, 'VALIDACAO' AS SECAO, 8 AS ORDEM FROM DUAL) S
ON (T.PROJETO = S.PROJETO AND T.SECAO = S.SECAO AND T.ORDEM = S.ORDEM)
WHEN MATCHED THEN
    UPDATE SET T.TITULO = 'Valide a atualização dos dados',
               T.CONTEUDO = q'[As views VW_<PROJETO>_KPI_%_DIA são materializadas e refletem o último refresh executado. Quando a atualidade da informação for relevante, verifique a data máxima disponível e não presuma que existem dados para o dia atual.]'
WHEN NOT MATCHED THEN
    INSERT (PROJETO, SECAO, ORDEM, TITULO, CONTEUDO)
    VALUES ('GLOBAL', 'VALIDACAO', 8, 'Valide a atualização dos dados',
            q'[As views VW_<PROJETO>_KPI_%_DIA são materializadas e refletem o último refresh executado. Quando a atualidade da informação for relevante, verifique a data máxima disponível e não presuma que existem dados para o dia atual.]');

-- =============================================================
-- SEÇÃO 4: DESVIO (Tratamento de exceções e limitações)
-- =============================================================

MERGE INTO META_ORIENTACAO_IA T
USING (SELECT 'GLOBAL' AS PROJETO, 'DESVIO' AS SECAO, 1 AS ORDEM FROM DUAL) S
ON (T.PROJETO = S.PROJETO AND T.SECAO = S.SECAO AND T.ORDEM = S.ORDEM)
WHEN MATCHED THEN
    UPDATE SET T.TITULO = 'Pergunta fora do escopo',
               T.CONTEUDO = q'[Quando a pergunta não puder ser respondida pelos objetos governados, informe objetivamente a limitação e indique quais informações relacionadas estão disponíveis na camada semântica.]'
WHEN NOT MATCHED THEN
    INSERT (PROJETO, SECAO, ORDEM, TITULO, CONTEUDO)
    VALUES ('GLOBAL', 'DESVIO', 1, 'Pergunta fora do escopo',
            q'[Quando a pergunta não puder ser respondida pelos objetos governados, informe objetivamente a limitação e indique quais informações relacionadas estão disponíveis na camada semântica.]');

MERGE INTO META_ORIENTACAO_IA T
USING (SELECT 'GLOBAL' AS PROJETO, 'DESVIO' AS SECAO, 2 AS ORDEM FROM DUAL) S
ON (T.PROJETO = S.PROJETO AND T.SECAO = S.SECAO AND T.ORDEM = S.ORDEM)
WHEN MATCHED THEN
    UPDATE SET T.TITULO = 'Pergunta ambígua',
               T.CONTEUDO = q'[Quando a pergunta permitir interpretações com métricas, períodos ou entidades diferentes, apresente a interpretação adotada ou solicite apenas a informação indispensável para eliminar a ambiguidade.]'
WHEN NOT MATCHED THEN
    INSERT (PROJETO, SECAO, ORDEM, TITULO, CONTEUDO)
    VALUES ('GLOBAL', 'DESVIO', 2, 'Pergunta ambígua',
            q'[Quando a pergunta permitir interpretações com métricas, períodos ou entidades diferentes, apresente a interpretação adotada ou solicite apenas a informação indispensável para eliminar a ambiguidade.]');

MERGE INTO META_ORIENTACAO_IA T
USING (SELECT 'GLOBAL' AS PROJETO, 'DESVIO' AS SECAO, 3 AS ORDEM FROM DUAL) S
ON (T.PROJETO = S.PROJETO AND T.SECAO = S.SECAO AND T.ORDEM = S.ORDEM)
WHEN MATCHED THEN
    UPDATE SET T.TITULO = 'Informação ainda não homologada',
               T.CONTEUDO = q'[Quando a resposta depender de definição pendente, não invente regras nem valores. Informe que a definição necessita de homologação e apresente somente os resultados que possam ser calculados com as regras vigentes.]'
WHEN NOT MATCHED THEN
    INSERT (PROJETO, SECAO, ORDEM, TITULO, CONTEUDO)
    VALUES ('GLOBAL', 'DESVIO', 3, 'Informação ainda não homologada',
            q'[Quando a resposta depender de definição pendente, não invente regras nem valores. Informe que a definição necessita de homologação e apresente somente os resultados que possam ser calculados com as regras vigentes.]');

-- =============================================================
-- SEÇÃO 5: RESPOSTA (Formatação e entrega de respostas)
-- =============================================================

MERGE INTO META_ORIENTACAO_IA T
USING (SELECT 'GLOBAL' AS PROJETO, 'RESPOSTA' AS SECAO, 1 AS ORDEM FROM DUAL) S
ON (T.PROJETO = S.PROJETO AND T.SECAO = S.SECAO AND T.ORDEM = S.ORDEM)
WHEN MATCHED THEN
    UPDATE SET T.TITULO = 'Apresente o resultado com contexto',
               T.CONTEUDO = q'[Informe o resultado, o período analisado, a unidade de medida, o nível de agregação e os filtros relevantes utilizados.]'
WHEN NOT MATCHED THEN
    INSERT (PROJETO, SECAO, ORDEM, TITULO, CONTEUDO)
    VALUES ('GLOBAL', 'RESPOSTA', 1, 'Apresente o resultado com contexto',
            q'[Informe o resultado, o período analisado, a unidade de medida, o nível de agregação e os filtros relevantes utilizados.]');

MERGE INTO META_ORIENTACAO_IA T
USING (SELECT 'GLOBAL' AS PROJETO, 'RESPOSTA' AS SECAO, 2 AS ORDEM FROM DUAL) S
ON (T.PROJETO = S.PROJETO AND T.SECAO = S.SECAO AND T.ORDEM = S.ORDEM)
WHEN MATCHED THEN
    UPDATE SET T.TITULO = 'Informe as fontes utilizadas',
               T.CONTEUDO = q'[Identifique as views da camada semântica utilizadas na consulta e, quando aplicável, a métrica ou a consulta de negócio que serviu como referência.]'
WHEN NOT MATCHED THEN
    INSERT (PROJETO, SECAO, ORDEM, TITULO, CONTEUDO)
    VALUES ('GLOBAL', 'RESPOSTA', 2, 'Informe as fontes utilizadas',
            q'[Identifique as views da camada semântica utilizadas na consulta e, quando aplicável, a métrica ou a consulta de negócio que serviu como referência.]');

MERGE INTO META_ORIENTACAO_IA T
USING (SELECT 'GLOBAL' AS PROJETO, 'RESPOSTA' AS SECAO, 3 AS ORDEM FROM DUAL) S
ON (T.PROJETO = S.PROJETO AND T.SECAO = S.SECAO AND T.ORDEM = S.ORDEM)
WHEN MATCHED THEN
    UPDATE SET T.TITULO = 'Apresente ressalvas relevantes',
               T.CONTEUDO = q'[Informe limitações que possam alterar a interpretação, como uso de cadastro vigente, indicador provisório, ausência de snapshot histórico, métrica estimada ou regra pendente de homologação.]'
WHEN NOT MATCHED THEN
    INSERT (PROJETO, SECAO, ORDEM, TITULO, CONTEUDO)
    VALUES ('GLOBAL', 'RESPOSTA', 3, 'Apresente ressalvas relevantes',
            q'[Informe limitações que possam alterar a interpretação, como uso de cadastro vigente, indicador provisório, ausência de snapshot histórico, métrica estimada ou regra pendente de homologação.]');

MERGE INTO META_ORIENTACAO_IA T
USING (SELECT 'GLOBAL' AS PROJETO, 'RESPOSTA' AS SECAO, 4 AS ORDEM FROM DUAL) S
ON (T.PROJETO = S.PROJETO AND T.SECAO = S.SECAO AND T.ORDEM = S.ORDEM)
WHEN MATCHED THEN
    UPDATE SET T.TITULO = 'Mostre o SQL quando solicitado',
               T.CONTEUDO = q'[Quando o usuário solicitar o SQL, apresente a consulta final com os parâmetros claramente identificados e indique, quando aplicável, o ID_CONSULTA da META_CONSULTA_NEGOCIO utilizada como referência.]'
WHEN NOT MATCHED THEN
    INSERT (PROJETO, SECAO, ORDEM, TITULO, CONTEUDO)
    VALUES ('GLOBAL', 'RESPOSTA', 4, 'Mostre o SQL quando solicitado',
            q'[Quando o usuário solicitar o SQL, apresente a consulta final com os parâmetros claramente identificados e indique, quando aplicável, o ID_CONSULTA da META_CONSULTA_NEGOCIO utilizada como referência.]');

MERGE INTO META_ORIENTACAO_IA T
USING (SELECT 'GLOBAL' AS PROJETO, 'RESPOSTA' AS SECAO, 5 AS ORDEM FROM DUAL) S
ON (T.PROJETO = S.PROJETO AND T.SECAO = S.SECAO AND T.ORDEM = S.ORDEM)
WHEN MATCHED THEN
    UPDATE SET T.TITULO = 'Informe a granularidade utilizada',
               T.CONTEUDO = q'[Informe se o resultado foi calculado no nível diário, mensal ou consolidado por período. Quando utilizar uma view materializada diária, indique a DATA_REFERENCIA e, se relevante, esclareça que os dados correspondem ao último refresh disponível.]'
WHEN NOT MATCHED THEN
    INSERT (PROJETO, SECAO, ORDEM, TITULO, CONTEUDO)
    VALUES ('GLOBAL', 'RESPOSTA', 5, 'Informe a granularidade utilizada',
            q'[Informe se o resultado foi calculado no nível diário, mensal ou consolidado por período. Quando utilizar uma view materializada diária, indique a DATA_REFERENCIA e, se relevante, esclareça que os dados correspondem ao último refresh disponível.]');

COMMIT;
