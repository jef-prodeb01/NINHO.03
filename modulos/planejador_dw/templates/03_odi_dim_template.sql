-- ==============================================================================
-- MODELO DDL: TABELA AUXILIAR PARA COMPONENTE DE DIMENSÕES E CUBOS DO ODI
-- ==============================================================================
-- Padrão Corporativo: ODI_DIM_<SISTEMA>_<DOMINIO>_<ENTIDADE> (ex: ODI_DIM_SEI_BA_UNIDADE, ODI_DIM_COST_MGMT_PROJETO)
-- Schema Alvo:        <SCHEMA_ALVO>
-- Tablespace:         <TABLESPACE_DADOS>
-- Papel:              Clone estrutural da DIM correspondente, sem PKs ou constraints restritivas.
--                     Utilizada exclusivamente pelo ODI para manobra do SCD Tipo 2 via IKM.
-- ==============================================================================

CREATE TABLE "<SCHEMA_ALVO>"."ODI_DIM_<SISTEMA>_<DOMINIO>_<ENTIDADE>" 
   (	"DIMENSION_KEY" NUMBER(38,0), 
	"ID_<ENTIDADE>" NUMBER(38,0), 
	"SIGLA_<ENTIDADE>" VARCHAR2(50), 
	"DS_<ENTIDADE>" VARCHAR2(255), 
	"TIPO_<ENTIDADE>" VARCHAR2(100), 
	"SIN_ATIVO" CHAR(1 CHAR) DEFAULT 'S', 
	"DTC_EFETIVACAO" DATE, 
	"DTC_EXPIRACAO" DATE, 
	"DES_ATUALIZAR" CHAR(1 CHAR) DEFAULT 'S',
	"DES_STATUS_REGISTRO" CHAR(1 CHAR) -- 'I' (Insert), 'U' (Update/Expire), 'D' (Delete/Inactive)
   ) SEGMENT CREATION IMMEDIATE 
  PCTFREE 10 PCTUSED 40 INITRANS 1 MAXTRANS 255 
  NOCOMPRESS LOGGING
  TABLESPACE "<TABLESPACE_DADOS>";

COMMENT ON TABLE "<SCHEMA_ALVO>"."ODI_DIM_<SISTEMA>_<DOMINIO>_<ENTIDADE>" IS 'Tabela auxiliar de trabalho exclusiva para o modulo de Dimensoes e Cubos do ODI (gerenciamento de SCD Tipo 2).';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."ODI_DIM_<SISTEMA>_<DOMINIO>_<ENTIDADE>"."DES_STATUS_REGISTRO" IS 'Flag de controle de CDC do ODI: I (Insert), U (Update), D (Delete).';
