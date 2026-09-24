-- ==============================================================================
-- MODELO DDL: TABELA AUXILIAR PARA COMPONENTE DE DIMENSÕES E CUBOS DO ODI
-- ==============================================================================
-- Padrão Corporativo: ODI_DIM_<DOMINIO>_<ENTIDADE> (ex: ODI_DIM_DEIC_ACAO, ODI_DIM_SEI_MUNIC_ORGAO)
-- Schema Alvo: <SCHEMA_ALVO>
-- Tablespace:  <TABLESPACE_DADOS>
-- Papel:       Clone exato da DIM correspondente, sem PKs ou constraints.
--              Utilizada exclusivamente pelo ODI para manobra do SCD Tipo 2.
-- ==============================================================================

CREATE TABLE "<SCHEMA_ALVO>"."ODI_DIM_<DOMINIO>_<ENTIDADE>" 
   (	"DIMENSION_KEY" NUMBER(38,0), 
	"ID_<ENTIDADE>" NUMBER(38,0), 
	"SIGLA_<ENTIDADE>" VARCHAR2(50), 
	"DS_<ENTIDADE>" VARCHAR2(255), 
	"TIPO_<ENTIDADE>" VARCHAR2(100), 
	"SIN_ATIVO_<ENTIDADE>" CHAR(1), 
	"DTC_EFETIVACAO" DATE, 
	"DTC_EXPIRACAO" DATE, 
	"DES_ATUALIZAR" CHAR(1)
   ) SEGMENT CREATION IMMEDIATE 
  PCTFREE 10 PCTUSED 40 INITRANS 1 MAXTRANS 255 
  NOCOMPRESS LOGGING
  TABLESPACE "<TABLESPACE_DADOS>";

COMMENT ON TABLE "<SCHEMA_ALVO>"."ODI_DIM_<DOMINIO>_<ENTIDADE>" IS 'Tabela auxiliar de trabalho exclusiva para o modulo de Dimensoes e Cubos do ODI (gerenciamento de SCD Tipo 2).';
