---
name: gerador-consultas-odi
description: Gera consultas SQL de extração e transformação para interfaces e mappings do Oracle Data Integrator (ODI 12c), incluindo lookups com fallback -1, surrogate keys e SCD2. Use APENAS quando a opção Oracle Data Integrator (ODI 12c) estiver explicitamente marcada no INTAKE_DW.md.
---

# Skill: Gerador de Consultas para Oracle Data Integrator (ODI 12c)

Esta skill orienta o agente na geração de scripts SQL de extração, transformação e enriquecimento calibrados especificamente para alimentação das interfaces e mappings do **Oracle Data Integrator (ODI 12c)**.

> 🛑 **REGRA CONDICIONAL INVIOLÁVEL:**  
> Esta skill **SÓ PODE SER ACIONADA** se a opção `[x] Oracle Data Integrator (ODI 12c)` estiver assinalada na Seção 1 do [`INTAKE_DW.md`](../../../modulos/planejador_dw/INTAKE_DW.md).  
> Se desmarcada, **NÃO GERE** os arquivos específicos do ODI.

---

## 🎯 Objetivo dos Scripts do ODI

No fluxo corporativo com ODI, o processo de carga do Data Warehouse é dividido em duas etapas SQL geradas:
1. **Carga das Dimensões (ou Tabelas Auxiliares `ODI_DIM_*`):**
   - Agrupamento pela chave natural de negócio (`GROUP BY COD_*`).
   - Geração da Surrogate Key via Sequence (`"SCHEMA"."SEQ_DIM_*".NEXTVAL AS DIMENSION_KEY`).
   - Extração e limpeza de siglas e domínios via `REGEXP_SUBSTR` e `CASE WHEN`.
   - Inicialização dos atributos de SCD Tipo 2:
     - `TRUNC(SYSDATE) AS DTC_EFETIVACAO`
     - `TO_DATE('2999-12-31', 'YYYY-MM-DD') AS DTC_EXPIRACAO`
     - `'S' AS DES_ATUALIZA` (ou `DES_STATUS_REGISTRO = 'I'`).
2. **Carga da Fato Principal:**
   - Leitura direta da tabela Staging (`STG_*`).
   - Junção (`LEFT JOIN`) com todas as dimensões vigentes para resolução de Surrogate Keys.
   - Aplicação obrigatória de fallback com `NVL(dim.DIMENSION_KEY, -1)` para **TODAS** as chaves estrangeiras, garantindo que registros órfãos ou não preenchidos apontem para o registro padrão `-1 - NÃO INFORMADO`.
   - Conversão de métricas e agregação no grão físico definido.

---

## 📂 Destino Canônico de Saída

Ao ser acionada, os scripts gerados devem ser salvos diretamente em:
- `saida/planejador_dw/03_dimensoes/03_selects_odi_dimensoes.sql` (Consultas para cada dimensão).
- `saida/planejador_dw/04_fatos/04_select_odi_fato.sql` (Consulta consolidada com Lookups da Fato).

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

Consulte o modelo estrutural completo em [template_selects_odi.sql](./templates/template_selects_odi.sql).
