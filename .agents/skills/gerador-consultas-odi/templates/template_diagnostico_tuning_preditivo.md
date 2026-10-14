# Template Oficial de Diagnóstico Preditivo & Tuning de Performance — ODI 12c (NINHO)

> Este template define a estrutura padronizada para emissão de relatórios de consultoria e diagnóstico preditivo quando um mapa ou esteira de ODI for inspecionada.

---

# Relatório de Diagnóstico Preditivo & Tuning de Performance — ODI 12c

**Mapeamento / Objeto Auditado:** `MAP_<NOME_DO_OBJETO>`  
**Origem dos Metadados:** `<ARQUIVO_FONTE_OU_SESSAO>`  
**Projeto:** `<NOME_DO_PROJETO>`  
**Data da Auditoria:** `YYYY-MM-DD`  
**Classificação:** Auditoria Preditiva de Engenharia de Dados (Plataforma NINHO)  

---

## 1. Resumo Executivo & Diagnóstico de Gargalos

| Dimensão de Análise | Situação Identificada (Cenário Atual) | Risco / Gargalo Operacional |
| :--- | :--- | :--- |
| **Estratégia de Carga** | Full Load (Truncate & Load) | Degradação linear diária conforme crescimento da base |
| **Colunas de Auditoria na Origem** | Possui `UPDATED_AT` / `DT_ALTERACAO` | Reprocessamento redundante de milhões de linhas estáticas |
| **Estrutura da Staging** | Tabela sem Primary Key definida | Impossibilita sincronização incremental via IKM Merge |
| **Integração Física (KM)** | `LKM SQL to Oracle` / `Control Append` | Efeito funil na JVM do Agent e tabelas temporárias `E$_` |
| **Topologia de Mapeamento** | Monolito com N fluxos independentes | Bloqueio serializado: cadastros leves travados por tabelas pesadas |

---

## 2. Heurísticas Preditivas Acionadas

### Heurística P1: Detecção de Colunas de Auditoria e Conversão para CDC Incremental
- **Nível de Gravidade:** `CRÍTICA`
- **Diagnóstico:** A tabela de origem contém colunas de controle de modificação (`<COLUNAS_UPDATE>`), mas a esteira lê 100% da base todos os dias.
- **Prescrição Técnica:**
  - Adicionar componente **Filtro** no Canvas com buffer deslizante:
    ```sql
    ORIGEM.<COLUNA_UPDATE> >= TRUNC(SYSDATE) - 2
    ```
    *(Ou variável ODI `#<PROJETO>.V_DATA_ULTIMA_CARGA`).*
  - Migrar IKM de Carga Total para **`IKM Oracle Merge`**.

### Heurística P2: Criação de Primary Key na Staging Area
- **Nível de Gravidade:** `ALERTA_ARQUITETURAL`
- **Diagnóstico:** O `IKM Oracle Merge` exige uma `Target Key` definida para montar a cláusula `ON (TARGET.PK = SOURCE.PK)`. Sem PK, a carga falha ou gera produto cartesiano.
- **Prescrição Técnica:**
  - Executar DDL de criação de Primary Key na Staging.
  - Selecionar a `Target Key` nas propriedades físicas do Target no Canvas ODI.

### Heurística P3: Duelo de IKMs: `IKM Oracle Merge` vs `IKM Oracle Incremental Update`
- **Nível de Gravidade:** `RECOMENDAÇÃO_PERFORMANCE`
- **Diagnóstico:** O `Incremental Update` executa dois passos lentos (Update correlacionado + Insert). O `Merge` resolve em um único comando SQL nativo no kernel do banco.
- **Prescrição Técnica:**
  - Selecionar **`IKM Oracle Merge`**.
  - Configurar `FLOW_CONTROL = False` para não gerar overhead de CKM (`E$_`).

### Heurística P4: Desacoplamento de Monolito Multi-Fluxo
- **Nível de Gravidade:** `ALERTA_ARQUITETURAL`
- **Diagnóstico:** N fluxos independentes na mesma tela forçam execução serial na JVM.
- **Prescrição Técnica:**
  - Isolar tabelas massivas em mapeamentos individuais.
  - Orquestrar no Pacote via `OdiStartScen -ASYNC=YES`.

### Heurística P5: Eliminação do Funil JDBC
- **Nível de Gravidade:** `ALERTA_PERFORMANCE`
- **Diagnóstico:** `LKM SQL to Oracle` trafega dados pela memória Java.
- **Prescrição Técnica:**
  - Migrar para `LKM Oracle to Oracle Pull (DB Link)`.

---

## 3. Matriz De/Para de Configurações no ODI Studio

| Componente / Propriedade | Configuração Atual (Lenta) | Configuração Preditiva Otimizada | Ação do Engenheiro no Canvas |
| :--- | :--- | :--- | :--- |
| **Canvas Lógico: Filtro** | Nenhum | `UPDATED_AT >= TRUNC(SYSDATE) - 2` | Arrastar componente Filtro pós-Datastore Origem |
| **Physical Target: IKM** | `IKM Oracle Insert` / `Control Append` | **`IKM Oracle Merge`** | Selecionar na paleta de IKMs do Target |
| **Physical Target: Target Key** | `Undefined` | **`PK_<NOME_STG>`** | Selecionar a constraint PK na lista suspensa |
| **Opção IKM: FLOW_CONTROL** | `True` | **`False`** | Desmarcar checagem de erros CKM |
| **Opção IKM: TRUNCATE_TARGET** | `True` | **`False`** | Preservar histórico para atualização incremental |

---

## 4. DDL de Implementação das Primary Keys na Staging

```sql
-- ============================================================================
-- SCRIPT DDL: CRIAÇÃO DE PRIMARY KEYS PARA CARGA INCREMENTAL (CDC)
-- ============================================================================
ALTER TABLE <NOME_STG> ADD CONSTRAINT PK_<NOME_STG> PRIMARY KEY (<COLUNA_PK>);
```

---

## 5. Projeção de Ganho de Performance

| Indicador | Antes do Tuning (Carga Atual) | Pós-Tuning Preditivo (CDC + Merge) | Ganho Esperado |
| :--- | :--- | :--- | :--- |
| **Tempo de Execução** | ~120 min (2h) | **3 a 5 min** | **Redução de ~95%** |
| **Volume de Leitura/Dia** | 100% da base histórica | ~0.1% a 1.0% (Apenas alterações) | **Queda de ~99% no I/O** |
| **Concorrência e Locks** | Locks prolongados na tabela | Transação atômica em segundos | **Risco de deadlock eliminado** |

