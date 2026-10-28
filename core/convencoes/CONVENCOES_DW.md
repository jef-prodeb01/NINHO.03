# CONVENCOES_DW.md — Padrões e Convenções Corporativas de Data Warehouse

Este documento estabelece o **DNA corporativo** para arquitetura, modelagem dimensional e esteiras de dados no ecossistema analítico. O **Planejador de DW** segue essas convenções estritamente na geração de todos os scripts DDL, rotinas de carga, procedimentos de tuning e artefatos de integração.

---

## 1. Padrão de Nomenclatura das Tabelas e Objetos

| Camada / Objeto | Padrão de Nome | Exemplo Real | Papel no Pipeline |
| :--- | :--- | :--- | :--- |
| **Auditoria** | `TB_CONTROLE_CARGA` | `SDM_OLAP.TB_CONTROLE_CARGA` | Registra início, fim, status (`SUCESSO`/`FALHA`) e volumetria de cada job. |
| **Staging Area** | `STG_<SISTEMA>_<DOMINIO>_<NOME>` | `STG_SEI_BA_F_AND_PROC_3M`, `STG_COST_MANAGEMENT_API` | Aterrissagem inicial das fontes (Hop, Python ou ODI) sem transformações pesadas. |
| **Auxiliar ODI** | `ODI_DIM_<SISTEMA>_<DOMINIO>_<NOME>` | `ODI_DIM_SEI_BA_UNIDADE`, `ODI_DIM_COST_MGMT_PROJETO` | Tabela transitória espelho com flag `DES_STATUS_REGISTRO` ('I'/'U'/'D') para o IKM do ODI. |
| **Dimensão** | `DIM_<SISTEMA>_<DOMINIO>_<NOME>` | `DIM_SEI_BA_UNIDADE`, `DIM_COST_MGMT_PROJETO` | Dimensão oficial com Surrogate Key (`DIMENSION_KEY`), vigência SCD Tipo 2 e B-Tree. |
| **Dimensão Tempo** | `DIM_TEMPO` | `DIM_TEMPO` | Dimensão conformada de calendário (chave integer `YYYYMMDD` ou surrogate key). |
| **Fato** | `FATO_<SISTEMA>_<DOMINIO>_<NOME>` | `FATO_SEI_BA_ANDA_PROCES_3M`, `FATO_COST_MGMT_CUSTO` | Fato com grão físico explícito, FKs `NOT NULL` apontando para `-1` e medidas tipadas. |
| **Procedure Tuning** | `PRC_<ACAO>_<ALVO>` | `PRC_POS_CARGA_FATO` | Rotina PL/SQL para rebuild de índices `NOLOGGING` e atualização do `DBMS_STATS`. |
| **Sequences** | `SEQ_<TABELA>` | `SEQ_DIM_SEI_BA_ORGAO`, `SEQ_DIM_COST_MGMT_CLUSTER` | Gerador automático de Surrogate Keys para dimensões no Oracle. |

> **Regra de Caixas:** TODOS os identificadores de tabelas, colunas, constraints e índices devem ser gerados em **MAIÚSCULAS**.

### 1.1 Regra Inegociável de Fidelidade 100% aos Nomes de Coluna da Origem (Zero Alucinação)
- **Proibição de Renomeação Arbitrária:** A IA e o engenheiro **NUNCA** devem renomear, abreviar ou inventar colunas que já existem na fonte de dados (`ddl_origem.sql` ou `ddl_completo.csv`).
  - *Exemplo de Erro:* Mudar `ID_CHAMADO` para `NUM_CHAMADO`, ou trocar `INDICADOR` para `IND_STATUS`, ou inventar `DS_SUMARIO` quando a coluna original é `RESUMO`.
  - *Comportamento Correto:* O nome original deve ser mantido ipsis litteris em maiúsculas (ex: `ID_CHAMADO`, `INDICADOR`, `DT_FECHAMENTO`).
- **Colunas Técnicas Exclusivas do DW:** As únicas colunas com nomes padronizados pelo framework que não existem na origem são as colunas de controle dimensional Kimball:
  - **Dimensões (`DIM_<PROJETO>_<ENTIDADE>`):** A Surrogate Key chama-se **SEMPRE `DIMENSION_KEY`** (proibido usar `<ENTIDADE>_KEY` ou `SK_<ENTIDADE>`), acompanhada de `SIN_ATIVO`, `DTC_EFETIVACAO`, `DTC_EXPIRACAO`, `DES_ATUALIZAR`.
  - **Dimensão Tempo (`DIM_TEMPO`):** Obrigatória em todo schema de trabalho (mesmo quando a fato parece estática), seguindo a estrutura corporativa de 24 colunas (`DIMENSION_KEY`, `IDE_SK_TEMPO`, `DES_DATA_DIA`, `NUM_ANO`, ..., `DTC_COMPLETA`).
  - **Fatos (`FATO_<PROJETO>_<PROCESSO>`):** As Foreign Keys para dimensões chamam-se **SEMPRE `DIM_<PROJETO>_<ENTIDADE>`** (ex: `DIM_ELEICOES_PSD_BA_MUNICIPIO`, `DIM_ELEICOES_PSD_BA_CARGO_ELEICAO`), além da FK obrigatória `DIM_TEMPO` e métricas com prefixos padronizados (`QTD_*`, `VAL_*`, `TOT_*`). **PROIBIDO** incluir `DTC_CARGA` ou `DTC_CARGA_DW` na Fato (redundante com `TB_CONTROLE_CARGA`).
  - **Staging (`STG_<PROJETO>_<ENTIDADE>`):** `DTC_EXTRACAO`, `ID_LOTE`.
- **Matriz De/Para Obrigatória:** Antes de gerar qualquer DDL, o agente deve apresentar no comando `/gerar-blueprint` a tabela completa De/Para mapeando 100% das colunas de origem para as tabelas de destino para validação do engenheiro.

### 1.2 Disciplina Estrita de Pastas de Saída (Sem Pastas com Nome do Projeto)
- **Estrutura Canônica Direta:** Todos os scripts e artefatos DEVEM ser gerados diretamente dentro das 11 pastas numeradas em `saida/planejador_dw/`:
  - `01_controle_carga/`
  - `02_staging/`
  - `03_dimensoes/`
  - `04_fatos/`
  - `05_procedimentos_manutencao/`
  - `06_pipelines_hop/` (se aplicável)
  - `07_extratores_python/` (se aplicável)
  - `08_datasets_bi/`
  - `09_relatorio_estrategias/`
  - `10_testes_integridade/`
  - `11_dicionario_dados/`
- **PROIBIDO Criar Subpastas de Projeto:** É expressamente proibido criar pastas como `saida/planejador_dw/<NOME_PROJETO>/`. Isso gera duplicação e quebra os scripts automáticos do pipeline de transição e validação.

### 1.3 Geração Condicional Estrita de Tecnologias (Apenas o Solicitado)
- **Gatilho de Geração:** O agente SOMENTE pode gerar código e scripts para as tecnologias marcadas com `[x]` na Seção 1 do [`INTAKE_DW.md`](../../modulos/planejador_dw/INTAKE_DW.md).
  - Se **Apache Hop** NÃO estiver marcado: a pasta `06_pipelines_hop/` permanece limpa (apenas com `.gitkeep`).
  - Se **Python (API)** NÃO estiver marcado: a pasta `07_extratores_python/` permanece limpa (apenas com `.gitkeep`).
  - Se o projeto for **100% Banco (ODI / PL/SQL)**: gerar estritamente DDLs, Procedures e Datasets de BI, sem inventar scripts Hop ou Python.


---

## 2. Padrão da Camada `STG_*` (Staging de Ingestão)

- **Objetivo:** Receber dados brutos da fonte com tipagem básica e mínima intervenção.
- **Chave Primária:** Chave natural de negócio da origem (`ID_<ENTIDADE>` ou UUID).
- **Metadados de Carga Obrigatórios:**
  - `DTC_EXTRACAO DATE DEFAULT SYSDATE`: Momento exato em que a linha aterrissou na staging.
  - `ID_LOTE NUMBER`: Identificador do lote para rastreabilidade de cargas em micro-lotes.
- **Tablespace:** Utilizar a tablespace de dados do projeto (`<PROJETO>_DATA`).

---

## 3. Padrão da Camada `DIM_*` (Dimensão Oficial com SCD Tipo 2)

Toda dimensão corporativa com histórico de alterações deve conter a seguinte estrutura canônica:

### 3.1 Colunas Obrigatórias
```sql
CREATE TABLE "<SCHEMA>"."DIM_<NOME>" (
    "DIMENSION_KEY"    NUMBER(38,0) NOT NULL,   -- Surrogate Key (PK via Sequence)
    "ID_<ENTIDADE>"    NUMBER(38,0) NOT NULL,   -- Chave de Negócio / Natural Key
    -- [Atributos descritivos de negócio...]
    "SIN_ATIVO"        CHAR(1 CHAR) DEFAULT 'S' NOT NULL, -- 'S' / 'N'
    "DTC_EFETIVACAO"   DATE NOT NULL,           -- Início da vigência do registro
    "DTC_EXPIRACAO"    DATE,                    -- NULL ou 2999-12-31 = Versão Vigente
    "DES_ATUALIZAR"    CHAR(1 CHAR) DEFAULT 'S' NOT NULL, -- Flag técnica para CDC ('S'/'N')
    CONSTRAINT "PK_DIM_<NOME>" PRIMARY KEY ("DIMENSION_KEY")
);
```

### 3.2 Regra de Ouro: Índices B-TREE em Dimensões
- **PROIBIDO usar índices Bitmap em tabelas Dimensão:** Como dimensões sofrem atualizações incrementais contínuas de expiração (`UPDATE DTC_EXPIRACAO = SYSDATE`) e inserção de novas versões, índices Bitmap causariam bloqueios de blocos inteiros no Oracle, gerando deadlocks severos (**`ORA-00060: deadlock detected`**).
- **Foco dos Índices B-Tree:**
  1. `PK_DIM_<NOME>` em `DIMENSION_KEY` (Unique B-Tree).
  2. `IDX_<NOME>_LOOKUP` em `(ID_<ENTIDADE>, DTC_EFETIVACAO)` para acelerar lookups do SCD2 no ETL.
  3. Campos descritivos de alta seletividade frequentemente filtrados no BI (`SIGLA`, `LOGIN`, `CODIGO`).

### 3.3 Registro Padrão Desconhecido (Linha `-1`)
Toda dimensão deve possuir obrigatoriamente um registro inicial fixo carregado via DML:
```sql
INSERT INTO "<SCHEMA>"."DIM_<NOME>" (
    "DIMENSION_KEY", "ID_<ENTIDADE>", "SIN_ATIVO", 
    "DTC_EFETIVACAO", "DTC_EXPIRACAO", "DES_ATUALIZAR", [ATRIBUTO_TEXTUAL]
) VALUES (
    -1, -1, 'N', 
    TO_DATE('1900-01-01', 'YYYY-MM-DD'), NULL, 'N', 'NAO INFORMADO'
);
```

### 3.4 Pureza Estrita das Tabelas Fato (`FATO_*` = Apenas Chaves de Dimensão + Métricas)
As tabelas Fato (`FATO_*` / `FAT_*`) representam medições quantitativas na interseção das dimensões e **obrigatoriamente** devem conter **APENAS**:
1. **Chaves das Dimensões (`FKs` / `SKs` / `DIMENSION_KEY`):** Colunas numéricas inteiras (`DIM_<ENTIDADE> NUMBER(38,0) NOT NULL`, `DIM_TEMPO NUMBER(38,0) NOT NULL`, `SK_*` ou `DIMENSION_KEY`) que referenciam `DIM_*.DIMENSION_KEY` (com fallback `-1` para ausências).
2. **Métricas Numéricas:** Colunas quantitativas (`NUMBER`) com prefixos de métrica (`VAL_*`, `VLR_*`, `QTD_*`, `QT_*`, `PCT_*`, `PER_*`, `MED_*`, `TOT_*`, `SOM_*`, `IND_*`, `DUR_*`, `DIAS_*`).

> 🛑 **PROIBIÇÃO DE TEXTO E ATRIBUTOS DESCRITIVOS NAS FATOS:**
> - **NUNCA** inclua colunas de texto (`VARCHAR2`, `CHAR`, `CLOB`, `NVARCHAR2`) ou datas brutas (`DATE`, `TIMESTAMP`) nas tabelas `FATO_*`.
> - Todo atributo textual, código descritivo (`DES_*`, `NOM_*`, `SIG_*`, `COD_*` alfanumérico, status, categoria) é responsabilidade exclusiva das **Dimensões (`DIM_*`)**, e toda data de evento deve ser convertida em chave inteira para a **`DIM_TEMPO`** (`NUMBER(38,0) NOT NULL` no formato `YYYYMMDD`).
> - Esta regra se aplica de forma unificada à Demonstração (`/demo`), ao Modo Simulador (`/simular-dw`) e à Execução Direta (`/executar-dw`).

### 3.5 Definição Canônica Obrigatória da `DIM_TEMPO` Corporativa
Sempre haverá uma `DIM_TEMPO` no schema de trabalho, mesmo quando os dados do projeto parecerem estáticos ou anuais. Sua estrutura física padrão é:
```sql
CREATE TABLE "<SCHEMA>"."DIM_TEMPO" (
    "DIMENSION_KEY"        NUMBER NOT NULL ENABLE,
    "IDE_SK_TEMPO"         NUMBER,
    "DES_DATA_DIA"         VARCHAR2(25),
    "NUM_ANO"              NUMBER(4,0),
    "NUM_MES"              NUMBER(3,0),
    "NUM_DIA"              NUMBER(3,0),
    "NUM_QUADRIMESTRE"     NUMBER(3,0),
    "NUM_TRIMESTRE"        NUMBER(2,0),
    "DES_QUINZENA"         VARCHAR2(12),
    "DES_QUADRIMESTRE"     VARCHAR2(12),
    "NUM_BIMESTRE"         NUMBER(3,0),
    "DES_BIMESTRE"         VARCHAR2(12),
    "DES_ANO_MES"          VARCHAR2(8),
    "DES_MES_ANO"          VARCHAR2(8),
    "DES_DIA"              VARCHAR2(7),
    "NUM_SEMESTRE"         NUMBER(3,0),
    "DES_MES_ANO_NUMERICO" VARCHAR2(7),
    "DES_TRIMESTRE"        VARCHAR2(12),
    "IND_FINAL_SEMANA"     CHAR(1),
    "DES_MES"              VARCHAR2(15),
    "NUM_QUINZENA"         NUMBER(3,0),
    "DES_MES_ANO_COMPLETO" VARCHAR2(30),
    "DES_SEMESTRE"         VARCHAR2(12),
    "DTC_COMPLETA"         DATE,
    CONSTRAINT "DIM_TEMPO_UK" UNIQUE ("NUM_ANO", "NUM_MES", "NUM_DIA")
        USING INDEX TABLESPACE "<TABLESPACE_IDX>" ENABLE,
    CONSTRAINT "DIM_TEMPO_PK" PRIMARY KEY ("DIMENSION_KEY")
        USING INDEX TABLESPACE "<TABLESPACE_IDX>" ENABLE
) TABLESPACE "<TABLESPACE_DATA>";

CREATE INDEX "<SCHEMA>"."IDX_DIM_TEMPO_ANO_MES" ON "<SCHEMA>"."DIM_TEMPO" ("NUM_ANO", "NUM_MES") TABLESPACE "<TABLESPACE_IDX>";
CREATE INDEX "<SCHEMA>"."IDX_DIM_TEMPO_DTC" ON "<SCHEMA>"."DIM_TEMPO" ("DTC_COMPLETA") TABLESPACE "<TABLESPACE_IDX>";
```

---

## 4. Padrão da Camada `ODI_DIM_*` (Auxiliar de Dimensão do ODI)

- **Clone Estrutural:** Possui exatamente as mesmas colunas da `DIM_*` correspondente.
- **Coluna Adicional de CDC:** `DES_STATUS_REGISTRO CHAR(1 CHAR)`:
  - `'I'` (Insert): Novo registro identificado na origem.
  - `'U'` (Update): Atributo rastreado alterou; gera expiração da versão anterior e inserção da nova versão.
  - `'D'` (Delete): Registro inativado na origem.
- **Sem Constraints:** Não deve conter PK, FK ou índices restritivos, pois é truncada e recarregada pelo IKM do ODI durante o processamento.

---

## 5. Padrão da Camada `FATO_*` (Fatos Analíticas)

### 5.1 Colunas Obrigatórias (Sem `DTC_CARGA` / `DTC_CARGA_DW`)
```sql
DIM_<DOMINIO>_<ENTIDADE_1> NUMBER(38,0) NOT NULL, -- FK para DIMENSION_KEY da Dimensão 1
DIM_<DOMINIO>_<ENTIDADE_2> NUMBER(38,0) NOT NULL, -- FK para DIMENSION_KEY da Dimensão 2
DIM_TEMPO                  NUMBER(38,0) NOT NULL, -- FK obrigatória para DIM_TEMPO (DIMENSION_KEY)
-- [Medidas quantitativas com prefixos padronizados...]
-- PROIBIDO incluir DTC_CARGA ou DTC_CARGA_DW na Fato (já existe TB_CONTROLE_CARGA)
```

> ⚠️ **Nenhuma Foreign Key na Fato pode ser nula (`NOT NULL ENABLE`):** Quando a origem trouxer valor nulo ou desconhecido, o mapeamento ETL deve converter obrigatoriamente para `-1` via expressão `NVL(LOOKUP.DIMENSION_KEY, -1)`.

### 5.2 Taxonomia e Prefixos de Métricas
* `TOT_` ou `QTD_`: Contagens absolutas e volumetrias aditivas (ex: `QTD_PROCESSOS_GERADOS`, `QTD_CPU_USO_CORE_HOURS`, `QTD_PVC`).
* `VAL_` ou `SOM_`: Valores monetários em R$ e somas financeiras (ex: `VAL_CUSTO_TOTAL`, `VAL_CUSTO_PLATAFORMA_DIST`).
* `MED_`: Médias estatísticas pré-agregadas (ex: `MED_DIAS_TRAMITACAO`, `MED_CONSUMO_RAM_GIB`).
* `IND_` ou `PCT_`: Indicadores percentuais e taxas (ex: `IND_PERM_ATIVA`, `PCT_EFICIENCIA_CPU`).
* `DUR_` ou `DIAS_`: Durações temporais e SLAs (ex: `DIAS_PERMANENCIA_ATIVIDADE`).

---

## 6. Seleção da Estratégia de Carga da Fato (Dual Strategy)

O Planejador de DW suporta duas estratégias distintas com base na volumetria e perfil da fonte:

### Estratégia A: Truncate & Load Massivo (Padrão SEI Bahia)
* **Cenário:** Grandes janelas históricas (ex: últimos 3 meses ou ano fechado) recarregadas periodicamente em lote a partir de bancos OLTP sem DML concorrente.
* **Indexação Física:**
  * **BITMAP INDEX** em todas as colunas de FK (`DIM_...`) e flags de baixa cardinalidade.
  * Habilita o plano **Star Transformation** do otimizador CBO no Oracle.
  * PK da fato utiliza B-Tree.
* **Manutenção Obrigatória:** Uso da procedure `PRC_POS_CARGA_FATO` para executar rebuild `NOLOGGING` e atualizar `DBMS_STATS(CASCADE => TRUE)`.

### Estratégia B: Carga Incremental Idempotente via `MERGE INTO` (Padrão FinOps / COAPS)
* **Cenário:** Cargas contínuas intra-dia ou diárias de APIs e telemetria (ex: últimos 10 dias) onde novos dados e atualizações convivem sem truncar o histórico.
* **Lógica SQL:**
  ```sql
  MERGE INTO "<SCHEMA>"."FATO_<NOME>" f
  USING (SELECT ...) src
  ON (f.DIM_ENTIDADE_1 = src.DIM_ENTIDADE_1 AND f.DIM_TEMPO = src.DIM_TEMPO)
  WHEN MATCHED THEN UPDATE SET f.VAL_TOTAL = src.VAL_TOTAL, f.DTC_ATUALIZACAO = SYSDATE
  WHEN NOT MATCHED THEN INSERT (...) VALUES (...);
  ```
* **Indexação Física:**
  * **B-TREE INDEX** normal e índices compostos nas chaves de busca do `ON (...)`.
  * Índices Bitmap são estritamente evitados aqui para prevenir contenção de locks durante o `MERGE`.

### 6.1 Gestão de Tablespaces (Data vs Index) e Prevenção de Estouro de Storage
- **Segregação Física Ideal:** Sempre que o DBA disponibilizar tablespaces separadas:
  - Tabelas (`STG_*`, `DIM_*`, `FATO_*`) na tablespace de dados: `TABLESPACE "<SCHEMA>_DATA"`.
  - Índices (`PK_*`, `IDX_*`, `BMI_*`) na tablespace de índices: `TABLESPACE "<SCHEMA>_INDEX"`.
  - Benefício: Evita que o crescimento de índices afete a inserção de novos dados em caso de esgotamento.
- **Cenário de Tablespace Única Compartilhada:** Se o ambiente possuir apenas uma tablespace (ex: `SEIMUNICIPIO_DATA`), dados e índices competem pela mesma cota.
  - O engenheiro deve evitar a criação indiscriminada de índices secundários.
  - Limitar índices de dimensões apenas à PK (`DIMENSION_KEY`) e ao índice de lookup (`ID_<ENTIDADE>, DTC_EFETIVACAO`).
- **Sizing de Índices Bitmap vs B-Tree:**
  - Em fatos com milhões de linhas, um **BITMAP INDEX** em coluna de baixa cardinalidade (ex: 2 a 50 valores distintos) ocupa até **90% menos espaço** que um B-Tree equivalente e acelera drasticamente queries analíticas via Star Transformation.
  - **Alerta de Perigo:** NUNCA crie índice Bitmap em colunas de alta cardinalidade (ex: chaves primárias, UUIDs, carimbos de data/hora milissegundos). Isso causará explosão catastrófica do tamanho do índice e estouro da tablespace.
- **Operações com Cláusula `NOLOGGING`:**
  - Na criação e no rebuild de índices, utilize sempre `NOLOGGING` para evitar a geração massiva de redo log e não sobrecarregar as tablespaces de Undo/Redo do Oracle:
    ```sql
    ALTER INDEX "<SCHEMA>"."<NOME_INDICE>" REBUILD NOLOGGING;
    ALTER INDEX "<SCHEMA>"."<NOME_INDICE>" LOGGING; -- Restaurar logging após rebuild
    ```
- **Query Útil para Diagnóstico de Uso de Tablespace por Tipo de Objeto:**
  ```sql
  SELECT 
      tablespace_name,
      segment_type,
      COUNT(*) AS qtd_objetos,
      ROUND(SUM(bytes) / 1024 / 1024, 2) AS ocupado_mb,
      ROUND(SUM(bytes) / 1024 / 1024 / 1024, 2) AS ocupado_gb
  FROM user_segments
  GROUP BY tablespace_name, segment_type
  ORDER BY ocupado_mb DESC;
  ```


---

## 7. Procedimentos Automatizados de Pré e Pós-Carga (`PRC_PRE_CARGA_FATO` e `PRC_POS_CARGA_FATO`)

Toda fato carregada via *Truncate & Load* (Estratégia A) deve utilizar o par de procedures corporativas em `07_prc_pos_carga_fato.sql`:
```sql
CREATE OR REPLACE PROCEDURE "<SCHEMA>"."PRC_PRE_CARGA_FATO" (
    p_tabela_fato IN VARCHAR2,
    p_owner       IN VARCHAR2 DEFAULT '<SCHEMA>'
) AUTHID CURRENT_USER IS
    v_sql VARCHAR2(1000);
BEGIN
    -- Desativa índices secundários não-únicos antes do Direct-Path Insert (/*+ APPEND PARALLEL(4) */)
    FOR r IN (
        SELECT owner, index_name
        FROM all_indexes
        WHERE owner = UPPER(TRIM(p_owner))
          AND table_name = UPPER(TRIM(p_tabela_fato))
          AND uniqueness = 'NONUNIQUE'
          AND status = 'VALID'
    ) LOOP
        v_sql := 'ALTER INDEX "' || r.owner || '"."' || r.index_name || '" UNUSABLE';
        EXECUTE IMMEDIATE v_sql;
    END LOOP;
END;
/

CREATE OR REPLACE PROCEDURE "<SCHEMA>"."PRC_POS_CARGA_FATO" (
    p_tabela_fato IN VARCHAR2,
    p_owner       IN VARCHAR2 DEFAULT '<SCHEMA>'
) AUTHID CURRENT_USER IS
    v_sql VARCHAR2(1000);
BEGIN
    -- 1. Rebuild PARALLEL 4 NOLOGGING de índices UNUSABLE ou BITMAP da fato + reset NOPARALLEL LOGGING
    FOR r IN (
        SELECT owner, index_name, status, index_type
        FROM all_indexes
        WHERE owner = UPPER(TRIM(p_owner))
          AND table_name = UPPER(TRIM(p_tabela_fato))
          AND (status = 'UNUSABLE' OR index_type LIKE '%BITMAP%')
    ) LOOP
        BEGIN
            v_sql := 'ALTER INDEX "' || r.owner || '"."' || r.index_name || '" REBUILD PARALLEL 4 NOLOGGING';
            EXECUTE IMMEDIATE v_sql;
            v_sql := 'ALTER INDEX "' || r.owner || '"."' || r.index_name || '" NOPARALLEL LOGGING';
            EXECUTE IMMEDIATE v_sql;
        EXCEPTION
            WHEN OTHERS THEN
                DBMS_OUTPUT.PUT_LINE('Erro ao reconstruir indice ' || r.index_name || ': ' || SQLERRM);
        END;
    END LOOP;

    -- 2. Coleta de Estatísticas completas com CASCADE e grau 4
    DBMS_STATS.GATHER_TABLE_STATS(
        ownname          => UPPER(TRIM(p_owner)),
        tabname          => UPPER(TRIM(p_tabela_fato)),
        estimate_percent => DBMS_STATS.AUTO_SAMPLE_SIZE,
        method_opt       => 'FOR ALL COLUMNS SIZE AUTO',
        degree           => 4,
        cascade          => TRUE,
        no_invalidate    => FALSE
    );
END;
/
```

---

## 8. Esteira de Ingestão Híbrida & Orquestração

### 8.1 Ingestão por Tipo de Fonte
1. **Bancos Relacionais (OLTP):** Mapeamentos diretos via **ODI 12c** (LKM SQL to Oracle / LKM Oracle to Oracle).
2. **Arquivos / Planilhas (CSV, Excel, SFTP):** Pipelines declarativos no **Apache Hop** (`.hpl` / `.hwf`) gravando na Staging via `Insert / update`.
3. **APIs REST e Serviços Externos:** Scripts modulares em **Python** com:
   * Autenticação OAuth2 (Bearer Token com auto-refresh).
   * Paginação resiliente com backoff exponencial para erros 429/503.
   * `flatten.py` para transformar JSON hierárquico em visão tabular plana.
   * Enriquecimento por regex para derivar órgãos/unidades (`REGEXP_SUBSTR`).

### 8.2 Orquestração Centralizada no ODI
O ODI é o maestro corporativo. Quando uma carga depende de scripts Python ou Apache Hop, o pacote do ODI dispara a execução remota através do componente **`OdiOSCommand`** (via SSH com chave assimétrica):
```bash
ssh -i /home/oracle/.ssh/id_rsa user_hop@servidor-hop "/opt/apache-hop/hop-run.sh -r local -j <PROJETO> -f /opt/hop/pipelines/<CARGA>.hpl"
```

---

## 9. Camada Semântica & Consumo Analítico (Power BI)

### 9.1 Padrão Power BI
- **Modo de Conexão:** **Import Mode (Importação)** para a memória VertiPaq.
- **Topologia:** **Modelo Estrela (Star Schema)** puro.
- **Relacionamentos:**
  - Cardinalidade: **1 para Muitos (1:*)** das Dimensões para a Fato.
  - Direção do Filtro Cruzado: **Única (Single)**.
- **Dimensão Calendário (`DIM_TEMPO`):** Marcada como *Tabela de Data* oficial (`DTC_COMPLETA`).
- **Medidas DAX:** Tabela dedicada `_Medidas`, organizadas por pastas de exibição com cálculo explícito e tratamento de divisão por zero (`DIVIDE`).

---

## 10. Arquitetura Lakehouse com MongoDB (Transição Cloud / AWS)

Para cenários onde os dados processados transitam para um Lakehouse documental antes da publicação na AWS (AWS Glue e **Amazon SageMaker Unified Studio / SageMaker Catalog — substituto do antigo AWS DataZone**):
- **Estratégia de Multi-Tenancy Governamental:**
  - Segregação por Banco de Dados: `lakehouse_<orgao>` (ex: `lakehouse_sec`, `lakehouse_saeb`, `lakehouse_prodeb`).
  - Coleções Particionadas por Domínio: `<dominio>_<evento>` (ex: `sei_andamentos`, `finops_custos_diarios`).
- **Padrão de Documento:** Cada documento armazena o evento em JSON flat com metadados de governança obrigatórios (`orgao`, `unidade_origem`, `extraido_em`, `batch_id`, `schema_version`) facilitando o catálogo automático pelo AWS Glue Crawler e a publicação no Amazon SageMaker Catalog.

---

## 11. Arquitetura Multi-Tenant, CDC por Ciclo de Vida e Tuning Preditivo (ODI / Banco)

### 11.1 Prevenção de Colisão de Chaves em Ambientes Multi-Tenant (`ORA-00001`)
- Em schemas compartilhados por múltiplos órgãos ou prefeituras (tenants), identificadores transacionais (`ID_USUARIO`, `ID_UNIDADE`, `ID_PROTOCOLO`) colidem entre bases.
- **Proibição de UK Simples:** NUNCA crie constraint `UNIQUE` apenas sobre a chave natural. Compô-la obrigatoriamente com a coluna identificadora do tenant e expiração:
  ```sql
  ALTER TABLE "<SCHEMA>"."DIM_USUARIO"
    ADD CONSTRAINT "UK_DIM_USUARIO" UNIQUE ("ID_USUARIO", "COD_TENANT", "DTC_EXPIRACAO");
  ```
- **Composição de Chave Natural no ETL:** Quando necessário desambiguar antes da geração da Surrogate Key:
  `TO_NUMBER(TO_CHAR(V_TENANT) || '000' || TO_CHAR(ORIGEM.ID_NATURAL))`

### 11.2 Estratégia de CDC quando a Origem NÃO possui `UPDATED_AT` (Delta por Ciclo de Vida)
- Tabelas transacionais de sistemas legados ou governamentais (ex: `atividade` no SEI com `dth_abertura` e `dth_conclusao`) frequentemente não possuem coluna de auditoria `updated_at`.
- **Filtro Composto de Eventos de Negócio:** Capturar tanto registros abertos recentemente quanto registros antigos concluídos na janela incremental (`#V_DATA_CORTE`):
  ```sql
  WHERE (A.DTH_ABERTURA >= :V_DATA_CORTE OR A.DTH_CONCLUSAO >= :V_DATA_CORTE)
  ```
- **Snapshot de Pendências + Fechamentos Recentes (Fato de Tramitação):**
  ```sql
  WHERE A.DTH_CONCLUSAO IS NULL            -- Permanece aberto/em andamento
     OR A.DTH_CONCLUSAO >= :V_DATA_CORTE   -- Concluído na janela recente
  ```
- **High-Watermark Centralizado (`ODI_SCHEMA_CTRL`):** Persistir a última data/ID processado por tabela e tenant na tabela de controle de carga para suportar retomada automática após falhas.

### 11.3 Estratégia Híbrida de Carga na Fato (Hot Window vs. Histórico Consolidado)
- Quando a tabela de origem possui dezenas de milhões de linhas e índices `BITMAP` na Fato:
  - **Carga Diária (Intra-Mês):** Executar `DELETE` seletivo na janela móvel ativa (ex: últimos 5 a 15 dias) ou partição vigente + `INSERT /*+ APPEND */`, seguido de rebuild `NOLOGGING` apenas dos índices afetados.
  - **Carga de Fechamento (Mensal/Fim de Semana):** Recarregar a janela histórica maior (ex: 3 meses) via *Truncate Partition* ou *Truncate & Load* para consolidar eventuais reaberturas retroativas.

### 11.4 Tuning Preditivo de Mappings ODI (`IKM Oracle Incremental Update`)
- **PK Obrigatória na Staging:** Toda tabela `STG_*` usada como fonte de um `MERGE` ou `IKM Incremental Update` DEVE ter `PRIMARY KEY` (ou índice único) declarada nas colunas da chave de negócio. Sem isso, o join entre a tabela de integração `I$_` e o destino degrada para *Full Table Scan* em loop.
- **Substituição de `IKM SQL Control Append` Lento:** Em tabelas volumosas, substituir updates linha-a-linha por `IKM Oracle Merge` com hint `/*+ APPEND PARALLEL(4) */` e `COMMIT` ao final do lote.

