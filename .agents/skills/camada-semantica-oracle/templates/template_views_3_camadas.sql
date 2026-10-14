-- =============================================================================
-- TEMPLATE OFICIAL: ARQUITETURA DE VIEWS ANALÍTICAS EM 3 CAMADAS (ORACLE 12c+)
-- =============================================================================
-- REGRAS OBRIGATÓRIAS:
-- 1. Substitua <PROJETO>, <DIMENSAO>, <FATO> e <MEDIDA> em MAIÚSCULAS sem acentos.
-- 2. NUNCA utilize aspas duplas em minúsculas ("coluna") ou prefixos banidos (SEM_VW_, SEC_, TST_).
-- 3. Toda view DEVE ter COMMENT ON TABLE iniciando com 'Uma linha representa...'.
-- 4. Toda coluna da view DEVE ter COMMENT ON COLUMN explicando regra, domínio e aditividade.
-- 5. Gere arquivos separados em saida/camada_semantica/vw_analiticas/ (1 arquivo por view ou por camada).
-- =============================================================================

-- =============================================================================
-- CAMADA 1: VIEW DE DIMENSÃO VIGENTE (VW_<PROJETO>_DIM_<DIMENSAO>_ATUAL)
-- =============================================================================
-- Objetivo: Expor apenas o registro corrente do SCD Tipo 2 (DTC_EXPIRACAO IS NULL),
--           ocultar colunas de auditoria física de carga e corrigir nomes legados.
-- =============================================================================
CREATE OR REPLACE FORCE VIEW VW_<PROJETO>_DIM_<DIMENSAO>_ATUAL AS
SELECT
    D.SK_<DIMENSAO>                                     AS SK_<DIMENSAO>,
    D.ID_<DIMENSAO>                                     AS ID_<DIMENSAO>,
    D.CD_<DIMENSAO>                                     AS CD_<DIMENSAO>,
    NVL(D.NM_<DIMENSAO>, 'NÃO INFORMADO')               AS NM_<DIMENSAO>,
    CASE D.CD_SITUACAO
        WHEN 'A' THEN 'ATIVO'
        WHEN 'I' THEN 'INATIVO'
        ELSE 'NÃO IDENTIFICADO'
    END                                                 AS DS_SITUACAO,
    D.IND_ATIVO                                         AS IND_ATIVO,
    D.DTC_INICIO                                        AS DTC_INICIO_VIGENCIA
FROM
    DIM_<DIMENSAO> D
WHERE
    D.DTC_EXPIRACAO IS NULL;

COMMENT ON TABLE VW_<PROJETO>_DIM_<DIMENSAO>_ATUAL IS
'Uma linha representa o cadastro vigente (SCD Tipo 2 atual, onde DTC_EXPIRACAO IS NULL) de <DIMENSAO>. Inclui o registro técnico -1 (NÃO INFORMADO).';

COMMENT ON COLUMN VW_<PROJETO>_DIM_<DIMENSAO>_ATUAL.SK_<DIMENSAO> IS 'Chave substituta (Surrogate Key) da dimensão <DIMENSAO>.';
COMMENT ON COLUMN VW_<PROJETO>_DIM_<DIMENSAO>_ATUAL.ID_<DIMENSAO> IS 'Identificador natural de negócio de <DIMENSAO> no sistema de origem.';
COMMENT ON COLUMN VW_<PROJETO>_DIM_<DIMENSAO>_ATUAL.CD_<DIMENSAO> IS 'Código curto ou sigla oficial de <DIMENSAO>.';
COMMENT ON COLUMN VW_<PROJETO>_DIM_<DIMENSAO>_ATUAL.NM_<DIMENSAO> IS 'Nome descritivo de <DIMENSAO>.';
COMMENT ON COLUMN VW_<PROJETO>_DIM_<DIMENSAO>_ATUAL.DS_SITUACAO IS 'Situação cadastral decodificada (ATIVO, INATIVO, NÃO IDENTIFICADO).';
COMMENT ON COLUMN VW_<PROJETO>_DIM_<DIMENSAO>_ATUAL.IND_ATIVO IS 'Indicador binário de registro ativo na origem (S/N).';
COMMENT ON COLUMN VW_<PROJETO>_DIM_<DIMENSAO>_ATUAL.DTC_INICIO_VIGENCIA IS 'Data de início da vigência da versão atual do registro (SCD2).';


-- =============================================================================
-- CAMADA 2: VIEW DE EVENTO / FATO ENRIQUECIDO (VW_<PROJETO>_EVENTO)
-- =============================================================================
-- Objetivo: Unir a tabela FATO às views DIM vigentes via LEFT JOIN, decodificar
--           códigos obscuros, aplicar NVL nas métricas e embutir filtro RLS (se ativo).
-- =============================================================================
CREATE OR REPLACE FORCE VIEW VW_<PROJETO>_EVENTO AS
SELECT
    -- Chaves e Identificadores Degenerados
    F.SK_<FATO>                                         AS SK_<FATO>,
    F.NR_PROTOCOLO                                      AS NR_PROTOCOLO,
    -- Datas e Competências
    T.DT_REFERENCIA                                     AS DT_EVENTO,
    T.NR_ANO                                            AS NR_ANO_EVENTO,
    T.NR_MES                                            AS NR_MES_EVENTO,
    T.CD_ANO_MES                                        AS CD_COMPETENCIA,
    -- Atributos Enriquecidos das Dimensões (com proteção contra órfãos via -1 / NVL)
    F.SK_<DIMENSAO>                                     AS SK_<DIMENSAO>,
    NVL(D.CD_<DIMENSAO>, 'N/I')                         AS CD_<DIMENSAO>,
    NVL(D.NM_<DIMENSAO>, 'NÃO INFORMADO')               AS NM_<DIMENSAO>,
    -- Domínios Decodificados
    CASE F.CD_STATUS_EVENTO
        WHEN 'P' THEN 'PENDENTE'
        WHEN 'C' THEN 'CONCLUÍDO'
        WHEN 'X' THEN 'CANCELADO'
        ELSE 'NÃO IDENTIFICADO'
    END                                                 AS DS_STATUS_EVENTO,
    F.IND_DENTRO_PRAZO                                  AS IND_DENTRO_PRAZO,
    -- Medidas Atômicas (com proteção NVL para medidas aditivas)
    NVL(F.QT_EVENTO, 0)                                 AS QT_EVENTO,
    NVL(F.VL_TOTAL_EVENTO, 0)                           AS VL_TOTAL_EVENTO,
    F.QT_DIAS_ATENDIMENTO                               AS QT_DIAS_ATENDIMENTO
FROM
    FATO_<FATO> F
    LEFT JOIN DIM_TEMPO T
        ON F.SK_TEMPO = T.SK_TEMPO
    LEFT JOIN VW_<PROJETO>_DIM_<DIMENSAO>_ATUAL D
        ON F.SK_<DIMENSAO> = D.SK_<DIMENSAO>
WHERE
    1 = 1
    -- [OPCIONAL - RLS] Descomentar/incluir apenas quando [x] RLS estiver marcado no INTAKE_SEMANTICA.md:
    -- AND EXISTS (
    --     SELECT 1
    --     FROM USUARIO_SEGMENTOS US
    --     WHERE US.USUARIO_ORACLE = SYS_CONTEXT('USERENV', 'SESSION_USER')
    --       AND US.PROJETO IN ('GLOBAL', '<PROJETO>')
    --       AND (US.IND_ACESSO_TOTAL = 'S' OR US.SEGMENTO = D.CD_<DIMENSAO>)
    -- )
;

COMMENT ON TABLE VW_<PROJETO>_EVENTO IS
'Uma linha representa um evento individual de <FATO> enriquecido com os atributos vigentes de <DIMENSAO> e calendário. Grão atômico para consultas detalhadas e base para views KPI.';

COMMENT ON COLUMN VW_<PROJETO>_EVENTO.SK_<FATO> IS 'Identificador único (Surrogate Key) do registro na tabela fato.';
COMMENT ON COLUMN VW_<PROJETO>_EVENTO.NR_PROTOCOLO IS 'Número natural do protocolo/documento do evento (dimensão degenerada).';
COMMENT ON COLUMN VW_<PROJETO>_EVENTO.DT_EVENTO IS 'Data de ocorrência do evento.';
COMMENT ON COLUMN VW_<PROJETO>_EVENTO.NR_ANO_EVENTO IS 'Ano calendário do evento (YYYY).';
COMMENT ON COLUMN VW_<PROJETO>_EVENTO.NR_MES_EVENTO IS 'Mês calendário do evento (1 a 12).';
COMMENT ON COLUMN VW_<PROJETO>_EVENTO.CD_COMPETENCIA IS 'Competência no formato YYYYMM.';
COMMENT ON COLUMN VW_<PROJETO>_EVENTO.SK_<DIMENSAO> IS 'Chave substituta da dimensão <DIMENSAO>.';
COMMENT ON COLUMN VW_<PROJETO>_EVENTO.CD_<DIMENSAO> IS 'Código ou sigla de <DIMENSAO>.';
COMMENT ON COLUMN VW_<PROJETO>_EVENTO.NM_<DIMENSAO> IS 'Nome de <DIMENSAO>.';
COMMENT ON COLUMN VW_<PROJETO>_EVENTO.DS_STATUS_EVENTO IS 'Status decodificado do evento (PENDENTE, CONCLUÍDO, CANCELADO, NÃO IDENTIFICADO).';
COMMENT ON COLUMN VW_<PROJETO>_EVENTO.IND_DENTRO_PRAZO IS 'Indicador se o evento foi concluído dentro do SLA (S/N).';
COMMENT ON COLUMN VW_<PROJETO>_EVENTO.QT_EVENTO IS 'Quantidade de eventos (Medida ADITIVA).';
COMMENT ON COLUMN VW_<PROJETO>_EVENTO.VL_TOTAL_EVENTO IS 'Valor financeiro total do evento em R$ (Medida ADITIVA).';
COMMENT ON COLUMN VW_<PROJETO>_EVENTO.QT_DIAS_ATENDIMENTO IS 'Prazo em dias corridos do atendimento. Em agregações, utilizar AVG ou MEDIAN (Medida NAO_ADITIVA para soma).';


-- =============================================================================
-- CAMADA 3: VIEW DE KPI PRÉ-AGREGADO (VW_<PROJETO>_KPI_<MEDIDA>_POR_<DIMENSAO>)
-- =============================================================================
-- Objetivo: Entregar indicadores oficiais prontos por recorte dimensional/temporal,
--           protegendo divisões por zero (NULLIF) e documentando métricas não-aditivas.
--           DEVE ler exclusivamente de VW_<PROJETO>_EVENTO (nunca da tabela física).
-- =============================================================================
CREATE OR REPLACE FORCE VIEW VW_<PROJETO>_KPI_<MEDIDA>_POR_<DIMENSAO> AS
SELECT
    E.NR_ANO_EVENTO                                     AS NR_ANO_EVENTO,
    E.CD_COMPETENCIA                                    AS CD_COMPETENCIA,
    E.CD_<DIMENSAO>                                     AS CD_<DIMENSAO>,
    E.NM_<DIMENSAO>                                     AS NM_<DIMENSAO>,
    -- Métricas Aditivas (podem ser somadas entre recortes)
    SUM(E.QT_EVENTO)                                    AS QT_TOTAL_EVENTOS,
    SUM(CASE WHEN E.DS_STATUS_EVENTO = 'CONCLUÍDO' THEN E.QT_EVENTO ELSE 0 END)
                                                        AS QT_EVENTOS_CONCLUIDOS,
    SUM(E.VL_TOTAL_EVENTO)                              AS VL_TOTAL_EVENTOS,
    -- Métricas Não-Aditivas (NÃO somar entre linhas; recalcular a partir do numerador/denominador)
    ROUND(AVG(E.QT_DIAS_ATENDIMENTO), 2)                AS VL_TEMPO_MEDIO_DIAS,
    ROUND(
        100.0 * SUM(CASE WHEN E.IND_DENTRO_PRAZO = 'S' THEN E.QT_EVENTO ELSE 0 END)
        / NULLIF(SUM(E.QT_EVENTO), 0),
        2
    )                                                   AS PCT_DENTRO_PRAZO
FROM
    VW_<PROJETO>_EVENTO E
WHERE
    E.DS_STATUS_EVENTO <> 'CANCELADO'
GROUP BY
    E.NR_ANO_EVENTO,
    E.CD_COMPETENCIA,
    E.CD_<DIMENSAO>,
    E.NM_<DIMENSAO>;

COMMENT ON TABLE VW_<PROJETO>_KPI_<MEDIDA>_POR_<DIMENSAO> IS
'Uma linha representa o resumo mensal de indicadores de <FATO> por competência (CD_COMPETENCIA) e <DIMENSAO> (CD_<DIMENSAO>), excluindo registros cancelados.';

COMMENT ON COLUMN VW_<PROJETO>_KPI_<MEDIDA>_POR_<DIMENSAO>.NR_ANO_EVENTO IS 'Ano de referência da competência.';
COMMENT ON COLUMN VW_<PROJETO>_KPI_<MEDIDA>_POR_<DIMENSAO>.CD_COMPETENCIA IS 'Competência mensal no formato YYYYMM.';
COMMENT ON COLUMN VW_<PROJETO>_KPI_<MEDIDA>_POR_<DIMENSAO>.CD_<DIMENSAO> IS 'Código/sigla de <DIMENSAO>.';
COMMENT ON COLUMN VW_<PROJETO>_KPI_<MEDIDA>_POR_<DIMENSAO>.NM_<DIMENSAO> IS 'Nome de <DIMENSAO>.';
COMMENT ON COLUMN VW_<PROJETO>_KPI_<MEDIDA>_POR_<DIMENSAO>.QT_TOTAL_EVENTOS IS 'Total de eventos válidos na competência (ADITIVA).';
COMMENT ON COLUMN VW_<PROJETO>_KPI_<MEDIDA>_POR_<DIMENSAO>.QT_EVENTOS_CONCLUIDOS IS 'Total de eventos concluídos na competência (ADITIVA).';
COMMENT ON COLUMN VW_<PROJETO>_KPI_<MEDIDA>_POR_<DIMENSAO>.VL_TOTAL_EVENTOS IS 'Soma financeira dos eventos na competência em R$ (ADITIVA).';
COMMENT ON COLUMN VW_<PROJETO>_KPI_<MEDIDA>_POR_<DIMENSAO>.VL_TEMPO_MEDIO_DIAS IS 'Tempo médio de atendimento em dias (NAO_ADITIVA: não somar entre competências ou órgãos).';
COMMENT ON COLUMN VW_<PROJETO>_KPI_<MEDIDA>_POR_<DIMENSAO>.PCT_DENTRO_PRAZO IS 'Percentual de eventos concluídos dentro do prazo de SLA de 0 a 100 (NAO_ADITIVA: recalcular razão).';
