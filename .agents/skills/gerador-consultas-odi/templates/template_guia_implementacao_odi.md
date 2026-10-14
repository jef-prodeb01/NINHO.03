# GUIA DE IMPLEMENTAÇÃO NO ODI 12c: FATO {NOME_FATO}
## `{TABELA_FATO_FINAL}` (Mapeamento Dimensional / Canvas do ODI)

Este guia apresenta o roteiro visual completo no **Oracle Data Integrator (ODI 12c em Português)** para a carga da fato **`{TABELA_FATO_FINAL}`**.

A esteira de carga é dividida em duas fases canônicas:
1. **FASE 1 (Extração de Origem para Staging):** Carga do banco transacional (SQL Server, PostgreSQL, MySQL ou Oracle OLTP) para a Staging Oracle (`STG_{NOME_PROJETO}_{NOME_FATO}`).
2. **FASE 2 (Staging para Fato Star Schema no DW):** Carga 100% interna no Oracle da Staging para a Fato final (`{TABELA_FATO_FINAL}`), com resolução de Surrogate Keys (`DIMENSION_KEY`), tratamento de dimensões SCD Tipo 2 e proteção da linha `-1` (*Não Informado*).

---

## 🧭 Visão Geral das 3 Estratégias do ODI 12c

| Estratégia | Nível de Acesso Necessário | Complexidade no ODI | Performance | Recomendação |
| :--- | :--- | :--- | :--- | :--- |
| **Estratégia 1: View no Banco de Origem** | Requer permissão de `CREATE VIEW` na fonte. | Mínima (1 para 1 no mapping). | Altíssima. | Ideal quando a equipe de BI tem acesso DDL à origem. |
| **Estratégia 2: 100% Visual no Canvas Lógico** | **Apenas permissão de LEITURA (`SELECT`).** | Média/Alta (componentes de canvas). | Alta. | **A escolha obrigatória corporativa quando não se pode criar objetos na fonte.** |
| **Estratégia 3: ODI Procedure Direta** | Apenas permissão de leitura. Código SQL direto. | Baixa no design visual, mas perde rastreabilidade. | Altíssima. | Alternativa de contingência para colar código manual. |

---

# PARTE 1: CARGA DA STAGING (`STG_{NOME_PROJETO}_{NOME_FATO}`)

### 1.1 Lógica SQL de Origem (Exemplo com Janela Temporal e Filtros)
```sql
WITH JanelaAtiva AS (
    SELECT DISTINCT a.{ID_ENTIDADE_CHAVE}
    FROM {BANCO_ORIGEM}.{SCHEMA}.{TABELA_ORIGEM} a WITH (NOLOCK)
    WHERE a.{COLUNA_DATA} >= DATEADD(MONTH, -3, GETDATE())
)
SELECT 
    a.{ID_EVENTO},
    a.{ID_ENTIDADE_CHAVE},
    a.{ID_UNIDADE},
    a.{ID_USUARIO},
    a.{ID_USUARIO_ATRIBUICAO},
    a.{ID_TIPO_EVENTO},
    a.{DTH_INICIO},
    a.{DTH_FIM},
    DATEDIFF(DAY, a.{DTH_INICIO}, ISNULL(a.{DTH_FIM}, GETDATE())) AS {COLUNA_DURACAO_DIAS}
FROM {BANCO_ORIGEM}.{SCHEMA}.{TABELA_ORIGEM} a WITH (NOLOCK)
INNER JOIN JanelaAtiva ja 
    ON ja.{ID_ENTIDADE_CHAVE} = a.{ID_ENTIDADE_CHAVE}
INNER JOIN {BANCO_ORIGEM}.{SCHEMA}.{TABELA_DOMINIO} t WITH (NOLOCK)
    ON t.{ID_TIPO_EVENTO} = a.{ID_TIPO_EVENTO}
WHERE t.{FLG_RELEVANTE} = 'S';
```

---

### 1.2 Modelagem Visual no Canvas Lógico do ODI (Passo a Passo)

```
[{TABELA_FILTRO}] ──► (FILTRO_PERIODO) ──► (DISTINCT_ID)
                                                 │
[{TABELA_DADOS}] ────────────────────────────────┼──► [JOIN_DADOS]
                                                            │
[{TABELA_DOMINIO}] ──► (FILTRO_ATIVOS) ─────────────────────┼──► [JOIN_DOMINIO]
                                                                      │
                                                                      ▼
                                                      [STG_{NOME_PROJETO}_{NOME_FATO}]
```

#### Passo 1: Filtragem da Janela Temporal
1. Arraste a tabela principal para o Canvas. Renomeie para **`TABELA_FILTRO`**.
2. Arraste o componente **`Filtro`** e conecte em `TABELA_FILTRO`.
   * Nome: **`FILTRO_PERIODO`**.
   * Condição: `{COLUNA_DATA} >= DATEADD(MONTH, -3, GETDATE())`.
3. Arraste o componente **`Distinto`** (*Distinct*) e conecte na saída de `FILTRO_PERIODO`.
   * Nome: **`DISTINCT_ID`** (mantenha apenas a chave da entidade).

#### Passo 2: Join com a Tabela de Dados Completa
1. Arraste uma segunda instância da tabela principal como **`TABELA_DADOS`**.
2. Arraste o componente **`Junção`** (*Join*).
   * Nome: **`JOIN_DADOS`** (`Inner Join`).
   * Condição: `TABELA_DADOS.{ID_ENTIDADE_CHAVE} = DISTINCT_ID.{ID_ENTIDADE_CHAVE}`.

#### Passo 3: Mapeamento dos Atributos para a Staging
Conecte no Datastore alvo **`STG_{NOME_PROJETO}_{NOME_FATO}`**:

| Coluna Destino Oracle | Expressão de Mapeamento | Observação Crucial |
| :--- | :--- | :--- |
| **`{ID_EVENTO}`** | `TABELA_DADOS.{ID_EVENTO}` | Chave natural única |
| **`{ID_ENTIDADE_CHAVE}`** | `TABELA_DADOS.{ID_ENTIDADE_CHAVE}` | Chave de negócio |
| **`{ID_UNIDADE}`** | `TABELA_DADOS.{ID_UNIDADE}` | FK natural |
| **`{ID_USUARIO}`** | `TABELA_DADOS.{ID_USUARIO}` | Permite NULL (ações automáticas de sistema) |
| **`{COLUNA_DURACAO_DIAS}`** | `DATEDIFF(DAY, TABELA_DADOS.{DTH_INICIO}, ISNULL(TABELA_DADOS.{DTH_FIM}, GETDATE()))` | Tipo **`NUMBER`** (nunca TIMESTAMP!) |
| **`DTC_EXTRACAO`** | `SYSDATE` | Metadado de carga |

---

### 1.3 Configurações na Aba Físico (Carga da Staging)
1. **Unidade de Execução Lógica:** Conectar a unidade lógica do banco fonte (ex: `BD_ORIGEM_LOGICO_UNIT`).
2. **LKM (Loading Knowledge Module):** `LKM SQL to Oracle (Built-In)`.
3. **IKM (Integration Knowledge Module):** `IKM Oracle Insert`.
   * **TRUNCATE**: `True`.
   * **INSERT_HINT**: `/*+ APPEND PARALLEL(4) */`.

---

# PARTE 2: CARGA DA FATO FINAL DW (`{TABELA_FATO_FINAL}`)

Esta etapa roda **100% dentro do Oracle (Oracle para Oracle)**, transformando as chaves naturais da Staging nas Surrogate Keys (`DIMENSION_KEY`) das dimensões SCD Tipo 2 e da dimensão Tempo.

---

### 2.1 Visão da Junção Dimensional no Canvas Lógico do ODI

```
[STG_{NOME_PROJETO}_{NOME_FATO}] (Origem Oracle)
        │
        ├──► [LOOKUP_UNID]   ◄── [DIM_{PROJETO}_UNIDADE] (DTC_EXPIRACAO IS NULL)
        │
        ├──► [LOOKUP_USR]    ◄── [DIM_{PROJETO}_USUARIO] (DTC_EXPIRACAO IS NULL)
        │
        ├──► [LOOKUP_ATRIB]  ◄── [DIM_{PROJETO}_USUARIO] (Alias: DIM_USR_ATRIB)
        │
        ├──► [LOOKUP_STATUS] ◄── [DIM_{PROJETO}_STATUS]  (DTC_EXPIRACAO IS NULL)
        │
        ├──► [LOOKUP_DT_INI] ◄── [DIM_TEMPO]             (TRUNC(DTH_INICIO) = DTC_COMPLETA)
        │
        └──► [LOOKUP_DT_FIM] ◄── [DIM_TEMPO]             (TRUNC(DTH_FIM) = DTC_COMPLETA)
                │
                ▼
      [{TABELA_FATO_FINAL}] (Destino DW)
```

---

### 2.2 Passo a Passo dos Lookups Dimensionais

No Canvas do novo Mapping (ex: `MAP_DW_{TABELA_FATO_FINAL}`):

1. **Adicione a Staging de Origem:** `STG_{NOME_PROJETO}_{NOME_FATO}` (alias `STG`).
2. **Lookup Dimensão Unidade:**
   * Arraste a dimensão: `DIM_{PROJETO}_UNIDADE` (alias `DIM_UNID`).
   * Arraste um componente **`Lookup`** (ou `Left Join`).
   * Condição:
     ```sql
     STG.ID_UNIDADE = DIM_UNID.ID_UNIDADE AND DIM_UNID.DTC_EXPIRACAO IS NULL
     ```
3. **Lookup Dimensão Usuário Executor:**
   * Arraste a dimensão: `DIM_{PROJETO}_USUARIO` (alias `DIM_USR`).
   * Condição:
     ```sql
     STG.ID_USUARIO = DIM_USR.ID_USUARIO AND DIM_USR.DTC_EXPIRACAO IS NULL
     ```
4. **Lookup Dimensão Usuário Atribuído (Role-Playing Dimension):**
   * Arraste uma **segunda instância** de: `DIM_{PROJETO}_USUARIO` (alias `DIM_USR_ATRIB`).
   * Condição:
     ```sql
     STG.ID_USUARIO_ATRIBUICAO = DIM_USR_ATRIB.ID_USUARIO AND DIM_USR_ATRIB.DTC_EXPIRACAO IS NULL
     ```
5. **Lookup Dimensão Calendário / Tempo Início:**
   * Arraste a dimensão conformada: `DIM_TEMPO` (alias `DIM_TEMPO_INI`).
   * Condição:
     ```sql
     TRUNC(STG.DTH_INICIO) = DIM_TEMPO_INI.DTC_COMPLETA
     ```
6. **Lookup Dimensão Calendário / Tempo Fim:**
   * Arraste uma **segunda instância** de: `DIM_TEMPO` (alias `DIM_TEMPO_FIM`).
   * Condição:
     ```sql
     TRUNC(STG.DTH_FIM) = DIM_TEMPO_FIM.DTC_COMPLETA
     ```

---

### 2.3 Regras de Mapeamento para a Fato Final (com Regra Inegociável do `-1`)

Arraste o Datastore de Destino **`{TABELA_FATO_FINAL}`** e preencha as expressões com fallback `NVL(..., -1)`:

| Coluna Destino Fato | Expressão ODI (com proteção de nulo para `-1`) | Descrição |
| :--- | :--- | :--- |
| **`{ID_EVENTO}`** | `STG.{ID_EVENTO}` | Primary Key da Fato (ou chave degenerada) |
| **`DIM_{PROJETO}_UNIDADE`** | `NVL(DIM_UNID.DIMENSION_KEY, -1)` | FK Unidade |
| **`DIM_{PROJETO}_USUARIO`** | `NVL(DIM_USR.DIMENSION_KEY, -1)` | FK Usuário (-1 se robô/sistema) |
| **`DIM_{PROJETO}_USR_ATRIB`**| `NVL(DIM_USR_ATRIB.DIMENSION_KEY, -1)`| FK Usuário Atribuído (-1 se sem atribuição) |
| **`DIM_TEMPO_INICIO`** | `NVL(DIM_TEMPO_INI.DIMENSION_KEY, -1)` | FK Data Início |
| **`DIM_TEMPO_FIM`** | `NVL(DIM_TEMPO_FIM.DIMENSION_KEY, -1)` | FK Data Término (-1 se pendente/em aberto) |
| **`NUM_DURACAO_DIAS`** | `NVL(STG.{COLUNA_DURACAO_DIAS}, 0)` | Métrica de duração |
| **`QTD_EVENTOS`** | `1` | Métrica aditiva unitária |
| **`DTC_CARGA`** | `SYSDATE` | Auditoria técnica |

---

### 2.4 Configurações Físicas (Carga da Fato DW)

Como a Staging, as Dimensões e a Fato já residem no mesmo schema Oracle (`{SCHEMA_ALVO}`):
1. **Unidade de Execução Lógica:** Uma única unidade lógica Oracle (`{SCHEMA_ALVO}_LOGICO_UNIT`).
2. **LKM:** **Nenhum** (execução 100% interna e direta no Oracle).
3. **IKM:** **`IKM Oracle Insert`**.
   * **TRUNCATE**: `True` (se Estratégia A de Truncate & Load).
   * **INSERT_HINT**: `/*+ APPEND PARALLEL(4) */` (Direct-Path Insert).
4. **Performance de Produção Estimada:** Carga de dezenas de milhões de registros em **~2 a 3 minutos** através do paralelismo nativo.
