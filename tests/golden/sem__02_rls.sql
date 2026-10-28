-- =============================================================================
-- NINHO — SEGURANÇA RLS / ORACLE VPD: 02_rls.sql (PROJETO: GLD)
-- Coluna de Segregação : DIM_ORGAO_PUBLICO
--
-- Identidade efetiva do usuário (resolvida SEMPRE pelo banco, nunca por parâmetro):
--   * Sessão de conta de serviço confiável (pool do Power BI / IA, cadastrada em
--     RLS_CONTAS_SERVICO) com CLIENT_IDENTIFIER definido -> usa o CLIENT_IDENTIFIER
--     (a aplicação chama DBMS_SESSION.SET_IDENTIFIER('<login do usuário final>')).
--   * Qualquer outra sessão -> SESSION_USER. Um usuário comum não consegue se passar
--     por outro definindo o próprio CLIENT_IDENTIFIER.
-- Fail-closed: sem vínculo em USUARIO_SEGMENTOS ou com erro, nenhuma linha é retornada.
-- Conceda SELECT em USUARIO_SEGMENTOS ao papel de consumo (o predicado o consulta).
-- =============================================================================

DECLARE
    PROCEDURE criar_se_nao_existir(p_ddl IN VARCHAR2) IS
    BEGIN
        EXECUTE IMMEDIATE p_ddl;
    EXCEPTION
        WHEN OTHERS THEN
            IF SQLCODE != -955 THEN RAISE; END IF;  -- ORA-00955: objeto já existe
    END;
BEGIN
    criar_se_nao_existir('CREATE TABLE DW_GLD.USUARIO_SEGMENTOS (
        PROJETO          VARCHAR2(50)  DEFAULT ''GLOBAL'' NOT NULL,
        USUARIO_ORACLE   VARCHAR2(128) NOT NULL,
        SEGMENTO         VARCHAR2(128) NOT NULL,
        IND_ACESSO_TOTAL CHAR(1)       DEFAULT ''N'' NOT NULL,
        DT_CRIACAO       DATE          DEFAULT SYSDATE NOT NULL,
        CONSTRAINT PK_USUARIO_SEGMENTOS PRIMARY KEY (PROJETO, USUARIO_ORACLE, SEGMENTO),
        CONSTRAINT CHK_USR_SEG_TOTAL CHECK (IND_ACESSO_TOTAL IN (''S'', ''N'')))');
    criar_se_nao_existir('CREATE TABLE DW_GLD.RLS_CONTAS_SERVICO (
        USUARIO_ORACLE   VARCHAR2(128) NOT NULL,
        DES_FINALIDADE   VARCHAR2(200) NOT NULL,
        DT_CRIACAO       DATE          DEFAULT SYSDATE NOT NULL,
        CONSTRAINT PK_RLS_CONTAS_SERVICO PRIMARY KEY (USUARIO_ORACLE))');
END;
/

COMMENT ON TABLE DW_GLD.USUARIO_SEGMENTOS IS 'Usuário efetivo (login do usuário final ou SESSION_USER) x segmento permitido nas views com RLS.';
COMMENT ON TABLE DW_GLD.RLS_CONTAS_SERVICO IS 'Contas de serviço confiáveis (pool BI/IA) autorizadas a repassar a identidade via CLIENT_IDENTIFIER.';

CREATE OR REPLACE PACKAGE DW_GLD.PKG_SECURITY_GLD AS
    FUNCTION FN_USUARIO_EFETIVO RETURN VARCHAR2;
    FUNCTION FN_PREDICADO_RLS(p_schema IN VARCHAR2, p_object IN VARCHAR2) RETURN VARCHAR2;
END PKG_SECURITY_GLD;
/

CREATE OR REPLACE PACKAGE BODY DW_GLD.PKG_SECURITY_GLD AS
    FUNCTION FN_USUARIO_EFETIVO RETURN VARCHAR2 IS
        v_sessao  VARCHAR2(128) := SYS_CONTEXT('USERENV', 'SESSION_USER');
        v_cliente VARCHAR2(128) := SYS_CONTEXT('USERENV', 'CLIENT_IDENTIFIER');
        v_qtd     NUMBER;
    BEGIN
        IF v_cliente IS NOT NULL THEN
            SELECT COUNT(1) INTO v_qtd FROM DW_GLD.RLS_CONTAS_SERVICO WHERE USUARIO_ORACLE = v_sessao;
            IF v_qtd > 0 THEN
                RETURN UPPER(v_cliente);
            END IF;
        END IF;
        RETURN v_sessao;
    END FN_USUARIO_EFETIVO;

    FUNCTION FN_PREDICADO_RLS(p_schema IN VARCHAR2, p_object IN VARCHAR2) RETURN VARCHAR2 IS
        v_usuario      VARCHAR2(128) := FN_USUARIO_EFETIVO;
        v_acesso_total CHAR(1);
    BEGIN
        SELECT NVL(MAX(IND_ACESSO_TOTAL), 'N') INTO v_acesso_total
          FROM DW_GLD.USUARIO_SEGMENTOS
         WHERE USUARIO_ORACLE = v_usuario AND PROJETO IN ('GLOBAL', 'GLD');
        IF v_acesso_total = 'S' THEN
            RETURN '1 = 1';
        END IF;
        -- Subconsulta em vez de lista concatenada: sem limite de 4000 bytes e sem injeção.
        RETURN 'DIM_ORGAO_PUBLICO = -1 OR TO_CHAR(DIM_ORGAO_PUBLICO) IN (SELECT u.SEGMENTO FROM DW_GLD.USUARIO_SEGMENTOS u'
            || ' WHERE u.PROJETO IN (''GLOBAL'', ''GLD'') AND u.USUARIO_ORACLE = '
            || DBMS_ASSERT.ENQUOTE_LITERAL(v_usuario) || ')';
    EXCEPTION
        WHEN OTHERS THEN
            RETURN '1 = 0';  -- Fail-closed
    END FN_PREDICADO_RLS;
END PKG_SECURITY_GLD;
/

-- Cadastro das contas de serviço do BI/IA (ajuste antes de executar):
-- INSERT INTO DW_GLD.RLS_CONTAS_SERVICO (USUARIO_ORACLE, DES_FINALIDADE) VALUES ('SVC_POWERBI', 'Pool do gateway Power BI');

BEGIN
    BEGIN
        DBMS_RLS.DROP_POLICY(object_schema => 'DW_GLD', object_name => 'VW_GLD_EVENTO_LICITACAO_CONTRATO', policy_name => 'POL_RLS_VW_GLD_EVENTO_LICITACA');
    EXCEPTION WHEN OTHERS THEN NULL;
    END;
    DBMS_RLS.ADD_POLICY(
        object_schema   => 'DW_GLD',
        object_name     => 'VW_GLD_EVENTO_LICITACAO_CONTRATO',
        policy_name     => 'POL_RLS_VW_GLD_EVENTO_LICITACA',
        function_schema => 'DW_GLD',
        policy_function => 'PKG_SECURITY_GLD.FN_PREDICADO_RLS',
        statement_types => 'SELECT',
        policy_type     => DBMS_RLS.DYNAMIC,  -- reavalia a cada execução (pool troca de usuário)
        enable          => TRUE
    );
END;
/

BEGIN
    BEGIN
        DBMS_RLS.DROP_POLICY(object_schema => 'DW_GLD', object_name => 'VW_GLD_KPI_LICITACAO_CONTRATO', policy_name => 'POL_RLS_VW_GLD_KPI_LICITACAO_C');
    EXCEPTION WHEN OTHERS THEN NULL;
    END;
    DBMS_RLS.ADD_POLICY(
        object_schema   => 'DW_GLD',
        object_name     => 'VW_GLD_KPI_LICITACAO_CONTRATO',
        policy_name     => 'POL_RLS_VW_GLD_KPI_LICITACAO_C',
        function_schema => 'DW_GLD',
        policy_function => 'PKG_SECURITY_GLD.FN_PREDICADO_RLS',
        statement_types => 'SELECT',
        policy_type     => DBMS_RLS.DYNAMIC,  -- reavalia a cada execução (pool troca de usuário)
        enable          => TRUE
    );
END;
/
