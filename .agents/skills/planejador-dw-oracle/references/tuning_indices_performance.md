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
