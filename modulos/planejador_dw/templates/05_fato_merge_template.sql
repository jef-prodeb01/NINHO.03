-- ==============================================================================
-- MODELO DDL & MERGE: FATO DIMENSIONAL - ESTRATÉGIA B (INCREMENTAL IDEMPOTENTE)
-- ==============================================================================
-- Padrão Corporativo: FATO_<SISTEMA>_<DOMINIO>_<EVENTO> (ex: FATO_COST_MGMT_CUSTO)
-- Schema Alvo:        <SCHEMA_ALVO>
-- Tablespace:         <TABLESPACE_DADOS>
-- Estratégia:         Cargas frequentes intra-dia ou diárias de APIs/telemetria.
-- Indexação:          B-TREE INDEX exclusivo (proibido Bitmap para evitar contenção de locks).
-- Operação:           MERGE INTO idempotente (UPDATE se existir, INSERT se novo).
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. TABELA FATO DIMENSIONAL
-- ------------------------------------------------------------------------------
CREATE TABLE "<SCHEMA_ALVO>"."FATO_<SISTEMA>_<DOMINIO>_<EVENTO>" 
   (	"DIM_<SISTEMA>_<DOMINIO>_<ENTIDADE_1>" NUMBER(38,0) NOT NULL ENABLE, 
	"DIM_<SISTEMA>_<DOMINIO>_<ENTIDADE_2>" NUMBER(38,0) NOT NULL ENABLE, 
	"DIM_TEMPO" NUMBER(38,0) NOT NULL ENABLE, 
	"TOT_<EVENTO>" NUMBER(38,0) DEFAULT 1 NOT NULL ENABLE, 
	"QTD_<MEDIDA_ADICIONAL>" NUMBER(18,4) DEFAULT 0, 
	"VAL_<METRICA_FINANCEIRA>" NUMBER(18,4) DEFAULT 0, 
	 CONSTRAINT "PK_FATO_<EVENTO>" PRIMARY KEY (
     "DIM_<SISTEMA>_<DOMINIO>_<ENTIDADE_1>", 
     "DIM_<SISTEMA>_<DOMINIO>_<ENTIDADE_2>", 
     "DIM_TEMPO"
   )
  USING INDEX PCTFREE 10 INITRANS 2 MAXTRANS 255 COMPUTE STATISTICS 
  TABLESPACE "<TABLESPACE_DADOS>" ENABLE
   ) SEGMENT CREATION IMMEDIATE 
  PCTFREE 10 PCTUSED 40 INITRANS 1 MAXTRANS 255 
  NOCOMPRESS LOGGING
  TABLESPACE "<TABLESPACE_DADOS>";

-- ------------------------------------------------------------------------------
-- 2. CHAVES ESTRANGEIRAS (FOREIGN KEYS) COM FALLBACK PARA -1
-- ------------------------------------------------------------------------------
ALTER TABLE "<SCHEMA_ALVO>"."FATO_<SISTEMA>_<DOMINIO>_<EVENTO>" 
  ADD CONSTRAINT "FK_FATO_<EVENTO>_DIM_1" FOREIGN KEY ("DIM_<SISTEMA>_<DOMINIO>_<ENTIDADE_1>")
  REFERENCES "<SCHEMA_ALVO>"."DIM_<SISTEMA>_<DOMINIO>_<ENTIDADE_1>" ("DIMENSION_KEY") ENABLE;

ALTER TABLE "<SCHEMA_ALVO>"."FATO_<SISTEMA>_<DOMINIO>_<EVENTO>" 
  ADD CONSTRAINT "FK_FATO_<EVENTO>_DIM_2" FOREIGN KEY ("DIM_<SISTEMA>_<DOMINIO>_<ENTIDADE_2>")
  REFERENCES "<SCHEMA_ALVO>"."DIM_<SISTEMA>_<DOMINIO>_<ENTIDADE_2>" ("DIMENSION_KEY") ENABLE;

ALTER TABLE "<SCHEMA_ALVO>"."FATO_<SISTEMA>_<DOMINIO>_<EVENTO>" 
  ADD CONSTRAINT "FK_FATO_<EVENTO>_DIM_TEMPO" FOREIGN KEY ("DIM_TEMPO")
  REFERENCES "<SCHEMA_ALVO>"."DIM_TEMPO" ("DIMENSION_KEY") ENABLE;

-- ------------------------------------------------------------------------------
-- 3. ÍNDICES B-TREE COMPOSTOS (OTIMIZADOS PARA O CLÁUSULA ON DO MERGE)
-- ------------------------------------------------------------------------------
-- NOTA: Em cargas incrementais com MERGE INTO frequentes, índices Bitmap causariam
-- deadlocks e serialização severa de transações (ORA-00060). Usar apenas B-Tree!
CREATE INDEX "<SCHEMA_ALVO>"."IDX_FATO_<EVENTO>_BUSCA" 
  ON "<SCHEMA_ALVO>"."FATO_<SISTEMA>_<DOMINIO>_<EVENTO>" (
    "DIM_<SISTEMA>_<DOMINIO>_<ENTIDADE_1>", 
    "DIM_TEMPO"
  ) 
  TABLESPACE "<TABLESPACE_DADOS>";

-- ------------------------------------------------------------------------------
-- 4. PATTERN SQL DE CARGA INCREMENTAL IDEMPOTENTE (MERGE INTO)
-- ------------------------------------------------------------------------------
/*
MERGE INTO "<SCHEMA_ALVO>"."FATO_<SISTEMA>_<DOMINIO>_<EVENTO>" F
USING (
    SELECT 
        NVL(D1.DIMENSION_KEY, -1) AS DIM_ENTIDADE_1,
        NVL(D2.DIMENSION_KEY, -1) AS DIM_ENTIDADE_2,
        NVL(DT.DIMENSION_KEY, -1) AS DIM_TEMPO,
        S.QTDE_BRUTA AS QTD_MEDIDA,
        S.VALOR_TOTAL AS VAL_METRICA
    FROM "<SCHEMA_ALVO>"."STG_<SISTEMA>_<DOMINIO>_<ENTIDADE>" S
    LEFT JOIN "<SCHEMA_ALVO>"."DIM_<SISTEMA>_<DOMINIO>_<ENTIDADE_1>" D1
        ON D1.ID_<ENTIDADE_1> = S.ID_ENTIDADE_1
       AND D1.DTC_EXPIRACAO IS NULL
    LEFT JOIN "<SCHEMA_ALVO>"."DIM_<SISTEMA>_<DOMINIO>_<ENTIDADE_2>" D2
        ON D2.ID_<ENTIDADE_2> = S.ID_ENTIDADE_2
       AND D2.DTC_EXPIRACAO IS NULL
    LEFT JOIN "<SCHEMA_ALVO>"."DIM_TEMPO" DT
        ON DT.DTC_COMPLETA = TRUNC(S.DATA_EVENTO)
    WHERE S.DTC_EXTRACAO >= TRUNC(SYSDATE) - 10 -- Janela móvel de reprocessamento
) SRC
ON (
    F.DIM_<SISTEMA>_<DOMINIO>_<ENTIDADE_1> = SRC.DIM_ENTIDADE_1
    AND F.DIM_<SISTEMA>_<DOMINIO>_<ENTIDADE_2> = SRC.DIM_ENTIDADE_2
    AND F.DIM_TEMPO = SRC.DIM_TEMPO
)
WHEN MATCHED THEN
    UPDATE SET 
        F.QTD_<MEDIDA_ADICIONAL>   = SRC.QTD_MEDIDA,
        F.VAL_<METRICA_FINANCEIRA> = SRC.VAL_METRICA
WHEN NOT MATCHED THEN
    INSERT (
        DIM_<SISTEMA>_<DOMINIO>_<ENTIDADE_1>,
        DIM_<SISTEMA>_<DOMINIO>_<ENTIDADE_2>,
        DIM_TEMPO,
        TOT_<EVENTO>,
        QTD_<MEDIDA_ADICIONAL>,
        VAL_<METRICA_FINANCEIRA>
    ) VALUES (
        SRC.DIM_ENTIDADE_1,
        SRC.DIM_ENTIDADE_2,
        SRC.DIM_TEMPO,
        1,
        SRC.QTD_MEDIDA,
        SRC.VAL_METRICA
    );
*/

-- ------------------------------------------------------------------------------
-- 5. DOCUMENTAÇÃO E COMENTÁRIOS DE METADADOS
-- ------------------------------------------------------------------------------
COMMENT ON TABLE "<SCHEMA_ALVO>"."FATO_<SISTEMA>_<DOMINIO>_<EVENTO>" IS 'Fato incremental idempotente para telemetria/APIs via MERGE INTO. B-Tree indexada.';

