# GUIA COMPLETO DE IMPLEMENTAÇÃO NO ODI 12c: ESTEIRA {NOME_PROJETO}
## Procedimentos, Mapeamentos, Pacotes e Cenários de Produção

Este guia apresenta o roteiro prático completo para o desenvolvedor de ETL implementar a esteira de dados no **Oracle Data Integrator (ODI 12c em Português)** para o projeto **`{NOME_PROJETO}`**.

A arquitetura oficial de esteira é dividida em **5 Componentes Canônicos**:
1. **PARTE 1: Procedures de Controle e Performance (`TRT_*`)** — Truncate dinâmico, auto-descoberta de schemas e rotinas de pré/pós-carga de índices.
2. **PARTE 2: Mapeamentos no Canvas (`MAP_*`)** — Carga de Staging, Dimensões e Fatos no Canvas Lógico e Físico.
3. **PARTE 3: Pacotes de Orquestração (`PACK_*`)** — Fluxos sequenciais e loops multi-tenant com variáveis e tratamento de erros.
4. **PARTE 4: Cenários de Produção (`SCEN_*`)** — Geração de versões e orquestração master via `OdiStartScen`.
5. **PARTE 5: Checklist Pré-Voo de Performance & Tuning** — Validação das 7 alavancas de aceleração para evitar gargalos.

---

## 🧭 Visão Geral das 3 Estratégias do ODI 12c

| Estratégia | Nível de Acesso Necessário | Complexidade no ODI | Performance | Recomendação |
| :--- | :--- | :--- | :--- | :--- |
| **Estratégia 1: View no Banco de Origem** | Requer permissão de `CREATE VIEW` na fonte. | Mínima (1 para 1 no mapping). | Altíssima. | Ideal quando a equipe de BI tem acesso DDL à origem. |
| **Estratégia 2: 100% Visual no Canvas Lógico** | **Apenas permissão de LEITURA (`SELECT`).** | Média/Alta (componentes de canvas). | Alta. | **A escolha obrigatória corporativa quando não se pode criar objetos na fonte.** |
| **Estratégia 3: ODI Procedure Direta** | Apenas permissão de leitura. Código SQL direto. | Baixa no design visual, mas perde rastreabilidade. | Altíssima. | Alternativa de contingência para colar código manual. |

---

# PARTE 1: PROCEDURES DE CONTROLE E PERFORMANCE (`TRT_*`)

As procedures do ODI executam comandos nativos no Oracle (DDL, PL/SQL e scripts de manutenção) fora do fluxo de dados dos mappings.

### 1.1 Procedure de Truncate Dinâmico de Staging (`TRT_TRUNC_STG_{NOME_PROJETO}`)
- **Finalidade:** Esvaziar rapidamente as tabelas de Staging antes da ingestão do lote, sem sobrecarregar logs de transação (REDO/UNDO).
- **Tecnologia:** `Oracle` | **Schema Lógico:** `{SCHEMA_ALVO}_LOGICO_UNIT`
- **Código do Passo (Command on Target):**
  ```sql
  BEGIN
      EXECUTE IMMEDIATE 'TRUNCATE TABLE STG_{NOME_PROJETO}_ATIVIDADE';
      EXECUTE IMMEDIATE 'TRUNCATE TABLE STG_{NOME_PROJETO}_DOCUMENTO';
      EXECUTE IMMEDIATE 'TRUNCATE TABLE STG_{NOME_PROJETO}_ORGAO';
      EXECUTE IMMEDIATE 'TRUNCATE TABLE STG_{NOME_PROJETO}_PROCEDIMENTO';
      EXECUTE IMMEDIATE 'TRUNCATE TABLE STG_{NOME_PROJETO}_USUARIO';
  END;
  ```

---

### 1.2 Procedure de Auto-Descoberta de Schemas Multi-Tenant (`TRT_UP_PROC_MERGE_ODI_CTRL`)
- **Finalidade:** Identificar dinamicamente novos órgãos/municípios criados no banco transacional e registrá-los na tabela de controle de esteira (`ODI_SCHEMA_CTRL`).
- **Passo 1 (Command on Source - Dicionário de Dados):**
  ```sql
  SELECT username AS SCHEMA_NAME
  FROM all_users u
  WHERE username LIKE '{PADRAO_SCHEMA_TENANT}%'
    AND EXISTS (
      SELECT 1 FROM all_tables t
      WHERE t.owner = u.username AND t.table_name = '{TABELA_TESTE_EXISTENCIA}'
    )
  ```
- **Passo 2 (Command on Target - Tabela de Controle):**
  ```sql
  MERGE INTO ODI_SCHEMA_CTRL tgt
  USING (SELECT '#SCHEMA_NAME' AS SCHEMA_NAME FROM dual) src
  ON (tgt.SCHEMA_NAME = src.SCHEMA_NAME)
  WHEN NOT MATCHED THEN
  INSERT (SCHEMA_NAME, ATIVO_FLG, CRIADO_EM)
  VALUES (src.SCHEMA_NAME, 'S', SYSDATE);
  ```

---

### 1.3 Procedure de Pré-Carga de Fatos: Desativação de Índices (`TRT_PRE_CARGA_FATOS`)
- **Finalidade:** Colocar índices secundários em estado `UNUSABLE` para permitir carga direta ultra-rápida via `/*+ APPEND */` sem custo de reindexação linha a linha.
- **Tecnologia:** `Oracle`
- **Código do Passo:**
  ```sql
  BEGIN
      PRC_PRE_CARGA_FATO('{TABELA_FATO_FINAL}', '{SCHEMA_ALVO}');
  END;
  ```

---

### 1.4 Procedure de Pós-Carga de Fatos: Rebuild Paralelo & Estatísticas (`TRT_POS_CARGA_FATOS`)
- **Finalidade:** Reconstruir índices secundários com paralelismo e atualizar estatísticas do otimizador do Oracle.
- **Tecnologia:** `Oracle`
- **Código do Passo:**
  ```sql
  BEGIN
      PRC_POS_CARGA_FATO('{TABELA_FATO_FINAL}', '{SCHEMA_ALVO}');
  END;
  ```

---

# PARTE 2: MAPEAMENTOS NO CANVAS (`MAP_*`)

## 2.1 Fase 1: Carga da Staging (`MAP_CARGA_STG_*`)

```
[{TABELA_ORIGEM}] ──► [EXP_COMPOSICAO_KEY] ──► [STG_{NOME_PROJETO}_{ENTIDADE}]
                        (#V_IBGE || '000' || ID)
```

### Passo a Passo no Canvas:
1. **Datastore Origem:** Arraste a tabela de origem. Em arquiteturas multi-tenant, defina a tabela como `#V_SCHEMA.{TABELA_ORIGEM}`.
2. **Componente Expressão (`EXP_COMPOSICAO_KEY`):**
   - Para projetos multi-tenant, concatene a chave da unidade/tenant para evitar colisões:
     ```sql
     CASE 
         WHEN {TABELA_ORIGEM}.{ID_NATURAL} IS NULL THEN NULL 
         ELSE TO_NUMBER(TO_CHAR(#V_IBGE) || '000' || TO_CHAR({TABELA_ORIGEM}.{ID_NATURAL})) 
     END
     ```
   - Carimbe a coluna de auditoria de tenant: `#V_IBGE`.
3. **Função Analítica para Fatos Snapshot / Estado Mais Recente (`ROW_NUMBER()`):**
   - Caso precise apenas do último evento:
     ```sql
     ROW_NUMBER() OVER (
         PARTITION BY {ID_ENTIDADE_CHAVE} 
         ORDER BY {DTH_EVENTO} DESC, {ID_EVENTO} DESC
     )
     ```
   - Conecte em um componente **`Filtro`** com a condição: `RN = 1`.

### Configurações Físicas na Aba Físico:
- **LKM:** `LKM SQL to Oracle (Built-In)` ou `LKM Oracle to Oracle Pull (DB Link)`.
- **IKM:** `IKM Oracle Insert`.
- **Opções Físicas de Alta Performance:**
  - `TRUNCATE = False` (pois o truncate é gerenciado na Procedure no início do lote).
  - `INSERT_HINT = /*+ APPEND */`.
  - `FLOW_CONTROL = False` (proibido validar CKM em staging).

---

## 2.2 Fase 2: Carga das Dimensões (`MAP_CARGA_DIM_*`)

```
[STG_{ENTIDADE}] ──► [IKM Oracle Merge] ──► [DIM_{PROJETO}_{ENTIDADE}]
```

### Regras de Mapeamento:
1. **Surrogate Key:** Utilizar a sequence do banco:
   ```sql
   "{SCHEMA_ALVO}"."SEQ_DIM_{ENTIDADE}".NEXTVAL
   ```
2. **Tratamento de Nulos com Fallback Seguro:**
   - Textos: `NVL(STG.{CAMPO}, 'NÃO INFORMADO')`.
   - Datas: `NVL(STG.{DATA}, TO_DATE('01/01/1900', 'DD/MM/YYYY'))`.
   - Números: `NVL(STG.{NUMERO}, -1)`.
3. **Decodificação de Domínios com Cláusula Protetora:**
   ```sql
   CASE STG.STATUS
       WHEN 'A' THEN 'ATIVO'
       WHEN 'I' THEN 'INATIVO'
       ELSE 'STATUS NÃO IDENTIFICADO'
   END
   ```
4. **Configurações Físicas:**
   - **IKM:** `IKM Oracle Merge` ou `IKM SQL Merge`.
   - **FLOW_CONTROL:** `False`.

---

## 2.3 Fase 3: Carga da Fato DW (`MAP_CARGA_FATO_*`)

```
[STG_{FATO}] (Origem Oracle DW)
     │
     ├──► [LOOKUP_UNID]   ◄── [DIM_{PROJETO}_UNIDADE] (DTC_EXPIRACAO IS NULL)
     │
     ├──► [LOOKUP_USR]    ◄── [DIM_{PROJETO}_USUARIO] (DTC_EXPIRACAO IS NULL)
     │
     ├──► [LOOKUP_STATUS] ◄── [DIM_{PROJETO}_STATUS]  (DTC_EXPIRACAO IS NULL)
     │
     ├──► [LOOKUP_DT_INI] ◄── [DIM_TEMPO]             (TRUNC(DTH_INI) = DTC_COMPLETA)
     │
     └──► [LOOKUP_DT_FIM] ◄── [DIM_TEMPO]             (TRUNC(DTH_FIM) = DTC_COMPLETA)
             │
             ▼
   [{TABELA_FATO_FINAL}] (Destino DW)
```

### Regras Inegociáveis de Mapeamento:
1. **Propriedade Obrigatória nos Lookups:**
   - Selecione cada componente `Lookup` no Canvas.
   - Na aba **Propriedades**, marque **`Lookup com Nulo Retornado = True`** (Left Outer Join).
2. **Regra do `-1` em Todas as FKs:**
   ```sql
   NVL(DIM_UNID.DIMENSION_KEY, -1)   AS DIM_{PROJETO}_UNIDADE,
   NVL(DIM_USR.DIMENSION_KEY, -1)    AS DIM_{PROJETO}_USUARIO,
   NVL(DIM_TEMPO_INI.DIMENSION_KEY, -1) AS DIM_TEMPO_INICIO,
   NVL(DIM_TEMPO_FIM.DIMENSION_KEY, -1) AS DIM_TEMPO_FIM
   ```
3. **Configurações Físicas:**
   - **LKM:** **Nenhum** (execução 100% interna Oracle para Oracle).
   - **IKM:** `IKM Oracle Insert`.
   - **INSERT_HINT:** `/*+ APPEND PARALLEL(4) */`.
   - **FLOW_CONTROL:** `False` | **STATIC_CONTROL:** `False`.

---

# PARTE 3: PACOTES DE ORQUESTRAÇÃO (`PACK_*`)

## 3.1 Pacote com Loop Multi-Tenant (`PACK_FLUXO_STG_{NOME_PROJETO}`)

Para processar múltiplos órgãos ou municípios de forma dinâmica sem duplicar mapeamentos:

```
[TRUNC_STG] ──► [UP_MERGE_CTRL] ──► (V_CNT = 1) ──► (V_MAX) ──► [EVAL_LOOP]
                                                                     │
  ┌──────────────────────────────────────────────────────────────────┘
  ▼
[V_SCHEMA / V_IBGE] ──► [MAP_CARGA_STG] ──► (V_CNT = V_CNT + 1) ──► [EVAL_LOOP]
                                                                        │
                                                                   (Se V_CNT > V_MAX)
                                                                        ▼
                                                                     [FIM OK]
```

### Configuração Passo a Passo no Designer:
1. **Passo 1 (Procedure):** Arraste `TRT_TRUNC_STG_{NOME_PROJETO}`.
2. **Passo 2 (Procedure):** Arraste `TRT_UP_PROC_MERGE_ODI_CTRL`.
3. **Passo 3 (Variável - Set):** Arraste `V_CNT` com a opção **Set Variable** = `1`.
4. **Passo 4 (Variável - Refresh):** Arraste `V_MAX` com **Refresh Variable**:
   ```sql
   SELECT TO_NUMBER(COUNT(*)) FROM ODI_SCHEMA_CTRL WHERE ATIVO_FLG = 'S'
   ```
5. **Passo 5 (Variável - Evaluate):** Arraste `V_CNT` com **Evaluate Variable**:
   - Operador: `Less than or equal to` (`<=`).
   - Valor: `#V_MAX`.
   - **Linha Verde (True):** Conecta no Passo 6.
   - **Linha Azul (False / Saída do Loop):** Conecta no encerramento com sucesso.
6. **Passo 6 (Variável - Refresh):** Arraste `V_SCHEMA` e `V_IBGE` com **Refresh Variable**:
   ```sql
   SELECT SCHEMA_NAME FROM (
       SELECT SCHEMA_NAME, ROW_NUMBER() OVER (ORDER BY NVL(ORDEM, 999999), SCHEMA_NAME) RN 
       FROM ODI_SCHEMA_CTRL WHERE ATIVO_FLG = 'S'
   ) WHERE RN = #V_CNT
   ```
7. **Passo 7 (Mapping):** Arraste `MAP_CARGA_STG_{ENTIDADE}`.
8. **Passo 8 (Variável - Increment):** Arraste `V_CNT` como **Increment Variable** (valor `1`).
9. **Retorno do Loop:** Conecte a saída do Passo 8 de volta ao Passo 5 (`EVAL_LOOP`).

---

## 3.2 Pacote de Carga Dimensional e Fato (`PACK_FLUXO_DW_{NOME_PROJETO}`)

```
[TRUNC_DIM_STG] ──► [MAP_DIM_1] ──► [MAP_DIM_2] ──► [TRT_PRE_CARGA_FATOS]
                                                             │
                                                             ▼
                                                    [MAP_CARGA_FATO]
                                                             │
                                                             ▼
                                                    [TRT_POS_CARGA_FATOS]
```

---

# PARTE 4: CENÁRIOS DE PRODUÇÃO (`SCEN_*`)

Em produção, os pacotes nunca são executados em modo de edição (designer); são compilados em **Cenários Executáveis**.

### 4.1 Compilação dos Cenários
1. Clique com o botão direito no Pacote -> **Generate Scenario**.
2. Nomenclatura Padrão:
   - `SCEN_FLUXO_STG_{NOME_PROJETO}` (Versão 001)
   - `SCEN_FLUXO_DIM_{NOME_PROJETO}` (Versão 001)
   - `SCEN_FLUXO_FATO_{NOME_PROJETO}` (Versão 001)

### 4.2 Cenário Master de Produção (`SCEN_FLUXO_PRD_{NOME_PROJETO}`)
Crie um Pacote Master que executa os 3 cenários em sequência através de comandos nativos do ODI:

```
[START_SCEN_STG] ──────► [START_SCEN_DIM] ──────► [START_SCEN_FATO]
(FLUXO_STG v001)         (FLUXO_DIM v001)         (FLUXO_FATO v001)
```

- **Comando do Passo 1:** `OdiStartScen -SCEN_NAME=SCEN_FLUXO_STG_{NOME_PROJETO} -SCEN_VERSION=001`
- **Comando do Passo 2:** `OdiStartScen -SCEN_NAME=SCEN_FLUXO_DIM_{NOME_PROJETO} -SCEN_VERSION=001`
- **Comando do Passo 3:** `OdiStartScen -SCEN_NAME=SCEN_FLUXO_FATO_{NOME_PROJETO} -SCEN_VERSION=001`

---

# PARTE 5: CHECKLIST PRÉ-VOO DE PERFORMANCE & TUNING

Antes de promover a esteira de homologação para produção, confira rigorosamente:

| Item de Verificação | Configuração Correta | Status |
| :--- | :--- | :---: |
| **1. CKM Desativado** | `FLOW_CONTROL = False` e `STATIC_CONTROL = False` em todos os IKMs. | [ ] |
| **2. Direct-Path Insert** | `INSERT_HINT = /*+ APPEND PARALLEL(4) */` na carga da Fato. | [ ] |
| **3. Índices Secundários** | `PRC_PRE_CARGA_FATO` (UNUSABLE) e `PRC_POS_CARGA_FATO` (REBUILD). | [ ] |
| **4. Proteção de Nulos (-1)** | `Lookup com Nulo Retornado = True` e `NVL(..., -1)` em 100% das FKs. | [ ] |
| **5. Staging no Target** | A área de staging física está configurada na Unidade Lógica do DW. | [ ] |
| **6. Índices na Staging** | Chaves naturais da Staging indexadas para acelerar os lookups da Fato. | [ ] |
| **7. Coleta de Estatísticas** | `DBMS_STATS` executado no encerramento da carga pós-rebuild de índices. | [ ] |

---
*Documento de engenharia de dados gerado de acordo com o padrão corporativo de arquitetura e tuning do ODI 12c.*
