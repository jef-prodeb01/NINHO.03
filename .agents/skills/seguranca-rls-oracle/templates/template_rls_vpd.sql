-- =============================================================
-- TEMPLATE: RLS (Row Level Security) / VPD no Oracle 12c+
-- PROJETO: <NOME_PROJETO> | SCHEMA: <SCHEMA_ALVO>
-- =============================================================

-- -------------------------------------------------------------
-- 1. TABELA DE APOIO: MAPEAMENTO USUARIO -> SEGMENTO(S)
-- -------------------------------------------------------------
CREATE TABLE USUARIO_SEGMENTOS (
    PROJETO           VARCHAR2(50) DEFAULT 'GLOBAL' NOT NULL,
    USUARIO_ORACLE    VARCHAR2(128) NOT NULL,
    SEGMENTO          VARCHAR2(128) NOT NULL,
    IND_ACESSO_TOTAL  CHAR(1) DEFAULT 'N' NOT NULL,  -- 'S' ignora o filtro
    DT_CRIACAO        DATE DEFAULT SYSDATE NOT NULL,
    CONSTRAINT PK_USUARIO_SEGMENTOS PRIMARY KEY (PROJETO, USUARIO_ORACLE, SEGMENTO),
    CONSTRAINT CHK_USR_SEG_TOTAL CHECK (IND_ACESSO_TOTAL IN ('S', 'N'))
);

COMMENT ON TABLE USUARIO_SEGMENTOS IS
'Mapeamento entre usuario de sessao, projeto e segmento(s) permitido(s) nas views com RLS.';
COMMENT ON COLUMN USUARIO_SEGMENTOS.PROJETO IS 'Identificador do projeto (ex.: SEI, SIPAR) ou ''GLOBAL'' para permissao compartilhada.';
COMMENT ON COLUMN USUARIO_SEGMENTOS.USUARIO_ORACLE IS 'Usuario Oracle (SYS_CONTEXT(''USERENV'',''SESSION_USER'')).';
COMMENT ON COLUMN USUARIO_SEGMENTOS.SEGMENTO IS 'Codigo ou sigla do segmento (orgao, secretaria, campus, cliente).';
COMMENT ON COLUMN USUARIO_SEGMENTOS.IND_ACESSO_TOTAL IS 'S = ignora filtro (administrador/auditor). N = restrito.';

-- -------------------------------------------------------------
-- 2. ESTRATEGIA A — FILTRO DIRETO NA VIEW SEMANTICA (SIMPLES)
-- -------------------------------------------------------------
-- Exemplo de utilizacao direta no WHERE da VW_EVENTO:
/*
CREATE OR REPLACE VIEW VW_<PROJETO>_EVENTO AS
SELECT f.*
FROM FATO_<PROJETO> f
JOIN DIM_<ENTIDADE> d ON f.DIM_<ENTIDADE> = d.DIMENSION_KEY
WHERE (
    -- Permite se usuario tem acesso total
    EXISTS (
        SELECT 1 FROM USUARIO_SEGMENTOS u
        WHERE u.USUARIO_ORACLE = SYS_CONTEXT('USERENV', 'SESSION_USER')
          AND u.IND_ACESSO_TOTAL = 'S'
    )
    -- Ou se pertence ao segmento permitido
    OR d.COD_SEGMENTO IN (
        SELECT u.SEGMENTO FROM USUARIO_SEGMENTOS u
        WHERE u.USUARIO_ORACLE = SYS_CONTEXT('USERENV', 'SESSION_USER')
    )
);
*/

-- -------------------------------------------------------------
-- 3. ESTRATEGIA C — ORACLE VPD (DBMS_RLS) TRANSPARENTE
-- -------------------------------------------------------------
-- 3.1 Funcao de Predicado de Seguranca
CREATE OR REPLACE FUNCTION FNC_RLS_PREDICADO_SEGMENTO (
    p_schema IN VARCHAR2,
    p_tabela IN VARCHAR2
) RETURN VARCHAR2 AS
    v_usuario       VARCHAR2(128);
    v_acesso_total  CHAR(1) := 'N';
BEGIN
    v_usuario := SYS_CONTEXT('USERENV', 'SESSION_USER');

    -- Verifica acesso total
    BEGIN
        SELECT IND_ACESSO_TOTAL INTO v_acesso_total
        FROM USUARIO_SEGMENTOS
        WHERE USUARIO_ORACLE = v_usuario
          AND IND_ACESSO_TOTAL = 'S'
          AND ROWNUM = 1;
    EXCEPTION
        WHEN NO_DATA_FOUND THEN v_acesso_total := 'N';
    END;

    -- Se tiver acesso irrestrito, nao injeta clausula WHERE
    IF v_acesso_total = 'S' THEN
        RETURN '1=1';
    END IF;

    -- Injeta predicado dinamico de seguranca
    RETURN 'COD_SEGMENTO IN (SELECT SEGMENTO FROM ' || p_schema || '.USUARIO_SEGMENTOS WHERE USUARIO_ORACLE = SYS_CONTEXT(''USERENV'',''SESSION_USER''))';
END;
/

-- 3.2 Aplicacao da Politica VPD na Tabela / View
/*
BEGIN
    DBMS_RLS.ADD_POLICY (
        object_schema   => '<SCHEMA_ALVO>',
        object_name     => 'FATO_<NOME_FATO>',
        policy_name     => 'POL_RLS_SEGMENTO_<PROJETO>',
        function_schema => '<SCHEMA_ALVO>',
        policy_function => 'FNC_RLS_PREDICADO_SEGMENTO',
        statement_types => 'SELECT',
        update_check    => FALSE,
        enable          => TRUE
    );
END;
/
*/

