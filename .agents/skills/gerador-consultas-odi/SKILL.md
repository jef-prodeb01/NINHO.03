---
name: gerador-consultas-odi
description: Gera consultas SQL de extração e transformação para interfaces e mappings do Oracle Data Integrator (ODI 12c), incluindo lookups com fallback -1, surrogate keys, SCD2 e o Guia Visual de Implementação no Canvas ODI 12c (Fase 1 e Fase 2). Use APENAS quando a opção Oracle Data Integrator (ODI 12c) estiver explicitamente marcada no INTAKE_DW.md.
---

# Skill: Gerador de Consultas e Guia de Canvas para Oracle Data Integrator (ODI 12c)

Esta skill orienta o agente na geração de scripts SQL de extração, transformação e enriquecimento calibrados especificamente para alimentação das interfaces e mappings do **Oracle Data Integrator (ODI 12c)**, além de gerar o **Guia Visual de Implementação no Canvas do ODI 12c** para o desenvolvedor de ETL.

> 🛑 **REGRA CONDICIONAL INVIOLÁVEL:**  
> Esta skill **SÓ PODE SER ACIONADA** se a opção `[x] Oracle Data Integrator (ODI 12c)` estiver assinalada na Seção 1 do [`INTAKE_DW.md`](../../../modulos/planejador_dw/INTAKE_DW.md).  
> Se desmarcada, **NÃO GERE** os arquivos específicos do ODI.

---

## 🎯 Arquitetura de 2 Fases no ODI 12c

O processo de carga do Data Warehouse com ODI 12c é dividido em duas fases canônicas de alta performance:

### FASE 1: Extração de Origem para Staging (`STG_*`)
- **SQL de Origem:** CTEs com `WITH (NOLOCK)` (se SQL Server), filtros temporais (janelas ativas de N meses), eliminação de duplicidades via `DISTINCT` e tipagem estrita (`NUMBER` para dias/durações, **nunca** `TIMESTAMP`).
- **LKM:** `LKM SQL to Oracle (Built-In)`.
- **IKM:** `IKM Oracle Insert` com opções físicas:
  - `TRUNCATE = True`
  - `INSERT_HINT = /*+ APPEND PARALLEL(4) */`

### FASE 2: Carga Dimensional da Staging para a Fato DW (`FATO_*`)
- **Ambiente:** Execução **100% interna Oracle para Oracle** no mesmo schema (`{SCHEMA_ALVO}`).
- **Zero LKM:** Nenhum LKM necessário (sem overhead de rede).
- **Resolução Dimensional:** Lookups dimensionais em dimensões SCD Tipo 2 (`DTC_EXPIRACAO IS NULL`) e dimensões conformadas (`DIM_TEMPO`).
- **Role-Playing Dimensions:** Uso de instâncias e aliases separados para dimensões reutilizadas (ex: `DIM_USR` executor e `DIM_USR_ATRIB` atribuído; `DIM_TEMPO_INI` e `DIM_TEMPO_FIM`).
- **Regra Inegociável do `-1`:** Aplicação de `NVL(dim.DIMENSION_KEY, -1)` para **TODAS** as FKs dimensionais, garantindo integridade referencial para registros nulos ou não encontrados.
- **IKM:** `IKM Oracle Insert` com Direct-Path Parallel (`/*+ APPEND PARALLEL(4) */`), atingindo milhões de linhas em minutos.

---

## 🧭 As 3 Estratégias de Implementação no ODI 12c

Ao documentar e gerar as esteiras de ODI, considere sempre as 3 estratégias de implementação:
1. **Estratégia 1 (View na Origem):** Quando a equipe tem permissão DDL no banco transacional. Mapeamento 1 para 1 direto no ODI.
2. **Estratégia 2 (100% Visual no Canvas Lógico):** **O padrão corporativo recomendado quando o acesso à origem é estritamente LEITURA (SELECT).** Modela todo o fluxo usando componentes nativos do ODI (`Datastore`, `Filtro`, `Distinto`, `Junção`, `Lookup`).
3. **Estratégia 3 (ODI Procedure Direta):** Script SQL/PL/SQL direto em uma procedure ODI para casos específicos de contingência.

---

## 📂 Destino Canônico de Saída

Ao ser acionada, os arquivos gerados devem ser salvos diretamente em:
- `saida/planejador_dw/03_dimensoes/03_selects_odi_dimensoes.sql` (Consultas de surrogate keys e SCD2 para dimensões).
- `saida/planejador_dw/04_fatos/04_select_odi_fato.sql` (Consulta consolidada com Lookups da Fato).
- `saida/planejador_dw/09_relatorio_estrategias/GUIA_IMPLEMENTACAO_ODI_<FATO>.md` (Roteiro passo a passo com diagramas visuais ASCII do Canvas Lógico e Físico para o desenvolvedor de ETL).

---

## 📐 Padrões Obrigatórios do ODI

1. **Uso de Sequences:** Sempre referenciar a sequence qualificada com aspas e schema:
   ```sql
   "SCHEMA_ALVO"."SEQ_DIM_NOME".NEXTVAL AS DIMENSION_KEY
   ```
2. **Tratamento de Nulos na Fato:** Proibido deixar FK nula:
   ```sql
   NVL(dp.DIMENSION_KEY, -1) AS DIM_PROJETO,
   NVL(dt.DIMENSION_KEY, -1) AS DIM_TEMPO
   ```
3. **Limpeza e Normalização com REGEXP:**
   ```sql
   UPPER(NVL(REGEXP_SUBSTR(CAMPO_TEXTO, '^([^-]+)', 1, 1, 'i', 1), CAMPO_TEXTO)) AS DES_SIGLA
   ```
4. **Função Analítica no Canvas para Fatos Snapshot (`ROW_NUMBER()`):**
   * Empregar o par `Componente Expressão (EXP_ANALITICA)` com `RN = ROW_NUMBER() OVER(PARTITION BY ... ORDER BY ... DESC)` + `Componente Filtro (RN = 1)` para extrair o estado mais recente no Canvas Lógico sem subqueries manuais.
5. **Lookups em Cadeia e "Lookup com Nulo Retornado":**
   * Quando uma chave depender de dimensão intermediária (ex: `STG -> DIM_USUARIO -> DIM_ORGAO`), encadear lookups.
   * Marcar **obrigatoriamente** `Lookup com Nulo Retornado = True` (Left Outer Join) para evitar o descarte silencioso de linhas.
6. **Tratamento de Vigências Abertas / Datas Nulas (`DIM_TEMPO_FIM = -1`):**
   * Mapear registros com data fim aberta (`DTH_FIM IS NULL`) com fallback para a linha `-1` da `DIM_TEMPO` (`DTC_COMPLETA = NULL`, `DES_MES = 'Não Informado / Vigente'`).
7. **Arquitetura de Fatos Híbridas para Tabelas Transacionais Massivas:**
   * Quando a fonte tiver dezenas/centenas de milhões de linhas, separar em Fato Histórica Agregada e Fato Snapshot Recente conforme [Arquitetura de Fatos Híbridas](../planejador-dw-oracle/references/arquitetura_fatos_hibridas.md).

Consulte os modelos estruturais em:
- [template_selects_odi.sql](./templates/template_selects_odi.sql)
- [template_guia_implementacao_odi.md](./templates/template_guia_implementacao_odi.md)
- [arquitetura_fatos_hibridas.md](../planejador-dw-oracle/references/arquitetura_fatos_hibridas.md)



