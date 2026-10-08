# Saídas do Planejador de DW

Esta pasta armazena os scripts SQL, procedimentos, pipelines, extratores e relatórios gerados pela IA durante o processo de planejamento e modelagem dimensional do DW.

---

## 📂 Estrutura de Pastas por Projeto

Cada projeto planejado terá sua própria pasta (`saida/planejador_dw/<NOME_PROJETO>/`), contendo:

- `01_controle_carga/`: Script DDL de criação da tabela de auditoria (`01_tb_controle_carga.sql`).
- `02_staging/`: DDLs de tabelas e views de staging (`02_create_stg_tables.sql`) com rastreabilidade por lote e data de extração.
- `03_dimensoes/`: DDLs de criação de dimensões (`04_create_dim_tables.sql`), tabelas auxiliares do ODI (`03_create_odi_dim_tables.sql`), Sequences e carga inicial da linha `-1` (`06_init_default_records.sql`).
- `04_fatos/`: DDLs de criação de fatos (`05_create_fato_tables.sql`), particionamento, chaves compostas e índices (Bitmap para Estratégia A ou B-Tree para Estratégia B).
- `05_procedimentos_manutencao/`: Procedure PL/SQL pós-carga (`07_prc_pos_carga_fato.sql`) para rebuild `NOLOGGING` de índices e atualização do `DBMS_STATS(CASCADE => TRUE)`.
- `06_pipelines_hop/`: Pipelines (`.hpl`) e workflows (`.hwf`) do Apache Hop para ingestão de arquivos CSV/Excel/SFTP.
- `07_extratores_python/`: Extratores Python modulares com autenticação OAuth2, paginação, flattening de JSON aninhado e carga em lote via `oracledb`.
- `08_datasets_bi/`: Especificações de consumo analítico, incluindo datasets declarativos em YAML para o Apache Superset (`superset_dataset_<fato>.yaml`) e guia de implementação no Power BI (`GUIA_ANALISTA_BI_<PROJETO>.md`).
- `09_relatorio_estrategias/`: Relatório executivo consolidando a topologia da esteira, matriz de linhagem De/Para, comandos SSH para o `OdiOSCommand` e estimativa de sizing para a equipe de DBA (`RELATORIO_ESTRATEGIAS.md`).
- `10_testes_integridade/`: Suíte de testes SQL de sanidade analítica pós-carga (`13_testes_integridade.sql`) para validar FKs, ausência de órfãos e status de índices.
- `11_dicionario_dados/`: Dicionário de dados interativo em HTML (`dicionario_dados.html`) para consulta rápida de tabelas, colunas e fórmulas pelo negócio.
