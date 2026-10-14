# Guia de Implementação no Power BI — Painel de {NOME_PROJETO}

> **Projeto:** Data Services — {NOME_PROJETO}  
> **Schema Oracle:** `{OWNER_OLAP}`  
> **Público-Alvo:** Analistas de BI, Engenheiros de Analytics e Designers de Painéis  
> **Versão:** 1.0  

---

## 1. Visão Geral e Estratégia de Conexão

Este documento orienta a equipe de Business Intelligence na reconexão e construção do painel no Power BI a partir do **Data Warehouse dimensional corporativo** na Oracle.

### Recomendações de Conexão:
- **Modo de Conexão:** **Import (Importação)** para datasets analíticos de até alguns milhões de linhas; ou **DirectQuery** apenas em casos de SLA de tempo real.
- **Padrão Arquitetural:** **Modelo Estrela (Star Schema)** conectando as Views da Camada Semântica (`VW_{PROJETO}_FATO_*`) com as Dimensões (`VW_{PROJETO}_DIM_*`).

---

## 2. Diagrama do Modelo Dimensional (Star Schema)

Configure os relacionamentos no Power BI estritamente com **cardinalidade 1 para Muitos (1:*)** e **direção de filtro simples (Single)**:

```mermaid
erDiagram
    VW_{PROJETO}_DIM_TEMPO ||--o{ VW_{PROJETO}_FATO_PRINCIPAL : "DTC_DATA -> DTC_EVENTO"
    VW_{PROJETO}_DIM_ENTIDADE_A ||--o{ VW_{PROJETO}_FATO_PRINCIPAL : "SK_ENTIDADE_A"
    VW_{PROJETO}_DIM_ENTIDADE_B ||--o{ VW_{PROJETO}_FATO_PRINCIPAL : "SK_ENTIDADE_B"
```

---

## 3. Dimensão Calendário / Tempo (`VW_{PROJETO}_DIM_TEMPO`)

1. **Importe a view:** Carregue `{OWNER_OLAP}.VW_{PROJETO}_DIM_TEMPO` e renomeie para `dCalendario`.
2. **Marque como Tabela de Data:** Clique com o botão direito na tabela `dCalendario` ➔ *Marcar como tabela de data* ➔ Selecione `DTC_DATA`.
3. **Configure as Ordenações:**
   - Ordene a coluna `DES_MES_NOME` pela coluna numérica `NUM_MES`.
   - Ordene `DES_MES_ANO_ABREV` pela coluna `COD_ANO_MES`.
   - Ordene `DES_SEMESTRE` pela coluna `NUM_SEMESTRE`.

---

## 4. Dicionário de Métricas DAX

Crie uma tabela dedicada a medidas (`_Medidas_{PROJETO}`) e utilize as métricas padronizadas:

### Métrica 1: Total de Eventos / Ocorrências
```dax
Total Registros = 
COUNTROWS(VW_{PROJETO}_FATO_PRINCIPAL)
```

### Métrica 2: Registros com Filtro de Negócio
```dax
Total Concluidos = 
CALCULATE(
    COUNTROWS(VW_{PROJETO}_FATO_PRINCIPAL),
    VW_{PROJETO}_FATO_PRINCIPAL[FLG_CONCLUIDO] = 1
)
```

### Métrica 3: Média de Tempo / SLA
```dax
Tempo Medio Atendimento (Dias) = 
AVERAGE(VW_{PROJETO}_FATO_PRINCIPAL[NUM_DIAS_ATENDIMENTO])
```
