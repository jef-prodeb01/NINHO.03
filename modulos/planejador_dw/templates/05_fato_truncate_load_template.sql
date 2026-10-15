-- ==============================================================================
-- MODELO DDL: FATO DIMENSIONAL - ESTRATÉGIA A (TRUNCATE & LOAD MASSIVO)
-- ==============================================================================
-- Padrão Corporativo: FATO_<SISTEMA>_<DOMINIO>_<EVENTO> (ex: FATO_SEI_BA_ANDA_PROCES_3M)
-- Schema Alvo:        <SCHEMA_ALVO>
-- Tablespace:         <TABLESPACE_DADOS>
-- Estratégia:         Carga periódica em lote (D-1, mensal ou janela móvel de N meses).
-- Indexação:          BITMAP INDEX nas FKs para Star Transformation do otimizador CBO.
-- Manutenção:         Obrigatório executar PRC_POS_CARGA_FATO pós-carga (rebuild + stats).
-- ==============================================================================

CREATE TABLE "<SCHEMA_ALVO>"."FATO_<SISTEMA>_<DOMINIO>_<EVENTO>" 
   (	"DIM_<SISTEMA>_<DOMINIO>_<ENTIDADE_1>" NUMBER(38,0) NOT NULL ENABLE, 
	"DIM_<SISTEMA>_<DOMINIO>_<ENTIDADE_2>" NUMBER(38,0) NOT NULL ENABLE, 
	"DIM_TEMPO" NUMBER(38,0) NOT NULL ENABLE, 
	"TOT_<EVENTO>" NUMBER(38,0) DEFAULT 1 NOT NULL ENABLE, 
	"QTD_<MEDIDA_ADICIONAL>" NUMBER(38,0) DEFAULT 0, 
	"VAL_<METRICA_FINANCEIRA>" NUMBER(18,4) DEFAULT 0, 
	"DUR_<TEMPO_DIAS>" NUMBER(10,2),
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
-- CHAVES ESTRANGEIRAS (FOREIGN KEYS) COM FALLBACK PARA -1
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
-- ÍNDICES BITMAP NAS CHAVES ESTRANGEIRAS (STAR TRANSFORMATION DE ALTA PERFORMANCE)
-- ------------------------------------------------------------------------------
-- NOTA: Bitmaps são recomendados apenas aqui porque a tabela opera sob Truncate & Load
-- noturno sem DMLs concorrentes de UPDATE ou INSERT de micro-lotes.
CREATE BITMAP INDEX "<SCHEMA_ALVO>"."BMX_FATO_<EVENTO>_DIM_1" 
  ON "<SCHEMA_ALVO>"."FATO_<SISTEMA>_<DOMINIO>_<EVENTO>" ("DIM_<SISTEMA>_<DOMINIO>_<ENTIDADE_1>") 
  TABLESPACE "<TABLESPACE_DADOS>";

CREATE BITMAP INDEX "<SCHEMA_ALVO>"."BMX_FATO_<EVENTO>_DIM_2" 
  ON "<SCHEMA_ALVO>"."FATO_<SISTEMA>_<DOMINIO>_<EVENTO>" ("DIM_<SISTEMA>_<DOMINIO>_<ENTIDADE_2>") 
  TABLESPACE "<TABLESPACE_DADOS>";

CREATE BITMAP INDEX "<SCHEMA_ALVO>"."BMX_FATO_<EVENTO>_TEMPO" 
  ON "<SCHEMA_ALVO>"."FATO_<SISTEMA>_<DOMINIO>_<EVENTO>" ("DIM_TEMPO") 
  TABLESPACE "<TABLESPACE_DADOS>";

-- ------------------------------------------------------------------------------
-- DOCUMENTAÇÃO E COMENTÁRIOS DE METADADOS
-- ------------------------------------------------------------------------------
COMMENT ON TABLE "<SCHEMA_ALVO>"."FATO_<SISTEMA>_<DOMINIO>_<EVENTO>" IS 'Fato transacional analitica carregada via Truncate & Load massivo. Grao: uma combinacao de <ENTIDADE_1>, <ENTIDADE_2> e DIM_TEMPO.';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."FATO_<SISTEMA>_<DOMINIO>_<EVENTO>"."DIM_<SISTEMA>_<DOMINIO>_<ENTIDADE_1>" IS 'Chave substituta artificial para a dimensao <ENTIDADE_1>. NVL(-1).';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."FATO_<SISTEMA>_<DOMINIO>_<EVENTO>"."DIM_<SISTEMA>_<DOMINIO>_<ENTIDADE_2>" IS 'Chave substituta artificial para a dimensao <ENTIDADE_2>. NVL(-1).';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."FATO_<SISTEMA>_<DOMINIO>_<EVENTO>"."DIM_TEMPO" IS 'Chave de relacionamento com DIM_TEMPO (DIMENSION_KEY).';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."FATO_<SISTEMA>_<DOMINIO>_<EVENTO>"."TOT_<EVENTO>" IS 'Contagem absoluta de ocorrencias do evento (aditiva).';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."FATO_<SISTEMA>_<DOMINIO>_<EVENTO>"."QTD_<MEDIDA_ADICIONAL>" IS 'Quantidade quantitativa do evento.';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."FATO_<SISTEMA>_<DOMINIO>_<EVENTO>"."VAL_<METRICA_FINANCEIRA>" IS 'Valor financeiro total do evento em moeda corrente.';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."FATO_<SISTEMA>_<DOMINIO>_<EVENTO>"."DUR_<TEMPO_DIAS>" IS 'Duracao ou tempo decorrido do evento em dias.';

