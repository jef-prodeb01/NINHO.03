# Módulos de Execução

Este diretório reúne os módulos especializados do framework. Cada módulo possui sua própria inteligência (instruções em `AGENTS.md`), ficha de intake (`INTAKE_*.md`) e templates específicos.

---

## 🚀 Módulos Disponíveis

### 1. [`planejador_dw/`](planejador_dw/)
> **Planejamento & Modelagem Dimensional (Oracle DW)**
- Conduz o processo de engenharia de dados do zero ao DW relacional.
- Gera estratégias de extração (ODI, Hop, Python), staging (`STG_`), dimensões SCD Tipo 2 (`DIM_`), tabelas fato (`FATO_`), controle de carga (`TB_CONTROLE_CARGA`) e scripts de inicialização de registros padrão (`-1`).

### 2. [`camada_semantica/`](camada_semantica/)
> **Camada Semântica & Metadados Ativos (Oracle DW)**
- Constrói a camada analítica sobre um DW existente.
- Gera as views em 3 camadas (`VW_*_DIM_*_ATUAL`, `VW_*_EVENTO`, `VW_*_KPI_*`) e popula o catálogo de 8 tabelas `META_*` (Glossário, Métrica, Objeto, Relacionamento, Regra de Negócio, Consultas, Orientações de IA e Domínios).

### 3. [`governanca_dados/`](governanca_dados/)
> **Data Lakehouse Governamental (MongoDB + AWS Glue & DataZone)**
- Arquitetura de governança moderna sem Amazon S3 para setor público.
- Estratégia de multi-órgãos em MongoDB (`gov_*`), envelope canônico com blocos `_org` e `_governance` (LAI/LGPD), e integração com AWS Glue Data Catalog e Amazon DataZone.

