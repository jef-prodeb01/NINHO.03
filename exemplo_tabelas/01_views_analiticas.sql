-- =============================================================
-- TEMPLATE — Views Analíticas (Oracle)
-- =============================================================
-- Arquitetura em 3 camadas:
-- 1. VIEWS DIM — Versão vigente da dimensão (SCD Type 2 filtrado)
-- 2. VIEWS EVENTO — FATO + JOINs com DIMs (camada intermediária)
-- 3. VIEWS KPI — Consolidadas para perguntas específicas
--
-- Este é um TEMPLATE genérico — adaptável a QUALQUER projeto DW.
-- Substitua os placeholders <...> pelos nomes do seu domínio.
--
-- TODOS os identificadores de banco devem ser EM MAIÚSCULAS.
-- Rode como o dono do schema do DW.
-- =============================================================

-- =============================================================
-- SEÇÃO 1 — VIEWS DIM (versão vigente)
-- =============================================================
-- As views DIM filtram apenas a versão vigente de cada dimensão
-- SCD Type 2 (dtc_expiracao IS NULL).
-- São usadas como base para as views EVENTO.

-- -------------------------------------------------------------
-- VW_<PROJETO>_DIM_<DIMENSAO>_ATUAL — versão vigente da dimensão
-- -------------------------------------------------------------
-- GRÃO: um registro por <objeto> vigente
-- ADITIVIDADE: N/A (dimensão)
CREATE OR REPLACE VIEW VW_<PROJETO>_DIM_<DIMENSAO>_ATUAL AS
SELECT
    <SK_COLUNA>                          AS SK_<DIMENSAO>,
    <ID_COLUNA>                          AS ID_<DIMENSAO>,
    <DESCRICAO_COLUNA>                   AS DESCRICAO_<DIMENSAO>,
    <CATEGORIA_COLUNA>                   AS CATEGORIA_<DIMENSAO>,
    <ATIVO_COLUNA>                       AS IND_ATIVO,
    <CODIGO_COLUNA>                      AS CODIGO_<DIMENSAO>
FROM DIM_<DIMENSAO>
WHERE DTC_EXPIRACAO IS NULL;

COMMENT ON TABLE VW_<PROJETO>_DIM_<DIMENSAO>_ATUAL IS
'Versão vigente da dimensão <DIMENSAO>. Grão: um registro por <OBJETO> vigente. FILTRO: DTC_EXPIRACAO IS NULL.';

COMMENT ON COLUMN VW_<PROJETO>_DIM_<DIMENSAO>_ATUAL.SK_<DIMENSAO> IS 'Chave substituta da versão vigente do <DIMENSAO>.';
COMMENT ON COLUMN VW_<PROJETO>_DIM_<DIMENSAO>_ATUAL.ID_<DIMENSAO> IS 'Identificador global de negócio do <DIMENSAO>.';
COMMENT ON COLUMN VW_<PROJETO>_DIM_<DIMENSAO>_ATUAL.DESCRICAO_<DIMENSAO> IS 'Descrição funcional do <DIMENSAO>.';
COMMENT ON COLUMN VW_<PROJETO>_DIM_<DIMENSAO>_ATUAL.CATEGORIA_<DIMENSAO> IS 'Categoria do <DIMENSAO>.';
COMMENT ON COLUMN VW_<PROJETO>_DIM_<DIMENSAO>_ATUAL.IND_ATIVO IS 'Indicador de situação ativa: S para sim, N para não.';
COMMENT ON COLUMN VW_<PROJETO>_DIM_<DIMENSAO>_ATUAL.CODIGO_<DIMENSAO> IS 'Código de referência do <DIMENSAO>.';

-- -------------------------------------------------------------
-- -------------------------------------------------------------
-- VW_<PROJETO>_DIM_<DIMENSAO2>_ATUAL — versão vigente da dimensão
-- -------------------------------------------------------------
CREATE OR REPLACE VIEW VW_<PROJETO>_DIM_<DIMENSAO2>_ATUAL AS
SELECT
    <SK_COLUNA>                          AS SK_<DIMENSAO2>,
    <ID_COLUNA>                          AS ID_<DIMENSAO2>,
    <DESCRICAO_COLUNA>                   AS DESCRICAO_<DIMENSAO2>,
    <CATEGORIA_COLUNA>                   AS CATEGORIA_<DIMENSAO2>,
    <ATIVO_COLUNA>                       AS IND_ATIVO,
    <CODIGO_COLUNA>                      AS CODIGO_<DIMENSAO2>
FROM DIM_<DIMENSAO2>
WHERE DTC_EXPIRACAO IS NULL;

COMMENT ON TABLE VW_<PROJETO>_DIM_<DIMENSAO2>_ATUAL IS
'Versão vigente da dimensão <DIMENSAO2>. Grão: um registro por <OBJETO> vigente. FILTRO: DTC_EXPIRACAO IS NULL.';

-- Repetir para cada dimensão SCD Type 2 do projeto.

-- =============================================================
-- SEÇÃO 2 — VIEWS EVENTO (camada intermediária)
-- =============================================================
-- As views EVENTO normalizam os dados brutos em registros
-- analíticos. Cada linha representa um evento com todas as
-- dimensões já resolvidas.
-- São a BASE para gerar views KPI.

-- -------------------------------------------------------------
-- VW_<PROJETO>_EVENTO — evento detalhado com dimensões
-- -------------------------------------------------------------
-- GRÃO: uma linha representa <descreva o que cada linha representa>
-- ADITIVIDADE: <aditiva / semi-aditiva / não-aditiva>
CREATE OR REPLACE VIEW VW_<PROJETO>_EVENTO AS
SELECT
    F.<FK_SK_DIMENSAO_1>                 AS SK_<DIMENSAO_1>,
    F.<FK_SK_DIMENSAO_2>                 AS SK_<DIMENSAO_2>,
    F.<FK_SK_DIMENSAO_3>                 AS SK_<DIMENSAO_3>,
    F.<FK_SK_TEMPO_CRIACAO>              AS SK_TEMPO_CRIACAO,
    F.<FK_SK_TEMPO_CONCLUSAO>            AS SK_TEMPO_CONCLUSAO,
    TC.<DT_COMPLETA>                     AS DT_CRIACAO,
    CASE WHEN F.<FK_SK_TEMPO_CONCLUSAO> <> -1 THEN TCO.<DT_COMPLETA> END AS DT_CONCLUSAO,
    D1.<ID_COLUNA>                       AS ID_<DIMENSAO_1>,
    D1.<DESCRICAO_COLUNA>                AS DESCRICAO_<DIMENSAO_1>,
    D1.<CATEGORIA_COLUNA>                AS CATEGORIA_<DIMENSAO_1>,
    D2.<ID_COLUNA>                       AS ID_<DIMENSAO_2>,
    D2.<DESCRICAO_COLUNA>                AS DESCRICAO_<DIMENSAO_2>,
    D2.<CATEGORIA_COLUNA>                AS CATEGORIA_<DIMENSAO_2>,
    D3.<ID_COLUNA>                       AS ID_<DIMENSAO_3>,
    D3.<DESCRICAO_COLUNA>                AS DESCRICAO_<DIMENSAO_3>,
    D3.<CATEGORIA_COLUNA>                AS CATEGORIA_<DIMENSAO_3>,
    F.<MEDIDA_1>                         AS <MEDIDA_1_NOME>,
    F.<MEDIDA_2>                         AS <MEDIDA_2_NOME>,
    F.<MEDIDA_3>                         AS <MEDIDA_3_NOME>,
    CASE WHEN F.<FK_SK_TEMPO_CONCLUSAO> <> -1 THEN 1 ELSE 0 END AS IND_CONCLUIDO,
    CASE WHEN F.<FK_SK_TEMPO_CONCLUSAO> = -1 THEN 1 ELSE 0 END AS IND_EM_ABERTO
FROM <FATO_PRINCIPAL> F
LEFT JOIN DIM_TEMPO TC ON TC.<DIMENSION_KEY> = F.<FK_SK_TEMPO_CRIACAO>
LEFT JOIN DIM_TEMPO TCO ON TCO.<DIMENSION_KEY> = F.<FK_SK_TEMPO_CONCLUSAO>
LEFT JOIN DIM_<DIMENSAO_1> D1 ON D1.<DIMENSION_KEY> = F.<FK_SK_DIMENSAO_1>
LEFT JOIN DIM_<DIMENSAO_2> D2 ON D2.<DIMENSION_KEY> = F.<FK_SK_DIMENSAO_2>
LEFT JOIN DIM_<DIMENSAO_3> D3 ON D3.<DIMENSION_KEY> = F.<FK_SK_DIMENSAO_3>
WHERE <FILTRO_ATIVO, SE HOUVER>;

COMMENT ON TABLE VW_<PROJETO>_EVENTO IS
'<descrição da view>. Grão: <descreva o que cada linha representa>. REGRA DE USO: <regras de uso específicas>. ADITIVIDADE: <aditividade das medidas>.';

COMMENT ON COLUMN VW_<PROJETO>_EVENTO.SK_<DIMENSAO_1> IS 'Chave substituta do <DIMENSAO_1>.';
COMMENT ON COLUMN VW_<PROJETO>_EVENTO.SK_<DIMENSAO_2> IS 'Chave substituta do <DIMENSAO_2>.';
COMMENT ON COLUMN VW_<PROJETO>_EVENTO.SK_<DIMENSAO_3> IS 'Chave substituta do <DIMENSAO_3>.';
COMMENT ON COLUMN VW_<PROJETO>_EVENTO.SK_TEMPO_CRIACAO IS 'Chave da data de criação ou geração do evento.';
COMMENT ON COLUMN VW_<PROJETO>_EVENTO.SK_TEMPO_CONCLUSAO IS 'Chave da data de conclusão; -1 representa data não identificada ou evento não concluído.';
COMMENT ON COLUMN VW_<PROJETO>_EVENTO.DT_CRIACAO IS 'Data de criação ou geração do evento.';
COMMENT ON COLUMN VW_<PROJETO>_EVENTO.DT_CONCLUSAO IS 'Data de conclusão do evento; nula quando não existe conclusão identificada.';
COMMENT ON COLUMN VW_<PROJETO>_EVENTO.DESCRICAO_<DIMENSAO_1> IS 'Descrição funcional do <DIMENSAO_1>.';
COMMENT ON COLUMN VW_<PROJETO>_EVENTO.CATEGORIA_<DIMENSAO_1> IS 'Categoria do <DIMENSAO_1>.';
COMMENT ON COLUMN VW_<PROJETO>_EVENTO.<MEDIDA_1_NOME> IS '<descrição da medida 1>. ADITIVA: <aditividade>.';
COMMENT ON COLUMN VW_<PROJETO>_EVENTO.<MEDIDA_2_NOME> IS '<descrição da medida 2>. ADITIVA: <aditividade>.';
COMMENT ON COLUMN VW_<PROJETO>_EVENTO.<MEDIDA_3_NOME> IS '<descrição da medida 3>. ADITIVA: <aditividade>.';
COMMENT ON COLUMN VW_<PROJETO>_EVENTO.IND_CONCLUIDO IS 'Indicador calculado: 1 quando existe chave de data de conclusão diferente de -1; 0 nos demais casos.';
COMMENT ON COLUMN VW_<PROJETO>_EVENTO.IND_EM_ABERTO IS 'Indicador calculado: 1 quando a chave de data de conclusão é -1; 0 nos demais casos.';

-- =============================================================
-- SEÇÃO 3 — VIEWS KPI (consolidadas para perguntas)
-- =============================================================
-- As views KPI são consolidadas para responder perguntas
-- específicas dos usuários. São geradas a partir das views
-- EVENTO e DIM.

-- -------------------------------------------------------------
-- VW_<PROJETO>_KPI_<MEDIDA>_POR_<DIMENSAO>_POR_MES
-- -------------------------------------------------------------
-- GRÃO: uma linha por <dimensao> por mês
-- ADITIVIDADE: <aditiva / semi-aditiva / não-aditiva>
CREATE OR REPLACE VIEW VW_<PROJETO>_KPI_<MEDIDA>_POR_<DIMENSAO>_POR_MES AS
WITH BASE AS
(
    SELECT
        E.SK_<DIMENSAO>,
        TRUNC(E.<COLUNA_DATA>, 'MM')          AS MES_REFERENCIA,
        COUNT(DISTINCT E.SK_<OBJETO_DISTINTO>) AS <MEDIDA_1>,
        SUM(E.<MEDIDA_2>)                     AS <MEDIDA_2_SOMA>,
        AVG(E.<MEDIDA_3>)                     AS <MEDIDA_3_MEDIA>
    FROM VW_<PROJETO>_EVENTO E
    WHERE E.<COLUNA_DATA> IS NOT NULL
      AND E.SK_<OBJETO_DISTINTO> <> -1
    GROUP BY
        E.SK_<DIMENSAO>,
        TRUNC(E.<COLUNA_DATA>, 'MM')
),
KPI_BASE AS
(
    SELECT
        D.<CODIGO_COLUNA>                     AS CODIGO_<DIMENSAO>,
        D.<DESCRICAO_COLUNA>                  AS DESCRICAO_<DIMENSAO>,
        B.SK_<DIMENSAO>                       AS SK_<DIMENSAO>,
        B.MES_REFERENCIA                      AS MES_REFERENCIA,
        TO_CHAR(B.MES_REFERENCIA, 'YYYYMM')   AS ANO_MES,
        NVL(B.<MEDIDA_1>, 0)                  AS <MEDIDA_1>,
        NVL(B.<MEDIDA_2_SOMA>, 0)             AS <MEDIDA_2_SOMA>,
        B.<MEDIDA_3_MEDIA>                    AS <MEDIDA_3_MEDIA>
    FROM BASE B
    INNER JOIN VW_<PROJETO>_DIM_<DIMENSAO>_ATUAL D
        ON D.SK_<DIMENSAO> = B.SK_<DIMENSAO>
)
SELECT
    CODIGO_<DIMENSAO>,
    DESCRICAO_<DIMENSAO>,
    SK_<DIMENSAO>,
    MES_REFERENCIA,
    ANO_MES,
    <MEDIDA_1>,
    <MEDIDA_2_SOMA>,
    <MEDIDA_3_MEDIA>
FROM KPI_BASE;

COMMENT ON TABLE VW_<PROJETO>_KPI_<MEDIDA>_POR_<DIMENSAO>_POR_MES IS
'<descrição da view KPI>. Grão: uma linha por <dimensao> por mês. ADITIVIDADE: <aditividade>. FONTE: VW_<PROJETO>_EVENTO.';

COMMENT ON COLUMN VW_<PROJETO>_KPI_<MEDIDA>_POR_<DIMENSAO>_POR_MES.CODIGO_<DIMENSAO> IS 'Código de referência do <DIMENSAO>.';
COMMENT ON COLUMN VW_<PROJETO>_KPI_<MEDIDA>_POR_<DIMENSAO>_POR_MES.DESCRICAO_<DIMENSAO> IS 'Descrição funcional do <DIMENSAO>.';
COMMENT ON COLUMN VW_<PROJETO>_KPI_<MEDIDA>_POR_<DIMENSAO>_POR_MES.SK_<DIMENSAO> IS 'Chave substituta do <DIMENSAO>.';
COMMENT ON COLUMN VW_<PROJETO>_KPI_<MEDIDA>_POR_<DIMENSAO>_POR_MES.MES_REFERENCIA IS 'Primeiro dia do mês de referência.';
COMMENT ON COLUMN VW_<PROJETO>_KPI_<MEDIDA>_POR_<DIMENSAO>_POR_MES.ANO_MES IS 'Identificador do mês no formato AAAAMM.';
COMMENT ON COLUMN VW_<PROJETO>_KPI_<MEDIDA>_POR_<DIMENSAO>_POR_MES.<MEDIDA_1> IS '<descrição da medida 1>. ADITIVA: <aditividade>.';
COMMENT ON COLUMN VW_<PROJETO>_KPI_<MEDIDA>_POR_<DIMENSAO>_POR_MES.<MEDIDA_2_SOMA> IS '<descrição da medida 2>. ADITIVA: <aditividade>.';
COMMENT ON COLUMN VW_<PROJETO>_KPI_<MEDIDA>_POR_<DIMENSAO>_POR_MES.<MEDIDA_3_MEDIA> IS '<descrição da medida 3>. NÃO-ADITIVA: recalcular.';

-- Repetir para cada pergunta de negócio.

-- =============================================================
-- SEÇÃO 4 — VIEWS MATERIALIZADAS (performance)
-- =============================================================
-- Views materializadas para consultas pesadas.
-- Refresh: COMPLETE ON DEMAND ou INCREMENTAL.

-- -------------------------------------------------------------
-- MV_<PROJETO>_KPI_<MEDIDA>_POR_<DIMENSAO>_POR_MES
-- -------------------------------------------------------------
-- GRÃO: uma linha por <dimensao> por mês
-- REFRESH: COMPLETE ON DEMAND
CREATE MATERIALIZED VIEW MV_<PROJETO>_KPI_<MEDIDA>_POR_<DIMENSAO>_POR_MES
BUILD IMMEDIATE
REFRESH COMPLETE ON DEMAND
AS
SELECT * FROM VW_<PROJETO>_KPI_<MEDIDA>_POR_<DIMENSAO>_POR_MES;

COMMENT ON MATERIALIZED VIEW MV_<PROJETO>_KPI_<MEDIDA>_POR_<DIMENSAO>_POR_MES IS
'<descrição da view materializada>. Grão: uma linha por <dimensao> por mês. REFRESH: COMPLETE ON DEMAND. FONTE: VW_<PROJETO>_KPI_<MEDIDA>_POR_<DIMENSAO>_POR_MES.';

-- -------------------------------------------------------------
-- VW_<PROJETO>_RESUMO_TEMPO — resumo agregado por período de tempo
-- -------------------------------------------------------------
-- GRÃO: uma linha por mês (ou período definido)
-- ADITIVIDADE: ADITIVA
CREATE OR REPLACE VIEW VW_<PROJETO>_RESUMO_TEMPO AS
SELECT
    TO_CHAR(E.<COLUNA_DATA>, 'YYYY')   AS ANO,
    TO_CHAR(E.<COLUNA_DATA>, 'MM')     AS MES,
    TO_CHAR(E.<COLUNA_DATA>, 'YYYYMM') AS ANO_MES,
    COUNT(*)                           AS QTDE_EVENTOS,
    SUM(E.<MEDIDA_1>)                  AS <MEDIDA_1_SOMA>,
    AVG(E.<MEDIDA_2>)                  AS <MEDIDA_2_MEDIA>
FROM VW_<PROJETO>_EVENTO E
WHERE E.<COLUNA_DATA> IS NOT NULL
GROUP BY
    TO_CHAR(E.<COLUNA_DATA>, 'YYYY'),
    TO_CHAR(E.<COLUNA_DATA>, 'MM'),
    TO_CHAR(E.<COLUNA_DATA>, 'YYYYMM');

COMMENT ON TABLE VW_<PROJETO>_RESUMO_TEMPO IS
'Resumo agregado por período de tempo. Grão: uma linha por mês. ADITIVA: soma de eventos por período. FONTE: VW_<PROJETO>_EVENTO.';

COMMENT ON COLUMN VW_<PROJETO>_RESUMO_TEMPO.ANO IS 'Ano do evento no formato AAAA.';
COMMENT ON COLUMN VW_<PROJETO>_RESUMO_TEMPO.MES IS 'Mês do evento no formato MM.';
COMMENT ON COLUMN VW_<PROJETO>_RESUMO_TEMPO.ANO_MES IS 'Ano e mês concatenados no formato AAAAMM.';
COMMENT ON COLUMN VW_<PROJETO>_RESUMO_TEMPO.QTDE_EVENTOS IS 'Contagem total de eventos no período.';
COMMENT ON COLUMN VW_<PROJETO>_RESUMO_TEMPO.<MEDIDA_1_SOMA> IS 'Soma da medida 1 no período. ADITIVA.';
COMMENT ON COLUMN VW_<PROJETO>_RESUMO_TEMPO.<MEDIDA_2_MEDIA> IS 'Média da medida 2 no período. NÃO-ADITIVA: média agregada.';

-- -------------------------------------------------------------
-- VW_<PROJETO>_EVOLUCAO_TEMPO — evolução temporal
-- -------------------------------------------------------------
CREATE OR REPLACE VIEW VW_<PROJETO>_EVOLUCAO_TEMPO AS
SELECT
    ANO,
    MES,
    ANO_MES,
    QTDE_EVENTOS,
    <MEDIDA_1_SOMA>,
    <MEDIDA_2_MEDIA>,
    LAG(QTDE_EVENTOS) OVER (ORDER BY ANO_MES) AS QTDE_ANTERIOR,
    QTDE_EVENTOS - LAG(QTDE_EVENTOS) OVER (ORDER BY ANO_MES) AS VARIACAO_ABSOLUTA,
    CASE 
        WHEN LAG(QTDE_EVENTOS) OVER (ORDER BY ANO_MES) > 0 
        THEN ROUND((QTDE_EVENTOS - LAG(QTDE_EVENTOS) OVER (ORDER BY ANO_MES)) * 100.0 / LAG(QTDE_EVENTOS) OVER (ORDER BY ANO_MES), 2)
        ELSE NULL 
    END AS VARIACAO_PERCENTUAL
FROM VW_<PROJETO>_RESUMO_TEMPO;

COMMENT ON TABLE VW_<PROJETO>_EVOLUCAO_TEMPO IS
'Evolução por período, com variação absoluta e percentual vs. período anterior. REGRA DE USO: VARIACAO_PERCENTUAL é NAO_ADITIVA — recalcular no contexto consultado.';

-- =============================================================
-- SEÇÃO 5 — VIEWS DE COMPOSIÇÃO (cruzamento de dimensões)
-- =============================================================

-- -------------------------------------------------------------
-- VW_<PROJETO>_COMPOSICAO — composição cruzada de dimensões
-- -------------------------------------------------------------
CREATE OR REPLACE VIEW VW_<PROJETO>_COMPOSICAO AS
SELECT
    TO_CHAR(E.<COLUNA_DATA>, 'YYYY')   AS ANO,
    TO_CHAR(E.<COLUNA_DATA>, 'MM')     AS MES,
    TO_CHAR(E.<COLUNA_DATA>, 'YYYYMM') AS ANO_MES,
    E.<DIMENSAO_1_CAT>,
    E.<DIMENSAO_1_DESC>,
    E.<DIMENSAO_2_CAT>,
    E.<DIMENSAO_2_DESC>,
    COUNT(*)                           AS QTDE_EVENTOS,
    SUM(E.<MEDIDA_1>)                  AS <MEDIDA_1_SOMA>
FROM VW_<PROJETO>_EVENTO E
GROUP BY
    TO_CHAR(E.<COLUNA_DATA>, 'YYYY'),
    TO_CHAR(E.<COLUNA_DATA>, 'MM'),
    TO_CHAR(E.<COLUNA_DATA>, 'YYYYMM'),
    E.<DIMENSAO_1_CAT>,
    E.<DIMENSAO_1_DESC>,
    E.<DIMENSAO_2_CAT>,
    E.<DIMENSAO_2_DESC>;

COMMENT ON TABLE VW_<PROJETO>_COMPOSICAO IS
'<descrição>. Grão: uma linha por combinação de período-dimensões. ADITIVA: pode somar livremente.';

-- =============================================================
-- NOTAS DE EXECUÇÃO
-- =============================================================
-- 1. Substitua TODOS os placeholders <...> pelos nomes do seu projeto.
-- 2. Adicione ou remova views conforme a necessidade do cliente.
-- 3. Cada view deve encapsular UMA regra de uso (grão, aditividade).
-- 4. Rode como o dono do schema do DW.
-- 5. COMMENT ON TABLE funciona também para views no Oracle.
