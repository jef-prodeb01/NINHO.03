---
name: planejador-dw-oracle
description: >-
  Conduz o planejamento de Data Warehouse no Oracle: modelagem Kimball Star Schema,
  SCD Tipo 2, criação de tabelas staging (STG_*), dimensões (DIM_*), fatos (FAT_*),
  constraints, sequences, tablespaces e validação do grão.
---

# Skill: Planejador de Data Warehouse (Oracle)

Esta skill orienta a concepção, modelagem dimensional e geração de DDLs de alta performance para novos Data Warehouses no Oracle Database (versões 12c a 19c+).

## 1. Princípios de Modelagem Dimensional (Kimball)

1. **Star Schema Puro:**
   - Dimensões (`DIM_*`) desnormalizadas, sem joins em cascata (evite Snowflake a menos que estritamente justificável).
   - Fatos (`FATO_*` ou `FAT_*`) conectadas às dimensões através de Surrogate Keys (`<NOME_DIM>_KEY`).
2. **Surrogate Keys e Sequences:**
   - Chave artificial `NUMBER(38,0)` gerada via Oracle Sequence (`SEQ_DIM_<NOME>`).
   - Nunca utilize a chave natural do sistema de origem como Primary Key no DW.
3. **Registro Padrão Inexistente / Não Informado (Linha `-1`):**
   - Toda dimensão DEVE possuir um registro inicial com `DIMENSION_KEY = -1` (script `06_init_default_records.sql`).
   - Representa dados nulos, órfãos ou não informados, prevenindo que a Fato quebre por violação de integridade referencial (`ORA-02291`).
4. **Slowly Changing Dimensions (SCD Tipo 2):**
   - Atributos padrão de versionamento histórico em todas as dimensões:
     - `DTC_EFETIVACAO DATE NOT NULL` (Data de início de vigência)
     - `DTC_EXPIRACAO DATE NULL` (Data fim; `NULL` indica registro vigente)
     - `DES_ATUALIZAR VARCHAR2(1) DEFAULT 'N' NOT NULL` ('S' para atualizar, 'N' para inalterado)
    - Se o ETL utilizar **Oracle Data Integrator (ODI)**, gere também a tabela auxiliar `ODI_DIM_<NOME>` com a coluna de controle `DES_STATUS_REGISTRO VARCHAR2(1)`.
5. **Arquitetura de Fatos Híbridas (Para Fontes com Dezenas de Milhões ou Bilhões de Linhas):**
   - Quando a tabela transacional da fonte tiver altíssima volumetria (ex: > 50M de linhas) e longo histórico (5 a 10 anos), **NÃO crie uma única fato "tudo-em-um"**.
   - Divida o domínio em **3 Fatos Especializadas**:
     1. `FATO_*_AGR_MENSAL` (Fato Histórica Agregada por Mês para tendências e painéis executivos);
     2. `FATO_*_SITUACAO_ATUAL` (Fato Snapshot de Estado Atual / SLA dos últimos N meses com `ROW_NUMBER()`);
     3. `FATO_*_ANDAMENTO` (Fato Linha do Tempo / Eventos Críticos com filtro de relevância funcional).
   - Consulte os detalhes completos em [arquitetura_fatos_hibridas.md](./references/arquitetura_fatos_hibridas.md).

---

## 2. Estratégias de Carga da Fato (Dual Strategy)

Ao projetar a Fato, selecione a estratégia conforme o preenchimento do `INTAKE_DW.md`:

### Estratégia A: Truncate & Load Massivo (Carga Noturna / Batch)
- **Quando usar:** Volumetria moderada a grande, carga diária noturna em lote fechado.
- **Indexação:** **BITMAP INDEX** nas Foreign Keys das Dimensões para habilitar **Star Transformation** no otimizador Oracle.
- **Rotina de Manutenção Obrigatória:** Procedure `PRC_POS_CARGA_FATO` (`07_prc_pos_carga_fato.sql`):
  1. Marca índices da fato como `UNUSABLE` antes da carga.
  2. Executa a carga massiva (`INSERT /*+ APPEND */`).
  3. Reconstrói os índices com `ALTER INDEX ... REBUILD NOLOGGING;`.
  4. Coleta estatísticas com `DBMS_STATS.GATHER_TABLE_STATS`.

### Estratégia B: Incremental Idempotente via MERGE (Micro-lotes / Near Real-Time)
- **Quando usar:** Cargas intra-dia, frequentes ou quando não é permitido truncar o histórico.
- **Indexação:** **B-TREE INDEX EXCLUSIVO** nas FKs.
- 🛑 **PROIBIÇÃO ABSOLUTA:** NUNCA crie Bitmap Index em tabelas carregadas via `MERGE` ou com concorrência DML — causa deadlocks `ORA-00060`.

---

## 3. Gestão de Tablespaces, Storage e Tuning no Oracle

Consulte os guias detalhados em:
- [tablespaces_oracle.md](./references/tablespaces_oracle.md) (Organização de Tablespaces e Storage)
- [tuning_indices_performance.md](./references/tuning_indices_performance.md) (Estratégias de Índices Bitmap vs B-Tree, Paralelismo e Compressão)
- [arquitetura_fatos_hibridas.md](./references/arquitetura_fatos_hibridas.md) (Arquitetura de Fatos Híbridas para Alta Volumetria)
- **Separação Física:** Se informado no Intake, aponte tabelas para `TABLESPACE <TS_DATA>` e índices para `TABLESPACE <TS_INDEX>`.
- **Dimensões:** Aceitam **apenas índices B-Tree**. NUNCA use Bitmaps em dimensões.
- **Compressão:** Em fatos históricas de alta volumetria, recomende `COMPRESS FOR OLTP` ou `COMPRESS FOR QUERY HIGH`. Em índices compostos, utilize `COMPRESS 1`.

---

## 4. Estrutura Canônica de Saída (11 Pastas)

Gere os arquivos nas subpastas apropriadas de `saida/planejador_dw/`:
1. `01_controle_carga/01_tb_controle_carga.sql` (se não existir no schema)
2. `02_staging/02_create_stg_tables.sql`
3. `03_dimensoes/03_create_odi_dim_tables.sql` (SE ODI habilitado)
4. `03_dimensoes/04_create_dim_tables.sql`
5. `03_dimensoes/06_init_default_records.sql`
6. `04_fatos/05_create_fato_tables.sql`
7. `05_procedimentos_manutencao/07_prc_pos_carga_fato.sql` (SE Estratégia A)
8. `08_datasets_bi/superset_dataset_<fato>.yaml` e `GUIA_ANALISTA_BI_<PROJETO>.md`
9. `09_relatorio_estrategias/RELATORIO_ESTRATEGIAS.md`
10. `10_testes_integridade/13_testes_integridade.sql`
11. `11_dicionario_dados/dicionario_dados.html`

> 🛑 **REGRA CANÔNICA:** Nunca crie subpastas com o nome do projeto (ex: `saida/planejador_dw/<PROJETO>/`). Salve diretamente nas pastas numeradas.

