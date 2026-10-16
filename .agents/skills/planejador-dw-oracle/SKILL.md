---
name: planejador-dw-oracle
description: >-
  Conduz o planejamento de Data Warehouse no Oracle: modelagem Kimball Star Schema,
  SCD Tipo 2, criação de tabelas staging (STG_*), dimensões (DIM_*), fatos (FAT_*),
  constraints, sequences, tablespaces, validação do grão e melhorias rápidas não-destrutivas
  (Fast-Track: comentários, índices, linha -1 e constraints NOVALIDATE) em DWs já construídos.
---

# Skill: Planejador de Data Warehouse (Oracle)

Esta skill orienta a concepção, modelagem dimensional e geração de DDLs de alta performance para novos Data Warehouses no Oracle Database (versões 12c a 19c+), além do modo **Fast-Track** para melhorias cirúrgicas não-destrutivas em DWs já construídos.

## 1. Princípios de Modelagem Dimensional (Kimball)

1. **Star Schema Puro e Padrão Corporativo de Chaves (`DIMENSION_KEY` / `DIM_<PROJETO>_<...>`):**
   - Dimensões (`DIM_<PROJETO>_<ENTIDADE>`) desnormalizadas, sem joins em cascata (evite Snowflake a menos que estritamente justificável).
   - **`DIM_TEMPO` Sempre Obrigatória:** Todo schema de trabalho DEVE conter a dimensão conformada `<SCHEMA>.DIM_TEMPO` no padrão corporativo (24 colunas, de `DIMENSION_KEY` a `DTC_COMPLETA`), e toda Fato DEVE possuir FK `DIM_TEMPO` apontando para `DIM_TEMPO(DIMENSION_KEY)`, mesmo quando a base pareça estática ou anual.
   - **Surrogate Key na Dimensão:** Chama-se **SEMPRE `DIMENSION_KEY NUMBER(38,0) NOT NULL`** em todas as dimensões (proibido usar `<ENTIDADE>_KEY` ou `SK_<ENTIDADE>`).
   - **Foreign Key na Fato:** Nas tabelas Fato (`FATO_<PROJETO>_<PROCESSO>`), a coluna de FK que referencia a dimensão chama-se **SEMPRE `DIM_<PROJETO>_<ENTIDADE> NUMBER(38,0) NOT NULL`** (ex: `DIM_ELEICOES_PSD_BA_MUNICIPIO`) e `DIM_TEMPO NUMBER(38,0) NOT NULL`, apontando para `DIMENSION_KEY`.
   - **Sem `DTC_CARGA` / `DTC_CARGA_DW` na Fato:** **NUNCA** inclua colunas de timestamp de carga (`DTC_CARGA`, `DTC_CARGA_DW`) nas tabelas Fato, pois a auditoria de carga já é controlada por `TB_CONTROLE_CARGA` / `ETA_ETAPAS_CARGA` (evita redundância e melhora a compressão).
2. **Surrogate Keys e Sequences:**
   - Chave artificial `DIMENSION_KEY NUMBER(38,0)` gerada via Oracle Sequence (`SEQ_DIM_<PROJETO>_<ENTIDADE>`).
   - Nunca utilize a chave natural do sistema de origem como Primary Key no DW.
3. **Registro Padrão Inexistente / Não Informado (Linha `-1`):**
   - Toda dimensão (incluindo `DIM_TEMPO`) DEVE possuir um registro inicial com `DIMENSION_KEY = -1` (script `06_init_default_records.sql`).
   - Representa dados nulos, órfãos ou não informados, prevenindo que a Fato quebre por violação de integridade referencial (`ORA-02291`).
4. **Slowly Changing Dimensions (SCD Tipo 2):**
   - Atributos padrão de versionamento histórico em todas as dimensões:
     - `DTC_EFETIVACAO DATE NOT NULL` (Data de início de vigência)
     - `DTC_EXPIRACAO DATE NULL` (Data fim; `NULL` indica registro vigente)
     - `DES_ATUALIZAR CHAR(1 CHAR) DEFAULT 'S' NOT NULL` ('S' para atualizar, 'N' para inalterado)
     - `SIN_ATIVO CHAR(1 CHAR) DEFAULT 'S' NOT NULL` ('S' para ativo na origem, 'N' para inativo)
    - **Regra Corporativa Inegociável (`STG_* -> DIM_* / FATO_*` é UNICAMENTE no ODI 12c):**
      - A ingestão inicial até a camada `STG_*` é flexível conforme a fonte: pode ser via **Python** (APIs ou pré-processamento CSV), via **Apache Hop** (CSV/FTPS para `STG_*`), **carga direta do CSV bruto em tabela `STG_*` no banco**, ou via **ODI** (DBLink/JDBC).
      - Porém, **a partir da `STG_*`, a geração das Dimensões (`DIM_*`) e das Fatos (`FATO_*`) é feita UNICAMENTE no ODI 12c** (nunca via procedure PL/SQL monolítica).
      - Portanto, **SEMPRE** gere as tabelas auxiliares `ODI_DIM_<PROJETO>_<ENTIDADE>` (`03_create_odi_dim_tables.sql`), os SELECTs de mapeamento do ODI (`03_selects_odi_dimensoes.sql` e `04_select_odi_fato.sql`) e o Guia Completo de Construção de cada objeto no ODI (`09_relatorio_estrategias/GUIA_IMPLEMENTACAO_ODI_<PROJETO>.md`).
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
- **Rotinas de Manutenção Obrigatórias (`07_prc_pos_carga_fato.sql`):**
  1. `PRC_PRE_CARGA_FATO`: Chamada pela procedure `TRT_PRE_CARGA_FATOS` do ODI antes do mapping da Fato; coloca índices não únicos da fato como `UNUSABLE` antes da carga massiva (`INSERT /*+ APPEND PARALLEL(4) */`), preservando a PK.
  2. `PRC_POS_CARGA_FATO`: Chamada pela procedure `TRT_POS_CARGA_FATOS` do ODI após o mapping da Fato; reconstrói os índices com `ALTER INDEX ... REBUILD PARALLEL 4 NOLOGGING;`, redefine para `NOPARALLEL LOGGING` e dispara coleta de estatísticas `DBMS_STATS.GATHER_TABLE_STATS(cascade => TRUE, degree => 4)`.
  - 🛑 **Atenção:** `07_prc_pos_carga_fato.sql` serve exclusivamente para manutenção física de índices/estatísticas pré e pós-carga invocada pelo ODI. **NUNCA** coloque lógica de ETL (`STG -> DIM/FATO`) dentro de uma procedure PL/SQL, pois `STG -> DIM/FATO` pertence exclusivamente aos Mappings do ODI 12c!

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
2. `02_staging/02_create_stg_tables.sql` (incluindo tabela bruta 1:1 quando a fonte for CSV e tabelas pré-processadas se houver Python/Hop)
3. `03_dimensoes/03_create_odi_dim_tables.sql` (**OBRIGATÓRIO em novo DW** — tabelas auxiliares `ODI_DIM_<PROJETO>_<ENTIDADE>` para manobra SCD2 no ODI)
4. `03_dimensoes/03_selects_odi_dimensoes.sql` (**OBRIGATÓRIO em novo DW** — consultas SQL de transformação `STG_* -> ODI_DIM_* / DIM_*` para os Mappings do ODI)
5. `03_dimensoes/04_create_dim_tables.sql` (**OBRIGATÓRIO em novo DW** — `DIM_TEMPO` + dimensões do projeto com PK `DIMENSION_KEY`)
6. `03_dimensoes/06_init_default_records.sql` (**OBRIGATÓRIO** — registro `-1` em todas as dimensões + `DIM_TEMPO`)
7. `04_fatos/04_select_odi_fato.sql` (**OBRIGATÓRIO em novo DW** — consultas SQL de carga das Fatos no ODI a partir da `STG_*` com Lookups nas `DIM_*` vigentes e `DIM_TEMPO`)
8. `04_fatos/05_create_fato_tables.sql` (**OBRIGATÓRIO em novo DW** — Fatos com FKs `DIM_<PROJETO>_<...>` e `DIM_TEMPO`, sem `DTC_CARGA_DW`)
9. `05_procedimentos_manutencao/07_prc_pos_carga_fato.sql` (contendo `PRC_PRE_CARGA_FATO` e `PRC_POS_CARGA_FATO` chamadas pelo ODI SE Estratégia A)
10. `08_datasets_bi/GUIA_ANALISTA_BI_<PROJETO>.md`
11. `09_relatorio_estrategias/RELATORIO_ESTRATEGIAS.md` e `09_relatorio_estrategias/GUIA_IMPLEMENTACAO_ODI_<PROJETO>.md` (**OBRIGATÓRIO em novo DW** — passo a passo de construção de cada `TRT_*`, `ODI_DIM_*`, `MAP_DIM_*`, `MAP_FATO_*`, `PACK_*` e `SCEN_*` no ODI 12c)
12. `10_testes_integridade/13_testes_integridade.sql`
13. `11_dicionario_dados/dicionario_dados.html`

> 🛑 **REGRA CANÔNICA:** Nunca crie subpastas com o nome do projeto (ex: `saida/planejador_dw/<PROJETO>/`). Salve diretamente nas pastas numeradas.

---

## 5. ⚡ Micro-Processos Independentes & Modo Fast-Track (`melhorar_dw_existente.py`)

Quando o Engenheiro de Dados **já construiu o DW** (`DIM_*`, `FATO_*`, `STG_*`) ou deseja rodar **apenas um micro-processo isolado** sem disparar o processo completo:

1. **Smart Bypass do Gate 0:** Não exija o preenchimento do `INTAKE_DW.md`. Basta o DDL em `entrega/planejador_dw/ddl/` (ou passado via `--caminho`).
2. **Modos Granulares Disponíveis em [`core/scripts_comuns/melhorar_dw_existente.py`](../../../core/scripts_comuns/melhorar_dw_existente.py):**
   - `--modo comentarios` (`/gerar-comentarios`): Gera `90_patch_comentarios_dimensoes.sql`, `90_patch_comentarios_fatos.sql`, `90_patch_comentarios_staging.sql` e `11_dicionario_dados/dicionario_dados.html`.
   - `--modo dicionario` (`/gerar-dicionario`): Gera exclusivamente o Dicionário de Dados HTML interativo (`11_dicionario_dados/dicionario_dados.html`).
   - `--modo indices` (`/gerar-indices`): Gera `91_patch_indices_dimensoes.sql` (B-Tree SCD2), `91_patch_indices_fatos.sql` (`BITMAP` se `--estrategia A` ou `B-TREE COMPRESS 1` se `--estrategia B`, mais `DBMS_STATS`) e `05_procedimentos_manutencao/07_prc_pos_carga_fato.sql`.
   - `--modo linha-default` (`/gerar-linha-default`): Gera apenas `03_dimensoes/06_init_default_records.sql` (`MERGE INTO` idempotente do registro `-1`).
   - `--modo constraints` (`/gerar-constraints`): Gera apenas `92_patch_ajustes_dimensoes.sql` e `92_patch_ajustes_fatos.sql` (`ALTER TABLE ... ADD CONSTRAINT ... ENABLE NOVALIDATE` / `RELY DISABLE NOVALIDATE` e `CREATE SEQUENCE`).
   - `--modo testes` (`/gerar-testes-dw`): Gera apenas `10_testes_integridade/13_testes_integridade.sql`.
   - `--modo guia-bi` (`/gerar-guia-bi`): Gera apenas `08_datasets_bi/GUIA_ANALISTA_BI_<PROJETO>.md`.
   - `--modo selects-odi` (`/gerar-selects-odi`): Gera apenas `03_create_odi_dim_tables.sql`, `03_selects_odi_dimensoes.sql` e `04_select_odi_fato.sql`.
   - `--modo guia-odi` (`/gerar-guia-odi`): Gera apenas os guias individuais de construção no Canvas do ODI 12c em `09_relatorio_estrategias/guia_estrategias_odi_*.md`.
   - `--modo odi`: Gera o conjunto ODI (`selects-odi` + `guia-odi` + `06_init_default_records.sql`).
   - `--modo tudo` (`/melhorar-dw-existente`): Executa todos os micro-processos não-destrutivos + `09_relatorio_estrategias/DIAGNOSTICO_MELHORIAS_DW_EXISTENTE.md`.
3. **Validação Automática (`validar_entrega.py`):**
   Execute `python core/scripts_comuns/validar_entrega.py saida` (ou `fast-track`) para validar 100% de conformidade dos artefatos gerados.

---

## 6. 🧪 Gerador de Simulações & Blueprint 100% Editável (`simular_projeto.py`)

Quando o Engenheiro de Dados quiser visualizar **de ponta a ponta** como o projeto de DW vai começar, transformar e terminar **antes** de fechar o cenário e entrar na esteira de execução real:

1. **Fase 1 — Gerar a Simulação Editável (`/simular-dw` ou `/simular-projeto`):**
   ```bash
   python core/scripts_comuns/simular_projeto.py --modulo dw --acao simular
   ```
   Gera [`entrega/planejador_dw/SIMULACAO_BLUEPRINT_DW.md`](../../../entrega/planejador_dw/SIMULACAO_BLUEPRINT_DW.md) contendo:
   - **Seção 1:** Gate de Aprovação (`- [ ] SIMULAÇÃO 100% FECHADA E APROVADA PARA EXECUÇÃO REAL`);
   - **Seção 2:** Parâmetros Globais editáveis (`PROJETO_SIGLA`, `SCHEMA_DW_ALVO`, `SCHEMA_STG_ALVO`, `ESTRATEGIA_CARGA_FATO`, `TABLESPACE_DADOS`, `TABLESPACE_INDICES`);
   - **Seção 3:** Arquitetura Visual da Esteira Completa (Mermaid);
   - **Seção 4:** Matriz Editável de Tabelas e Colunas (`[x]`/`[ ]` para incluir/excluir colunas, renomear colunas destino, trocar tipos Oracle, alterar `SCD1`/`SCD2` e editar descrições `COMMENT ON`);
   - **Seção 5:** **Simulação Dry-Run de Dados (Amostra Visual de 3 Linhas)** mostrando exatamente como cada tabela ficará populada (incluindo o registro sentinela `-1`);
   - **Seção 6:** Radar Consultivo da IA (`[x]`/`[ ]`);
   - **Seção 7:** Escopo de Entregáveis Físicos (`01_tablespaces` a `11_dicionario_html`) com checkboxes individuais.
2. **Fase 2 — Executar na Esteira Real após Aprovação (`/executar-simulacao`):**
   ```bash
   python core/scripts_comuns/simular_projeto.py --modulo dw --acao executar
   ```
   Lê todas as edições feitas pelo engenheiro na `SIMULACAO_BLUEPRINT_DW.md` e gera os artefatos reais em `saida/planejador_dw/`.
