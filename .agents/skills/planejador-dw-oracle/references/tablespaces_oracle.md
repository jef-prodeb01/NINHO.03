# Guia de Tablespaces, Sizing e Storage (Oracle DW)

Este documento técnico detalha as boas práticas de alocação de armazenamento no Oracle Database para Data Warehouses corporativos.

## 1. Separação de Tablespaces: Dados vs Índices

Em ambientes Oracle de alta performance, a melhor prática arquitetural é segregar os segmentos de tabela dos segmentos de índice:

1. **Tablespace de Dados (`<SCHEMA>_DATA`):**
   - Armazena as tabelas Staging (`STG_*`), Dimensões (`DIM_*`), Fatos (`FATO_*`) e Tabelas de Controle (`TB_CONTROLE_CARGA`).
   - Parâmetros recomendados: `EXTENT MANAGEMENT LOCAL AUTOALLOCATE SEGMENT SPACE MANAGEMENT AUTO`.

2. **Tablespace de Índices (`<SCHEMA>_INDEX`):**
   - Armazena as Primary Keys, Chaves Únicas, Índices B-Tree de busca e Índices Bitmap de Star Transformation.
   - **Benefício Operacional:** Permite monitorar e isolar manutenções de índices (como rebuilds massivos e cargas com `NOLOGGING`) sem risco de esgotar o espaço destinado aos dados primários da aplicação.

### O que fazer quando há apenas UMA Tablespace no Schema?
Se a infraestrutura fornecer apenas uma tablespace (ex: `SEIMUNICIPIO_DATA`):
- O banco funcionará perfeitamente, mas ambos os tipos de objetos competem pela mesma cota (`MAX_BYTES`).
- **Atenção Redobrada:** O engenheiro deve auditar a ocupação periodicamente para garantir que índices bitmap ou índices não reconstruídos não consumam mais espaço do que os dados reais da fato.

---

## 2. Queries de Monitoramento e Diagnóstico

### 2.1 Verificar Cotas do Usuário na Tablespace
```sql
SELECT tablespace_name,
       ROUND(bytes / 1024 / 1024, 2) AS ocupado_mb,
       CASE WHEN max_bytes = -1 THEN 'ILIMITADO'
            ELSE TO_CHAR(ROUND(max_bytes / 1024 / 1024, 2))
       END AS cota_mb
FROM user_ts_quotas;
```

### 2.2 Diagnosticar Ocupação por Tipo de Segmento (Tabelas vs Índices)
```sql
SELECT tablespace_name,
       segment_type,
       COUNT(*) AS qtd_objetos,
       ROUND(SUM(bytes) / 1024 / 1024, 2) AS ocupado_mb,
       ROUND(SUM(bytes) / (SELECT SUM(bytes) FROM user_segments WHERE tablespace_name = s.tablespace_name) * 100, 2) AS pct_ocupacao
FROM user_segments s
GROUP BY tablespace_name, segment_type
ORDER BY ocupado_mb DESC;
```

---

## 3. Diretrizes de Rebuild e Performance

1. **Rebuild com NOLOGGING:**
   - Durante a rotina `PRC_POS_CARGA_FATO`, todos os rebuilds de índice devem utilizar `NOLOGGING` para evitar sobrecarga nas tablespaces de Undo e nos archives de Redo:
   ```sql
   ALTER INDEX "<SCHEMA>"."<NOME_INDICE>" REBUILD NOLOGGING;
   ```
2. **Coleta Imediata de Estatísticas:**
   - Após rebuild, colete estatísticas para o otimizador CBO:
   ```sql
   DBMS_STATS.GATHER_TABLE_STATS(
       ownname          => '<SCHEMA>',
       tabname          => 'FATO_<NOME>',
       estimate_percent => DBMS_STATS.AUTO_SAMPLE_SIZE,
       cascade          => TRUE,
       degree           => DBMS_STATS.DEFAULT_DEGREE
   );
   ```
