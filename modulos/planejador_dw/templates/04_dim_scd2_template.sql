-- ==============================================================================
-- MODELO DDL: DIMENSÃO OFICIAL COM HISTÓRICO SCD TIPO 2 (B-TREE ONLY)
-- ==============================================================================
-- Padrão Corporativo: DIM_<SISTEMA>_<DOMINIO>_<ENTIDADE> (ex: DIM_SEI_BA_UNIDADE, DIM_COST_MGMT_PROJETO)
-- Schema Alvo:        <SCHEMA_ALVO>
-- Tablespace:         <TABLESPACE_DADOS>
-- Chave:              DIMENSION_KEY (Surrogate Key via Sequence)
-- Histórico:          DTC_EFETIVACAO, DTC_EXPIRACAO (NULL = versão vigente)
-- Regra Crítica:      PROIBIDO BITMAP EM DIMENSÕES! Apenas índices B-Tree para
--                     evitar locks de bloco e deadlocks (ORA-00060) em atualizações.
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. SEQUENCE CORPORATIVA PARA SURROGATE KEY
-- ------------------------------------------------------------------------------
CREATE SEQUENCE "<SCHEMA_ALVO>"."SEQ_DIM_<SISTEMA>_<DOMINIO>_<ENTIDADE>"
  START WITH 1
  INCREMENT BY 1
  CACHE 50
  NOCYCLE
  NOORDER;

-- ------------------------------------------------------------------------------
-- 2. TABELA DIMENSÃO OFICIAL
-- ------------------------------------------------------------------------------
CREATE TABLE "<SCHEMA_ALVO>"."DIM_<SISTEMA>_<DOMINIO>_<ENTIDADE>" 
   (	"DIMENSION_KEY" NUMBER(38,0) NOT NULL ENABLE, 
	"ID_<ENTIDADE>" NUMBER(38,0) NOT NULL ENABLE, 
	"SIGLA_<ENTIDADE>" VARCHAR2(50), 
	"DS_<ENTIDADE>" VARCHAR2(255), 
	"TIPO_<ENTIDADE>" VARCHAR2(100), 
	"SIN_ATIVO" CHAR(1 CHAR) DEFAULT 'S' NOT NULL ENABLE, 
	"COD_IBGE" NUMBER(38,0), 
	"DTC_EFETIVACAO" DATE NOT NULL ENABLE, 
	"DTC_EXPIRACAO" DATE, 
	"DES_ATUALIZAR" CHAR(1 CHAR) DEFAULT 'S' NOT NULL ENABLE, 
	 CONSTRAINT "PK_DIM_<ENTIDADE>" PRIMARY KEY ("DIMENSION_KEY")
  USING INDEX PCTFREE 10 INITRANS 2 MAXTRANS 255 COMPUTE STATISTICS 
  TABLESPACE "<TABLESPACE_DADOS>" ENABLE
   ) SEGMENT CREATION IMMEDIATE 
  PCTFREE 10 PCTUSED 40 INITRANS 1 MAXTRANS 255 
  NOCOMPRESS LOGGING
  TABLESPACE "<TABLESPACE_DADOS>";

-- ------------------------------------------------------------------------------
-- 3. ÍNDICES B-TREE COMPOSTOS PARA HISTÓRICO E LOOKUP DE SCD TIPO 2 NO ETL
-- ------------------------------------------------------------------------------
CREATE INDEX "<SCHEMA_ALVO>"."IDX_DIM_<ENTIDADE>_HIST" 
  ON "<SCHEMA_ALVO>"."DIM_<SISTEMA>_<DOMINIO>_<ENTIDADE>" ("ID_<ENTIDADE>", "DTC_EFETIVACAO") 
  PCTFREE 10 INITRANS 2 MAXTRANS 255 COMPUTE STATISTICS 
  TABLESPACE "<TABLESPACE_DADOS>";

ALTER TABLE "<SCHEMA_ALVO>"."DIM_<SISTEMA>_<DOMINIO>_<ENTIDADE>" 
  ADD CONSTRAINT "UK_DIM_<ENTIDADE>_HIST" UNIQUE ("ID_<ENTIDADE>", "DTC_EFETIVACAO")
  USING INDEX "<SCHEMA_ALVO>"."IDX_DIM_<ENTIDADE>_HIST" ENABLE;

CREATE INDEX "<SCHEMA_ALVO>"."IDX_DIM_<ENTIDADE>_LOOKUP" 
  ON "<SCHEMA_ALVO>"."DIM_<SISTEMA>_<DOMINIO>_<ENTIDADE>" ("ID_<ENTIDADE>", "DTC_EXPIRACAO") 
  PCTFREE 10 INITRANS 2 MAXTRANS 255 COMPUTE STATISTICS 
  TABLESPACE "<TABLESPACE_DADOS>";

-- ------------------------------------------------------------------------------
-- 4. ÍNDICES B-TREE ADICIONAIS PARA FILTROS ANALÍTICOS (ALTA SELETIVIDADE)
-- ------------------------------------------------------------------------------
CREATE INDEX "<SCHEMA_ALVO>"."IDX_DIM_<ENTIDADE>_SIGLA" 
  ON "<SCHEMA_ALVO>"."DIM_<SISTEMA>_<DOMINIO>_<ENTIDADE>" ("SIGLA_<ENTIDADE>") 
  TABLESPACE "<TABLESPACE_DADOS>";

-- ------------------------------------------------------------------------------
-- 5. DOCUMENTAÇÃO E COMENTÁRIOS DE METADADOS
-- ------------------------------------------------------------------------------
COMMENT ON TABLE "<SCHEMA_ALVO>"."DIM_<SISTEMA>_<DOMINIO>_<ENTIDADE>" IS 'Dimensao historica oficial corporativa de <ENTIDADE> com controle de vigencia SCD Tipo 2.';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."DIM_<SISTEMA>_<DOMINIO>_<ENTIDADE>"."DIMENSION_KEY" IS 'Chave substituta artificial (Surrogate Key) da versao historica da dimensao gerada via SEQUENCE.';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."DIM_<SISTEMA>_<DOMINIO>_<ENTIDADE>"."ID_<ENTIDADE>" IS 'Identificador global de negocio (Natural Key) da entidade na origem.';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."DIM_<SISTEMA>_<DOMINIO>_<ENTIDADE>"."SIGLA_<ENTIDADE>" IS 'Sigla representativa da entidade.';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."DIM_<SISTEMA>_<DOMINIO>_<ENTIDADE>"."DS_<ENTIDADE>" IS 'Descricao textual ou razao social da entidade.';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."DIM_<SISTEMA>_<DOMINIO>_<ENTIDADE>"."SIN_ATIVO" IS 'Indicador de situacao ativa (S ou N).';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."DIM_<SISTEMA>_<DOMINIO>_<ENTIDADE>"."DTC_EFETIVACAO" IS 'Data de inicio da validade desta versao dimensional.';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."DIM_<SISTEMA>_<DOMINIO>_<ENTIDADE>"."DTC_EXPIRACAO" IS 'Data de fim da validade. Nulo indica que esta versao e a atualmente vigente.';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."DIM_<SISTEMA>_<DOMINIO>_<ENTIDADE>"."DES_ATUALIZAR" IS 'Flag tecnica utilizada pelo processo de carga do ODI para controle de CDC.';

