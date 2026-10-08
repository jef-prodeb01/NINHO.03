# Relatório de Estratégias & Linhagem: <NOME_PROJETO>

> **Versão do Projeto:** 1.0  
> **Engenheiro Responsável:** `<NOME_ENGENHEIRO>`  
> **Schema Alvo:** `<SCHEMA_ALVO>`  
> **Data de Planejamento:** `<DATA>`  

---

## 1. Topologia da Esteira & Disparo via `OdiOSCommand` (SSH)

O ODI orquestra toda a esteira corporativa. Abaixo estão as configurações exatas para os componentes `OdiOSCommand`:

### 1.1 Ingestão de Arquivos / FTPs via Apache Hop
- **Ferramenta:** Apache Hop
- **Pipeline Hop:** `<NOME_PIPELINE>.hpl`
- **Servidor Remoto:** `<HOST_SERVIDOR_HOP>`
- **Comando SSH configurado no `OdiOSCommand`:**
  ```bash
  ssh <USUARIO_SSH>@<HOST_SERVIDOR_HOP> "/opt/hop/hop-run.sh -r local -f /opt/etl/hop/pipelines/<NOME_PIPELINE>.hpl -l Basic"
  ```
- **Tabela Destino no Oracle:** `STG_<DOMINIO>_<ARQUIVO>`
- **Estratégia de Carga na STG:** `TRUNCATE & LOAD` antes da execução.

### 1.2 Ingestão de APIs Web via Python
- **Ferramenta:** Python 3 (Requests / Polars / oracledb)
- **Script:** `<NOME_SCRIPT>.py`
- **Servidor Remoto:** `<HOST_SERVIDOR_PYTHON>`
- **Comando SSH configurado no `OdiOSCommand`:**
  ```bash
  ssh <USUARIO_SSH>@<HOST_SERVIDOR_PYTHON> "/usr/bin/python3 /opt/etl/python/<NOME_SCRIPT>.py --data-ref \$(date +\%Y-\%m-\%d)"
  ```
- **Tabela Destino no Oracle:** `STG_<DOMINIO>_<SERVICO>`
- **Estratégia de Carga na STG:** `APPEND` com controle por `ID_LOTE`.

---

## 2. Dicionário de Linhagem & "Como Chegar em Cada Valor"

### 2.1 Carga da Dimensão `DIM_<DOMINIO>_<ENTIDADE>` (SCD Tipo 2)
- **Tabela Origem:** `STG_<DOMINIO>_<ENTIDADE>`
- **Tabela Auxiliar do ODI:** `ODI_DIM_<DOMINIO>_<ENTIDADE>`
- **Mecanismo ODI:** Módulo *Dimensões e Cubos* (IKM Oracle Slowly Changing Dimension).

| Coluna Destino | Tipo | Origem (STG) | Regra / Transformação | Comportamento SCD2 |
| :--- | :--- | :--- | :--- | :--- |
| **DIMENSION_KEY** | NUMBER | - | Gerado pela SEQUENCE corporativa `SEQ_DIM_<ENTIDADE>.NEXTVAL` | Surrogate Key |
| **ID_<ENTIDADE>** | NUMBER | `STG.ID_<ENTIDADE>` | Direto da chave de negócio na origem | Chave Natural (Compare) |
| **SIGLA_<ENTIDADE>** | VARCHAR2 | `STG.SIGLA` | `UPPER(TRIM(STG.SIGLA))` | Histórico (Gera nova linha se mudar) |
| **DS_<ENTIDADE>** | VARCHAR2 | `STG.DESCRICAO` | `TRIM(STG.DESCRICAO)` | Histórico (Gera nova linha se mudar) |
| **SIN_ATIVO** | CHAR(1) | `STG.ATIVO` | `CASE WHEN STG.ATIVO = 1 THEN 'S' ELSE 'N' END` | Histórico |
| **DTC_EFETIVACAO** | DATE | - | Preenchido com `TRUNC(SYSDATE)` na inserção da nova versão | Início da vigência |
| **DTC_EXPIRACAO** | DATE | - | Mantido `NULL` enquanto vigente. Atualizado com `TRUNC(SYSDATE) - 1` ao expirar | Fim da vigência |
| **DES_ATUALIZAR** | CHAR(1) | - | Controlado automaticamente pelo ODI ('N' padrão) | Controle de Carga |

---

### 2.2 Carga da Tabela `FATO_<DOMINIO>_<EVENTO>`
- **Tabela Origem:** `STG_<DOMINIO>_<ENTIDADE>`
- **Grão Físico:** Uma ocorrência de `<EVENTO>` por data e combinação dimensional.

| Coluna Destino | Tipo | Origem (STG) | Regra / Como Calcular o Valor | Estratégia ODI (Lookup) |
| :--- | :--- | :--- | :--- | :--- |
| **DIM_<ENTIDADE_1>** | FK | `STG.ID_ENTIDADE_1` | Buscar `DIMENSION_KEY` em `DIM_<ENTIDADE_1>` onde `ID = STG.ID_ENTIDADE_1` e `DTC_EXPIRACAO IS NULL`. Se nulo, atribuir `-1`. | Lookup em memória / Join no Mapping |
| **DIM_<ENTIDADE_2>** | FK | `STG.ID_ENTIDADE_2` | Buscar `DIMENSION_KEY` em `DIM_<ENTIDADE_2>` onde `ID = STG.ID_ENTIDADE_2` e `DTC_EXPIRACAO IS NULL`. Se nulo, atribuir `-1`. | Lookup em memória / Join no Mapping |
| **DIM_TEMPO** | FK | `STG.DATA_EVENTO` | `TO_NUMBER(TO_CHAR(STG.DATA_EVENTO, 'YYYYMMDD'))`. Buscar em `DIM_TEMPO`. Se nulo, atribuir `-1`. | Conversão numérica de data |
| **QTD_<EVENTO>** | Medida | - | Constante `1` para cada registro do evento. | Medida Aditiva direta |
| **QTD_<VALOR_1>** | Medida | `STG.QTDE_BRUTA` | `NVL(STG.QTDE_BRUTA, 0)`. Validar se `>= 0`. | Medida Aditiva direta |
| **DTC_CARGA** | Auditoria | - | Preenchido com `SYSDATE` durante a execução do mapping. | Timestamp do job |

---

## 3. Estimativa de Sizing e Crescimento de Storage (Para DBAs)

Cálculo de volumetria para alinhamento de infraestrutura:

### Parâmetros da Fato Principal:
- **Tamanho médio estimado por linha:** `<BYTES_LINHA>` bytes
- **Volume de carga projetado:** `<LINHAS_DIA>` linhas/dia (~`<LINHAS_MES>` linhas/mês)
- **Crescimento Anual Estimado:**
  $$\frac{<BYTES_LINHA> \times <LINHAS_MES> \times 12}{1024 \times 1024 \times 1024} \approx \mathbf{<GB_ANO>\text{ GB/ano}}$$
- **Recomendação de Tablespace:**
  - Alocação inicial recomendada para `<TABLESPACE_DADOS>`: `<GB_INICIAL>` GB com `AUTOEXTEND ON NEXT 1G MAXSIZE UNLIMITED`.
  - Estratégia de Particionamento: Interval Partitioning mensal por `DIM_TEMPO`.

---

## 4. Ponte com o Módulo de Camada Semântica

Ao finalizar a execução dos DDLs e a primeira carga no ODI, o projeto já se integra automaticamente com o módulo existente:

1. **Views `DIM_ATUAL`:** Geradas filtrando `WHERE DTC_EXPIRACAO IS NULL AND DIMENSION_KEY <> -1`.
2. **Views `EVENTO`:** Fato com os joins para as dimensões vigentes.
3. **Views `KPI`:** Consolidações das perguntas de negócio listadas no Intake.
4. **8 Tabelas `META_*`:** Metadados pré-mapeados para alimentar a inteligência artificial corporativa.
