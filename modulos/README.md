# Módulos de Execução

Este diretório reúne os módulos especializados do framework. Cada módulo possui sua própria inteligência (instruções em `AGENTS.md`), ficha de intake (`INTAKE_*.md`) e templates específicos.

---

## 🚀 Módulos Disponíveis

### 1. [`planejador_dw/`](planejador_dw/)
> **Planejamento, Modelagem Dimensional & Fast-Track para DWs Existentes (Oracle DW)**
- Conduz o processo de engenharia de dados do zero ao DW relacional (**Greenfield**) ou aplica melhorias cirúrgicas não-destrutivas em DWs já construídos sem alterar a carga (**Fast-Track**: `/gerar-comentarios`, `/gerar-indices`, `/melhorar-dw-existente`).
- Gera estratégias de extração (ODI, Hop, Python), staging (`STG_*`), dimensões SCD Tipo 2 (`DIM_*`), tabelas auxiliares (`ODI_DIM_*`), tabelas fato (`FATO_*`), controle de carga (`TB_CONTROLE_CARGA`), scripts de inicialização de registros padrão (`-1`), patches de comentários/índices e Dicionário de Dados HTML.

### 2. [`camada_semantica/`](camada_semantica/)
> **Camada Semântica & Metadados Ativos (Oracle DW)**
- Constrói a camada analítica sobre um DW existente.
- Gera as views em 3 camadas (`VW_*_DIM_*_ATUAL`, `VW_*_EVENTO`, `VW_*_KPI_*`) e popula o catálogo de 8 tabelas `META_*` (Glossário, Métrica, Objeto, Relacionamento, Regra de Negócio, Consultas, Orientações de IA e Domínios).

### 3. [`governanca_dados/`](governanca_dados/)
> **Governança Corporativa PRODEB (MongoDB Enterprise + AWS Glue & SageMaker Catalog)**
- Audita a qualidade dos insumos na origem (**Gate 0.5** com emissão de Relatório de Devolução ao Cliente em caso de dados/metadados vazios).
- Modela as 5 coleções corporativas no MongoDB (`tb_dataset`, `tb_sem_dominios`, `tb_sem_conceitos`, `tb_auditoria_eventos`, `tb_quarentena`), aplica enquadramento LGPD/LAI e publica metadados no AWS Glue Data Catalog e Amazon SageMaker Catalog (ex-DataZone).


