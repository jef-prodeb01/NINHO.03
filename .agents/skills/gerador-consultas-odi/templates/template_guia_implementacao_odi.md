# TEMPLATES CANÔNICOS DE GUIAS DE IMPLEMENTAÇÃO NO ODI 12c (1 ARQUIVO POR TABELA)

> 🛑 **REGRA DE OURO:** NUNCA compile todas as tabelas de um projeto em um único arquivo gigante. Gere sempre **1 arquivo `.md` separado e ultra-detalhado para cada tabela Dimensão (`guia_estrategias_odi_dim_<entidade>.md`) e para cada tabela Fato (`guia_estrategias_odi_fato_<entidade>.md`)** dentro de `saida/planejador_dw/09_relatorio_estrategias/`.
> - **Para Dimensões (`DIM_*`):** Não descreva como criar o objeto em "Dimensões e Cubos" nem fixe prefixos específicos de outros projetos (como `S_BA_`). Vá direto para a montagem passo a passo do mapeamento `CARGA_DIM_<PROJETO>_<ENTIDADE>` no Canvas Lógico e Físico.
> - **Para Fatos (`FATO_*`):** Detalhe todas as etapas de Joins, Filtros, Funções Analíticas (`ROW_NUMBER()`), Lookups em escada diagonal com vigência SCD2 Point-in-Time e o tratamento coluna a coluna no componente `EXPRESSION`.

---

## 📄 MODELO A: GUIA POR TABELA DIMENSÃO (`guia_estrategias_odi_dim_<entidade>.md`)

```markdown
# GUIA DE IMPLEMENTAÇÃO NO ODI 12c: DIMENSÃO {NOME_DIMENSAO} (`CARGA_DIM_{PROJETO}_{ENTIDADE}`)

Este guia apresenta o roteiro passo a passo para a montagem visual no **Oracle Data Integrator (ODI 12c)** do mapeamento **`CARGA_DIM_{PROJETO}_{ENTIDADE}`**, responsável pela carga e versionamento histórico SCD Tipo 2 da tabela **`{SCHEMA_ALVO}.DIM_{PROJETO}_{ENTIDADE}`**.

---

## 1. A Consulta SQL Alvo (Lógica de Negócio da Dimensão)

```sql
SELECT DISTINCT
    STG.{COL_NK}                                                                 AS {ID_NK},
    UPPER(TRIM(NVL(STG.{COL_DESC}, 'NÃO INFORMADO')))                            AS {NM_DESC},
    'S'                                                                          AS SIN_ATIVO,
    TRUNC(SYSDATE)                                                               AS DTC_EFETIVACAO,
    CAST(NULL AS DATE)                                                           AS DTC_EXPIRACAO,
    STANDARD_HASH(UPPER(TRIM(NVL(STG.{COL_DESC}, 'NI'))), 'MD5')                 AS DES_ATUALIZAR
FROM {SCHEMA_ALVO}.{TABELA_STG_ORIGEM} STG
WHERE STG.{COL_NK} IS NOT NULL;
```

---

## 2. Diagrama de Blocos no Canvas do ODI 12c

```text
[{TABELA_STG_ORIGEM}]
          │
          ▼
    (FILTRO_VALIDOS) : {COL_NK} IS NOT NULL
          │
          ▼
   (DISTINCT_{ENTIDADE}) : Garante 1 linha única por Chave Natural
          │
          ▼
   (EXP_{ENTIDADE}) : Higienização, Decodificação CASE, SIN_ATIVO, DTC_EFETIVACAO e Hash MD5
          │
          ▼
[DIM_{PROJETO}_{ENTIDADE}] (Componente Alvo no Canvas)
```

---

## 3. PASSO A PASSO NO CANVAS LÓGICO DO ODI

### ETAPA 1: Origem e Filtro de Validação
1. **Arraste a tabela `{TABELA_STG_ORIGEM}`** para o Canvas Lógico.
2. **Arraste o componente `Filtro` (*Filter*)** e renomeie para **`FILTRO_VALIDOS`**.
   * Condição do Filtro: `{TABELA_STG_ORIGEM}.{COL_NK} IS NOT NULL`

### ETAPA 2: Deduplicação da Chave Natural (`DISTINCT` ou `AGGREGATE`)
1. **Arraste o componente `Distinto` (*Distinct*)** (ou `Agregação` se houver métricas de porte) e renomeie para **`DISTINCT_{ENTIDADE}`**.
2. Conecte a saída do `FILTRO_VALIDOS` nele, garantindo que saia exatamente **1 linha por `{COL_NK}`**.

### ETAPA 3: Transformação e Cálculo do Hash SCD2 no Componente `EXPRESSION`
1. **Arraste o componente `Expressão` (*Expression*)** e renomeie para **`EXP_{ENTIDADE}`**.
2. Configure cada coluna de saída conforme a tabela detalhada abaixo:

| Coluna Destino na `{NOME_DIMENSAO}` | Expressão de Mapeamento no `EXP_{ENTIDADE}` | Tipo no Destino | Regra de Negócio / Tratamento |
| :--- | :--- | :--- | :--- |
| **`{ID_NK}`** | `DISTINCT_{ENTIDADE}.{COL_NK}` | `NUMBER(10)` | Chave Natural da dimensão. |
| **`{NM_DESC}`** | `UPPER(TRIM(NVL(DISTINCT_{ENTIDADE}.{COL_DESC}, 'NÃO INFORMADO')))` | `VARCHAR2(...)` | Padronização em caixa alta e sem espaços. |
| **`SIN_ATIVO`** | `'S'` | `CHAR(1)` | Flag de versão ativa para o gatilho SCD2. |
| **`DTC_EFETIVACAO`** | `TRUNC(SYSDATE)` | `DATE` | Data de início de vigência do registro. |
| **`DES_ATUALIZAR`** | `STANDARD_HASH(..., 'MD5')` | `VARCHAR2(32)` | Hash MD5 determinístico das colunas monitoradas pelo SCD2. |

### ETAPA 4: Conexão no Componente Alvo `DIM_{PROJETO}_{ENTIDADE}`
1. **Arraste a dimensão alvo `DIM_{PROJETO}_{ENTIDADE}`** para o Canvas e conecte a saída do `EXP_{ENTIDADE}` nela.
2. **Na aba `Propriedades -> Histórico` do bloco alvo `DIM_{PROJETO}_{ENTIDADE}`**, confira os parâmetros do SCD Tipo 2:
   * **Horário de Efetivação Padrão de Registro Inicial:** `TO_DATE('01/01/1900', 'DD/MM/YYYY')`
   * **Horário de Efetivação Padrão de Registro Aberto:** `TRUNC(SYSDATE)`
   * **Tempo de Expiração Padrão de Registro Aberto:** `NULL`
   * **Tipo de Alteração Lenta:** `Tipo 2` | **Intervalo Tipo 2:** `1` | **Unidade:** `Segundos`

---

## 4. Configurações Físicas e Performance (Aba Físico)
1. **Unidade de Execução:** `{SCHEMA_ALVO}_LOGICO_UNIT` (100% interno no Oracle DW, sem LKM).
2. **Tabela de Manobra SCD2 (`ODI_DIM_*`):** O padrão de dimensão utiliza automaticamente `{SCHEMA_ALVO}.ODI_DIM_{PROJETO}_{ENTIDADE}` para deduplicar (`DEDUP_EXPR`), comparar com a versão atual (`LKP_CURR`) e dividir nos 3 fluxos (`TGT_INS`, `TGT_CLS`, `TGT_UPD`).

---

## 5. Checklist Rápido Pré-Execução
- [ ] A chave natural `{ID_NK}` está desduplicada antes de entrar no bloco da dimensão.
- [ ] A coluna `DES_ATUALIZAR` usa `STANDARD_HASH(..., 'MD5')` sobre todas as colunas de negócio versionadas.
- [ ] O registro default `-1` já foi inserido na tabela `DIM_{PROJETO}_{ENTIDADE}`.
```

---

## 📄 MODELO B: GUIA POR TABELA FATO (`guia_estrategias_odi_fato_<entidade>.md`)

```markdown
# GUIA DE IMPLEMENTAÇÃO NO ODI 12c: FATO {NOME_FATO} (`STG_*` E `CARGA_FATO_{PROJETO}_{ENTIDADE}`)

Este guia apresenta o roteiro passo a passo completo no **Oracle Data Integrator (ODI 12c)** para construir a tabela **`{SCHEMA_ALVO}.FATO_{PROJETO}_{ENTIDADE}`**, dividido nas duas etapas de Canvas:
- **PARTE A:** Preparação Visual da Staging da Fato (`{TABELA_STG_FATO}`) com Joins, Filtros, Agregações / `ROW_NUMBER()`.
- **PARTE B:** Mapeamento Final da Fato (`CARGA_FATO_{PROJETO}_{ENTIDADE}`) com **Escada Diagonal de Lookups SCD2 Point-in-Time** e tratamento completo no **`EXPRESSION` Final**.

---

## 1. A Consulta SQL Alvo (Lógica de Negócio Completa)

```sql
-- [SQL completo com CTEs de preparação + SELECT final com LEFT JOIN nas DIM_* e DIM_TEMPO]
```

---

## 2. Visão Geral das 3 Estratégias (Preparação da Staging)

| Estratégia | Nível de Acesso Necessário | Complexidade no ODI | Performance | Recomendação |
| :--- | :--- | :--- | :--- | :--- |
| **Estratégia 1: View no Banco** | Requer `CREATE VIEW` na Origem. | Mínima (1 para 1). | Altíssima. | Ideal quando se tem privilégios de DDL na origem. |
| **Estratégia 2: 100% Visual no ODI** | **Apenas leitura (`SELECT`).** Feito no Canvas do ODI. | Média / Alta (Uso de componentes). | Alta. | **Escolha padrão quando toda a regra deve ficar visível no Canvas do ODI.** |
| **Estratégia 3: ODI Procedure** | Apenas leitura. Código SQL direto. | Baixa no design, perde rastreabilidade. | Altíssima. | Alternativa de contingência. |

---

## 3. PARTE A — PASSO A PASSO NO CANVAS PARA A STAGING (`{TABELA_STG_FATO}`)

*(Diagrama de blocos ASCII + Etapas detalhadas de Filtro, Distinct, Join, Agregação / `EXP_ANALITICA` com `ROW_NUMBER()` + `FILTRO (RN = 1)` + Tabela completa de expressões da `STG_*` + Dica de Ouro do `Subquery / Inline View`)*.

---

## 4. PARTE B — PASSO A PASSO NO CANVAS PARA A FATO (`CARGA_FATO_{PROJETO}_{ENTIDADE}`)

### 4.1 Diagrama de Blocos no Canvas (Escada Diagonal de Lookups + Expression Final)

```text
                                                                                      [DIM_TEMPO]
                                                                                           │
                                                            [DIM_{PROJETO}_3]              ▼
                                                                   │                  (LOOKUP3) ──► [EXPRESSION] ──► [FATO_{PROJETO}_{ENTIDADE}]
                                    [DIM_{PROJETO}_2]              ▼                       ▲
                                           │                  (LOOKUP2) ───────────────────┘
            [DIM_{PROJETO}_1]              ▼                       ▲
                   │                  (LOOKUP1) ───────────────────┘
                   ▼                       ▲
[STG_FATO] ──► (LOOKUP) ───────────────────┘
```

### 4.2 Passo a Passo Detalhado dos `LOOKUP`s (Etapa por Etapa)
*(Para cada `LOOKUP`, detalhar a tabela de dimensão, a propriedade `Lookup com Nulo Retornado = True` e a `Condição de Pesquisa` exata com `TRUNC(STG.DT_REF) >= DIM.DTC_EFETIVACAO AND TRUNC(STG.DT_REF) <= NVL(DIM.DTC_EXPIRACAO, DATE '2999-12-31')`)*.

### 4.3 Filtragem e Mapeamento Detalhado no Componente `EXPRESSION` Final
*(Tabela completa linha a linha de todas as FKs com `NVL(DIM_*.DIMENSION_KEY, -1)`, chaves degeneradas e métricas com `NVL(..., 0)`)*.

---

## 5. Configurações Físicas e Otimizações no ODI (Aba Físico)
*(Execution Unit, LKM, IKM Oracle Insert com `TRUNCATE = True` e `INSERT HINT = /*+ APPEND PARALLEL(4) */`, Batch/Array Size = 50000)*.

---

## 6. Checklist Rápido Pré-Execução
```
