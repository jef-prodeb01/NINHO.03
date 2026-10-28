-- =============================================================
-- TEMPLATE — RLS (Row Level Security) opcional (Oracle 12c+)
-- Fonte única: modulos/camada_semantica/templates/02_rls_template.sql
-- (a cópia em .agents/skills/seguranca-rls-oracle/templates/ é sincronizada
--  e verificada por tests/test_templates_sincronizados.py)
-- =============================================================
-- Só use este script se o INTAKE (Seção 4.1) indicou "acesso restrito".
-- O gerador /gerar-rls produz uma versão já parametrizada (02_rls.sql).
--
-- IDENTIDADE EFETIVA (vale para todas as estratégias):
--   Power BI, gateways e agentes de IA conectam com UMA conta de serviço
--   (pool). Filtrar só por SESSION_USER daria a todos a visão da conta de
--   serviço. A aplicação informa o usuário final com
--   DBMS_SESSION.SET_IDENTIFIER('<login>'), e o banco só aceita esse
--   CLIENT_IDENTIFIER se SESSION_USER estiver em RLS_CONTAS_SERVICO.
--   Um usuário comum que defina o próprio CLIENT_IDENTIFIER continua
--   sendo filtrado pelo SESSION_USER (não consegue se passar por outro).
--
-- Estratégias (escolha UMA):
--   A — Filtro EXISTS direto na view final (mais simples e transparente).
--   C — VPD (DBMS_RLS): política aplicada pelo banco a qualquer SQL.
--   D — RLS por projeto nas tabelas META_*.
--   (A antiga estratégia B — LISTAGG em contexto no logon — foi removida:
--    estourava 4000 bytes (ORA-01489) com muitos segmentos e não funciona
--    com pool, pois o logon acontece antes do SET_IDENTIFIER.)
-- =============================================================

-- -------------------------------------------------------------
-- Tabelas de apoio (necessárias em qualquer estratégia)
-- -------------------------------------------------------------
CREATE TABLE USUARIO_SEGMENTOS (
    PROJETO           VARCHAR2(50)  DEFAULT 'GLOBAL' NOT NULL,
    USUARIO_ORACLE    VARCHAR2(128) NOT NULL,
    SEGMENTO          VARCHAR2(128) NOT NULL,
    IND_ACESSO_TOTAL  CHAR(1)       DEFAULT 'N' NOT NULL,  -- 'S' ignora o filtro de segmento
    DT_CRIACAO        DATE          DEFAULT SYSDATE NOT NULL,
    CONSTRAINT PK_USUARIO_SEGMENTOS PRIMARY KEY (PROJETO, USUARIO_ORACLE, SEGMENTO),
    CONSTRAINT CHK_USR_SEG_TOTAL CHECK (IND_ACESSO_TOTAL IN ('S', 'N'))
);

COMMENT ON TABLE USUARIO_SEGMENTOS IS
'Usuário efetivo (login do usuário final via pool confiável, ou SESSION_USER) x segmento permitido nas views com RLS.';
COMMENT ON COLUMN USUARIO_SEGMENTOS.PROJETO IS 'Projeto (ex.: SEI) ou ''GLOBAL'' para permissão compartilhada.';
COMMENT ON COLUMN USUARIO_SEGMENTOS.USUARIO_ORACLE IS 'Usuário efetivo retornado por FN_<PROJETO>_USUARIO_EFETIVO.';
COMMENT ON COLUMN USUARIO_SEGMENTOS.SEGMENTO IS 'Valor do segmento permitido (ex.: código de cidade, secretaria, órgão).';
COMMENT ON COLUMN USUARIO_SEGMENTOS.IND_ACESSO_TOTAL IS 'S = ignora o filtro de segmento (gestor/auditor). N = respeita o filtro.';

CREATE TABLE RLS_CONTAS_SERVICO (
    USUARIO_ORACLE    VARCHAR2(128) NOT NULL,
    DES_FINALIDADE    VARCHAR2(200) NOT NULL,
    DT_CRIACAO        DATE          DEFAULT SYSDATE NOT NULL,
    CONSTRAINT PK_RLS_CONTAS_SERVICO PRIMARY KEY (USUARIO_ORACLE)
);

COMMENT ON TABLE RLS_CONTAS_SERVICO IS
'Contas de serviço confiáveis (pool Power BI / IA) autorizadas a repassar a identidade do usuário final via CLIENT_IDENTIFIER.';

-- Exemplo: INSERT INTO RLS_CONTAS_SERVICO VALUES ('SVC_POWERBI', 'Pool do gateway Power BI', SYSDATE);

-- -------------------------------------------------------------
-- Função de identidade efetiva (usada por todas as estratégias)
-- -------------------------------------------------------------
CREATE OR REPLACE FUNCTION FN_<PROJETO>_USUARIO_EFETIVO RETURN VARCHAR2 AS
    V_SESSAO  VARCHAR2(128) := SYS_CONTEXT('USERENV', 'SESSION_USER');
    V_CLIENTE VARCHAR2(128) := SYS_CONTEXT('USERENV', 'CLIENT_IDENTIFIER');
    V_QTD     NUMBER;
BEGIN
    IF V_CLIENTE IS NOT NULL THEN
        SELECT COUNT(1) INTO V_QTD FROM RLS_CONTAS_SERVICO WHERE USUARIO_ORACLE = V_SESSAO;
        IF V_QTD > 0 THEN
            RETURN UPPER(V_CLIENTE);
        END IF;
    END IF;
    RETURN V_SESSAO;
END FN_<PROJETO>_USUARIO_EFETIVO;
/

-- =============================================================
-- ESTRATÉGIA A — Filtro EXISTS direto na view final
-- =============================================================
-- Sem lista concatenada (sem limite de 4000 bytes). Adicione às views
-- de EVENTO/KPI que precisam de RLS:
--
-- WHERE EXISTS (
--         SELECT 1 FROM USUARIO_SEGMENTOS u
--          WHERE u.USUARIO_ORACLE = FN_<PROJETO>_USUARIO_EFETIVO
--            AND u.PROJETO IN ('GLOBAL', '<PROJETO>')
--            AND (u.IND_ACESSO_TOTAL = 'S' OR u.SEGMENTO = TO_CHAR(<COLUNA_SEGMENTO>))
--       )
--    OR <COLUNA_SEGMENTO> = -1   -- linha sentinela "Não Informado"

-- =============================================================
-- ESTRATÉGIA C — VPD (DBMS_RLS) — política aplicada pelo banco
-- =============================================================
CREATE OR REPLACE FUNCTION FN_<PROJETO>_RLS_PREDICADO (
    P_SCHEMA IN VARCHAR2,
    P_OBJETO IN VARCHAR2
) RETURN VARCHAR2 AS
    V_USUARIO      VARCHAR2(128) := FN_<PROJETO>_USUARIO_EFETIVO;
    V_ACESSO_TOTAL CHAR(1);
BEGIN
    SELECT NVL(MAX(IND_ACESSO_TOTAL), 'N')
      INTO V_ACESSO_TOTAL
      FROM USUARIO_SEGMENTOS
     WHERE USUARIO_ORACLE = V_USUARIO
       AND PROJETO IN ('GLOBAL', '<PROJETO>');

    IF V_ACESSO_TOTAL = 'S' THEN
        RETURN '1 = 1';  -- sem filtro
    END IF;

    -- O usuário entra como literal protegido (DBMS_ASSERT): sem injeção de SQL.
    RETURN '<COLUNA_SEGMENTO> = -1 OR TO_CHAR(<COLUNA_SEGMENTO>) IN ('
        || 'SELECT u.SEGMENTO FROM USUARIO_SEGMENTOS u '
        || 'WHERE u.PROJETO IN (''GLOBAL'', ''<PROJETO>'') AND u.USUARIO_ORACLE = '
        || DBMS_ASSERT.ENQUOTE_LITERAL(V_USUARIO) || ')';
EXCEPTION
    WHEN OTHERS THEN
        RETURN '1 = 0';  -- fail-closed: erro na política nunca libera dados
END FN_<PROJETO>_RLS_PREDICADO;
/

-- Aplica a política em cada view/tabela que precisa de RLS.
-- POLICY_TYPE DYNAMIC: reavalia a cada execução (o pool troca de usuário na mesma sessão).
BEGIN
    DBMS_RLS.ADD_POLICY(
        OBJECT_SCHEMA   => USER,
        OBJECT_NAME     => 'VW_<PROJETO>_EVENTO',
        POLICY_NAME     => 'POL_<PROJETO>_EVENTO',
        FUNCTION_SCHEMA => USER,
        POLICY_FUNCTION => 'FN_<PROJETO>_RLS_PREDICADO',
        STATEMENT_TYPES => 'SELECT',
        POLICY_TYPE     => DBMS_RLS.DYNAMIC
    );
END;
/

-- Para remover uma política:
-- BEGIN
--     DBMS_RLS.DROP_POLICY(OBJECT_SCHEMA => USER, OBJECT_NAME => 'VW_<PROJETO>_EVENTO', POLICY_NAME => 'POL_<PROJETO>_EVENTO');
-- END;
-- /

-- =============================================================
-- ESTRATÉGIA D — RLS POR PROJETO NAS TABELAS META_
-- (Regras 'GLOBAL' sempre visíveis + regras do projeto permitido)
-- =============================================================
-- D.1 — Views de metadados por projeto (declarativa):
-- CREATE OR REPLACE VIEW VW_<PROJETO>_META_GLOSSARIO AS
-- SELECT * FROM META_GLOSSARIO WHERE PROJETO IN ('GLOBAL', '<PROJETO>');
--
-- D.2 — VPD nas próprias tabelas META_*:
CREATE OR REPLACE FUNCTION FN_META_RLS_PREDICADO (
    P_SCHEMA IN VARCHAR2,
    P_OBJETO IN VARCHAR2
) RETURN VARCHAR2 AS
    V_USUARIO      VARCHAR2(128) := FN_<PROJETO>_USUARIO_EFETIVO;
    V_ACESSO_TOTAL CHAR(1);
BEGIN
    SELECT NVL(MAX(IND_ACESSO_TOTAL), 'N')
      INTO V_ACESSO_TOTAL
      FROM USUARIO_SEGMENTOS
     WHERE USUARIO_ORACLE = V_USUARIO;

    IF V_ACESSO_TOTAL = 'S' THEN
        RETURN '1 = 1';  -- visualiza todos os projetos
    END IF;

    RETURN 'PROJETO = ''GLOBAL'' OR PROJETO IN (SELECT u.SEGMENTO FROM USUARIO_SEGMENTOS u WHERE u.USUARIO_ORACLE = '
        || DBMS_ASSERT.ENQUOTE_LITERAL(V_USUARIO) || ')';
EXCEPTION
    WHEN OTHERS THEN
        RETURN 'PROJETO = ''GLOBAL''';  -- fail-closed: só regras universais
END FN_META_RLS_PREDICADO;
/

-- =============================================================
-- NOTAS
-- =============================================================
-- 1. Documente a estratégia escolhida em
--    documentacao/catalogo_projetos/PROJETO_RESUMO.md, seção 6 (Regras de Acesso).
-- 2. Conceda SELECT em USUARIO_SEGMENTOS ao papel de consumo: o predicado
--    da VPD é executado com os privilégios de quem consulta.
-- 3. A aplicação/gateway deve chamar DBMS_SESSION.SET_IDENTIFIER antes de
--    cada consulta e DBMS_SESSION.CLEAR_IDENTIFIER ao devolver a conexão ao pool.
-- 4. Teste com usuários de diferentes segmentos e com a conta de serviço antes
--    de liberar em produção (saida/camada_semantica/meta_projeto/09_validacoes.sql).
COMMIT;
