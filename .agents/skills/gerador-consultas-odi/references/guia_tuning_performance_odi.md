# Guia Avançado de Arquitetura e Tuning de Performance no Oracle Data Integrator (ODI 12c)

Este documento estabelece as diretrizes canônicas de engenharia e otimização de performance para o **Oracle Data Integrator (ODI 12c)**, cobrindo tanto o desenvolvimento de novos projetos quanto o diagnóstico e tuning de projetos legados com janelas de carga lentas.

---

## 🎯 As 7 Alavancas de Aceleração de Performance no ODI 12c

Ao projetar ou auditar qualquer objeto do ODI 12c (Mappings, Packages, Procedures ou Scenarios), estas 7 alavancas devem ser rigorosamente verificadas:

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                   AS 7 ALAVANCAS DE PERFORMANCE NO ODI 12c                      │
├────────────────────┬───────────────────────────────────┬────────────────────────┤
│ Alavanca           │ Anti-Padrão Comum (Lento)         │ Padrão Otimizado       │
├────────────────────┼───────────────────────────────────┼────────────────────────┤
│ 1. CKM / Flow Ctrl │ FLOW_CONTROL = True (Gera E$_...) │ FLOW_CONTROL = False   │
│ 2. Índices na Fato │ Índices B-Tree ativos na carga    │ Índices UNUSABLE na STG│
│ 3. Direct-Path     │ Insert tradicional (Gera Redo)    │ /*+ APPEND PARALLEL */ │
│ 4. Multi-Tenant    │ Loop sequencial síncrono 1 a N    │ OdiStartScen -ASYNC=YES│
│ 5. Staging Area    │ Staging no Source ou intermediário│ Staging no Target (DW) │
│ 6. Lookups Canvas  │ Múltiplos lookups sem índices STG │ Índices na STG nas FKs │
│ 7. DBMS_STATS      │ Coleta repetida ou ausente        │ Coleta única pós-carga │
└────────────────────┴───────────────────────────────────┴────────────────────────┘
```

---

### Alavanca 1: Eliminação de CKM e Flow Control em Staging e DW
- **Diagnóstico:** Quando o IKM selecionado é do tipo `Control Append` ou a opção `FLOW_CONTROL` está marcada como `True`, o ODI gera tabelas temporárias de erro (`E$_...`) e executa queries adicionais de checagem para cada constraint de tabela (PK, UK, FK, Check).
- **Impacto:** Multiplica o tempo de carga em até **10 vezes**.
- **Solução de Tuning:**
  - Em ambientes de Data Warehouse onde os dados são saneados na Staging e as dimensões possuem fallback `-1`, desative o controle de fluxo no IKM:
    - `FLOW_CONTROL = False`
    - `STATIC_CONTROL = False`
  - Utilizar preferencialmente **`IKM Oracle Insert`** (para cargas truncate & load ou insert-only) ou **`IKM Oracle Merge`** (para dimensões com atualização).

---

### Alavanca 2: Índices Secundários Desativados na Carga Massiva
- **Diagnóstico:** Inserir 5 a 50 milhões de linhas em uma tabela Fato com 10 índices secundários (FKs, datas, status) ativos obriga o Oracle a rebalancear e escrever em cada árvore de índice B-Tree a cada linha inserida.
- **Impacto:** Degradação severa de I/O de disco e impossibilidade de paralelismo pleno.
- **Solução de Tuning:**
  - Manter **apenas** a Primary Key ou Unique Index ativo durante a inserção (para salvaguardar o grão).
  - Executar procedure de **Pré-Carga** antes do mapping:
    ```sql
    -- Coloca índices secundários em estado UNUSABLE
    ALTER INDEX IDX_FATO_DIM_USUARIO UNUSABLE;
    ALTER INDEX IDX_FATO_DIM_UNIDADE UNUSABLE;
    ALTER INDEX IDX_FATO_DIM_TEMPO   UNUSABLE;
    ```
  - Executar procedure de **Pós-Carga** imediatamente após o mapping:
    ```sql
    -- Reconstrói em paralelo sem gerar REDO massivo
    ALTER INDEX IDX_FATO_DIM_USUARIO REBUILD PARALLEL 4 NOLOGGING;
    ALTER INDEX IDX_FATO_DIM_USUARIO NOPARALLEL LOGGING;
    ```

---

### Alavanca 3: Direct-Path Insert com Paralelismo (`/*+ APPEND PARALLEL */`)
- **Diagnóstico:** Inserts normais buscam blocos com espaço livre na lista de blocos (freelists/ASSM), gerando contenção de buffers e registro completo no log de transação (REDO).
- **Impacto:** Alta contenção de I/O e estouro de tablespaces de REDO/UNDO.
- **Solução de Tuning:**
  - Na aba **Físico** do Mapping, nas propriedades do IKM:
    - **`INSERT_HINT`**: `/*+ APPEND PARALLEL(4) */`
  - A tabela de destino deve ter a propriedade `NOLOGGING` ativada durante a janela de carga.
  - O Direct-Path grava blocos inteiros diretamente acima da *High-Water Mark* (HWM), ignorando freelists e aumentando a velocidade de inserção em até **8 vezes**.

---

### Alavanca 4: Otimização de Loops Multi-Tenant (Sequencial vs Paralelo Assíncrono)
- **Diagnóstico:** Em arquiteturas com dezenas de schemas de órgãos/municípios, o pacote do ODI tradicional executa um loop sequencial com contador (`V_CNT = 1` até `V_MAX`). Se houver 80 schemas e cada um levar 3 minutos, a esteira leva 240 minutos (4 horas).
- **Impacto:** Janela de carga inviável.
- **Solução de Tuning:**
  - **Estratégia Sequencial Otimizada:** Se os recursos do servidor forem restritos, manter o loop sequencial, mas garantir que a Staging seja truncada antes e que cada ciclo faça apenas `INSERT /*+ APPEND */`.
  - **Estratégia de Lotes Paralelos / Assíncronos:**
    - Dividir o lote em 4 a 8 buckets ou disparar os cenários de extração via `OdiStartScen`:
      ```bash
      OdiStartScen -SCEN_NAME=FLUXO_STG_CLIENTE -SCEN_VERSION=001 -ASYNC=YES "-VAR_TENANT=101"
      ```
    - A carga de 80 clientes executando em 4 threads paralelos derruba o tempo total de 4 horas para **menos de 1 hora**.
  - **Padrão Corporativo de Tabela de Controle Multi-Tenant (`ODI_SCHEMA_CTRL`):**
    Para controlar a iteração dos schemas municipais/órgãos em esteiras do ODI, utilizar a tabela canônica:
    ```sql
    CREATE TABLE ODI_SCHEMA_CTRL (
        SCHEMA_NAME     VARCHAR2(100) NOT NULL PRIMARY KEY,
        ATIVO_FLG       VARCHAR2(1) DEFAULT 'S' NOT NULL, -- 'S' ativo, 'N' inativo/ignorar
        ORDEM           NUMBER(10),                       -- Sequência de prioridade
        DT_ATUALIZACAO  TIMESTAMP,                        -- Timestamp do último merge/carga
        COD_IBGE        VARCHAR2(20)                      -- Identificador do município/órgão
    );
    ```
    O pacote ODI executa `SELECT SCHEMA_NAME, COD_IBGE FROM ODI_SCHEMA_CTRL WHERE ATIVO_FLG = 'S' ORDER BY ORDEM` alimentando as variáveis de loop `#V_SCHEMA`, `#V_IBGE` e `#V_CNT`.

---

### Alavanca 5: Posicionamento Físico da Staging Area (Staging no Target)
- **Diagnóstico:** No Physical Design do Mapping, a **Staging Area** está configurada na Unidade Lógica de Origem (Source) ou em um schema intermediário sem comunicação direta.
- **Impacto:** Os dados intermediários são trafegados via rede ou DBLink múltiplas vezes, gerando tráfego cruzado ineficiente.
- **Solução de Tuning:**
  - Configurar a **Staging Area** para residir **exatamente na mesma Unidade Física do Target (DW Oracle)**.
  - Isso permite que o Oracle resolva todas as transformações, funções de janela analítica (`ROW_NUMBER()`) e lookups em memória local e tablespaces temporárias (`TEMP`), com **Zero I/O de rede**.

---

### Alavanca 6: Otimização de Lookups e Joins no Canvas
- **Diagnóstico:** Um Mapping da Fato faz lookups em 8 dimensões. A tabela de Staging possui 10 milhões de linhas e não tem nenhum índice em suas colunas de chave natural (`ID_USUARIO`, `ID_UNIDADE`, etc.).
- **Impacto:** O otimizador do Oracle pode optar por `NESTED LOOPS` com varreduras repetidas ou `HASH JOIN` gigantescos que estouram a `PGA_AGGREGATE_TARGET`.
- **Solução de Tuning:**
  - Garantir que a Staging possua índices rápidos locais ou temporários nas colunas de chave que participam dos lookups.
  - No Canvas Lógico do ODI, selecionar cada componente **`Lookup`** e marcar **`Lookup com Nulo Retornado = True`** (Left Outer Join) para evitar filtros acidentais.
  - Utilizar a técnica de **Lookups em Cadeia** somente quando necessário, preferindo resolver hierarquias no grão da própria dimensão.

---

### Alavanca 7: Coleta de Estatísticas do Otimizador (`DBMS_STATS`) no Ponto Correto
- **Diagnóstico:** Três erros comuns:
  1. Chamar `DBMS_STATS` a cada iteração do loop multi-tenant (sobrecarga inútil).
  2. Não chamar `DBMS_STATS` após a carga, deixando o otimizador com cardinalidade desatualizada e planos ruins no dia seguinte.
  3. Coletar estatísticas *antes* de reconstruir os índices.
- **Impacto:** Consultas do Power BI / Camada Semântica executando em minutos por falta de histogramas e estatísticas de índices atualizadas.
- **Solução de Tuning:**
  - Disparar a coleta **exatamente uma vez**, no encerramento da esteira pós-rebuild de índices:
    ```sql
    DBMS_STATS.GATHER_TABLE_STATS(
        ownname          => 'DW_CORPORATIVO',
        tabname          => 'FAT_DOCUMENTO',
        estimate_percent => DBMS_STATS.AUTO_SAMPLE_SIZE,
        method_opt       => 'FOR ALL COLUMNS SIZE AUTO',
        degree           => 4,
        cascade          => TRUE,
        no_invalidate    => FALSE
    );
    ```

---

## 🧠 Motor de Regras Preditivas: As 5 Heurísticas de Diagnóstico Automático

Em vez de aceitar cegamente esteiras de carga lenta, a arquitetura do NINHO implementa um **Motor Preditivo** composto por 5 heurísticas automáticas para detecção precoce de gargalos:

### Heurística P1: Taxonomia Ampla de Datas & CDC para Ciclos de Vida (Sem UPDATED_AT Clássico)

Nem todas as origens possuem colunas padronizadas como `updated_at`. O arquiteto e o motor de regras devem classificar a tabela em um dos 4 padrões de arquitetura temporal:

#### Padrão P1.A: Colunas de Auditoria Clássicas (`UPDATED_AT`, `DT_ALTERACAO`, `MODIFIED_DATE`)
- **Filtro Direto:** `ORIGEM.UPDATED_AT >= TRUNC(SYSDATE) - 2` (ou `#PROJETO.V_DATA_ULTIMA_CARGA`).
- **IKM:** `IKM Oracle Merge` com Target Key na Staging.

#### Padrão P1.B: Tabelas de Ciclo de Vida de Workflow / Transacionais (`dth_abertura` + `dth_conclusao`)
- **Caso Real:** Exemplo da tabela `BD_SAEB_SEIBAHIA.dbo.atividade` (SEI Bahia / SEI Municípios):
  - `dth_abertura datetime NOT NULL` (nascimento da atividade)
  - `dth_conclusao datetime NULL` (encerramento/atualização do estado)
  - **Problema:** A tabela não possui `updated_at`. Se filtrar apenas por `dth_abertura`, ignora processos antigos que foram concluídos hoje. Se fizer Carga Total, reprocessa 50 milhões de linhas em 2 horas.
- **Solução Preditiva — Filtro de Janela de Ciclo de Vida:**
  ```sql
  (ORIGEM.dth_abertura >= TRUNC(SYSDATE) - 3 
   OR ORIGEM.dth_conclusao >= TRUNC(SYSDATE) - 3 
   OR ORIGEM.dth_conclusao IS NULL)
  ```
  *(Sintaxe SQL Server na origem: `dth_abertura >= DATEADD(day, -3, CAST(GETDATE() AS DATE)) OR dth_conclusao >= DATEADD(day, -3, CAST(GETDATE() AS DATE)) OR dth_conclusao IS NULL`)*
- **Racional de Ganho Brutal:**
  - Em uma base com 50 milhões de registros históricos, 49.7 milhões já estão concluídos há mais de 3 dias (`dth_conclusao < D-3`).
  - Apenas as atividades abertas (`dth_conclusao IS NULL`, ~200 mil) + as que abriram ou concluíram nos últimos 3 dias (~50 mil) são lidas!
  - **Volume lido cai de 50.000.000 para 250.000 linhas (redução de 99.5% no I/O)**.
  - O `IKM Oracle Merge` sincroniza na Staging via PK `id_atividade` em segundos.

#### Padrão P1.C: Tabelas Append-Only / Históricas (Apenas Data de Criação e ID Sequencial)
- **Caso Real:** Tabelas de auditoria, logs ou protocolos onde registros nunca sofrem UPDATE após criados.
- **Solução Preditiva:**
  - Filtro por data de criação: `ORIGEM.dth_abertura >= TRUNC(SYSDATE) - 1`
  - OU High-Water Mark por ID numérico sequencial: `ORIGEM.id_atividade > #PROJETO.V_MAX_ID_ATIVIDADE`
  - **IKM:** `IKM Oracle Insert` com Direct-Path `/*+ APPEND */` (sem truncate).

#### Padrão P1.D: Tabelas sem Nenhuma Coluna Temporal
- **Tabelas Cadastrais Pequenas/Médias (< 100k linhas, ex: `unidade`, `tarefa`):** Carga Total com `TRUNCATE = True` e `FLOW_CONTROL = False` é o caminho mais limpo e rápido (executa em 2 segundos).
- **Tabelas Massivas sem Datas:** Habilitar Change Tracking nativo do banco de origem (SQL Server Change Tracking / Oracle CDC) ou CDC diferencial por Hash (`ORA_HASH`).

---

### Heurística P2: Pré-requisito Estrutural de Primary Key na Staging Area
- **Condição de Disparo:** Proposta de carga incremental (Merge ou Incremental Update) para uma tabela de Staging (`STG_*`).
- **Risco Operacional:** Se a tabela de Staging no banco de dados não possuir Primary Key ou Unique Constraint, o IKM do ODI não sabe como casar os registros existentes (`Match Condition`). Isso causa erro de compilação ou tentativa desastrosa de cruzar todas as colunas, degradando a performance em um produto cartesiano.
- **Prescrição Preditiva:**
  1. Criar a Primary Key física na tabela Staging:
     ```sql
     ALTER TABLE STG_EST_CONTATOS ADD CONSTRAINT PK_STG_EST_CONTATOS PRIMARY KEY (ID);
     ```
  2. No ODI Designer, abrir o Datastore da Staging, marcar a coluna de chave como **Primary Key** e no nó físico do mapeamento definir:
     - **`Target Key`**: Selecionar a constraint `PK_STG_EST_CONTATOS`.

---

### Heurística P3: Duelo de IKMs: Por que `IKM Oracle Merge` supera o `Incremental Update`
- **Condição de Disparo:** Configuração de IKM para sincronização de dimensões ou Staging com chave única.
- **Comparativo Técnico:**

| Característica | `IKM Oracle Incremental Update` | `IKM Oracle Merge` (Recomendado) |
| :--- | :--- | :--- |
| **Mecanismo de Execução** | 2 passos lentos: 1. `UPDATE` com subquery correlata + 2. `INSERT WHERE NOT EXISTS` | **1 passo atômico nativo:** `MERGE INTO ... USING ... ON (...)` |
| **Custo de CPU e I/O** | Alto (dupla varredura das tabelas de staging e destino) | **Baixo (única varredura otimizada pelo kernel Oracle)** |
| **Paralelismo** | Limitado no passo de Update | **Totalmente compatível com `PARALLEL` e Direct-Path** |
| **Geração de REDO/UNDO** | Elevada | **Mínima** |
| **Velocidade Relativa** | 1x (Base) | **4x a 8x mais rápido** |

- **Prescrição Preditiva:**
  - Adotar sempre o **`IKM Oracle Merge`**.
  - Nas propriedades físicas do Target:
    - `FLOW_CONTROL`: `False` (elimina checagem de erros via `E$_`).
    - `TRUNCATE_TARGET_TABLE`: `False`.

---

### Heurística P4: Detecção de Mapeamento Monolítico Multi-Tabelas
- **Condição de Disparo:** Um único mapeamento ODI contém mais de 3 fluxos independentes de extração (ex: 10 tabelas de cadastro e evento na mesma tela).
- **Risco Operacional:** O ODI Agent executa as etapas do mapeamento em um único thread compartilhado. Se uma tabela tiver 10 milhões de linhas e demorar 1h30, as outras 9 tabelas pequenas (que levariam 10 segundos) ficam retidas esperando. Se houver falha em 1 tabela, todo o mapeamento aborta.
- **Prescrição Preditiva:**
  1. Isolar tabelas massivas em mapeamentos atômicos (`MAP_STG_TABELA_PESADA`).
  2. No Pacote (`PACK_*`), acionar os cenários de carga de forma assíncrona concorrente:
     ```bash
     OdiStartScen -SCEN_NAME=SCEN_STG_TABELA_A -SCEN_VERSION=001 -ASYNC=YES
     OdiStartScen -SCEN_NAME=SCEN_STG_TABELA_B -SCEN_VERSION=001 -ASYNC=YES
     ```

---

### Heurística P5: Detecção de Funil de I/O em Driver JDBC (LKM SQL to Oracle)
- **Condição de Disparo:** Extração de uma base de origem Oracle para um Data Warehouse Oracle configurada com `LKM SQL to Oracle (Built-In)`.
- **Risco Operacional:** O driver JDBC do ODI Agent atua como um funil: lê milhões de linhas pela rede para a memória da JVM do Agent, converte em Java Objects e escreve em lotes na tabela temporária `C$_` no schema de trabalho.
- **Prescrição Preditiva:**
  - Migrar para **`LKM Oracle to Oracle Pull (DB Link)`**.
  - O banco de destino dispara um Direct-Path Insert direto via Database Link (`INSERT /*+ APPEND PARALLEL(4) */ INTO STG SELECT ... FROM ORIGEM@DBLINK`), reduzindo o tempo de transferência em mais de 70% e eliminando a tabela `C$_`.

---

## 🛠️ Roteiro de Consultoria de Tuning de Objetos ODI Existentes

Quando um projeto legado ou em andamento apresentar lentidão, solicite ao engenheiro:
1. O arquivo XML exportado do Mapping (`MAP_*.xml`) ou Pacote (`PACK_*.xml`).
2. Alternativamente, o código SQL gerado na aba de execução do Operador do ODI (Session Log).

### Auditoria Automatizada via CLI:
Execute o script oficial do NINHO:
```bash
python core/scripts_comuns/auditar_mapa_odi.py <caminho_mapa.xml> --output <relatorio.md>
```

### Checklist de Diagnóstico de Tuning:
1. **Auditoria de KMs:**
   - [ ] LKM é `LKM SQL to Oracle (Built-In)` ou `LKM Oracle to Oracle Pull (DB Link)`?
   - [ ] IKM é `IKM Oracle Insert` (Full) ou `IKM Oracle Merge` (Incremental)?
   - [ ] `FLOW_CONTROL` e `STATIC_CONTROL` estão como `False`?
   - [ ] `TRUNCATE` está configurado corretamente em vez de `DELETE FROM`?
2. **Auditoria de Índices e Constraints:**
   - [ ] Tabelas de Staging possuem Primary Key física criada para viabilizar CDC Incremental?
   - [ ] Há procedure de pré-carga desativando índices secundários (`UNUSABLE`) na Fato?
   - [ ] Há procedure de pós-carga reconstruindo com `PARALLEL 4 NOLOGGING`?
   - [ ] Constraints estrangeiras (FKs) na Fato estão desabilitadas ou validadas na modelagem?
3. **Auditoria de Expressões e Lookups:**
   - [ ] Todas as FKs possuem fallback `NVL(..., -1)`?
   - [ ] Os Lookups possuem `Lookup com Nulo Retornado = True`?
   - [ ] Há transformações `UPPER`, `REGEXP` ou `TO_NUMBER` sendo executadas repetidamente em colunas de join?
4. **Auditoria de Orquestração (Pacotes/Cenários):**
   - [ ] Há tratamento de erros nos passos do pacote (fluxo vermelho)?
   - [ ] O loop possui condição de parada segura?
   - [ ] O cenário master encadeia STG -> DIM -> FATO na ordem correta?

### Modelo de Saída: Relatório de Diagnóstico & Tuning
O agente deve compilar e entregar o relatório em `saida/planejador_dw/09_relatorio_estrategias/DIAGNOSTICO_TUNING_ODI_<OBJETO>.md` contendo:
1. **Resumo Executivo do Diagnóstico** (gargalos identificados e tempo atual estimado).
2. **Tabela de Alterações Recomendadas nas Propriedades do ODI** (de/para de configurações).
3. **Scripts PL/SQL de Aceleração** (índices, pré/pós-carga, hints, PKs de Staging).
4. **Projeção de Ganho de Performance** (tempo atual vs tempo projetado pós-tuning).


