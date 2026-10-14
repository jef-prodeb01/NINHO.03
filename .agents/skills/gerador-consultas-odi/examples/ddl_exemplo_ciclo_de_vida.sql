-- Exemplo de DDL Transacional de Workflow com Ciclo de Vida (Abertura e Conclusão)
-- Utilizado como caso de teste da Heurística P1.B da skill gerador-consultas-odi

CREATE TABLE BD_SAEB_SEIBAHIA.dbo.atividade (
	id_atividade int NOT NULL,
	id_protocolo bigint NOT NULL,
	id_unidade int NOT NULL,
	dth_abertura datetime NOT NULL,
	dth_conclusao datetime NULL,
	id_tarefa int NULL,
	id_unidade_origem int NOT NULL,
	id_usuario_conclusao int NULL,
	sin_inicial char(1) COLLATE Latin1_General_CI_AS NOT NULL,
	id_usuario_visualizacao int NULL,
	id_usuario_atribuicao int NULL,
	dta_prazo datetime NULL,
	tipo_visualizacao int NOT NULL,
	id_usuario int NULL,
	id_usuario_origem int NOT NULL,
	CONSTRAINT pk_atividade PRIMARY KEY (id_atividade)
);

CREATE NONCLUSTERED INDEX fk_atividade_protocolo ON BD_SAEB_SEIBAHIA.dbo.atividade ( id_protocolo ASC );
CREATE NONCLUSTERED INDEX fk_atividade_tarefa ON BD_SAEB_SEIBAHIA.dbo.atividade ( id_tarefa ASC );
CREATE NONCLUSTERED INDEX fk_atividade_unidade ON BD_SAEB_SEIBAHIA.dbo.atividade ( id_unidade ASC );
CREATE NONCLUSTERED INDEX i03_atividade ON BD_SAEB_SEIBAHIA.dbo.atividade ( id_unidade ASC , dth_conclusao ASC , sin_inicial ASC );
CREATE NONCLUSTERED INDEX i04_atividade ON BD_SAEB_SEIBAHIA.dbo.atividade ( id_unidade ASC , dth_abertura ASC , id_tarefa ASC ) INCLUDE ( dth_conclusao , id_atividade , id_protocolo );
CREATE NONCLUSTERED INDEX i10_atividade ON BD_SAEB_SEIBAHIA.dbo.atividade ( dth_abertura ASC , id_tarefa ASC );

