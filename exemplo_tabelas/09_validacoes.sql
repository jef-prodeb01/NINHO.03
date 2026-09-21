-- =============================================================
-- TEMPLATE — Validações da camada semântica (Oracle 12c+)
-- =============================================================
-- Rode DEPOIS de views (inserts/vw_analiticas/), META_ (inserts/meta_projeto/01_create_meta_tables.sql) e INSERTs (inserts/meta_projeto/01-08.sql) estarem no ar.
--
-- Este script NÃO altera dados — apenas reporta problemas. Rode cada
-- bloco separadamente e trate qualquer linha retornada como pendência
-- a corrigir antes de liberar a camada semântica.
-- =============================================================

SET SERVEROUTPUT ON SIZE UNLIMITED

-- -------------------------------------------------------------
-- 1. Órfãos em META_RELACIONAMENTO (objeto não existe em META_OBJETO no mesmo PROJETO ou GLOBAL)
-- -------------------------------------------------------------
SELECT R.PROJETO, 'META_RELACIONAMENTO' AS TABELA, R.OBJETO_ORIGEM AS OBJETO_ORFAO, 'ORIGEM' AS PAPEL
FROM META_RELACIONAMENTO R
WHERE NOT EXISTS (
    SELECT 1 FROM META_OBJETO O 
    WHERE O.NOME_OBJETO = R.OBJETO_ORIGEM 
      AND O.PROJETO IN ('GLOBAL', R.PROJETO)
)
UNION ALL
SELECT R.PROJETO, 'META_RELACIONAMENTO', R.OBJETO_DESTINO, 'DESTINO'
FROM META_RELACIONAMENTO R
WHERE NOT EXISTS (
    SELECT 1 FROM META_OBJETO O 
    WHERE O.NOME_OBJETO = R.OBJETO_DESTINO 
      AND O.PROJETO IN ('GLOBAL', R.PROJETO)
);

-- -------------------------------------------------------------
-- 2. Órfãos em META_VALOR_DOMINIO (objeto não existe em META_OBJETO no mesmo PROJETO ou GLOBAL)
-- -------------------------------------------------------------
SELECT V.PROJETO, 'META_VALOR_DOMINIO' AS TABELA, V.NOME_OBJETO AS OBJETO_ORFAO
FROM META_VALOR_DOMINIO V
WHERE NOT EXISTS (
    SELECT 1 FROM META_OBJETO O 
    WHERE O.NOME_OBJETO = V.NOME_OBJETO 
      AND O.PROJETO IN ('GLOBAL', V.PROJETO)
);

-- -------------------------------------------------------------
-- 3. META_OBJETO ativo sem objeto físico correspondente no schema
-- -------------------------------------------------------------
SELECT O.PROJETO, O.NOME_OBJETO, O.OBJETO_FISICO
FROM META_OBJETO O
WHERE O.IND_ATIVO = 'S'
  AND O.OBJETO_FISICO NOT IN (
      SELECT TABLE_NAME FROM USER_TABLES
      UNION ALL
      SELECT VIEW_NAME FROM USER_VIEWS
      UNION ALL
      SELECT MVIEW_NAME FROM USER_MVIEWS
  );

-- -------------------------------------------------------------
-- 4. Métricas sem fórmula SQL preenchida (governança incompleta)
-- -------------------------------------------------------------
SELECT PROJETO, NOME_METRICA
FROM META_METRICA
WHERE FORMULA_SQL IS NULL;

-- -------------------------------------------------------------
-- 5. Regras de negócio ainda PENDENTE (não homologadas)
-- -------------------------------------------------------------
SELECT PROJETO, ID_REGRA, REGRA, SEVERIDADE
FROM META_REGRA_NEGOCIO
WHERE STATUS_REGRA = 'PENDENTE'
ORDER BY PROJETO, SEVERIDADE;

-- -------------------------------------------------------------
-- 6. Teste de execução das views/consultas (PL/SQL)
-- -------------------------------------------------------------
-- Roda um SELECT COUNT(*) em cada objeto ativo de META_OBJETO e em
-- cada SQL de META_CONSULTA_NEGOCIO, reportando falhas via
-- DBMS_OUTPUT. Não interrompe no primeiro erro.
-- Observação: SQL_VALIDADO_INTERPRETACAO é CLOB; EXECUTE IMMEDIATE
-- aceita CLOB diretamente (12c+), desde que o texto caiba no limite
-- de 32767 bytes (ou MAX_STRING_SIZE=EXTENDED esteja habilitado).
DECLARE
    V_COUNT PLS_INTEGER;
    V_OK    PLS_INTEGER := 0;
    V_FALHA PLS_INTEGER := 0;
BEGIN
    DBMS_OUTPUT.PUT_LINE('--- Teste de objetos (META_OBJETO) ---');
    FOR R IN (SELECT PROJETO, NOME_OBJETO, OBJETO_FISICO FROM META_OBJETO WHERE IND_ATIVO = 'S') LOOP
        BEGIN
            EXECUTE IMMEDIATE 'SELECT COUNT(*) FROM ' || R.OBJETO_FISICO INTO V_COUNT;
            DBMS_OUTPUT.PUT_LINE('OK    [' || R.PROJETO || '] ' || R.NOME_OBJETO || ' (' || R.OBJETO_FISICO || ') = ' || V_COUNT || ' linhas');
            V_OK := V_OK + 1;
        EXCEPTION
            WHEN OTHERS THEN
                DBMS_OUTPUT.PUT_LINE('FALHA [' || R.PROJETO || '] ' || R.NOME_OBJETO || ' (' || R.OBJETO_FISICO || ') -> ' || SQLERRM);
                V_FALHA := V_FALHA + 1;
        END;
    END LOOP;

    DBMS_OUTPUT.PUT_LINE('--- Teste de consultas (META_CONSULTA_NEGOCIO) ---');
    FOR R IN (SELECT PROJETO, ID_CONSULTA, SQL_VALIDADO_INTERPRETACAO AS SQL_TXT FROM META_CONSULTA_NEGOCIO) LOOP
        BEGIN
            EXECUTE IMMEDIATE 'SELECT COUNT(*) FROM (' || R.SQL_TXT || ')' INTO V_COUNT;
            DBMS_OUTPUT.PUT_LINE('OK    [' || R.PROJETO || '] ' || R.ID_CONSULTA || ' retornou ' || V_COUNT || ' linhas');
            V_OK := V_OK + 1;
        EXCEPTION
            WHEN OTHERS THEN
                DBMS_OUTPUT.PUT_LINE('FALHA [' || R.PROJETO || '] ' || R.ID_CONSULTA || ' -> ' || SQLERRM);
                V_FALHA := V_FALHA + 1;
        END;
    END LOOP;

    DBMS_OUTPUT.PUT_LINE('--- Resumo: ' || V_OK || ' OK / ' || V_FALHA || ' falha(s) ---');
END;
/

-- -------------------------------------------------------------
-- 7. Contagem de registros por META_ (Total e por PROJETO)
-- -------------------------------------------------------------
SELECT 'META_GLOSSARIO' AS TABELA, PROJETO, COUNT(*) AS REGISTROS FROM META_GLOSSARIO GROUP BY PROJETO
UNION ALL SELECT 'META_METRICA', PROJETO, COUNT(*) FROM META_METRICA GROUP BY PROJETO
UNION ALL SELECT 'META_OBJETO', PROJETO, COUNT(*) FROM META_OBJETO GROUP BY PROJETO
UNION ALL SELECT 'META_RELACIONAMENTO', PROJETO, COUNT(*) FROM META_RELACIONAMENTO GROUP BY PROJETO
UNION ALL SELECT 'META_REGRA_NEGOCIO', PROJETO, COUNT(*) FROM META_REGRA_NEGOCIO GROUP BY PROJETO
UNION ALL SELECT 'META_CONSULTA_NEGOCIO', PROJETO, COUNT(*) FROM META_CONSULTA_NEGOCIO GROUP BY PROJETO
UNION ALL SELECT 'META_ORIENTACAO_IA', PROJETO, COUNT(*) FROM META_ORIENTACAO_IA GROUP BY PROJETO
UNION ALL SELECT 'META_VALOR_DOMINIO', PROJETO, COUNT(*) FROM META_VALOR_DOMINIO GROUP BY PROJETO
ORDER BY TABELA, PROJETO;

-- -------------------------------------------------------------
-- 8. Teste de aditividade (opcional — ajuste ao domínio real)
-- -------------------------------------------------------------
-- Se houver linha de total oficial, compare com a soma do detalhe.
-- Ajuste <MEDIDA>, <FATO>, <FILTRO_LINHA_TOTAL> ao seu modelo.
--
-- SELECT
--     (SELECT SUM(<MEDIDA>) FROM <FATO> WHERE <FILTRO_LINHA_DETALHE>) AS SOMA_DETALHE,
--     (SELECT <MEDIDA> FROM <FATO> WHERE <FILTRO_LINHA_TOTAL>)        AS VALOR_LINHA_TOTAL
-- FROM DUAL;
--
-- Se os dois valores não baterem, a medida NÃO é aditiva como
-- declarado em META_METRICA — corrija TIPO_ADITIVIDADE.

-- -------------------------------------------------------------
-- 9. Teste de RLS (ajuste ao usuário/segmento de teste)
-- -------------------------------------------------------------
-- Rode como um usuário de teste (não o dono do schema) e confirme
-- que só enxerga o segmento esperado:
--
-- SELECT DISTINCT <COLUNA_SEGMENTO> FROM VW_<PROJETO>_EVENTO;
-- -- deve retornar APENAS os segmentos do USUARIO_SEGMENTOS do usuário logado
