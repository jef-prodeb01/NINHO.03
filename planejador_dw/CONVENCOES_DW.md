# CONVENCOES_DW.md — Padrões e Convenções de Modelagem

Este documento estabelece o **DNA corporativo** para a criação de tabelas e estruturas dimensionais no Oracle DW. O Planejador de DW segue essas convenções estritamente na geração de todos os scripts DDL.

---

## 1. Padrão de Nomenclatura das Tabelas

| Camada | Padrão de Nome | Exemplo Real | Papel no Pipeline |
| :--- | :--- | :--- | :--- |
| **Auditoria** | `TB_CONTROLE_CARGA` | `SDM_OLAP.TB_CONTROLE_CARGA` | Registra a conclusão e o timestamp de cada execução do projeto. |
| **Staging** | `STG_<DOMINIO>_<ENTIDADE>` | `STG_DEIC_ACAO`, `STG_SEI_PROCEDIMENTO` | Aterrissagem inicial das fontes (Hop, Python ou ODI). |
| **Auxiliar ODI** | `ODI_DIM_<DOMINIO>_<ENTIDADE>` | `ODI_DIM_DEIC_ACAO`, `ODI_DIM_SEI_MUNIC_DOCUMENTO` | Tabela de trabalho espelho para o componente de *Dimensões e Cubos* do ODI. |
| **Dimensão** | `DIM_<DOMINIO>_<ENTIDADE>` | `DIM_DEIC_ACAO`, `DIM_SEI_MUNIC_ORGAO` | Dimensão oficial com Surrogate Key e histórico SCD Tipo 2. |
| **Fato** | `FATO_<DOMINIO>_<EVENTO>` | `FATO_DEIC_ACAO`, `FATO_SEI_MUNIC_DOCUMENTO` | Fato transacional / acumulada com FKs dimensionais e medidas `QTD_*`. |

> **Regra de Caixas:** TODOS os identificadores de tabelas, colunas, constraints e índices devem ser gerados em **MAIÚSCULAS**.

---

## 2. Padrão da Camada `STG_*` (Staging de Ingestão)

- **Objetivo:** Receber os dados brutos da fonte sem transformação pesada.
- **Chave Primária:** Chave de negócio natural da origem (`ID_<ENTIDADE>`).
- **Colunas:** Podem mesclar atributos descritivos e medidas numéricas que depois serão separadas entre Fato e Dimensões.
- **Tablespace:** Utilizar a tablespace designada do projeto (`<PROJETO>_DATA`).

---

## 3. Padrão da Camada `DIM_*` (Dimensão Oficial)

Toda dimensão corporativa possui a seguinte estrutura canônica:

### 3.1 Colunas Obrigatórias
```sql
DIMENSION_KEY     NUMBER(38,0) NOT NULL, -- Surrogate Key (PK)
ID_<ENTIDADE>     NUMBER(38,0) NOT NULL, -- Chave de Negócio / Natural Key
-- [Colunas de Atributos de Negócio]
DTC_EFETIVACAO    DATE,                  -- Início da validade da versão
DTC_EXPIRACAO     DATE,                  -- Fim da validade (NULL = versão vigente!)
DES_ATUALIZAR     CHAR(1)                -- Flag de controle técnico do ODI ('S'/'N')
```

### 3.2 Constraints e Índices Obrigatórios
1. **Primary Key:** `CONSTRAINT <NOME_TABELA>_PK PRIMARY KEY (DIMENSION_KEY)`.
2. **Índice e Unique Constraint de Histórico:**
   ```sql
   CREATE INDEX IDX_<ENTIDADE>_EFETIV ON <NOME_TABELA> (ID_<ENTIDADE>, DTC_EFETIVACAO);
   ALTER TABLE <NOME_TABELA> ADD CONSTRAINT <NOME_TABELA>_UNIQUE UNIQUE (ID_<ENTIDADE>, DTC_EFETIVACAO);
   ```

### 3.3 Registro Padrão Desconhecido (Linha `-1`)
Toda dimensão deve ter obrigatoriamente um registro inicial de chave `-1` para garantir que fatos com chaves nulas ou ainda não cadastradas não quebrem a integridade:
```sql
INSERT INTO DIM_<DOMINIO>_<ENTIDADE> (
    DIMENSION_KEY, ID_<ENTIDADE>, DTC_EFETIVACAO, DTC_EXPIRACAO, DES_ATUALIZAR, [DESCRICAO]
) VALUES (
    -1, -1, TO_DATE('1900-01-01', 'YYYY-MM-DD'), NULL, 'N', 'NÃO INFORMADO'
);
```

---

## 4. Padrão da Camada `ODI_DIM_*` (Auxiliar de Dimensão do ODI)

- **Clone Estrutural:** Possui exatamente as mesmas colunas da `DIM_*` correspondente.
- **Sem Constraints:** Não deve conter PK, FK, Unique ou índices, pois é truncada e recarregada pelo IKM do ODI durante o processamento de *Dimensões e Cubos*.

---

## 5. Padrão da Camada `FATO_*` (Fatos Analíticas)

### 5.1 Colunas Obrigatórias
```sql
DIM_<DOMINIO>_<ENTIDADE_1> NUMBER(38,0), -- FK para DIMENSION_KEY da Dimensão 1
DIM_<DOMINIO>_<ENTIDADE_2> NUMBER(38,0), -- FK para DIMENSION_KEY da Dimensão 2
DIM_TEMPO                  NUMBER(38,0), -- FK para DIM_TEMPO (DIMENSION_KEY)
QTD_<NOME_MEDIDA>          NUMBER(38,0), -- Medidas quantitativas (prefixo QTD_ ou VL_)
DTC_CARGA                  DATE          -- Timestamp de gravação da linha no DW
```

### 5.2 Primary Key Composta
- A PK da tabela Fato é sempre a combinação de **todas as chaves estrangeiras dimensionais**:
  ```sql
  CONSTRAINT FATO_<NOME>_PK PRIMARY KEY (DIM_ENTIDADE_1, DIM_ENTIDADE_2, DIM_TEMPO)
  ```

### 5.3 Foreign Keys
- Devem referenciar explicitamente a coluna `DIMENSION_KEY` de cada dimensão:
  ```sql
  ALTER TABLE FATO_<NOME> ADD CONSTRAINT FATO_<NOME>_DIM_<ENTIDADE>_FK
      FOREIGN KEY (DIM_<ENTIDADE>) REFERENCES DIM_<ENTIDADE> (DIMENSION_KEY);
  ```

---

## 6. Otimização Física de Performance (Oracle Tuning)

O Planejador não gera DDLs engessados. Ele aplica as seguintes regras de tuning:

### 6.1 Índices Bitmap vs. B-Tree
- **B-Tree:** Utilizado em PKs, chaves de negócio (`ID_*`) e colunas com alta cardinalidade.
- **Bitmap:** Utilizado em colunas com **baixa cardinalidade** para acelerar filtros em estrela:
  - Indicadores booleanos/flags (`SIN_ATIVO_*`, `HOUVE_*`, `DES_ATUALIZAR`).
  - Categorias discretas (`TIPO_USUARIO`, `FASE_ACAO`, `STATUS_*`).
  - Nas FKs de tabelas FATO com mais de 1 milhão de linhas (habilita *Star Transformation*).

### 6.2 Particionamento (Para Fatos Volumosas)
- Quando o volume projetado ultrapassar **5 milhões de linhas**:
  - Aplicar **Interval Partitioning por Mês/Ano** baseado na data do evento (`DIM_TEMPO` ou `DTC_CARGA`).
  - Permite ganho massivo de performance (*Partition Pruning*) e viabiliza *Partition Exchange* no ODI.

### 6.3 Documentação Obrigatória (Comments)
- Toda tabela gerada deve conter `COMMENT ON TABLE`.
- Toda coluna gerada deve conter `COMMENT ON COLUMN`, descrevendo se é chave substituta, chave de negócio, medida aditiva ou coluna de controle.
