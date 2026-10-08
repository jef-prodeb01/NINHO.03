-- ==============================================================================
-- MODELO DDL: TABELA DE STAGING (ATERRISSAGEM INICIAL DE FONTES)
-- ==============================================================================
-- Padrão Corporativo: STG_<SISTEMA>_<DOMINIO>_<ENTIDADE> (ex: STG_SEI_BA_F_AND_PROC, STG_COST_MGMT_API)
-- Schema Alvo:        <SCHEMA_ALVO>
-- Tablespace:         <TABLESPACE_DADOS>
-- Ingestão:           Alimentada via Apache Hop (Arquivos), Python (APIs) ou ODI (Banco)
-- ==============================================================================

CREATE TABLE "<SCHEMA_ALVO>"."STG_<SISTEMA>_<DOMINIO>_<ENTIDADE>" 
   (	"ID_<ENTIDADE>" NUMBER(38,0) NOT NULL ENABLE, 
	"DATA_<EVENTO>" DATE, 
	"TIPO_<ENTIDADE>" VARCHAR2(100), 
	"NOME_<ENTIDADE>" VARCHAR2(200), 
	"FASE_<ENTIDADE>" VARCHAR2(100), 
	"QTDE_<MEDIDA_1>" NUMBER, 
	"QTDE_<MEDIDA_2>" NUMBER, 
	"VAL_<VALOR_1>" NUMBER(18,4),
	"FLAG_<INDICADOR_1>" VARCHAR2(3), 
	"FLAG_<INDICADOR_2>" VARCHAR2(3), 
	"LINK_DOCUMENTO" VARCHAR2(500), 
	"RESUMO" CLOB, 
	"ID_LOTE" NUMBER(38,0), 
	"DTC_EXTRACAO" DATE DEFAULT SYSDATE NOT NULL ENABLE, 
	 CONSTRAINT "STG_<SISTEMA>_<DOMINIO>_<ENTIDADE>_PK" PRIMARY KEY ("ID_<ENTIDADE>")
  USING INDEX PCTFREE 10 INITRANS 2 MAXTRANS 255 COMPUTE STATISTICS 
  TABLESPACE "<TABLESPACE_DADOS>" ENABLE
   ) SEGMENT CREATION IMMEDIATE 
  PCTFREE 10 PCTUSED 40 INITRANS 1 MAXTRANS 255 
  NOCOMPRESS LOGGING
  TABLESPACE "<TABLESPACE_DADOS>"
  LOB ("RESUMO") STORE AS SECUREFILE (
    TABLESPACE "<TABLESPACE_DADOS>" ENABLE STORAGE IN ROW CHUNK 8192
    NOCACHE LOGGING NOCOMPRESS KEEP_DUPLICATES
  );

COMMENT ON TABLE "<SCHEMA_ALVO>"."STG_<SISTEMA>_<DOMINIO>_<ENTIDADE>" IS 'Tabela de staging para aterrissagem dos dados operacionais da entidade <ENTIDADE>.';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."STG_<SISTEMA>_<DOMINIO>_<ENTIDADE>"."ID_<ENTIDADE>" IS 'Identificador natural/operacional unico na origem.';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."STG_<SISTEMA>_<DOMINIO>_<ENTIDADE>"."DATA_<EVENTO>" IS 'Data e hora do evento na origem.';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."STG_<DOMINIO>_<ENTIDADE>"."RESUMO" IS 'Descritivo textual detalhado em formato CLOB.';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."STG_<SISTEMA>_<DOMINIO>_<ENTIDADE>"."ID_LOTE" IS 'Identificador sequencial do lote de carga para rastreabilidade de micro-lotes.';
COMMENT ON COLUMN "<SCHEMA_ALVO>"."STG_<SISTEMA>_<DOMINIO>_<ENTIDADE>"."DTC_EXTRACAO" IS 'Data e hora exata em que o registro aterrissou na camada de staging.';
