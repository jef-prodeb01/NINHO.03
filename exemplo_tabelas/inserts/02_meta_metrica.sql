-- =============================================================
-- INSERTs — META_METRICA
-- =============================================================
-- INSERTs para a tabela META_METRICA.
-- Gerado pela IA a partir dos insumos do INTAKE.
-- O engenheiro deve validar antes de executar.
-- =============================================================

-- INSERT INTO META_METRICA (PROJETO, NOME_METRICA, DESCRICAO_NEGOCIO, FORMULA_SQL, TIPO_ADITIVIDADE, DATA_REFERENCIA, FILTROS_OBRIGATORIOS, DIMENSOES_PERMITIDAS, UNIDADE) VALUES
-- ('<PROJETO>', '<nome>', '<descrição>', q'[<sql>]', '<aditividade>', '<data_ref>', '<filtros>', '<dimensoes>', '<unidade>');

-- Exemplo de formato:
-- INSERT INTO META_METRICA (PROJETO, NOME_METRICA, DESCRICAO_NEGOCIO, FORMULA_SQL, TIPO_ADITIVIDADE, DATA_REFERENCIA, FILTROS_OBRIGATORIOS, DIMENSOES_PERMITIDAS, UNIDADE) VALUES
-- ('<PROJETO>', 'TOTAL_VALOR', 'Soma dos valores dos processos', q'[SELECT SUM(VL_VALOR) FROM FATO_X]', 'ADITIVA', 'DT_ANDAMENTO', 'CD_STATUS = ''ATIVO''', 'NM_CIDADE, NM_SECRETARIA', 'R$');

COMMIT;
