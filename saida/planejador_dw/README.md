# Saídas do Planejador de DW

Esta pasta armazena os scripts SQL e relatórios gerados pela IA durante o processo de planejamento e modelagem dimensional do DW.

---

## 📂 Subpastas

- `01_controle_carga/`: Script DDL de criação da tabela de controle e auditoria (`TB_CONTROLE_CARGA`).
- `02_staging/`: DDLs de tabelas e views de staging (`STG_<FONTE>_<ENTIDADE>`).
- `03_dimensoes/`: DDLs de criação de dimensões (`DIM_<ENTIDADE>`), índices e scripts de carga SCD Tipo 2.
- `04_fatos/`: DDLs de criação de fatos (`FATO_<PROCESSO>`), particionamento e scripts de inserção.
- `05_relatorio_estrategias/`: Relatório executivo consolidando o grão, chaves, regras de carga e matriz barramento de fatos e dimensões.
