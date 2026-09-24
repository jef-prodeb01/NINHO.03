-- ==============================================================================
-- MODELO DDL: FATO DIMENSIONAL (TRANSAÇÃO / ACUMULADA)
-- ==============================================================================
-- Padrão Corporativo: FATO_<DOMINIO>_<EVENTO> (ex: FATO_SEI_MUNIC_DOCUMENTO, FATO_DEIC_ACAO)
-- Schema Alvo: <SCHEMA_ALVO>
-- Tablespace:  <TABLESPACE_DADOS>
-- Chaves:      FKs com o mesmo nome da dimensao (DIM_*)
-- Medidas:     Prefixo QTD_* (ou VL_*)
-- Auditoria:   DTC_CARGA DATE
-- ==============================================================================

CREATE TABLE "<SCHEMA_ALVO>"."FATO_<DOMINIO>_<EVENTO>" 
   (	"DIM_<DOMINIO>_<ENTIDADE_1>" NUMBER(38,0) NOT NULL ENABLE, 
	"DIM_<DOMINIO>_<ENTIDADE_2>" NUMBER(38,0) NOT NULL ENABLE, 
	"DIM_TEMPO" NUMBER(38,0) NOT NULL ENABLE, 
	"QTD_<EVENTO>" NUMBER(38,0) DEFAULT 1, 
	"QTD_<MEDIDA_ADICIONAL>" NUMBER(38,0) DEFAULT 0, 
	"DTC_CARGA" DATE DEFAULT SYSDATE, 
	 CONSTRAINT "FATO_<DOMINIO>_<EVENTO>_PK" PRIMARY KEY (
     "DIM_<DOMINIO>_<ENTIDADE_1>", 
     "DIM_<DOMINIO>_<ENTIDADE_2>", 
     "DIM_TEMPO"
   )
  USING INDEX PCTFREE 10 INITRANS 2 MAXTRANS 255 COMPUTE STATISTICS 
  TABLESPACE "<TABLESPACE_DADOS>" ENABLE
   ) SEGMENT CREATION IMMEDIATE 
  PCTFREE 10 PCTUSED 40 INITRANS 1 MAXTRANS 255 
  NOCOMPRESS LOGGING
  TABLESPACE "<TABLESPACE_DADOS>";

-- ------------------------------------------------------------------------------
-- CHAVES ESTRANGEIRAS (FOREIGN KEYS)
-- ------------------------------------------------------------------------------
ALTER TABLE "<SCHEMA_ALVO>"."FATO_<DOMINIO>_<EVENTO>" 
  ADD CONSTRAINT "FATO_<EVENTO>_DIM_<ENTIDADE_1>_FK" FOREIGN KEY ("DIM_<DOMINIO>_<ENTIDADE_1>")
  REFERENCES "<SCHEMA_ALVO>"."DIM_<DOMINIO>_<ENTIDADE_1>" ("DIMENSION_KEY") ENABLE;

ALTER TABLE "<SCHEMA_ALVO>"."FATO_<DOMINIO>_<EVENTO>" 
  ADD CONSTRAINT "FATO_<EVENTO>_DIM_<ENTIDADE_2>_FK" FOREIGN KEY ("DIM_<DOMINIO>_<ENTIDADE_2>")
  REFERENCES "<SCHEMA_ALVO>"."DIM_<DOMINIO>_<ENTIDADE_2>" ("DIMENSION_KEY") ENABLE;

ALTER TABLE "<SCHEMA_ALVO>"."FATO_<DOMINIO>_<EVENTO>" 
  ADD CONSTRAINT "FATO_<EVENTO>_DIM_TEMPO_FK" FOREIGN KEY ("DIM_TEMPO")
  REFERENCES "<SCHEMA_ALVO>"."DIM_TEMPO" ("DIMENSION_KEY") ENABLE;

-- ------------------------------------------------------------------------------
-- ÍNDICES BITMAP NAS CHAVES ESTRANGEIRAS (ALTA PERFORMANCE STAR TRANSFORMATION)
-- ------------------------------------------------------------------------------
CREATE BITMAP INDEX "<SCHEMA_ALVO>"."BMX_FATO_<EVENTO>_DIM_1" 
  ON "<SCHEMA_ALVO>"."FATO_<DOMINIO>_<EVENTO>" ("DIM_<DOMINIO>_<ENTIDADE_1>") 
  TABLESPACE "<TABLESPACE_DADOS>";

CREATE BITMAP INDEX "<SCHEMA_ALVO>"."BMX_FATO_<EVENTO>_DIM_2" 
  ON "<SCHEMA_ALVO>"."FATO_<DOMINIO>_<EVENTO>" ("DIM_<DOMINIO>_<ENTIDADE_2>") 
  TABLESPACE "<TABLESPACE_DADOS>";

CREATE BITMAP INDEX "<SCHEMA_ALVO>"."BMX_FATO_<EVENTO>_TEMPO" 
  ON "<SCHEMA_ALVO>"."FATO_<DOMINIO>_<EVENTO>" ("DIM_TEMPO") 
  TABLESPACE "<TABLESPACE_DADOS>";

-- ------------------------------------------------------------------------------
-- DOCUMENTAÇÃO E COMENTÁRIOS
-- ------------------------------------------------------------------------------
COMMENT ON TABLE "<SCHEMA_ALVO>"."FATO_<DOMINIO>_<EVENTO>" IS 'Fato transacional de <EVENTO>. Grao fisico: uma combinacao de <ENTIDADE_1>, <ENTIDADE_2> e data de ocorrencia.';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."FATO_<DOMINIO>_<EVENTO>"."DIM_<DOMINIO>_<ENTIDADE_1>" IS 'Chave substituta para a dimensao <ENTIDADE_1>.';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."FATO_<DOMINIO>_<EVENTO>"."DIM_<DOMINIO>_<ENTIDADE_2>" IS 'Chave substituta para a dimensao <ENTIDADE_2>.';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."FATO_<DOMINIO>_<EVENTO>"."DIM_TEMPO" IS 'Chave da dimensao tempo correspondente a data de ocorrencia do evento.';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."FATO_<DOMINIO>_<EVENTO>"."QTD_<EVENTO>" IS 'Medida aditiva principal de ocorrencia do evento (normalmente 1 por linha).';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."FATO_<DOMINIO>_<EVENTO>"."QTD_<MEDIDA_ADICIONAL>" IS 'Medida quantitativa complementar do evento.';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."FATO_<DOMINIO>_<EVENTO>"."DTC_CARGA" IS 'Timestamp da realizacao da carga pelo job ETL/ODI.';
