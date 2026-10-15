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

-- ==============================================================================
-- 6. DIM_TEMPO CORPORATIVA CONFORMADA (SEMPRE OBRIGATÓRIA NO SCHEMA DE TRABALHO)
-- ==============================================================================
CREATE TABLE "<SCHEMA_ALVO>"."DIM_TEMPO" 
   (	"DIMENSION_KEY" NUMBER NOT NULL ENABLE, 
	"IDE_SK_TEMPO" NUMBER, 
	"DES_DATA_DIA" VARCHAR2(25), 
	"NUM_ANO" NUMBER(4,0), 
	"NUM_MES" NUMBER(3,0), 
	"NUM_DIA" NUMBER(3,0), 
	"NUM_QUADRIMESTRE" NUMBER(3,0), 
	"NUM_TRIMESTRE" NUMBER(2,0), 
	"DES_QUINZENA" VARCHAR2(12), 
	"DES_QUADRIMESTRE" VARCHAR2(12), 
	"NUM_BIMESTRE" NUMBER(3,0), 
	"DES_BIMESTRE" VARCHAR2(12), 
	"DES_ANO_MES" VARCHAR2(8), 
	"DES_MES_ANO" VARCHAR2(8), 
	"DES_DIA" VARCHAR2(7), 
	"NUM_SEMESTRE" NUMBER(3,0), 
	"DES_MES_ANO_NUMERICO" VARCHAR2(7), 
	"DES_TRIMESTRE" VARCHAR2(12), 
	"IND_FINAL_SEMANA" CHAR(1), 
	"DES_MES" VARCHAR2(15), 
	"NUM_QUINZENA" NUMBER(3,0), 
	"DES_MES_ANO_COMPLETO" VARCHAR2(30), 
	"DES_SEMESTRE" VARCHAR2(12), 
	"DTC_COMPLETA" DATE, 
	 CONSTRAINT "DIM_TEMPO_UK" UNIQUE ("NUM_ANO", "NUM_MES", "NUM_DIA")
  USING INDEX PCTFREE 10 INITRANS 2 MAXTRANS 255 COMPUTE STATISTICS 
  TABLESPACE "<TABLESPACE_DADOS>" ENABLE, 
	 CONSTRAINT "DIM_TEMPO_PK" PRIMARY KEY ("DIMENSION_KEY")
  USING INDEX PCTFREE 10 INITRANS 2 MAXTRANS 255 COMPUTE STATISTICS 
  TABLESPACE "<TABLESPACE_DADOS>" ENABLE
   ) SEGMENT CREATION IMMEDIATE 
  PCTFREE 10 PCTUSED 40 INITRANS 1 MAXTRANS 255 
  NOCOMPRESS LOGGING
  TABLESPACE "<TABLESPACE_DADOS>";

CREATE INDEX "<SCHEMA_ALVO>"."IDX_DIM_TEMPO_ANO_MES" ON "<SCHEMA_ALVO>"."DIM_TEMPO" ("NUM_ANO", "NUM_MES") 
  PCTFREE 10 INITRANS 2 MAXTRANS 255 COMPUTE STATISTICS 
  TABLESPACE "<TABLESPACE_DADOS>";

CREATE INDEX "<SCHEMA_ALVO>"."IDX_DIM_TEMPO_DTC" ON "<SCHEMA_ALVO>"."DIM_TEMPO" ("DTC_COMPLETA") 
  PCTFREE 10 INITRANS 2 MAXTRANS 255 COMPUTE STATISTICS 
  TABLESPACE "<TABLESPACE_DADOS>";

COMMENT ON TABLE "<SCHEMA_ALVO>"."DIM_TEMPO" IS 'Dimensao conformada de calendario no nivel diario, reutilizada em diferentes papeis de data pelas tabelas fato.';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."DIM_TEMPO"."DIMENSION_KEY" IS 'Chave substituta da data no data warehouse.';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."DIM_TEMPO"."IDE_SK_TEMPO" IS 'Identificador alternativo da data na dimensao tempo.';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."DIM_TEMPO"."DES_DATA_DIA" IS 'Data no formato numerico textual AAAAMMDD.';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."DIM_TEMPO"."NUM_ANO" IS 'Ano calendario.';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."DIM_TEMPO"."NUM_MES" IS 'Numero do mes, de 1 a 12.';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."DIM_TEMPO"."NUM_DIA" IS 'Dia do mes.';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."DIM_TEMPO"."NUM_QUADRIMESTRE" IS 'Numero do quadrimestre no ano.';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."DIM_TEMPO"."NUM_TRIMESTRE" IS 'Numero do trimestre no ano.';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."DIM_TEMPO"."DES_QUINZENA" IS 'Descricao da quinzena e mes.';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."DIM_TEMPO"."DES_QUADRIMESTRE" IS 'Descricao do quadrimestre e ano.';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."DIM_TEMPO"."NUM_BIMESTRE" IS 'Numero do bimestre no ano.';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."DIM_TEMPO"."DES_BIMESTRE" IS 'Descricao do bimestre e ano.';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."DIM_TEMPO"."DES_ANO_MES" IS 'Ano e mes no formato AAAAMM.';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."DIM_TEMPO"."DES_MES_ANO" IS 'Mes abreviado e ano.';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."DIM_TEMPO"."DES_DIA" IS 'Nome do dia da semana.';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."DIM_TEMPO"."NUM_SEMESTRE" IS 'Numero do semestre no ano.';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."DIM_TEMPO"."DES_MES_ANO_NUMERICO" IS 'Mes e ano no formato MM/AAAA.';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."DIM_TEMPO"."DES_TRIMESTRE" IS 'Descricao do trimestre e ano.';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."DIM_TEMPO"."IND_FINAL_SEMANA" IS 'Indicador de final de semana, onde 1 representa sabado ou domingo.';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."DIM_TEMPO"."DES_MES" IS 'Nome do mes.';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."DIM_TEMPO"."NUM_QUINZENA" IS 'Numero da quinzena no mes.';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."DIM_TEMPO"."DES_MES_ANO_COMPLETO" IS 'Nome completo do mes e ano.';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."DIM_TEMPO"."DES_SEMESTRE" IS 'Descricao do semestre e ano.';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."DIM_TEMPO"."DTC_COMPLETA" IS 'Data calendario completa, sem componente de hora relevante.';


