# Estratégia de Indexação e Tuning de Performance no Oracle DW

Este documento consolida as diretrizes técnicas corporativas de indexação para Data Warehouse no Oracle Database, extraídas de cenários reais de alta volumetria (PRODBA, SEI Bahia e UNEBi).

---

## 🎯 1. Princípio Fundamental de Separação: Fatos vs. Dimensões

| Objeto | Tipo de Índice Recomendado | Motivo Arquitetural |
| :--- | :--- | :--- |
| **Tabelas Fato** *(Carga Batch / Truncate & Load)* | **BITMAP INDEX** nas FKs (`DIM_*`) e Flags analíticas; **B-TREE** na PK e códigos únicos. | Permite Star Transformation no otimizador Oracle, combinando filtros com baixo consumo de memória. Cargas em lote não sofrem contenção. |
| **Tabelas Dimensão** *(Carga Incremental SCD Tipo 2)* | **ESTRITAMENTE B-TREE (NORMAL)**. | **NUNCA use Bitmap em Dimensões SCD2.** Updates na data de expiração (`DTC_EXPIRACAO`) e inserts de nova versão causam bloqueio de blocos inteiros, gerando deadlocks (`ORA-00060`). |

---

## ⚡ 2. Padrão de Execução Paralela e Criação Online

Para criar índices em ambientes de produção com grandes volumes sem degradar o sistema ou deixar o paralelismo preso:

```sql
-- 1. Criação acelerada em paralelo e sem bloquear DMLs concorrentes:
CREATE INDEX "SCHEMA_OLAP"."IDX_FATO_EVENTO_DTC" 
ON "SCHEMA_OLAP"."FATO_EVENTO" ("DTC_EVENTO") 
TABLESPACE "SCHEMA_DATA" PARALLEL 4 ONLINE;

-- 2. RESET OBRIGATÓRIO de paralelismo:
ALTER INDEX "SCHEMA_OLAP"."IDX_FATO_EVENTO_DTC" NOPARALLEL;
```

> [!WARNING]
> Se o comando `ALTER INDEX ... NOPARALLEL;` for omitido, o índice herdará o grau de paralelismo 4 permanentemente, fazendo com que até consultas simples de dashboards aloquem múltiplos processos no Oracle, esgotando o pool de recursos (`parallel_max_servers`).

---

## 🗜️ 3. Compressão de Prefixos de Índices Compostos (`COMPRESS 1`)

Em índices compostos onde a primeira coluna tem baixa cardinalidade (muitas repetições) e a segunda é seletiva (ex: data):

```sql
CREATE INDEX "SCHEMA_OLAP"."IDX_FATO_ORGAO_DATA" 
ON "SCHEMA_OLAP"."FATO_ATENDIMENTO" ("DIM_ORGAO", "DTC_CRIACAO") 
TABLESPACE "SCHEMA_DATA" COMPRESS 1 PARALLEL 4 ONLINE;

ALTER INDEX "SCHEMA_OLAP"."IDX_FATO_ORGAO_DATA" NOPARALLEL;
```
- O modificador `COMPRESS 1` elimina a duplicação do valor de `DIM_ORGAO` nos nós folha da árvore B-Tree, reduzindo o tamanho físico do índice em até 40% a 60% e acelerando o cache do Oracle.

---

## 🔍 4. Índices Críticos em Dimensões SCD Tipo 2

Nas dimensões SCD Tipo 2, os seguintes índices B-Tree devem ser sempre criados:

1. **Chave Primária Surrogate (`SK_*`):** Índice Único B-Tree.
2. **Lookup de Carga Incremental do ETL:**
   ```sql
   CREATE INDEX "SCHEMA_OLAP"."IDX_DIM_CLIENTE_SCD2" 
   ON "SCHEMA_OLAP"."DIM_CLIENTE" ("COD_NATURAL", "FLG_VIGENTE") 
   TABLESPACE "SCHEMA_DATA" COMPRESS 1;
   ```
3. **Campos de Busca Frequente no BI:** Sigla, Nome, Código Natural e Descrição da Categoria.

---

## 📊 5. Coleta de Estatísticas Pós-Criação de Índices

Sempre finalize a esteira de indexação garantindo que as estatísticas do otimizador de custos (CBO) estejam atualizadas:

```sql
EXEC DBMS_STATS.GATHER_TABLE_STATS(ownname => 'SCHEMA_OLAP', tabname => 'FATO_ATENDIMENTO', cascade => TRUE, estimate_percent => DBMS_STATS.AUTO_SAMPLE_SIZE);
```

---

## ⚡ 6. Ciclo de Carga em Fatos: Procedimentos Pré e Pós-Carga

Em esteiras de carga massiva (Truncate & Load ou Carga Batch com `INSERT /*+ APPEND PARALLEL(4) */`), manter índices secundários (Bitmap ou B-Tree) ativos durante a inserção causa degradação extrema de desempenho por contenção de I/O e geração massiva de redo.

### 6.1 Arquitetura do Ciclo
1. **Pré-Carga (`PRC_PRE_CARGA_FATOS`):** Desativa todos os índices secundários (`uniqueness = 'NONUNIQUE'`) colocando-os em estado `UNUSABLE`. **Mantém a Primary Key / Unique ativa** para garantir a integridade do grão.
2. **Carga Massiva (ETL/ELT):** Executa `INSERT /*+ APPEND */` em alta velocidade (Direct-Path Write).
3. **Pós-Carga (`PRC_POS_CARGA_FATOS`):** Reconstrói os índices em paralelo (`REBUILD PARALLEL 4 NOLOGGING`), redefine imediatamente para `NOPARALLEL LOGGING` e dispara coleta de estatísticas (`DBMS_STATS.GATHER_TABLE_STATS`).

### 6.2 Stored Procedure de Pré-Carga (`PRC_PRE_CARGA_FATOS`)

```sql
CREATE OR REPLACE PROCEDURE "SCHEMA_OLAP"."PRC_PRE_CARGA_FATOS" (
  p_tabela_alvo IN VARCHAR2 DEFAULT NULL
) 
AUTHID CURRENT_USER
IS
  v_owner VARCHAR2(30) := 'SCHEMA_OLAP';
  v_sql   VARCHAR2(1000);
  v_count NUMBER := 0;
BEGIN
  DBMS_OUTPUT.PUT_LINE('>> [PRC_PRE_CARGA_FATOS] Iniciando desativação de índices secundários...');

  FOR r IN (
    SELECT i.owner, i.table_name, i.index_name
    FROM all_indexes i
    WHERE i.owner = v_owner
      AND (p_tabela_alvo IS NULL OR i.table_name = UPPER(TRIM(p_tabela_alvo)))
      -- Mantém PK e índices de unicidade ativos para garantir a integridade do grão
      AND i.uniqueness = 'NONUNIQUE'
      AND i.status = 'VALID'
    ORDER BY i.table_name, i.index_name
  ) LOOP
    BEGIN
      v_sql := 'ALTER INDEX "' || r.owner || '"."' || r.index_name || '" UNUSABLE';
      EXECUTE IMMEDIATE v_sql;
      v_count := v_count + 1;
    EXCEPTION
      WHEN OTHERS THEN
        DBMS_OUTPUT.PUT_LINE('>> ERRO ao desativar índice ' || r.index_name || ': ' || SQLERRM);
    END;
  END LOOP;

  DBMS_OUTPUT.PUT_LINE('>> [PRC_PRE_CARGA_FATOS] Concluído. Total de índices desativados: ' || v_count);
END PRC_PRE_CARGA_FATOS;
/
```

### 6.3 Stored Procedure de Pós-Carga (`PRC_POS_CARGA_FATOS`)

```sql
CREATE OR REPLACE PROCEDURE "SCHEMA_OLAP"."PRC_POS_CARGA_FATOS" (
  p_tabela_alvo IN VARCHAR2 DEFAULT NULL,
  p_parallel    IN NUMBER   DEFAULT 4
)
AUTHID CURRENT_USER
IS
  v_owner VARCHAR2(30) := 'SCHEMA_OLAP';
  v_sql   VARCHAR2(1000);
  v_count NUMBER := 0;
BEGIN
  DBMS_OUTPUT.PUT_LINE('>> [PRC_POS_CARGA_FATOS] Iniciando REBUILD de índices UNUSABLE...');

  -- 1. Rebuild acelerado em paralelo com NOLOGGING
  FOR r IN (
    SELECT i.owner, i.table_name, i.index_name
    FROM all_indexes i
    WHERE i.owner = v_owner
      AND (p_tabela_alvo IS NULL OR i.table_name = UPPER(TRIM(p_tabela_alvo)))
      AND i.status = 'UNUSABLE'
    ORDER BY i.table_name, i.index_name
  ) LOOP
    BEGIN
      v_sql := 'ALTER INDEX "' || r.owner || '"."' || r.index_name || '" REBUILD PARALLEL ' || p_parallel || ' NOLOGGING';
      EXECUTE IMMEDIATE v_sql;

      -- RESET OBRIGATÓRIO: impede que dashboards executem em paralelo e restaura logging
      v_sql := 'ALTER INDEX "' || r.owner || '"."' || r.index_name || '" NOPARALLEL LOGGING';
      EXECUTE IMMEDIATE v_sql;

      v_count := v_count + 1;
    EXCEPTION
      WHEN OTHERS THEN
        DBMS_OUTPUT.PUT_LINE('>> ERRO no REBUILD de ' || r.index_name || ': ' || SQLERRM);
    END;
  END LOOP;

  DBMS_OUTPUT.PUT_LINE('>> [PRC_POS_CARGA_FATOS] Rebuild concluído. Total: ' || v_count);

  -- 2. Atualização imediata de estatísticas do CBO
  DBMS_OUTPUT.PUT_LINE('>> [PRC_POS_CARGA_FATOS] Coletando estatísticas CBO...');
  FOR t IN (
    SELECT table_name
    FROM all_tables
    WHERE owner = v_owner
      AND (p_tabela_alvo IS NULL OR table_name = UPPER(TRIM(p_tabela_alvo)))
      AND table_name LIKE 'FAT%'
    ORDER BY table_name
  ) LOOP
    BEGIN
      DBMS_STATS.GATHER_TABLE_STATS(
        ownname          => v_owner,
        tabname          => t.table_name,
        estimate_percent => DBMS_STATS.AUTO_SAMPLE_SIZE,
        method_opt       => 'FOR ALL COLUMNS SIZE AUTO',
        degree           => p_parallel,
        cascade          => TRUE,   -- Atualiza índices e colunas simultaneamente
        no_invalidate    => FALSE   -- Invalida cursores obsoletos imediatamente
      );
    EXCEPTION
      WHEN OTHERS THEN
        DBMS_OUTPUT.PUT_LINE('>> ERRO em DBMS_STATS para ' || t.table_name || ': ' || SQLERRM);
    END;
  END LOOP;

  DBMS_OUTPUT.PUT_LINE('>> [PRC_POS_CARGA_FATOS] Ciclo de pós-carga finalizado com sucesso.');
END PRC_POS_CARGA_FATOS;
/
```


