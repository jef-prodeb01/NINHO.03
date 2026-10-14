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
5. **Arquitetura Multi-Tenant e Prevenção de ORA-00001:**
   - Se o DW compartilhar schemas entre múltiplos órgãos/municípios, nunca crie constraint `UNIQUE` unicolunar na chave natural. Utilize chave composta `(ID_NATURAL, COD_TENANT)`. No ETL/ELT, componha `to_number(to_char(V_TENANT) || '000' || to_char(ORIGEM.ID_NATURAL))` para evitar colisões.
6. **Arquitetura de Fatos Híbridas (Para Fontes com Dezenas de Milhões ou Bilhões de Linhas):**
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
- **Rotinas de Manutenção Obrigatórias:**
  1. `PRC_PRE_CARGA_FATOS`: Coloca índices não únicos da fato como `UNUSABLE` antes da carga massiva (`INSERT /*+ APPEND PARALLEL(4) */`), preservando a PK.
  2. `PRC_POS_CARGA_FATOS`: Reconstrói os índices com `ALTER INDEX ... REBUILD PARALLEL 4 NOLOGGING;`, redefine para `NOPARALLEL LOGGING` e dispara coleta de estatísticas `DBMS_STATS.GATHER_TABLE_STATS(cascade => TRUE)`.

### Estratégia B: Incremental Idempotente via MERGE (Micro-lotes / Near Real-Time)
- **Quando usar:** Cargas intra-dia, frequentes ou quando não é permitido truncar o histórico.
- **Indexação:** **B-TREE INDEX EXCLUSIVO** nas FKs.
- 🛑 **PROIBIÇÃO ABSOLUTA:** NUNCA crie Bitmap Index em tabelas carregadas via `MERGE` ou com concorrência DML — causa deadlocks `ORA-00060`.

---

## 3. Gestão de Tablespaces, Storage e Tuning no Oracle

Consulte os guias detalhados em:
- [tablespaces_oracle.md](./references/tablespaces_oracle.md) (Organização de Tablespaces e Storage)
- [tuning_indices_performance.md](./references/tuning_indices_performance.md) (Estratégias de Índices Bitmap vs B-Tree, Paralelismo, Ciclo Pré/Pós-Carga e Compressão)
- [arquitetura_fatos_hibridas.md](./references/arquitetura_fatos_hibridas.md) (Arquitetura de Fatos Híbridas para Alta Volumetria)
- [convencoes_dw.md](./references/convencoes_dw.md) (Nomenclaturas, Tipos Oracle e Diretrizes Multi-Tenant)
- **Separação Física:** Se informado no Intake, aponte tabelas para `TABLESPACE <TS_DATA>` e índices para `TABLESPACE <TS_INDEX>`.
- **Dimensões:** Aceitam **apenas índices B-Tree**. NUNCA use Bitmaps em dimensões.
- **Compressão:** Em fatos históricas de alta volumetria, recomende `COMPRESS FOR OLTP` ou `COMPRESS FOR QUERY HIGH`. Em índices compostos, utilize `COMPRESS 1`.

---

## 🤝 Quality Gate 1: Blueprint, Radar Consultivo da IA & Alinhamento com o Engenheiro (Anti-Caixa-Preta)

Nenhum DDL físico deve ser gerado no escuro. Diante de tabelas volumosas, regras não documentadas ou fontes heterogêneas:
0. **Inspeção Determinística da Origem & Radar de KPIs (`/inspecionar-fontes`):** Sempre que houver scripts `.sql` em `entrega/planejador_dw/ddl/` (ou `schemas_origem/`), execute `python core/scripts_comuns/inspecionar_ddl_origem.py` para extrair 100% das colunas, PKs, FKs, índices, o diagnóstico automático de CDC e o **Radar Consultivo de Oportunidades Analíticas**.
1. **Compilação do Blueprint com Expansão Analítica (`/gerar-blueprint`):** O agente estrutura a proposta de Star Schema, o grão da Fato, a Matriz De/Para de Colunas 100% fiel à origem, as dimensões conformadas e divide os indicadores/regras em dois blocos claros:
   - **🎯 Escopo Solicitado pelo Cliente (Mandatório):** Todas as regras de negócio, métricas e perguntas pedidas originalmente pelo cliente no `INTAKE_DW.md` ou nos documentos da pasta `entrega/planejador_dw/`.
   - **💡 Radar Consultivo da IA (Sugestões Proativas para Aprovação):** Novos KPIs de alto valor (ex: *Lead Time/Tempo de Ciclo*, *Backlog Ativo*, *Faixas de Envelhecimento/Aging*, *Cumprimento de SLA*, *Taxa de Auto-Tramitação/Retrabalho*, *Variação Mensal MoM*), Regras de Sanitização/Qualidade (ex: *tratamento de datas invertidas `CONCLUSAO < ABERTURA`*, *fila órfã sem responsável mapeada para `-1`*) e Novas Perguntas Executivas/Táticas/Auditoria que o cliente não percebeu na hora.
2. **Pausa para Discussão Técnica e Seleção:** O agente expõe os trade-offs arquiteturais e pergunta ao Engenheiro de Dados quais sugestões do **Radar Consultivo da IA** devem ser incorporadas fisicamente na Fato, nas Views e no Guia de BI.
3. **Aprovação Explícita (`/aprovar-blueprint`):** A geração física nas 11 pastas canônicas só é liberada após o aval conjunto com o Engenheiro.
4. **Auditoria Pós-Geração (`/validar-entrega`):** Após gerar os artefatos, execute `python core/scripts_comuns/validar_entrega.py saida` para certificar que nenhuma Regra de Ouro foi violada.

---

## 4. Estrutura Canônica de Saída (11 Pastas)

Gere os arquivos nas subpastas apropriadas de `saida/planejador_dw/`:
1. `01_controle_carga/01_tb_controle_carga.sql` (se não existir no schema)
2. `02_staging/02_create_stg_tables.sql`
3. `03_dimensoes/03_create_odi_dim_tables.sql` (SE ODI habilitado)
4. `03_dimensoes/04_create_dim_tables.sql`
5. `03_dimensoes/06_init_default_records.sql`
6. `04_fatos/05_create_fato_tables.sql`
7. `05_procedimentos_manutencao/07_prc_pre_carga_fato.sql` e `08_prc_pos_carga_fato.sql` (SE Estratégia A)
8. `08_datasets_bi/superset_dataset_<fato>.yaml` e `GUIA_ANALISTA_BI_<PROJETO>.md`
9. `09_relatorio_estrategias/RELATORIO_ESTRATEGIAS.md`
10. `10_testes_integridade/13_testes_integridade.sql`
11. `11_dicionario_dados/dicionario_dados.html`

> 🛑 **REGRA CANÔNICA:** Nunca crie subpastas com o nome do projeto (ex: `saida/planejador_dw/<PROJETO>/`). Salve diretamente nas pastas numeradas.

