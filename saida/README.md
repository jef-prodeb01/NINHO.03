# Saída dos Módulos (Artefatos Gerados)

Este diretório centraliza **todas as saídas e scripts gerados** pelos módulos do framework. Cada módulo possui sua pasta dedicada para manter o isolamento dos artefatos.

---

## 📁 Estrutura de Saída por Módulo

- **[`planejador_dw/`](planejador_dw/)**: Scripts e estratégias gerados pelo Planejador de DW.
  - `01_controle_carga/`: DDLs de tabelas e triggers de controle de carga (`TB_CONTROLE_CARGA`).
  - `02_staging/`: DDLs de tabelas e views de Staging (`STG_`).
  - `03_dimensoes/`: DDLs de dimensões SCD Tipo 2 e comandos de carga/MERGE.
  - `04_fatos/`: DDLs de tabelas fato particionadas e scripts de inserção.
  - `05_relatorio_estrategias/`: Relatório executivo de arquitetura, volumetria e periodicidade.
- **[`camada_semantica/`](camada_semantica/)**: Scripts gerados pela Camada Semântica.
  - `vw_analiticas/`: Views SQL em 3 camadas (`VW_*_DIM_*_ATUAL`, `VW_*_EVENTO`, `VW_*_KPI_*`).
  - `meta_projeto/`: Scripts DDL e Inserts das 8 tabelas `META_*`.
- **[`governanca_dados/`](governanca_dados/)**: Artefatos e catálogos gerados.
  - `schemas_mongo/`: Esquemas de validação JSON Schema / BSON para coleções MongoDB.
  - `aws_datazone/`: Definições de Metadata Forms e publicação no Amazon DataZone.

