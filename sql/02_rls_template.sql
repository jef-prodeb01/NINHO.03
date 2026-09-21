-- =============================================================
-- TEMPLATE — RLS (Row Level Security) opcional (Oracle 12c+)
-- =============================================================
-- Só use este script se o INTAKE (Seção 4.1) indicou "acesso restrito".
-- Se a resposta foi "acesso total", ignore este arquivo.
--
-- Três estratégias possíveis — escolha UMA (não misture):
--
-- ESTRATÉGIA A — Filtro por subquery direto na view final (mais
--   simples). Não precisa deste arquivo: basta adicionar o WHERE com
--   subquery contra usuario_segmentos na view de EVENTO/KPI, como no
--   exemplo do AGENTS.md/README.md.
--
-- ESTRATÉGIA B — Contexto de sessão (DBMS_SESSION) + views. Fácil de
--   depurar, funciona com qualquer client (BI, IA, SQL Developer).
--
-- ESTRATÉGIA C — VPD (DBMS_RLS) — política aplicada automaticamente
--   pelo banco a QUALQUER SQL sobre a tabela/view, mesmo consultas
--   ad-hoc. Mais forte, porém mais "invisível" — quem não conhece a
--   policy pode ler contagens filtradas sem perceber que há um filtro.
--
-- Rode como o dono do schema do DW. Estratégias B e C exigem o
-- privilégio EXECUTE em DBMS_SESSION/DBMS_RLS (normalmente concedido
-- via CREATE SESSION + privilégios de schema owner).
-- =============================================================

-- -------------------------------------------------------------
-- Tabela de apoio: mapeamento usuário -> segmento(s) permitido(s)
-- -------------------------------------------------------------
-- Necessária em QUALQUER estratégia. Ajuste o nome/domínio da coluna
-- "SEGMENTO" ao caso real (cidade, secretaria, órgão, projeto etc.).
CREATE TABLE USUARIO_SEGMENTOS (
    USUARIO_ORACLE    VARCHAR2(128) NOT NULL,
    SEGMENTO          VARCHAR2(128) NOT NULL,
    IND_ACESSO_TOTAL  CHAR(1) DEFAULT 'N' NOT NULL,  -- 'S' ignora o filtro de segmento
    DT_CRIACAO        DATE DEFAULT SYSDATE NOT NULL,
    CONSTRAINT PK_USUARIO_SEGMENTOS PRIMARY KEY (USUARIO_ORACLE, SEGMENTO)
);

COMMENT ON TABLE USUARIO_SEGMENTOS IS
'Mapeamento entre usuário Oracle (SESSION_USER) e o(s) segmento(s) que ele pode enxergar nas views com RLS. Um usuário pode ter múltiplas linhas (múltiplos segmentos permitidos).';
COMMENT ON COLUMN USUARIO_SEGMENTOS.USUARIO_ORACLE IS 'Usuário de sessão (SYS_CONTEXT(''USERENV'',''SESSION_USER'')).';
COMMENT ON COLUMN USUARIO_SEGMENTOS.SEGMENTO IS 'Valor do segmento permitido (ex.: código de cidade, secretaria, órgão).';
COMMENT ON COLUMN USUARIO_SEGMENTOS.IND_ACESSO_TOTAL IS 'S = ignora o filtro de segmento (acesso total, ex.: gestor). N = respeita o filtro.';
COMMENT ON COLUMN USUARIO_SEGMENTOS.DT_CRIACAO IS 'Data de criação do vínculo usuário/segmento.';

-- =============================================================
-- ESTRATÉGIA B — Contexto de sessão (DBMS_SESSION)
-- =============================================================

-- 1. Package que popula o contexto no logon
CREATE OR REPLACE PACKAGE PKG_<PROJETO>_SEGURANCA AS
    PROCEDURE DEFINIR_CONTEXTO;
END PKG_<PROJETO>_SEGURANCA;
/

CREATE OR REPLACE PACKAGE BODY PKG_<PROJETO>_SEGURANCA AS
    PROCEDURE DEFINIR_CONTEXTO IS
        V_SEGMENTOS    VARCHAR2(4000);
        V_ACESSO_TOTAL CHAR(1);
    BEGIN
        SELECT MAX(IND_ACESSO_TOTAL)
          INTO V_ACESSO_TOTAL
          FROM USUARIO_SEGMENTOS
         WHERE USUARIO_ORACLE = SYS_CONTEXT('USERENV', 'SESSION_USER');

        DBMS_SESSION.SET_CONTEXT('CTX_<PROJETO>', 'ACESSO_TOTAL', NVL(V_ACESSO_TOTAL, 'N'));

        SELECT LISTAGG(SEGMENTO, ',') WITHIN GROUP (ORDER BY SEGMENTO)
          INTO V_SEGMENTOS
          FROM USUARIO_SEGMENTOS
         WHERE USUARIO_ORACLE = SYS_CONTEXT('USERENV', 'SESSION_USER');

        DBMS_SESSION.SET_CONTEXT('CTX_<PROJETO>', 'SEGMENTOS', V_SEGMENTOS);
    END DEFINIR_CONTEXTO;
END PKG_<PROJETO>_SEGURANCA;
/

-- 2. Contexto de aplicação (depende do package acima já existir)
CREATE OR REPLACE CONTEXT CTX_<PROJETO> USING PKG_<PROJETO>_SEGURANCA;

-- Nota: SELECT MAX(...)/LISTAGG(...) sem GROUP BY sempre retornam uma
-- linha (com NULL se não houver match) — não há necessidade de tratar
-- NO_DATA_FOUND aqui; usuário sem vínculo cai naturalmente em
-- ACESSO_TOTAL='N' e SEGMENTOS=NULL (nega acesso por padrão).
CREATE OR REPLACE TRIGGER TRG_<PROJETO>_LOGON
AFTER LOGON ON DATABASE
BEGIN
    PKG_<PROJETO>_SEGURANCA.DEFINIR_CONTEXTO;
END;
/

-- 4. Uso nas views — adicione este WHERE às views de EVENTO/KPI que
--    precisam de RLS:
--
-- WHERE SYS_CONTEXT('CTX_<PROJETO>', 'ACESSO_TOTAL') = 'S'
--    OR <COLUNA_SEGMENTO> IN (
--         SELECT REGEXP_SUBSTR(SYS_CONTEXT('CTX_<PROJETO>', 'SEGMENTOS'), '[^,]+', 1, LEVEL)
--         FROM DUAL
--         CONNECT BY REGEXP_SUBSTR(SYS_CONTEXT('CTX_<PROJETO>', 'SEGMENTOS'), '[^,]+', 1, LEVEL) IS NOT NULL
--       )

-- =============================================================
-- ESTRATÉGIA C — VPD (DBMS_RLS) — política aplicada pelo banco
-- =============================================================

-- 1. Função que retorna o predicado (WHERE) dinamicamente
CREATE OR REPLACE FUNCTION FN_<PROJETO>_RLS_PREDICADO (
    P_SCHEMA IN VARCHAR2,
    P_OBJETO IN VARCHAR2
) RETURN VARCHAR2 AS
    V_ACESSO_TOTAL CHAR(1);
BEGIN
    SELECT MAX(IND_ACESSO_TOTAL)
      INTO V_ACESSO_TOTAL
      FROM USUARIO_SEGMENTOS
     WHERE USUARIO_ORACLE = SYS_CONTEXT('USERENV', 'SESSION_USER');

    IF NVL(V_ACESSO_TOTAL, 'N') = 'S' THEN
        RETURN '1=1';  -- sem filtro
    END IF;

    RETURN q'[<COLUNA_SEGMENTO> IN (
        SELECT SEGMENTO FROM USUARIO_SEGMENTOS
        WHERE USUARIO_ORACLE = SYS_CONTEXT('USERENV', 'SESSION_USER')
    )]';
END FN_<PROJETO>_RLS_PREDICADO;
/

-- 2. Aplica a política em cada view/tabela que precisa de RLS
BEGIN
    DBMS_RLS.ADD_POLICY(
        OBJECT_SCHEMA   => USER,
        OBJECT_NAME     => 'VW_<PROJETO>_EVENTO',
        POLICY_NAME     => 'POL_<PROJETO>_EVENTO',
        FUNCTION_SCHEMA => USER,
        POLICY_FUNCTION => 'FN_<PROJETO>_RLS_PREDICADO',
        STATEMENT_TYPES => 'SELECT'
    );
END;
/

-- Repita DBMS_RLS.ADD_POLICY para cada view/tabela que precisa do filtro.

-- Para remover uma política:
-- BEGIN
--     DBMS_RLS.DROP_POLICY(
--         OBJECT_SCHEMA => USER,
--         OBJECT_NAME   => 'VW_<PROJETO>_EVENTO',
--         POLICY_NAME   => 'POL_<PROJETO>_EVENTO'
--     );
-- END;
-- /

-- =============================================================
-- ESTRATÉGIA D — RLS POR PROJETO NAS TABELAS META_
-- (Herança de Regras 'GLOBAL' + Regras do Projeto Permitido)
-- =============================================================
-- Utilize esta estratégia quando múltiplos projetos compartilharem o mesmo
-- schema Oracle e for necessário isolar os metadados (glossário, métricas,
-- regras, orientações de IA) por projeto, garantindo que diretrizes
-- universais ('GLOBAL') continuem visíveis para todos.
--
-- D.1 — Via Views de Metadados por Projeto (Abordagem Declarativa):
-- CREATE OR REPLACE VIEW VW_<PROJETO>_META_GLOSSARIO AS
-- SELECT * FROM META_GLOSSARIO WHERE PROJETO IN ('GLOBAL', '<PROJETO>');
--
-- CREATE OR REPLACE VIEW VW_<PROJETO>_META_METRICA AS
-- SELECT * FROM META_METRICA WHERE PROJETO IN ('GLOBAL', '<PROJETO>');
--
-- CREATE OR REPLACE VIEW VW_<PROJETO>_META_CONSULTA_NEGOCIO AS
-- SELECT * FROM META_CONSULTA_NEGOCIO WHERE PROJETO IN ('GLOBAL', '<PROJETO>');
--
-- CREATE OR REPLACE VIEW VW_<PROJETO>_META_ORIENTACAO_IA AS
-- SELECT * FROM META_ORIENTACAO_IA WHERE PROJETO IN ('GLOBAL', '<PROJETO>');
--
-- D.2 — Via VPD (DBMS_RLS) nas próprias tabelas META_*:
CREATE OR REPLACE FUNCTION FN_META_RLS_PREDICADO (
    P_SCHEMA IN VARCHAR2,
    P_OBJETO IN VARCHAR2
) RETURN VARCHAR2 AS
    V_ACESSO_TOTAL CHAR(1);
BEGIN
    SELECT MAX(IND_ACESSO_TOTAL)
      INTO V_ACESSO_TOTAL
      FROM USUARIO_SEGMENTOS
     WHERE USUARIO_ORACLE = SYS_CONTEXT('USERENV', 'SESSION_USER');

    IF NVL(V_ACESSO_TOTAL, 'N') = 'S' THEN
        RETURN '1=1';  -- visualiza todos os projetos
    END IF;

    -- Regras 'GLOBAL' são sempre visíveis + apenas o(s) projeto(s) associado(s) ao usuário
    RETURN q'[PROJETO = 'GLOBAL' OR PROJETO IN (
        SELECT SEGMENTO FROM USUARIO_SEGMENTOS
        WHERE USUARIO_ORACLE = SYS_CONTEXT('USERENV', 'SESSION_USER')
    )]';
END FN_META_RLS_PREDICADO;
/

-- Aplicar a política nas tabelas META_ desejadas (exemplo para META_METRICA e META_ORIENTACAO_IA):
-- BEGIN
--     DBMS_RLS.ADD_POLICY(
--         OBJECT_SCHEMA   => USER,
--         OBJECT_NAME     => 'META_METRICA',
--         POLICY_NAME     => 'POL_META_METRICA_PROJETO',
--         FUNCTION_SCHEMA => USER,
--         POLICY_FUNCTION => 'FN_META_RLS_PREDICADO',
--         STATEMENT_TYPES => 'SELECT'
--     );
-- END;
-- /

-- =============================================================
-- NOTAS
-- =============================================================
-- 1. Escolha a estratégia de RLS e documente a escolha em
--    PROJETO_RESUMO.md, seção 6 (Regras de Acesso).
-- 2. Estratégia C/D (VPD) é a mais robusta contra acesso ad-hoc, mas
--    exige mais cuidado: erros na função de predicado afetam TODAS as
--    consultas ao objeto, inclusive as da própria IA/BI.
-- 3. Teste sempre com usuários de diferentes segmentos antes de
--    liberar em produção (ver inserts/meta_projeto/09_validacoes.sql, seção de RLS).
COMMIT;
