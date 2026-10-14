-- ==============================================================================
-- PROCEDIMENTOS PL/SQL: MANUTENÇÃO E TUNING PRÉ E PÓS-CARGA DA FATO
-- ==============================================================================
-- Padrão Corporativo: PRC_PRE_CARGA_FATO / PRC_POS_CARGA_FATO
-- Schema Alvo:        <SCHEMA_ALVO>
-- Papel:              1. PRC_PRE_CARGA_FATO: Marca índices BITMAP e secundários
--                        não-únicos como UNUSABLE antes de cargas Direct-Path.
--                     2. PRC_POS_CARGA_FATO: Executa rebuild PARALLEL 4 NOLOGGING,
--                        retorna para NOPARALLEL LOGGING e coleta estatísticas
--                        do otimizador CBO via DBMS_STATS (CASCADE => TRUE).
-- Execução:           Chamada obrigatória em cargas Estratégia A (Truncate & Load).
-- ==============================================================================

CREATE OR REPLACE PROCEDURE "<SCHEMA_ALVO>"."PRC_PRE_CARGA_FATO" (
    p_tabela_fato IN VARCHAR2,
    p_owner       IN VARCHAR2 DEFAULT '<SCHEMA_ALVO>'
) IS
    v_schema VARCHAR2(30) := UPPER(NVL(p_owner, '<SCHEMA_ALVO>'));
    v_sql    VARCHAR2(1000);
BEGIN
    DBMS_OUTPUT.PUT_LINE('>>> Iniciando preparacao pre-carga para: ' || v_schema || '.' || UPPER(p_tabela_fato));

    FOR r IN (
        SELECT index_name, index_type
        FROM all_indexes
        WHERE owner = v_schema
          AND table_name = UPPER(p_tabela_fato)
          AND uniqueness = 'NONUNIQUE'
    ) LOOP
        BEGIN
            v_sql := 'ALTER INDEX "' || v_schema || '"."' || r.index_name || '" UNUSABLE';
            EXECUTE IMMEDIATE v_sql;
            DBMS_OUTPUT.PUT_LINE('Indice marcado como UNUSABLE: ' || r.index_name || ' (' || r.index_type || ')');
        EXCEPTION
            WHEN OTHERS THEN
                DBMS_OUTPUT.PUT_LINE('AVISO ao desativar indice ' || r.index_name || ': ' || SQLERRM);
        END;
    END LOOP;

    DBMS_OUTPUT.PUT_LINE('>>> Preparacao pre-carga concluida para ' || UPPER(p_tabela_fato));
END PRC_PRE_CARGA_FATO;
/

CREATE OR REPLACE PROCEDURE "<SCHEMA_ALVO>"."PRC_POS_CARGA_FATO" (
    p_tabela_fato IN VARCHAR2,
    p_owner       IN VARCHAR2 DEFAULT '<SCHEMA_ALVO>'
) IS
    v_schema        VARCHAR2(30) := UPPER(NVL(p_owner, '<SCHEMA_ALVO>'));
    v_sql           VARCHAR2(1000);
    v_total_rebuilt NUMBER := 0;
BEGIN
    DBMS_OUTPUT.PUT_LINE('>>> Iniciando manutencao pos-carga para: ' || v_schema || '.' || UPPER(p_tabela_fato));

    -- --------------------------------------------------------------------------
    -- 1. REBUILD PARALLEL NOLOGGING DE ÍNDICES BITMAP OU UNUSABLE
    -- --------------------------------------------------------------------------
    FOR r IN (
        SELECT index_name, status, index_type
        FROM all_indexes
        WHERE owner = v_schema
          AND table_name = UPPER(p_tabela_fato)
          AND (status = 'UNUSABLE' OR index_type LIKE '%BITMAP%')
    ) LOOP
        BEGIN
            DBMS_OUTPUT.PUT_LINE('Reconstruindo indice: ' || r.index_name || ' (' || r.index_type || ')...');
            
            -- Rebuild em modo PARALLEL 4 NOLOGGING para performance máxima e menor geração de REDO
            v_sql := 'ALTER INDEX "' || v_schema || '"."' || r.index_name || '" REBUILD PARALLEL 4 NOLOGGING';
            EXECUTE IMMEDIATE v_sql;
            
            -- Retorna o índice para NOPARALLEL LOGGING (evita tempestade de PX servers em queries concorrentes)
            v_sql := 'ALTER INDEX "' || v_schema || '"."' || r.index_name || '" NOPARALLEL LOGGING';
            EXECUTE IMMEDIATE v_sql;
            
            v_total_rebuilt := v_total_rebuilt + 1;
        EXCEPTION
            WHEN OTHERS THEN
                DBMS_OUTPUT.PUT_LINE('ERRO ao reconstruir indice ' || r.index_name || ': ' || SQLERRM);
        END;
    END LOOP;

    DBMS_OUTPUT.PUT_LINE('Total de indices reconstruidos: ' || v_total_rebuilt);

    -- --------------------------------------------------------------------------
    -- 2. COLETA DE ESTATÍSTICAS COMPLETAS COM CASCADE
    -- --------------------------------------------------------------------------
    DBMS_OUTPUT.PUT_LINE('Coletando estatisticas via DBMS_STATS (CASCADE => TRUE)...');
    
    DBMS_STATS.GATHER_TABLE_STATS(
        ownname          => v_schema,
        tabname          => UPPER(p_tabela_fato),
        estimate_percent => DBMS_STATS.AUTO_SAMPLE_SIZE,
        method_opt       => 'FOR ALL COLUMNS SIZE AUTO',
        degree           => 4,
        cascade          => TRUE
    );

    DBMS_OUTPUT.PUT_LINE('>>> Manutencao pos-carga finalizada com SUCESSO para ' || UPPER(p_tabela_fato));
EXCEPTION
    WHEN OTHERS THEN
        DBMS_OUTPUT.PUT_LINE('ERRO FATAL em PRC_POS_CARGA_FATO: ' || SQLERRM);
        RAISE;
END PRC_POS_CARGA_FATO;
/

