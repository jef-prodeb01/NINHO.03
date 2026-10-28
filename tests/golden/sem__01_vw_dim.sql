-- =============================================================================
-- NINHO — CAMADA SEMÂNTICA ORACLE (MICRO-PROCESSO: VIEWS DE DIMENSÃO VIGENTE)
-- Projeto / Sigla : GLD
-- Schema Alvo     : DW_GLD
-- Gerado em       : <DATA_HORA>
-- Regra de Ouro   : Proibido SELECT *; obrigatório filtro DTC_EXPIRACAO IS NULL
-- =============================================================================

-- -----------------------------------------------------------------------------
-- View Camada 1: DW_GLD.VW_GLD_DIM_ORGAO_PUBLICO_ATUAL
-- Grão: Uma linha representa o registro atualmente vigente de ORGAO_PUBLICO (ID_ORGAO).
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FORCE VIEW DW_GLD.VW_GLD_DIM_ORGAO_PUBLICO_ATUAL AS
SELECT
    d.DIMENSION_KEY AS DIMENSION_KEY,
    d.ID_ORGAO AS ID_ORGAO,
    d.SIG_ORGAO AS SIG_ORGAO,
    NVL(d.NOM_ORGAO, 'Não Informado') AS NOM_ORGAO,
    NVL(d.DES_ESFERA, 'Não Informado') AS DES_ESFERA,
    d.SIN_ATIVO AS SIN_ATIVO,
    d.DTC_EFETIVACAO AS DTC_EFETIVACAO,
    d.DTC_EXPIRACAO AS DTC_EXPIRACAO
FROM DW_GLD.DIM_ORGAO_PUBLICO d
WHERE d.DTC_EXPIRACAO IS NULL;

COMMENT ON TABLE DW_GLD.VW_GLD_DIM_ORGAO_PUBLICO_ATUAL IS 'View semântica de registros vigentes (SCD2 ativo) da dimensão DIM_ORGAO_PUBLICO. Uma linha representa o registro atualmente vigente de ORGAO_PUBLICO (ID_ORGAO).';
COMMENT ON COLUMN DW_GLD.VW_GLD_DIM_ORGAO_PUBLICO_ATUAL.DIMENSION_KEY IS 'Surrogate Key técnica da dimensão (PK). Contém o registro sentinela -1 para ''NÃO INFORMADO''.';
COMMENT ON COLUMN DW_GLD.VW_GLD_DIM_ORGAO_PUBLICO_ATUAL.ID_ORGAO IS 'Identificador numérico ou chave natural na origem de Órgão (Chave Natural do sistema de origem).';
COMMENT ON COLUMN DW_GLD.VW_GLD_DIM_ORGAO_PUBLICO_ATUAL.SIG_ORGAO IS 'Sigla ou abreviação oficial de Órgão.';
COMMENT ON COLUMN DW_GLD.VW_GLD_DIM_ORGAO_PUBLICO_ATUAL.NOM_ORGAO IS 'Nome completo ou razão social de Órgão.';
COMMENT ON COLUMN DW_GLD.VW_GLD_DIM_ORGAO_PUBLICO_ATUAL.DES_ESFERA IS 'Descrição textual ou detalhamento de Esfera.';
COMMENT ON COLUMN DW_GLD.VW_GLD_DIM_ORGAO_PUBLICO_ATUAL.SIN_ATIVO IS 'Sinalizador de registro ativo na fonte (''S'' = Ativo, ''N'' = Inativo).';
COMMENT ON COLUMN DW_GLD.VW_GLD_DIM_ORGAO_PUBLICO_ATUAL.DTC_EFETIVACAO IS 'Data de início de vigência da versão do registro (Slowly Changing Dimension Tipo 2).';
COMMENT ON COLUMN DW_GLD.VW_GLD_DIM_ORGAO_PUBLICO_ATUAL.DTC_EXPIRACAO IS 'Data de fim de vigência do registro (SCD Tipo 2). Valor NULL indica o registro ativo/vigente.';

-- -----------------------------------------------------------------------------
-- View Camada 1: DW_GLD.VW_GLD_DIM_FORNECEDOR_ATUAL
-- Grão: Uma linha representa o registro atualmente vigente de FORNECEDOR (ID_FORNECEDOR).
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FORCE VIEW DW_GLD.VW_GLD_DIM_FORNECEDOR_ATUAL AS
SELECT
    d.DIMENSION_KEY AS DIMENSION_KEY,
    d.ID_FORNECEDOR AS ID_FORNECEDOR,
    d.NUM_CNPJ AS NUM_CNPJ,
    NVL(d.NOM_FORNECEDOR, 'Não Informado') AS NOM_FORNECEDOR,
    d.SIG_UF AS SIG_UF,
    NVL(d.DES_PORTE_EMPRESA, 'Não Informado') AS DES_PORTE_EMPRESA,
    d.SIN_ATIVO AS SIN_ATIVO,
    d.DTC_EFETIVACAO AS DTC_EFETIVACAO,
    d.DTC_EXPIRACAO AS DTC_EXPIRACAO
FROM DW_GLD.DIM_FORNECEDOR d
WHERE d.DTC_EXPIRACAO IS NULL;

COMMENT ON TABLE DW_GLD.VW_GLD_DIM_FORNECEDOR_ATUAL IS 'View semântica de registros vigentes (SCD2 ativo) da dimensão DIM_FORNECEDOR. Uma linha representa o registro atualmente vigente de FORNECEDOR (ID_FORNECEDOR).';
COMMENT ON COLUMN DW_GLD.VW_GLD_DIM_FORNECEDOR_ATUAL.DIMENSION_KEY IS 'Surrogate Key técnica da dimensão (PK). Contém o registro sentinela -1 para ''NÃO INFORMADO''.';
COMMENT ON COLUMN DW_GLD.VW_GLD_DIM_FORNECEDOR_ATUAL.ID_FORNECEDOR IS 'Identificador numérico ou chave natural na origem de Fornecedor (Chave Natural do sistema de origem).';
COMMENT ON COLUMN DW_GLD.VW_GLD_DIM_FORNECEDOR_ATUAL.NUM_CNPJ IS 'Número ou código numérico de Cnpj.';
COMMENT ON COLUMN DW_GLD.VW_GLD_DIM_FORNECEDOR_ATUAL.NOM_FORNECEDOR IS 'Nome completo ou razão social de Fornecedor.';
COMMENT ON COLUMN DW_GLD.VW_GLD_DIM_FORNECEDOR_ATUAL.SIG_UF IS 'Sigla ou abreviação oficial de UF.';
COMMENT ON COLUMN DW_GLD.VW_GLD_DIM_FORNECEDOR_ATUAL.DES_PORTE_EMPRESA IS 'Descrição textual ou detalhamento de Porte Empresa.';
COMMENT ON COLUMN DW_GLD.VW_GLD_DIM_FORNECEDOR_ATUAL.SIN_ATIVO IS 'Sinalizador de registro ativo na fonte (''S'' = Ativo, ''N'' = Inativo).';
COMMENT ON COLUMN DW_GLD.VW_GLD_DIM_FORNECEDOR_ATUAL.DTC_EFETIVACAO IS 'Data de início de vigência da versão do registro (Slowly Changing Dimension Tipo 2).';
COMMENT ON COLUMN DW_GLD.VW_GLD_DIM_FORNECEDOR_ATUAL.DTC_EXPIRACAO IS 'Data de fim de vigência do registro (SCD Tipo 2). Valor NULL indica o registro ativo/vigente.';
