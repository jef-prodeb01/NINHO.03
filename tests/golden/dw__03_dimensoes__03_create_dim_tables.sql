-- =============================================================================
-- NINHO — 03_create_dim_tables.sql (SCHEMA: DW_GLD)
-- =============================================================================

CREATE TABLE DW_GLD.DIM_ORGAO_PUBLICO (
    DIMENSION_KEY NUMBER(38,0) NOT NULL,
    ID_ORGAO NUMBER(10,0) NOT NULL,
    SIG_ORGAO VARCHAR2(20 CHAR) NOT NULL,
    NOM_ORGAO VARCHAR2(150 CHAR) NOT NULL,
    DES_ESFERA VARCHAR2(50 CHAR),
    SIN_ATIVO CHAR(1 CHAR) DEFAULT 'S' NOT NULL,
    DTC_EFETIVACAO DATE NOT NULL,
    DTC_EXPIRACAO DATE,
    DES_ATUALIZAR CHAR(1 CHAR) DEFAULT 'S' NOT NULL,
    CONSTRAINT PK_DIM_ORGAO_PUBLICO PRIMARY KEY (DIMENSION_KEY) USING INDEX TABLESPACE GLD_INDEX
) TABLESPACE GLD_DATA;

CREATE TABLE DW_GLD.DIM_FORNECEDOR (
    DIMENSION_KEY NUMBER(38,0) NOT NULL,
    ID_FORNECEDOR NUMBER(12,0) NOT NULL,
    NUM_CNPJ VARCHAR2(18 CHAR) NOT NULL,
    NOM_FORNECEDOR VARCHAR2(200 CHAR) NOT NULL,
    SIG_UF CHAR(2 CHAR),
    DES_PORTE_EMPRESA VARCHAR2(60 CHAR),
    SIN_ATIVO CHAR(1 CHAR) DEFAULT 'S' NOT NULL,
    DTC_EFETIVACAO DATE NOT NULL,
    DTC_EXPIRACAO DATE,
    DES_ATUALIZAR CHAR(1 CHAR) DEFAULT 'S' NOT NULL,
    CONSTRAINT PK_DIM_FORNECEDOR PRIMARY KEY (DIMENSION_KEY) USING INDEX TABLESPACE GLD_INDEX
) TABLESPACE GLD_DATA;

-- Dimensão Conformada Padrão Corporativa: DIM_TEMPO (CONVENCOES_DW.md Seção 3.4 - 24 colunas)
-- Surrogate Key Padrão: DIMENSION_KEY (compatível com SK_TEMPO no formato YYYYMMDD ou -1)
CREATE TABLE DW_GLD.DIM_TEMPO (
    DIMENSION_KEY          NUMBER(38,0)       NOT NULL,
    DTC_COMPLETA           DATE               NOT NULL,
    DES_DATA_DIA           VARCHAR2(10 CHAR)  NOT NULL,
    NUM_ANO                NUMBER(4,0)        NOT NULL,
    NUM_MES                NUMBER(2,0)        NOT NULL,
    NOM_MES                VARCHAR2(20 CHAR)  NOT NULL,
    SIG_MES                CHAR(3 CHAR)       NOT NULL,
    DES_ANO_MES            VARCHAR2(7 CHAR)   NOT NULL,
    NUM_ANO_MES            NUMBER(6,0)        NOT NULL,
    NUM_DIA                NUMBER(2,0)        NOT NULL,
    NUM_DIA_ANO            NUMBER(3,0)        NOT NULL,
    NUM_DIA_SEMANA         NUMBER(1,0)        NOT NULL,
    NOM_DIA_SEMANA         VARCHAR2(20 CHAR)  NOT NULL,
    SIG_DIA_SEMANA         CHAR(3 CHAR)       NOT NULL,
    NUM_SEMANA_ANO         NUMBER(2,0)        NOT NULL,
    NUM_SEMANA_MES         NUMBER(1,0)        NOT NULL,
    NUM_BIMESTRE           NUMBER(1,0)        NOT NULL,
    DES_BIMESTRE           VARCHAR2(15 CHAR)  NOT NULL,
    NUM_TRIMESTRE          NUMBER(1,0)        NOT NULL,
    DES_TRIMESTRE          VARCHAR2(15 CHAR)  NOT NULL,
    DES_ANO_TRIMESTRE      VARCHAR2(7 CHAR)   NOT NULL,
    NUM_SEMESTRE           NUMBER(1,0)        NOT NULL,
    DES_SEMESTRE           VARCHAR2(15 CHAR)  NOT NULL,
    FLG_FINAL_SEMANA       CHAR(1 CHAR)       DEFAULT 'N' NOT NULL,
    FLG_DIA_UTIL           CHAR(1 CHAR)       DEFAULT 'S' NOT NULL,
    CONSTRAINT PK_DIM_TEMPO PRIMARY KEY (DIMENSION_KEY) USING INDEX TABLESPACE GLD_INDEX
) TABLESPACE GLD_DATA;
COMMENT ON TABLE DW_GLD.DIM_TEMPO IS 'Dimensão conformada corporativa de calendário civil e fiscal. Uma linha representa um dia civil único no calendário (DIMENSION_KEY no formato YYYYMMDD ou -1).';

-- =============================================================================
-- PATCH FAST-TRACK: COMENTÁRIOS DE TABELAS E COLUNAS (DIMENSÕES (DIM_*))
-- Schema Alvo: DW_GLD | Gerado em: <DATA_HORA>
-- Nota: Script 100% não-destrutivo. Não altera estrutura nem esteira de carga.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Tabela: DW_GLD.DIM_ORGAO_PUBLICO (DIM)
-- -----------------------------------------------------------------------------
COMMENT ON TABLE DW_GLD.DIM_ORGAO_PUBLICO IS 'Dimensão Órgão Publico (com histórico de vigência SCD Tipo 2). Uma linha representa uma versão cadastral de Órgão Publico (incluindo linha técnica -1 para Não Informado).';

COMMENT ON COLUMN DW_GLD.DIM_ORGAO_PUBLICO.DIMENSION_KEY IS 'Surrogate Key técnica da dimensão (PK). Contém o registro sentinela -1 para ''NÃO INFORMADO''.';
COMMENT ON COLUMN DW_GLD.DIM_ORGAO_PUBLICO.ID_ORGAO IS 'Identificador numérico ou chave natural na origem de Órgão (Chave Natural do sistema de origem).';
COMMENT ON COLUMN DW_GLD.DIM_ORGAO_PUBLICO.SIG_ORGAO IS 'Sigla ou abreviação oficial de Órgão.';
COMMENT ON COLUMN DW_GLD.DIM_ORGAO_PUBLICO.NOM_ORGAO IS 'Nome completo ou razão social de Órgão.';
COMMENT ON COLUMN DW_GLD.DIM_ORGAO_PUBLICO.DES_ESFERA IS 'Descrição textual ou detalhamento de Esfera.';
COMMENT ON COLUMN DW_GLD.DIM_ORGAO_PUBLICO.SIN_ATIVO IS 'Sinalizador de registro ativo na fonte (''S'' = Ativo, ''N'' = Inativo).';
COMMENT ON COLUMN DW_GLD.DIM_ORGAO_PUBLICO.DTC_EFETIVACAO IS 'Data de início de vigência da versão do registro (Slowly Changing Dimension Tipo 2).';
COMMENT ON COLUMN DW_GLD.DIM_ORGAO_PUBLICO.DTC_EXPIRACAO IS 'Data de fim de vigência do registro (SCD Tipo 2). Valor NULL indica o registro ativo/vigente.';
COMMENT ON COLUMN DW_GLD.DIM_ORGAO_PUBLICO.DES_ATUALIZAR IS 'Flag de controle de processamento SCD no ODI (''S'' = atualizar, ''N'' = inalterado).';

-- -----------------------------------------------------------------------------
-- Tabela: DW_GLD.DIM_FORNECEDOR (DIM)
-- -----------------------------------------------------------------------------
COMMENT ON TABLE DW_GLD.DIM_FORNECEDOR IS 'Dimensão Fornecedor (com histórico de vigência SCD Tipo 2). Uma linha representa uma versão cadastral de Fornecedor (incluindo linha técnica -1 para Não Informado).';

COMMENT ON COLUMN DW_GLD.DIM_FORNECEDOR.DIMENSION_KEY IS 'Surrogate Key técnica da dimensão (PK). Contém o registro sentinela -1 para ''NÃO INFORMADO''.';
COMMENT ON COLUMN DW_GLD.DIM_FORNECEDOR.ID_FORNECEDOR IS 'Identificador numérico ou chave natural na origem de Fornecedor (Chave Natural do sistema de origem).';
COMMENT ON COLUMN DW_GLD.DIM_FORNECEDOR.NUM_CNPJ IS 'Número ou código numérico de Cnpj.';
COMMENT ON COLUMN DW_GLD.DIM_FORNECEDOR.NOM_FORNECEDOR IS 'Nome completo ou razão social de Fornecedor.';
COMMENT ON COLUMN DW_GLD.DIM_FORNECEDOR.SIG_UF IS 'Sigla ou abreviação oficial de UF.';
COMMENT ON COLUMN DW_GLD.DIM_FORNECEDOR.DES_PORTE_EMPRESA IS 'Descrição textual ou detalhamento de Porte Empresa.';
COMMENT ON COLUMN DW_GLD.DIM_FORNECEDOR.SIN_ATIVO IS 'Sinalizador de registro ativo na fonte (''S'' = Ativo, ''N'' = Inativo).';
COMMENT ON COLUMN DW_GLD.DIM_FORNECEDOR.DTC_EFETIVACAO IS 'Data de início de vigência da versão do registro (Slowly Changing Dimension Tipo 2).';
COMMENT ON COLUMN DW_GLD.DIM_FORNECEDOR.DTC_EXPIRACAO IS 'Data de fim de vigência do registro (SCD Tipo 2). Valor NULL indica o registro ativo/vigente.';
COMMENT ON COLUMN DW_GLD.DIM_FORNECEDOR.DES_ATUALIZAR IS 'Flag de controle de processamento SCD no ODI (''S'' = atualizar, ''N'' = inalterado).';
