-- =============================================================
-- TABELAS META_ — camada semântica sobre o DW Oracle (Oracle 12c+)
-- =============================================================
-- Rode este script UMA VEZ no início do projeto.
-- Ele cria as 8 tabelas de catálogo semântico e as triggers de auditoria.
-- Os INSERTs ficam em arquivos separados (inserts/meta_projeto/).
--
-- NOTA MULTI-PROJETO:
-- Todas as tabelas possuem a coluna PROJETO (DEFAULT 'GLOBAL').
-- Regras e metadados globais/compartilhados utilizam PROJETO = 'GLOBAL'.
-- Quando houver isolamento por projeto, registros específicos utilizam
-- PROJETO = '<NOME_PROJETO>' e filtros RLS carregam:
-- WHERE PROJETO IN ('GLOBAL', '<NOME_PROJETO>').
--
-- Ordem de criação:
--   1. META_GLOSSARIO
--   2. META_METRICA
--   3. META_CONSULTA_NEGOCIO
--   4. META_OBJETO
--   5. META_RELACIONAMENTO
--   6. META_REGRA_NEGOCIO
--   7. META_VALOR_DOMINIO
--   8. META_ORIENTACAO_IA
--   Triggers de auditoria (uma por tabela)
-- =============================================================

-- -------------------------------------------------------------
-- META_GLOSSARIO — glossário semântico por domínio
-- -------------------------------------------------------------
CREATE TABLE META_GLOSSARIO (
    PROJETO             VARCHAR2(50) DEFAULT 'GLOBAL' NOT NULL,
    DOMINIO             VARCHAR2(255) NOT NULL,
    IDENTIFICADOR       VARCHAR2(255) NOT NULL,
    DESCRICAO           VARCHAR2(4000) NOT NULL,
    SINONIMOS           VARCHAR2(4000),
    EXEMPLOS_VALORES    VARCHAR2(4000),
    REGRA_USO           VARCHAR2(4000),
    CLASSIFICACAO       VARCHAR2(50),
    DT_CRIACAO          DATE DEFAULT SYSDATE NOT NULL,
    DT_ATUALIZACAO      DATE DEFAULT SYSDATE NOT NULL,
    USUARIO_ATUALIZACAO VARCHAR2(128) DEFAULT SYS_CONTEXT('USERENV','SESSION_USER'),
    CONSTRAINT PK_META_GLOSSARIO PRIMARY KEY (PROJETO, IDENTIFICADOR)
);

COMMENT ON TABLE META_GLOSSARIO IS
'Glossário semântico do projeto. Documenta conceitos de negócio, indicadores, objetos, colunas e regras técnicas para apoiar a interpretação das informações e a geração de consultas por usuários e assistentes de IA.';

COMMENT ON COLUMN META_GLOSSARIO.PROJETO IS 'Identificador do projeto (ex.: SEI, SIPAR) ou ''GLOBAL'' para conceitos compartilhados.';
COMMENT ON COLUMN META_GLOSSARIO.DOMINIO IS 'Área temática ou domínio de negócio ao qual o item pertence.';
COMMENT ON COLUMN META_GLOSSARIO.IDENTIFICADOR IS 'Identificador único do conceito, indicador, objeto ou coluna documentada dentro do projeto.';
COMMENT ON COLUMN META_GLOSSARIO.DESCRICAO IS 'Definição funcional do conceito, indicador, objeto ou coluna no contexto deste projeto.';
COMMENT ON COLUMN META_GLOSSARIO.SINONIMOS IS 'Termos equivalentes, abreviações e formas alternativas de referência ao item. Utilizado para relacionar perguntas em linguagem natural aos conceitos da camada semântica.';
COMMENT ON COLUMN META_GLOSSARIO.EXEMPLOS_VALORES IS 'Exemplos representativos de valores, formatos ou categorias associados ao item.';
COMMENT ON COLUMN META_GLOSSARIO.REGRA_USO IS 'Orientação semântica para utilização correta do item em filtros, agrupamentos, cálculos e consultas.';
COMMENT ON COLUMN META_GLOSSARIO.CLASSIFICACAO IS 'Classificação do item documentado, como CONCEITO_DE_NEGOCIO, INDICADOR, OBJETO_SEMANTICO, REGRA_TECNICA ou CONCEITO_DE_MODELAGEM.';
COMMENT ON COLUMN META_GLOSSARIO.DT_CRIACAO IS 'Data de criação do registro.';
COMMENT ON COLUMN META_GLOSSARIO.DT_ATUALIZACAO IS 'Data da última atualização do registro (mantida por trigger).';
COMMENT ON COLUMN META_GLOSSARIO.USUARIO_ATUALIZACAO IS 'Usuário Oracle que realizou a última atualização (mantido por trigger).';

-- -------------------------------------------------------------
-- META_METRICA — catálogo de métricas com fórmula e regras
-- -------------------------------------------------------------
CREATE TABLE META_METRICA (
    PROJETO              VARCHAR2(50) DEFAULT 'GLOBAL' NOT NULL,
    NOME_METRICA         VARCHAR2(255) NOT NULL,
    DESCRICAO_NEGOCIO    VARCHAR2(4000) NOT NULL,
    FORMULA_SQL          VARCHAR2(4000),
    TIPO_ADITIVIDADE     VARCHAR2(50) NOT NULL,  -- 'ADITIVA', 'SEMI_ADITIVA', 'NAO_ADITIVA'
    DATA_REFERENCIA      VARCHAR2(255),
    FILTROS_OBRIGATORIOS VARCHAR2(4000),
    DIMENSOES_PERMITIDAS VARCHAR2(4000),
    UNIDADE              VARCHAR2(50),
    DT_CRIACAO           DATE DEFAULT SYSDATE NOT NULL,
    DT_ATUALIZACAO       DATE DEFAULT SYSDATE NOT NULL,
    USUARIO_ATUALIZACAO  VARCHAR2(128) DEFAULT SYS_CONTEXT('USERENV','SESSION_USER'),
    CONSTRAINT PK_META_METRICA PRIMARY KEY (PROJETO, NOME_METRICA)
);

COMMENT ON TABLE META_METRICA IS
'Catálogo de métricas da camada semântica. Documenta definições de negócio, fórmulas de cálculo, regras de agregação, referências temporais, filtros obrigatórios, dimensões permitidas e unidades de medida.';

COMMENT ON COLUMN META_METRICA.PROJETO IS 'Identificador do projeto (ex.: SEI, SIPAR) ou ''GLOBAL'' para métricas compartilhadas.';
COMMENT ON COLUMN META_METRICA.NOME_METRICA IS 'Nome único da métrica utilizada na camada semântica dentro do projeto.';
COMMENT ON COLUMN META_METRICA.DESCRICAO_NEGOCIO IS 'Definição funcional da métrica, descrevendo o que ela mede e como deve ser interpretada.';
COMMENT ON COLUMN META_METRICA.FORMULA_SQL IS 'Expressão ou consulta SQL de referência para cálculo da métrica.';
COMMENT ON COLUMN META_METRICA.TIPO_ADITIVIDADE IS 'Regra de agregação: ADITIVA (soma livre), SEMI_ADITIVA (com restrição) ou NAO_ADITIVA (recalcular).';
COMMENT ON COLUMN META_METRICA.DATA_REFERENCIA IS 'Campo, competência ou contexto temporal utilizado para apuração da métrica.';
COMMENT ON COLUMN META_METRICA.FILTROS_OBRIGATORIOS IS 'Filtros e condições que devem ser aplicados para garantir o cálculo correto.';
COMMENT ON COLUMN META_METRICA.DIMENSOES_PERMITIDAS IS 'Dimensões pelas quais a métrica pode ser filtrada ou agrupada.';
COMMENT ON COLUMN META_METRICA.UNIDADE IS 'Unidade de medida utilizada na apresentação do resultado.';
COMMENT ON COLUMN META_METRICA.DT_CRIACAO IS 'Data de criação do registro.';
COMMENT ON COLUMN META_METRICA.DT_ATUALIZACAO IS 'Data da última atualização do registro (mantida por trigger).';
COMMENT ON COLUMN META_METRICA.USUARIO_ATUALIZACAO IS 'Usuário Oracle que realizou a última atualização (mantido por trigger).';

-- -------------------------------------------------------------
-- META_CONSULTA_NEGOCIO — perguntas + SQL validado
-- -------------------------------------------------------------
CREATE TABLE META_CONSULTA_NEGOCIO (
    PROJETO                        VARCHAR2(50) DEFAULT 'GLOBAL' NOT NULL,
    ID_CONSULTA                    VARCHAR2(10) NOT NULL,
    PERGUNTA_LINGUAGEM_NATURAL     VARCHAR2(4000),
    PAINEL_RELACIONADO             VARCHAR2(255),
    OBSERVACOES                    VARCHAR2(4000),
    SQL_VALIDADO_INTERPRETACAO     CLOB,
    OBJETOS_CHAVE                  VARCHAR2(1000),
    DT_CRIACAO                     DATE DEFAULT SYSDATE NOT NULL,
    DT_ATUALIZACAO                 DATE DEFAULT SYSDATE NOT NULL,
    USUARIO_ATUALIZACAO            VARCHAR2(128) DEFAULT SYS_CONTEXT('USERENV','SESSION_USER'),
    CONSTRAINT PK_META_CONSULTA_NEGOCIO PRIMARY KEY (PROJETO, ID_CONSULTA)
);

COMMENT ON TABLE META_CONSULTA_NEGOCIO IS
'Catálogo de perguntas de negócio com consultas SQL validadas. Orienta usuários e assistentes de IA na interpretação das perguntas, seleção dos objetos adequados e geração de resultados consistentes.';

COMMENT ON COLUMN META_CONSULTA_NEGOCIO.PROJETO IS 'Identificador do projeto (ex.: SEI, SIPAR) ou ''GLOBAL'' para consultas compartilhadas.';
COMMENT ON COLUMN META_CONSULTA_NEGOCIO.ID_CONSULTA IS 'Identificador único da consulta de negócio cadastrada dentro do projeto.';
COMMENT ON COLUMN META_CONSULTA_NEGOCIO.PERGUNTA_LINGUAGEM_NATURAL IS 'Pergunta de negócio representativa, escrita em linguagem natural.';
COMMENT ON COLUMN META_CONSULTA_NEGOCIO.PAINEL_RELACIONADO IS 'Painel, tema ou domínio analítico ao qual a pergunta está relacionada.';
COMMENT ON COLUMN META_CONSULTA_NEGOCIO.OBSERVACOES IS 'Orientações para interpretação e execução da consulta.';
COMMENT ON COLUMN META_CONSULTA_NEGOCIO.SQL_VALIDADO_INTERPRETACAO IS 'Consulta SQL de referência validada para responder à pergunta.';
COMMENT ON COLUMN META_CONSULTA_NEGOCIO.OBJETOS_CHAVE IS 'Lista dos principais objetos da camada semântica utilizados pela consulta.';
COMMENT ON COLUMN META_CONSULTA_NEGOCIO.DT_CRIACAO IS 'Data de criação do registro.';
COMMENT ON COLUMN META_CONSULTA_NEGOCIO.DT_ATUALIZACAO IS 'Data da última atualização do registro (mantida por trigger).';
COMMENT ON COLUMN META_CONSULTA_NEGOCIO.USUARIO_ATUALIZACAO IS 'Usuário Oracle que realizou a última atualização (mantido por trigger).';

-- -------------------------------------------------------------
-- META_OBJETO — catálogo de objetos semânticos com governança
-- -------------------------------------------------------------
CREATE TABLE META_OBJETO (
    PROJETO             VARCHAR2(50) DEFAULT 'GLOBAL' NOT NULL,
    NOME_OBJETO         VARCHAR2(128) NOT NULL,
    TIPO_OBJETO         VARCHAR2(30) NOT NULL,  -- 'DIMENSAO', 'EVENTO', 'KPI', 'ALERTA'
    DOMINIO             VARCHAR2(100) NOT NULL,
    GRAO                VARCHAR2(500) NOT NULL,
    SCHEMA_ORIGEM       VARCHAR2(128),
    OBJETO_FISICO       VARCHAR2(128),
    IND_GOVERNADO       CHAR(1) DEFAULT 'S' NOT NULL,  -- 'S' / 'N'
    IND_ATIVO           CHAR(1) DEFAULT 'S' NOT NULL,  -- 'S' / 'N'
    DT_INICIO_VIGENCIA  DATE NOT NULL,
    DT_FIM_VIGENCIA     DATE,
    DT_CRIACAO          DATE DEFAULT SYSDATE NOT NULL,
    DT_ATUALIZACAO      DATE DEFAULT SYSDATE NOT NULL,
    USUARIO_ATUALIZACAO VARCHAR2(128) DEFAULT SYS_CONTEXT('USERENV','SESSION_USER'),
    CONSTRAINT PK_META_OBJETO PRIMARY KEY (PROJETO, NOME_OBJETO)
);

COMMENT ON TABLE META_OBJETO IS
'Catálogo dos objetos da camada semântica. Documenta o tipo, domínio, grão, origem, situação de governança, disponibilidade e período de vigência de cada objeto.';

COMMENT ON COLUMN META_OBJETO.PROJETO IS 'Identificador do projeto (ex.: SEI, SIPAR) ou ''GLOBAL'' para objetos compartilhados.';
COMMENT ON COLUMN META_OBJETO.NOME_OBJETO IS 'Nome do objeto disponibilizado na camada semântica.';
COMMENT ON COLUMN META_OBJETO.TIPO_OBJETO IS 'Classificação funcional: DIMENSAO, EVENTO, KPI ou ALERTA.';
COMMENT ON COLUMN META_OBJETO.DOMINIO IS 'Área ou domínio de negócio ao qual o objeto pertence.';
COMMENT ON COLUMN META_OBJETO.GRAO IS 'Descrição do menor nível de detalhe representado por uma linha do objeto.';
COMMENT ON COLUMN META_OBJETO.SCHEMA_ORIGEM IS 'Schema Oracle no qual está localizado o objeto físico.';
COMMENT ON COLUMN META_OBJETO.OBJETO_FISICO IS 'Nome da tabela, view ou outro objeto utilizado como referência física.';
COMMENT ON COLUMN META_OBJETO.IND_GOVERNADO IS 'Indica se o objeto está homologado e governado: S para sim, N para não.';
COMMENT ON COLUMN META_OBJETO.IND_ATIVO IS 'Indica se o objeto está disponível: S para ativo, N para inativo.';
COMMENT ON COLUMN META_OBJETO.DT_INICIO_VIGENCIA IS 'Data de início da vigência do registro.';
COMMENT ON COLUMN META_OBJETO.DT_FIM_VIGENCIA IS 'Data de encerramento da vigência. Nula enquanto vigente.';
COMMENT ON COLUMN META_OBJETO.DT_CRIACAO IS 'Data de criação do registro.';
COMMENT ON COLUMN META_OBJETO.DT_ATUALIZACAO IS 'Data da última atualização do registro (mantida por trigger).';
COMMENT ON COLUMN META_OBJETO.USUARIO_ATUALIZACAO IS 'Usuário Oracle que realizou a última atualização (mantido por trigger).';

-- -------------------------------------------------------------
-- META_RELACIONAMENTO — relacionamentos entre objetos
-- -------------------------------------------------------------
CREATE TABLE META_RELACIONAMENTO (
    ID_RELACIONAMENTO   NUMBER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    PROJETO             VARCHAR2(50) DEFAULT 'GLOBAL' NOT NULL,
    OBJETO_ORIGEM       VARCHAR2(128) NOT NULL,
    COLUNA_ORIGEM       VARCHAR2(128) NOT NULL,
    OBJETO_DESTINO      VARCHAR2(128) NOT NULL,
    COLUNA_DESTINO      VARCHAR2(128) NOT NULL,
    TIPO_JOIN           VARCHAR2(10) DEFAULT 'LEFT',  -- 'LEFT', 'INNER', 'RIGHT'
    CARDINALIDADE       VARCHAR2(10) DEFAULT 'N:1',   -- 'N:1', '1:1', '1:N'
    OBSERVACAO          VARCHAR2(4000),
    DT_CRIACAO          DATE DEFAULT SYSDATE NOT NULL,
    DT_ATUALIZACAO      DATE DEFAULT SYSDATE NOT NULL,
    USUARIO_ATUALIZACAO VARCHAR2(128) DEFAULT SYS_CONTEXT('USERENV','SESSION_USER')
);

COMMENT ON TABLE META_RELACIONAMENTO IS
'Catálogo de relacionamentos entre objetos da camada semântica. Documenta joins, cardinalidades e observações técnicas.';

COMMENT ON COLUMN META_RELACIONAMENTO.PROJETO IS 'Identificador do projeto (ex.: SEI, SIPAR) ou ''GLOBAL'' para relacionamentos compartilhados.';
COMMENT ON COLUMN META_RELACIONAMENTO.ID_RELACIONAMENTO IS 'Identificador único do relacionamento.';
COMMENT ON COLUMN META_RELACIONAMENTO.OBJETO_ORIGEM IS 'Nome do objeto de origem do relacionamento.';
COMMENT ON COLUMN META_RELACIONAMENTO.COLUNA_ORIGEM IS 'Coluna de origem do relacionamento.';
COMMENT ON COLUMN META_RELACIONAMENTO.OBJETO_DESTINO IS 'Nome do objeto de destino do relacionamento.';
COMMENT ON COLUMN META_RELACIONAMENTO.COLUNA_DESTINO IS 'Coluna de destino do relacionamento.';
COMMENT ON COLUMN META_RELACIONAMENTO.TIPO_JOIN IS 'Tipo de join: LEFT, INNER ou RIGHT.';
COMMENT ON COLUMN META_RELACIONAMENTO.CARDINALIDADE IS 'Cardinalidade: N:1, 1:1 ou 1:N.';
COMMENT ON COLUMN META_RELACIONAMENTO.OBSERVACAO IS 'Observações técnicas sobre o relacionamento.';
COMMENT ON COLUMN META_RELACIONAMENTO.DT_CRIACAO IS 'Data de criação do registro.';
COMMENT ON COLUMN META_RELACIONAMENTO.DT_ATUALIZACAO IS 'Data da última atualização do registro (mantida por trigger).';
COMMENT ON COLUMN META_RELACIONAMENTO.USUARIO_ATUALIZACAO IS 'Usuário Oracle que realizou a última atualização (mantido por trigger).';

-- -------------------------------------------------------------
-- META_REGRA_NEGOCIO — regras de negócio com severidade e status
-- -------------------------------------------------------------
CREATE TABLE META_REGRA_NEGOCIO (
    ID_REGRA            NUMBER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    PROJETO             VARCHAR2(50) DEFAULT 'GLOBAL' NOT NULL,
    REGRA               VARCHAR2(4000) NOT NULL,
    SEVERIDADE          VARCHAR2(20) NOT NULL,  -- 'CRITICA', 'ALERTA', 'INFORMATIVA'
    STATUS_REGRA        VARCHAR2(20) DEFAULT 'PENDENTE',  -- 'HOMOLOGADA', 'PROVISORIA', 'PENDENTE'
    CONTEXTO            VARCHAR2(500),
    OBSERVACAO          VARCHAR2(4000),
    DT_CRIACAO          DATE DEFAULT SYSDATE NOT NULL,
    DT_ATUALIZACAO      DATE DEFAULT SYSDATE NOT NULL,
    USUARIO_ATUALIZACAO VARCHAR2(128) DEFAULT SYS_CONTEXT('USERENV','SESSION_USER')
);

COMMENT ON TABLE META_REGRA_NEGOCIO IS
'Catálogo de regras de negócio da camada semântica. Documenta regras, severidade, status de homologação e contexto de aplicação.';

COMMENT ON COLUMN META_REGRA_NEGOCIO.PROJETO IS 'Identificador do projeto (ex.: SEI, SIPAR) ou ''GLOBAL'' para regras compartilhadas.';
COMMENT ON COLUMN META_REGRA_NEGOCIO.ID_REGRA IS 'Identificador único da regra de negócio.';
COMMENT ON COLUMN META_REGRA_NEGOCIO.REGRA IS 'Descrição da regra de negócio em linguagem natural.';
COMMENT ON COLUMN META_REGRA_NEGOCIO.SEVERIDADE IS 'Severidade: CRITICA (obrigatória), ALERTA (recomendada), INFORMATIVA (orientação).';
COMMENT ON COLUMN META_REGRA_NEGOCIO.STATUS_REGRA IS 'Status de homologação: HOMOLOGADA (aprovada), PROVISORIA (em teste), PENDENTE (a validar).';
COMMENT ON COLUMN META_REGRA_NEGOCIO.CONTEXTO IS 'Contexto de aplicação da regra (tabela, view, domínio).';
COMMENT ON COLUMN META_REGRA_NEGOCIO.OBSERVACAO IS 'Observações técnicas sobre a regra.';
COMMENT ON COLUMN META_REGRA_NEGOCIO.DT_CRIACAO IS 'Data de criação do registro.';
COMMENT ON COLUMN META_REGRA_NEGOCIO.DT_ATUALIZACAO IS 'Data da última atualização do registro (mantida por trigger).';
COMMENT ON COLUMN META_REGRA_NEGOCIO.USUARIO_ATUALIZACAO IS 'Usuário Oracle que realizou a última atualização (mantido por trigger).';

-- -------------------------------------------------------------
-- META_VALOR_DOMINIO — valores válidos por coluna
-- -------------------------------------------------------------
CREATE TABLE META_VALOR_DOMINIO (
    ID_VALOR_DOMINIO    NUMBER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    PROJETO             VARCHAR2(50) DEFAULT 'GLOBAL' NOT NULL,
    NOME_OBJETO         VARCHAR2(128) NOT NULL,
    NOME_COLUNA         VARCHAR2(128) NOT NULL,
    VALOR               VARCHAR2(4000) NOT NULL,
    DESCRICAO           VARCHAR2(4000),
    IND_ATIVO           CHAR(1) DEFAULT 'S' NOT NULL,  -- 'S' / 'N'
    DT_CRIACAO          DATE DEFAULT SYSDATE NOT NULL,
    DT_ATUALIZACAO      DATE DEFAULT SYSDATE NOT NULL,
    USUARIO_ATUALIZACAO VARCHAR2(128) DEFAULT SYS_CONTEXT('USERENV','SESSION_USER')
);

COMMENT ON TABLE META_VALOR_DOMINIO IS
'Catálogo de valores válidos por coluna. Documenta domínios, descrições e status de ativação dos valores.';

COMMENT ON COLUMN META_VALOR_DOMINIO.PROJETO IS 'Identificador do projeto (ex.: SEI, SIPAR) ou ''GLOBAL'' para valores de domínio compartilhados.';
COMMENT ON COLUMN META_VALOR_DOMINIO.ID_VALOR_DOMINIO IS 'Identificador único do valor de domínio.';
COMMENT ON COLUMN META_VALOR_DOMINIO.NOME_OBJETO IS 'Nome do objeto (tabela/view) ao qual o valor pertence.';
COMMENT ON COLUMN META_VALOR_DOMINIO.NOME_COLUNA IS 'Nome da coluna ao qual o valor pertence.';
COMMENT ON COLUMN META_VALOR_DOMINIO.VALOR IS 'Valor válido da coluna.';
COMMENT ON COLUMN META_VALOR_DOMINIO.DESCRICAO IS 'Descrição do valor em linguagem de negócio.';
COMMENT ON COLUMN META_VALOR_DOMINIO.IND_ATIVO IS 'Indica se o valor está ativo: S para sim, N para não.';
COMMENT ON COLUMN META_VALOR_DOMINIO.DT_CRIACAO IS 'Data de criação do registro.';
COMMENT ON COLUMN META_VALOR_DOMINIO.DT_ATUALIZACAO IS 'Data da última atualização do registro (mantida por trigger).';
COMMENT ON COLUMN META_VALOR_DOMINIO.USUARIO_ATUALIZACAO IS 'Usuário Oracle que realizou a última atualização (mantido por trigger).';

-- -------------------------------------------------------------
-- META_ORIENTACAO_IA — roteiro da IA com seções e ordem
-- -------------------------------------------------------------
CREATE TABLE META_ORIENTACAO_IA (
    ID_ORIENTACAO       NUMBER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    PROJETO             VARCHAR2(50) DEFAULT 'GLOBAL' NOT NULL,
    SECAO               VARCHAR2(30) NOT NULL,  -- 'WORKFLOW', 'PRINCIPIO', 'VALIDACAO', 'DESVIO', 'RESPOSTA'
    ORDEM               NUMBER NOT NULL,
    TITULO              VARCHAR2(255) NOT NULL,
    CONTEUDO            CLOB NOT NULL,
    DT_CRIACAO          DATE DEFAULT SYSDATE NOT NULL,
    DT_ATUALIZACAO      DATE DEFAULT SYSDATE NOT NULL,
    USUARIO_ATUALIZACAO VARCHAR2(128) DEFAULT SYS_CONTEXT('USERENV','SESSION_USER'),
    CONSTRAINT UK_META_ORIENTACAO_IA UNIQUE (PROJETO, SECAO, ORDEM)
);

COMMENT ON TABLE META_ORIENTACAO_IA IS
'Roteiro de orientação para assistentes de IA. Documenta workflow, princípios, validação, desvios e formatos de resposta.';

COMMENT ON COLUMN META_ORIENTACAO_IA.PROJETO IS 'Identificador do projeto (ex.: SEI, SIPAR) ou ''GLOBAL'' para diretrizes universais de IA.';
COMMENT ON COLUMN META_ORIENTACAO_IA.ID_ORIENTACAO IS 'Identificador único da orientação.';
COMMENT ON COLUMN META_ORIENTACAO_IA.SECAO IS 'Seção: WORKFLOW, PRINCIPIO, VALIDACAO, DESVIO ou RESPOSTA.';
COMMENT ON COLUMN META_ORIENTACAO_IA.ORDEM IS 'Ordem de execução dentro da seção.';
COMMENT ON COLUMN META_ORIENTACAO_IA.TITULO IS 'Título da orientação.';
COMMENT ON COLUMN META_ORIENTACAO_IA.CONTEUDO IS 'Conteúdo da orientação em linguagem natural.';
COMMENT ON COLUMN META_ORIENTACAO_IA.DT_CRIACAO IS 'Data de criação do registro.';
COMMENT ON COLUMN META_ORIENTACAO_IA.DT_ATUALIZACAO IS 'Data da última atualização do registro (mantida por trigger).';
COMMENT ON COLUMN META_ORIENTACAO_IA.USUARIO_ATUALIZACAO IS 'Usuário Oracle que realizou a última atualização (mantido por trigger).';

-- =============================================================
-- TRIGGERS DE AUDITORIA — mantêm dt_atualizacao/usuario_atualizacao
-- =============================================================
CREATE OR REPLACE TRIGGER TRG_META_GLOSSARIO_UPD
BEFORE UPDATE ON META_GLOSSARIO
FOR EACH ROW
BEGIN
    :NEW.DT_ATUALIZACAO := SYSDATE;
    :NEW.USUARIO_ATUALIZACAO := SYS_CONTEXT('USERENV', 'SESSION_USER');
END;
/

CREATE OR REPLACE TRIGGER TRG_META_METRICA_UPD
BEFORE UPDATE ON META_METRICA
FOR EACH ROW
BEGIN
    :NEW.DT_ATUALIZACAO := SYSDATE;
    :NEW.USUARIO_ATUALIZACAO := SYS_CONTEXT('USERENV', 'SESSION_USER');
END;
/

CREATE OR REPLACE TRIGGER TRG_META_CONSULTA_NEGOCIO_UPD
BEFORE UPDATE ON META_CONSULTA_NEGOCIO
FOR EACH ROW
BEGIN
    :NEW.DT_ATUALIZACAO := SYSDATE;
    :NEW.USUARIO_ATUALIZACAO := SYS_CONTEXT('USERENV', 'SESSION_USER');
END;
/

CREATE OR REPLACE TRIGGER TRG_META_OBJETO_UPD
BEFORE UPDATE ON META_OBJETO
FOR EACH ROW
BEGIN
    :NEW.DT_ATUALIZACAO := SYSDATE;
    :NEW.USUARIO_ATUALIZACAO := SYS_CONTEXT('USERENV', 'SESSION_USER');
END;
/

CREATE OR REPLACE TRIGGER TRG_META_RELACIONAMENTO_UPD
BEFORE UPDATE ON META_RELACIONAMENTO
FOR EACH ROW
BEGIN
    :NEW.DT_ATUALIZACAO := SYSDATE;
    :NEW.USUARIO_ATUALIZACAO := SYS_CONTEXT('USERENV', 'SESSION_USER');
END;
/

CREATE OR REPLACE TRIGGER TRG_META_REGRA_NEGOCIO_UPD
BEFORE UPDATE ON META_REGRA_NEGOCIO
FOR EACH ROW
BEGIN
    :NEW.DT_ATUALIZACAO := SYSDATE;
    :NEW.USUARIO_ATUALIZACAO := SYS_CONTEXT('USERENV', 'SESSION_USER');
END;
/

CREATE OR REPLACE TRIGGER TRG_META_VALOR_DOMINIO_UPD
BEFORE UPDATE ON META_VALOR_DOMINIO
FOR EACH ROW
BEGIN
    :NEW.DT_ATUALIZACAO := SYSDATE;
    :NEW.USUARIO_ATUALIZACAO := SYS_CONTEXT('USERENV', 'SESSION_USER');
END;
/

CREATE OR REPLACE TRIGGER TRG_META_ORIENTACAO_IA_UPD
BEFORE UPDATE ON META_ORIENTACAO_IA
FOR EACH ROW
BEGIN
    :NEW.DT_ATUALIZACAO := SYSDATE;
    :NEW.USUARIO_ATUALIZACAO := SYS_CONTEXT('USERENV', 'SESSION_USER');
END;
/

COMMIT;
