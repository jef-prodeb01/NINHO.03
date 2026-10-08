# Guia de Implementação no Power BI — <NOME_PROJETO>

> **Projeto:** <NOME_PROJETO_EXTENSO>  
> **Schema Oracle:** `<SCHEMA_OWNER>`  
> **Engenheiro de Dados:** <NOME_ENGENHEIRO>  
> **Público-Alvo:** Analistas de BI, Engenheiros de Analytics e Designers de Mockup  
> **Data:** <DATA_CRIACAO> | **Versão:** 1.0  

---

## 1. Visão Geral e Estratégia de Modelagem

Este documento orienta a equipe de Business Intelligence na construção do **Modelo Analítico e Dashboards do projeto <NOME_PROJETO>** no Microsoft Power BI e/ou Apache Superset. O modelo foi projetado sobre a arquitetura dimensional do Oracle, garantindo rastreabilidade, alto desempenho e governança.

### Recomendações de Conexão no Power BI:
- **Modo de Conexão:** **Importação (Import Mode)**. O modelo dimensional é otimizado para o motor colunar **VertiPaq**, permitindo compressão máxima em memória e performance instantânea em filtros e cálculos DAX.
- **Topologia do Modelo:** **Modelo Estrela (Star Schema)** puro, com as dimensões filtrando a tabela fato central.
- **Cardinalidade e Filtros:** Cardinalidade **1 para Muitos (1:*)** das Dimensões para a Fato, com Direção de Filtro Cruzado **Única (Single)**.

---

## 2. Diagrama do Modelo Dimensional (Star Schema)

Configure os relacionamentos na guia **Modelo** do Power BI conectando as Surrogate Keys (`DIMENSION_KEY` ou `SK_*`):

```mermaid
erDiagram
    <DIM_TEMPO> ||--o{ <FATO_TABELA> : "<COLUNA_DATA_FK>"
    <DIM_ENTIDADE_1> ||--o{ <FATO_TABELA> : "<COLUNA_SK_1>"
    <DIM_ENTIDADE_2> ||--o{ <FATO_TABELA> : "<COLUNA_SK_2>"
    <DIM_ENTIDADE_3> ||--o{ <FATO_TABELA> : "<COLUNA_SK_3>"
```

---

## 3. Catálogo de Objetos do Projeto no Oracle

| Objeto no Oracle | Papel Arquitetural | Descrição / Granularidade |
| :--- | :--- | :--- |
| **`<FATO_TABELA>`** | Tabela Fato Principal | 1 linha por <DESCRICAO_GRAO_FATO>. Contém as métricas quantitativas e chaves estrangeiras. |
| **`<DIM_ENTIDADE_1>`** | Dimensão SCD2 / Entidade 1 | Atributos de <ENTIDADE_1>. Contém linha técnica `-1` para registros não informados. |
| **`<DIM_ENTIDADE_2>`** | Dimensão SCD2 / Entidade 2 | Atributos de <ENTIDADE_2>. |
| **`<DIM_TEMPO>`** | Dimensão Calendário Corporativa | Calendário corporativo padrão (`DTC_COMPLETA`, `NUM_ANO`, `NUM_MES`, `NUM_SEMESTRE`). |
| **`<VW_FATO_EVENTO>`** | View Semântica Unificada | View amigável pronta para relatórios rápidos ou Superset. |

---

## 4. Configuração da Dimensão Tempo (`<DIM_TEMPO>`) no Power BI

1. **Importação:** Conecte na tabela `<DIM_TEMPO>` e renomeie para **`dTempo`**.
2. **Marcar como Tabela de Data:**
   - Clique com o botão direito na tabela `dTempo` ➔ *Marcar como tabela de data* ➔ Selecione a coluna `<COLUNA_DATA_CONTINUA>`.
3. **Classificação Obrigatória de Colunas (Sort by Column):**
   - Classifique `DES_MES` pela coluna `NUM_MES`.
   - Classifique `DES_MES_ANO` pela coluna `COD_ANO_MES` ou `DES_MES_ANO_NUMERICO`.
   - Classifique `DES_SEMESTRE` pela coluna `NUM_SEMESTRE`.
   - Classifique `DES_TRIMESTRE` pela coluna `NUM_TRIMESTRE`.
4. **Relacionamento com a Fato:**
   - `dTempo[<COLUNA_PK_DATA>]` (1) ➔ `<FATO_TABELA>[<COLUNA_FK_DATA>]` (*) | *Filtro: Único (Single)*.

---

## 5. Dicionário de Métricas e Fórmulas DAX

Crie a tabela dedicada **`_Medidas_<NOME_PROJETO>`** e adicione as fórmulas estruturadas por pasta:

### 📁 Pasta: `01. Totais Consolidados`

#### Métrica 1: Volume Total de Eventos / Ocorrências
* **Conceito:** Contagem total de transações ou registros da fato.
* **Tabela de Origem:** `<FATO_TABELA>`
```dax
Total Registros = 
COUNTROWS('<FATO_TABELA>')
```

#### Métrica 2: Valor Total Consolidado (R$ / Unidades)
* **Conceito:** Somatório financeiro ou quantitativo principal.
* **Tabela de Origem:** `<FATO_TABELA>`
```dax
Valor Total = 
SUM('<FATO_TABELA>'[<COLUNA_METRICA_VALOR>])
```

---

### 📁 Pasta: `02. Contagens Distintas e Entidades Únicas`

#### Métrica 3: Entidades Únicas Atendidas
* **Conceito:** Contagem distinta de entidades de negócio desconsiderando a linha não informada `-1`.
```dax
Qtd Entidades Unicas = 
CALCULATE(
    DISTINCTCOUNT('<FATO_TABELA>'[<COLUNA_FK_ENTIDADE>]),
    '<FATO_TABELA>'[<COLUNA_FK_ENTIDADE>] <> -1
)
```

---

### 📁 Pasta: `03. Proporções e Médias (%)`

#### Métrica 4: Ticket Médio / Custo Médio Unitário
* **Conceito:** Divisão segura entre valor total e volume de eventos.
```dax
Valor Medio = 
DIVIDE([Valor Total], [Total Registros], 0)
```

---

### 📁 Pasta: `04. Metas e Indicadores de Desempenho (KPIs)`

#### Métrica 5: Percentual de Atingimento da Meta (%)
```dax
% Atingimento Meta = 
DIVIDE([Valor Total], [Meta Institucional], 0)
```

---

### 📁 Pasta: `05. Inteligência Temporal (Time Intelligence)`

#### Métrica 6: Acumulado no Ano (YTD)
```dax
Valor YTD = 
TOTALYTD([Valor Total], 'dTempo'[<COLUNA_DATA_CONTINUA>])
```

#### Métrica 7: Variação em Relação ao Mês Anterior (MoM %)
```dax
Valor Mes Anterior = 
CALCULATE(
    [Valor Total],
    DATEADD('dTempo'[<COLUNA_DATA_CONTINUA>], -1, MONTH)
)

Variacao MoM % = 
DIVIDE([Valor Total] - [Valor Mes Anterior], [Valor Mes Anterior], 0)
```

---

## 6. Mapeamento de Segmentadores Recomendados

| Nome do Filtro no Dashboard | Campo Recomendado | Tabela de Origem | Comportamento / Observações |
| :--- | :--- | :--- | :--- |
| **Ano / Semestre / Mês** | `NUM_ANO`, `DES_SEMESTRE`, `DES_MES_ANO` | `dTempo` | Hierarquia temporal corporativa padrão. |
| **Entidade 1** | `<NOM_ENTIDADE_1>` | `<DIM_ENTIDADE_1>` | Filtro de seleção múltipla ou lista suspensa. |
| **Situação / Status** | `<DES_STATUS>` | `<DIM_ENTIDADE_2>` | Filtro categórico de status. |

---

## 7. Checklist de Qualidade Pré-Publicação

- [ ] Relacionamentos configurados como **1:* e Filtro Single**.
- [ ] Tabela `dTempo` marcada oficialmente como Tabela de Data.
- [ ] Colunas textuais de tempo classificadas por colunas numéricas.
- [ ] Surrogate Keys e FKs ocultas para os usuários finais.
- [ ] Todas as divisões utilizam a função `DIVIDE(..., 0)`.
- [ ] Valores conferidos contra consultas SQL no banco de homologação.

