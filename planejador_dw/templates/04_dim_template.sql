-- ==============================================================================
-- MODELO DDL: DIMENSÃO OFICIAL COM HISTÓRICO SCD TIPO 2
-- ==============================================================================
-- Padrão Corporativo: DIM_<DOMINIO>_<ENTIDADE> (ex: DIM_SEI_MUNIC_ORGAO, DIM_DEIC_ACAO)
-- Schema Alvo: <SCHEMA_ALVO>
-- Tablespace:  <TABLESPACE_DADOS>
-- Chave:       DIMENSION_KEY (Surrogate Key)
-- Histórico:   DTC_EFETIVACAO, DTC_EXPIRACAO (NULL = vigente)
-- ==============================================================================

CREATE TABLE "<SCHEMA_ALVO>"."DIM_<DOMINIO>_<ENTIDADE>" 
   (	"DIMENSION_KEY" NUMBER(38,0) NOT NULL ENABLE, 
	"ID_<ENTIDADE>" NUMBER(38,0) NOT NULL ENABLE, 
	"SIGLA_<ENTIDADE>" VARCHAR2(50), 
	"DS_<ENTIDADE>" VARCHAR2(255), 
	"TIPO_<ENTIDADE>" VARCHAR2(100), 
	"SIN_ATIVO_<ENTIDADE>" CHAR(1), 
	"COD_IBGE" NUMBER(38,0), 
	"DTC_EFETIVACAO" DATE, 
	"DTC_EXPIRACAO" DATE, 
	"DES_ATUALIZAR" CHAR(1), 
	 CONSTRAINT "DIM_<DOMINIO>_<ENTIDADE>_PK" PRIMARY KEY ("DIMENSION_KEY")
  USING INDEX PCTFREE 10 INITRANS 2 MAXTRANS 255 COMPUTE STATISTICS 
  TABLESPACE "<TABLESPACE_DADOS>" ENABLE
   ) SEGMENT CREATION IMMEDIATE 
  PCTFREE 10 PCTUSED 40 INITRANS 1 MAXTRANS 255 
  NOCOMPRESS LOGGING
  TABLESPACE "<TABLESPACE_DADOS>";

-- ------------------------------------------------------------------------------
-- ÍNDICE E CONSTRAINT DE HISTÓRICO (SCD TIPO 2)
-- ------------------------------------------------------------------------------
CREATE INDEX "<SCHEMA_ALVO>"."IDX_<ENTIDADE>_EFETIV" 
  ON "<SCHEMA_ALVO>"."DIM_<DOMINIO>_<ENTIDADE>" ("ID_<ENTIDADE>", "DTC_EFETIVACAO") 
  PCTFREE 10 INITRANS 2 MAXTRANS 255 COMPUTE STATISTICS 
  TABLESPACE "<TABLESPACE_DADOS>";

ALTER TABLE "<SCHEMA_ALVO>"."DIM_<DOMINIO>_<ENTIDADE>" 
  ADD CONSTRAINT "DIM_<DOMINIO>_<ENTIDADE>_UNIQUE" UNIQUE ("ID_<ENTIDADE>", "DTC_EFETIVACAO")
  USING INDEX "<SCHEMA_ALVO>"."IDX_<ENTIDADE>_EFETIV" ENABLE;

-- ------------------------------------------------------------------------------
-- ÍNDICE BITMAP (PARA COLUNAS DE BAIXA CARDINALIDADE)
-- ------------------------------------------------------------------------------
CREATE BITMAP INDEX "<SCHEMA_ALVO>"."BMX_DIM_<ENTIDADE>_ATIVO" 
  ON "<SCHEMA_ALVO>"."DIM_<DOMINIO>_<ENTIDADE>" ("SIN_ATIVO_<ENTIDADE>") 
  TABLESPACE "<TABLESPACE_DADOS>";

-- ------------------------------------------------------------------------------
-- DOCUMENTAÇÃO E COMENTÁRIOS
-- ------------------------------------------------------------------------------
COMMENT ON TABLE "<SCHEMA_ALVO>"."DIM_<DOMINIO>_<ENTIDADE>" IS 'Dimensao historica oficial de <ENTIDADE> com controle de vigencia SCD Tipo 2.';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."DIM_<DOMINIO>_<ENTIDADE>"."DIMENSION_KEY" IS 'Chave substituta (Surrogate Key) da versao historica da dimensao.';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."DIM_<DOMINIO>_<ENTIDADE>"."ID_<ENTIDADE>" IS 'Identificador global de negocio da entidade na origem.';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."DIM_<DOMINIO>_<ENTIDADE>"."SIGLA_<ENTIDADE>" IS 'Sigla representativa da entidade.';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."DIM_<DOMINIO>_<ENTIDADE>"."DS_<ENTIDADE>" IS 'Descricao ou nome completo da entidade.';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."DIM_<DOMINIO>_<ENTIDADE>"."SIN_ATIVO_<ENTIDADE>" IS 'Indicador de situacao ativa (S ou N).';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."DIM_<DOMINIO>_<ENTIDADE>"."DTC_EFETIVACAO" IS 'Data de inicio da validade desta versao dimensional.';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."DIM_<DOMINIO>_<ENTIDADE>"."DTC_EXPIRACAO" IS 'Data de fim da validade. Nulo indica que esta e a versao vigente.';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."DIM_<DOMINIO>_<ENTIDADE>"."DES_ATUALIZAR" IS 'Indicador tecnico utilizado pelo processo ODI para controle de atualizacao.';
