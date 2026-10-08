# Guia de Implementação no Power BI — <NOME_PROJETO>

> **Projeto:** <NOME_PROJETO_EXTENSO>  
> **Destino / Painel:** <PORTAL_OU_PAINEL_DESTINO> *(ex: Portal UNEBi, Painel SEI Bahia, FinOps OpenShift)*  
> **Schema Oracle:** `<SCHEMA_OWNER>`  
> **Tablespace de Dados:** `<TABLESPACE_DATA>` | **Tablespace de Índices:** `<TABLESPACE_INDEX>`  
> **Engenheiro de Dados Responsável:** <NOME_ENGENHEIRO>  
> **Público-Alvo:** Analistas de BI, Engenheiros de Analytics e Desenvolvedores de Painéis *(Uso Externo)*  
> **Data de Geração:** <DATA_CRIACAO> | **Versão do Modelo:** <VERSAO_MODELO>  

---

> ⚠️ **Nota Institucional de Handoff (Engenharia de Dados ➔ Business Intelligence):**  
> Este documento é o **entregável oficial de transição** gerado pelo **Planejador de DW da Plataforma NINHO**. Ele sintetiza a arquitetura dimensional física implantada no Oracle e fornece à equipe de Business Intelligence todas as diretrizes, fórmulas DAX, mapeamentos de filtros e queries de conciliação necessárias para a construção do mockup e publicação do painel homologado no Power BI.

---

## Sumário

- [1. Visão Geral e Estratégia de Modelagem](#1-visao-geral)
- [2. Diagrama do Modelo Dimensional (Star Schema)](#2-diagrama-star-schema)
- [3. Catálogo de Tabelas e Objetos no Data Warehouse](#3-catalogo-tabelas)
- [4. Configuração da Dimensão Tempo Corporativa (DIM_TEMPO)](#4-dimensao-tempo)
- [5. Governança de Dimensões SCD2 e Linha Sentinela -1](#5-scd2-linha-menos-1)
- [6. Dicionário Completo de Métricas e Fórmulas DAX](#6-dicionario-dax)
  - [6.1 Grupo 1: Totais Consolidados e Volumes](#61-totais-consolidados)
  - [6.2 Grupo 2: Contagens Distintas e Entidades Únicas](#62-contagens-distintas)
  - [6.3 Grupo 3: Prazos, Médias, Proporções e SLA](#63-prazos-medias-sla)
  - [6.4 Grupo 4: Metas Institucionais e % de Atingimento](#64-metas-atingimento)
  - [6.5 Grupo 5: Inteligência Temporal (Time Intelligence)](#65-time-intelligence)
  - [6.6 Grupo 6: Auditoria de Dados e Inatividade](#66-auditoria-inatividade)
- [7. Mapeamento de Segmentadores Recomendados (Filtros do Painel)](#7-segmentadores-recomendados)
- [8. Proposta de Estrutura Visual para o Mockup / Páginas](#8-estrutura-visual-mockup)
- [9. Consultas Rápidas de Conferência (Power BI vs. Oracle SQL)](#9-consultas-conferencia)
- [10. Checklist de Qualidade Pré-Publicação](#10-checklist-qualidade)

---

<a id="1-visao-geral"></a>
## 1. Visão Geral e Estratégia de Modelagem

Este documento orienta a equipe de Business Intelligence na construção do **Painel de BI do projeto <NOME_PROJETO>** no Microsoft Power BI. O modelo resolve os desafios de volumetria transacional através de uma **Arquitetura Dimensional em Modelo Estrela (Star Schema)**, garantindo integridade corporativa, rastreabilidade e máxima agilidade analítica.

### Recomendações de Conexão no Power BI:
* **Modo de Conexão Obrigatório:** **Importação (Import Mode)**. O modelo dimensional foi projetado no grão ideal com chaves surrogate inteiras (`NUMBER`). Isso resulta em uma base ultracompacta no motor colunar em memória **VertiPaq** do Power BI, garantindo carregamento em segundos, resposta instantânea em segmentadores e suporte completo a todas as funções DAX de agregação e inteligência temporal.
* **Topologia do Modelo:** **Modelo Estrela (Star Schema)** puro, conectando as Dimensões (`DIM_*`) e a Dimensão Calendário (`DIM_TEMPO`) diretamente às Tabelas Fato (`FATO_*`).
* **Cardinalidade dos Relacionamentos:** **1 para Muitos (1:*)** das Dimensões para as Fatos.
* **Direção de Filtro Cruzado:** **Única (Single)** — da Dimensão para a Fato. **Nunca utilize filtros bidirecionais (`Both`)**, pois geram ambiguidades de contexto, perda de performance no VertiPaq e potenciais erros em métricas calculadas.

---

<a id="2-diagrama-star-schema"></a>
## 2. Diagrama do Modelo Dimensional (Star Schema)

No Power BI (exibição de **Modelo**), conecte as tabelas importadas respeitando a cardinalidade `1:*` e a direção de filtro `Single`, conforme o diagrama abaixo:

```mermaid
erDiagram
    <DIM_TEMPO> ||--o{ <FATO_TABELA_1> : "<COLUNA_DATA_FK> -> DTC_COMPLETA"
    <DIM_ENTIDADE_1> ||--o{ <FATO_TABELA_1> : "<COLUNA_SK_1>"
    <DIM_ENTIDADE_2> ||--o{ <FATO_TABELA_1> : "<COLUNA_SK_2>"
    <DIM_STATUS> ||--o{ <FATO_TABELA_1> : "<COLUNA_SK_STATUS>"

    <DIM_TEMPO> ||--o{ <FATO_TABELA_2> : "<COLUNA_DATA_FK_2> -> DTC_COMPLETA"
    <DIM_ENTIDADE_1> ||--o{ <FATO_TABELA_2> : "<COLUNA_SK_1>"
    <DIM_ENTIDADE_3> ||--o{ <FATO_TABELA_2> : "<COLUNA_SK_3>"

    <DIM_TEMPO> {
        NUMBER DIMENSION_KEY PK
        DATE DTC_COMPLETA
        NUMBER NUM_ANO
        NUMBER NUM_MES
        VARCHAR2 DES_MES
        VARCHAR2 DES_MES_ANO
        NUMBER NUM_SEMESTRE
        VARCHAR2 DES_SEMESTRE
        CHAR IND_FINAL_SEMANA
    }

    <DIM_ENTIDADE_1> {
        NUMBER <COLUNA_SK_1> PK
        VARCHAR2 <COD_NATURAL_1>
        VARCHAR2 <NOM_ENTIDADE_1>
        VARCHAR2 <DES_CATEGORIA_1>
        CHAR IND_REGISTRO_ATIVO
    }

    <FATO_TABELA_1> {
        NUMBER <COLUNA_SK_1> FK
        NUMBER <COLUNA_SK_2> FK
        NUMBER <COLUNA_DATA_FK> FK
        NUMBER <COLUNA_METRICA_VALOR>
        NUMBER <COLUNA_METRICA_QTD>
    }
```

---

<a id="3-catalogo-tabelas"></a>
## 3. Catálogo de Tabelas e Objetos no Data Warehouse

| Nome da Tabela no Oracle | Papel Arquitetural | Granularidade / Grão | Descrição de Negócio & Utilização |
| :--- | :--- | :--- | :--- |
| **`<FATO_TABELA_1>`** | Fato Principal / Agregada | 1 linha por <GRAO_FATO_1> | Contém as métricas quantitativas e financeiras principais do projeto. Base para os relatórios executivos. |
| **`<FATO_TABELA_2>`** | Fato Snapshot / Prazos | 1 linha por <GRAO_FATO_2> | Histórico recente ou snapshot de posição para medição de SLA, tempos de atendimento e gargalos. |
| **`<DIM_ENTIDADE_1>`** | Dimensão SCD Tipo 2 | 1 linha por versão de <ENTIDADE_1> | Catálogo cadastral com histórico. Contém linha técnica `-1` para não informados e flag de registro ativo. |
| **`<DIM_ENTIDADE_2>`** | Dimensão SCD Tipo 2 | 1 linha por versão de <ENTIDADE_2> | Estrutura organizacional, hierarquia ou classificação de negócio. |
| **`<DIM_STATUS>`** | Dimensão Estática | 1 linha por código de status | Tabela pequena e estável contendo as situações e fases do ciclo de vida. |
| **`<DIM_TEMPO>`** | Dimensão Calendário | 1 linha por dia contínuo | Calendário corporativo conformado padronizado com atributos civis, acadêmicos e fiscais. |
| **`<VW_EVENTO>`** | View Semântica Unificada | Visão desnormalizada | View analítica amigável pronta para relatórios rápidos, autosserviço ou Apache Superset. |

---

<a id="4-dimensao-tempo"></a>
## 4. Configuração da Dimensão Tempo Corporativa (DIM_TEMPO)

A dimensão calendário conformada **`<DIM_TEMPO>`** é a espinha dorsal de qualquer análise temporal no Power BI.

### Passo a Passo de Configuração no Power BI:
1. **Importação:** Carregue a tabela `<DIM_TEMPO>` (ou a view `VW_DIM_TEMPO`) e renomeie para **`dCalendario`** ou **`dTempo`**.
2. **Marcar como Tabela de Data (Mark as Date Table):**
   * Clique com o botão direito sobre a tabela `dCalendario` no painel Dados ➔ selecione **Marcar como tabela de data** (Mark as Date Table).
   * Selecione a coluna de data contínua **`DTC_COMPLETA`** (ou `DTC_DATA`).
   * *Benefício:* O Power BI desabilita as hierarquias automáticas ocultas, economizando memória no VertiPaq e habilitando o cálculo perfeito de Time Intelligence DAX.
3. **Crie os Relacionamentos (1:*):**
   * `dCalendario[DIMENSION_KEY]` (1) ➔ `<FATO_TABELA_1>[<COLUNA_DATA_FK>]` (*)
   * `dCalendario[DIMENSION_KEY]` (1) ➔ `<FATO_TABELA_2>[<COLUNA_DATA_FK_2>]` (*)
   *(Se a fato utilizar chave de data em DATE em vez de surrogate numérica: `dCalendario[DTC_COMPLETA]` (1) ➔ `FATO[DTC_EVENTO]` (*))*.
4. **Classificação Obrigatória de Colunas (Sort by Column):**
   Para garantir que os meses e períodos apareçam em ordem cronológica (e não alfabética) nos gráficos e segmentadores, configure:
   * Selecione a coluna **`DES_MES`** ➔ guia Ferramentas de Coluna ➔ **Classificar por Coluna** ➔ selecione **`NUM_MES`**.
   * Selecione a coluna **`DES_MES_ANO`** ➔ **Classificar por Coluna** ➔ selecione **`DES_MES_ANO_NUMERICO`** (ou `COD_ANO_MES`).
   * Selecione a coluna **`DES_SEMESTRE`** ➔ **Classificar por Coluna** ➔ selecione **`NUM_SEMESTRE`**.
   * Selecione a coluna **`DES_TRIMESTRE`** ➔ **Classificar por Coluna** ➔ selecione **`NUM_TRIMESTRE`**.
   * Selecione a coluna **`DES_QUINZENA`** ➔ **Classificar por Coluna** ➔ selecione **`NUM_QUINZENA`**.

---

<a id="5-scd2-linha-menos-1"></a>
## 5. Governança de Dimensões SCD2 e Linha Sentinela -1

Para manter a consistência com o padrão arquitetural do Data Warehouse:

### 1. Tratamento da Linha Técnica -1 (Não Informado / Não Identificado):
* Toda dimensão do DW possui obrigatoriamente a linha técnica `DIMENSION_KEY = -1` com descrições padronizadas como `"NÃO INFORMADO"`, `"INDEFINIDO"` ou `"NÃO APLICÁVEL"`.
* Ao calcular contagens distintas no DAX, filtre a linha `-1` para não superestimar a quantidade real de entidades atendidas:
  ```dax
  Qtd Entidades Reais = 
  CALCULATE(
      DISTINCTCOUNT('<FATO_TABELA>'[<COLUNA_FK_ENTIDADE>]),
      '<FATO_TABELA>'[<COLUNA_FK_ENTIDADE>] <> -1
  )
  ```

### 2. Ocultação de Chaves Técnicas (Campos SK e FK):
* Na visão de **Modelo** do Power BI, selecione todas as colunas de Surrogate Keys (`DIMENSION_KEY`, `SK_*`) e chaves estrangeiras (`FK_*`) nas tabelas fato e dimensões, clique com o botão direito e selecione **Ocultar na exibição de relatório**.
* Os usuários finais devem visualizar apenas os atributos amigáveis de negócio (nomes, descrições, códigos naturais e categorias), prevenindo erros de agrupamento por chaves substitutas.

---

<a id="6-dicionario-dax"></a>
## 6. Dicionário Completo de Métricas e Fórmulas DAX

Crie no Power BI uma tabela vazia dedicada para armazenar todas as medidas corporativas, chamada **`_Medidas_<NOME_PROJETO>`** (ou simplesmente **`_Medidas`**). Configure a propriedade **Pasta de Exibição (Display Folder)** em cada medida, distribuindo-as nas pastas abaixo:

---

<a id="61-totais-consolidados"></a>
### 📁 Pasta: `01. Totais Consolidados`

#### Indicador 1.1: Volume Total de Eventos / Registros
* **Conceito:** Contagem total de ocorrências ou registros processados no período selecionado.
* **Tabela de Origem:** `<FATO_TABELA_1>`
```dax
Total Registros = 
COUNTROWS('<FATO_TABELA_1>')
```

#### Indicador 1.2: Valor Total Consolidado (R$ / Unidades)
* **Conceito:** Somatório financeiro ou quantitativo monetário do processo de negócio.
* **Tabela de Origem:** `<FATO_TABELA_1>`
```dax
Valor Total = 
SUM('<FATO_TABELA_1>'[<COLUNA_METRICA_VALOR>])
```

#### Indicador 1.3: Quantidade Total de Itens / Volumes
* **Conceito:** Quantidade física de itens, cotas, documentos ou transações concluídas.
```dax
Quantidade Total = 
SUM('<FATO_TABELA_1>'[<COLUNA_METRICA_QTD>])
```

---

<a id="62-contagens-distintas"></a>
### 📁 Pasta: `02. Contagens Distintas e Entidades Únicas`

#### Indicador 2.1: Total de Entidades / Clientes / Discentes Únicos
* **Conceito:** Quantidade distinta de beneficiários ou indivíduos atendidos, eliminando duplicidade caso a mesma entidade possua múltiplos registros na fato, e desconsiderando registros não informados (`-1`).
* **Tabela de Origem:** `<FATO_TABELA_1>`
```dax
Total Entidades Distintas = 
CALCULATE(
    DISTINCTCOUNT('<FATO_TABELA_1>'[<COLUNA_FK_ENTIDADE>]),
    '<FATO_TABELA_1>'[<COLUNA_FK_ENTIDADE>] <> -1
)
```

---

<a id="63-prazos-medias-sla"></a>
### 📁 Pasta: `03. Prazos, Médias, Proporções e SLA`

#### Indicador 3.1: Tempo Médio de Atendimento (Dias / Horas)
* **Conceito:** Média do ciclo total de atendimento desde a abertura até a conclusão definitiva.
* **Tabela de Origem:** `<FATO_TABELA_2>`
```dax
Tempo Medio Atendimento (Dias) = 
DIVIDE(
    SUM('<FATO_TABELA_2>'[<SOM_DIAS_ATENDIMENTO>]),
    SUM('<FATO_TABELA_2>'[<QTD_CASOS_CONCLUIDOS>]),
    0
)
```

#### Indicador 3.2: Taxa de Resolução / Eficácia (%)
* **Conceito:** Percentual de casos finalizados com sucesso frente ao volume total de entradas no período.
```dax
Taxa de Resolucao % = 
VAR vEntradas = [Total Registros]
VAR vConcluidos = CALCULATE([Total Registros], '<DIM_STATUS>'[DES_STATUS] = "CONCLUÍDO")
RETURN
DIVIDE(vConcluidos, vEntradas, 0)
```

#### Indicador 3.3: Valor Médio por Item / Ticket Médio
* **Conceito:** Razão entre o valor financeiro total e a quantidade total de ocorrências.
```dax
Ticket Medio = 
DIVIDE([Valor Total], [Total Registros], 0)
```

---

<a id="64-metas-atingimento"></a>
### 📁 Pasta: `04. Metas Institucionais e % de Atingimento`

#### Indicador 4.1: Meta Institucional Estipulada
* **Conceito:** Cota ou meta física/financeira contratual planejada para o ciclo.
```dax
Meta Institucional = <VALOR_META_FIXA_OU_MEDIDA_DINAMICA>
```

#### Indicador 4.2: Percentual de Atingimento da Meta (%)
* **Conceito:** Comparativo percentual entre o realizado e o alvo estabelecido, com proteção nativa contra divisão por zero.
```dax
% Atingimento Meta = 
DIVIDE([Valor Total], [Meta Institucional], 0)
```

---

<a id="65-time-intelligence"></a>
### 📁 Pasta: `05. Inteligência Temporal (Time Intelligence)`

> 💡 **Pré-requisito:** Estas fórmulas exigem que a tabela `dCalendario` esteja oficialmente marcada como *Tabela de Data* e relacionada via cardinalidade `1:*`.

#### Indicador 5.1: Acumulado no Ano (Year-to-Date - YTD)
* **Conceito:** Acumulação contínua dos valores desde o dia 1º de janeiro do ano corrente até a data selecionada.
```dax
Valor YTD = 
TOTALYTD(
    [Valor Total],
    'dCalendario'[DTC_COMPLETA]
)
```

#### Indicador 5.2: Valor no Mês Anterior (MoM)
* **Conceito:** Deslocamento dinâmico de 1 mês no calendário para comparativos de curto prazo.
```dax
Valor Mes Anterior = 
CALCULATE(
    [Valor Total],
    DATEADD('dCalendario'[DTC_COMPLETA], -1, MONTH)
)
```

#### Indicador 5.3: Variação Percentual Mês a Mês (MoM %)
```dax
Variacao MoM % = 
VAR vAtual = [Valor Total]
VAR vAnterior = [Valor Mes Anterior]
RETURN
DIVIDE(vAtual - vAnterior, vAnterior, 0)
```

#### Indicador 5.4: Comparativo com o Mesmo Período do Ano Anterior (SPLY / YoY %)
```dax
Valor Ano Anterior = 
CALCULATE(
    [Valor Total],
    SAMEPERIODLASTYEAR('dCalendario'[DTC_COMPLETA])
)

Crescimento YoY % = 
VAR vAtual = [Valor Total]
VAR vPassado = [Valor Ano Anterior]
RETURN
DIVIDE(vAtual - vPassado, vPassado, 0)
```

---

<a id="66-auditoria-inatividade"></a>
### 📁 Pasta: `06. Auditoria de Dados e Inatividade`

#### Indicador 6.1: Casos Parados em Gargalo Crítico (> 30 Dias)
* **Conceito:** Contagem de itens ou processos ativos que não registraram nenhuma movimentação na unidade atual por mais de 30 dias.
```dax
Casos Criticos (> 30d Parados) = 
CALCULATE(
    COUNTROWS('<FATO_TABELA_2>'),
    '<FATO_TABELA_2>'[DIAS_PARADO] > 30
)
```

---

<a id="7-segmentadores-recomendados"></a>
## 7. Mapeamento de Segmentadores Recomendados (Filtros do Painel)

Para garantir fluidez na navegação do usuário e padronização visual corporativa, utilize os seguintes segmentadores:

| Nome do Filtro no Dashboard | Campo Recomendado | Tabela de Origem | Configuração / Comportamento Sugerido |
| :--- | :--- | :--- | :--- |
| **Ano / Semestre / Mês** | `NUM_ANO`, `DES_SEMESTRE`, `DES_MES_ANO` | `dCalendario` | Hierarquia temporal corporativa em cascata ou lista horizontal suspensa. Habilitar **Sincronizar Segmentações** (*Sync Slicers*) em todas as páginas. |
| **Órgão / Departamento** | `<NOM_DEPARTAMENTO>` | `<DIM_ENTIDADE_2>` | Menu suspenso (Dropdown) com opção de pesquisa por digitação ativada. |
| **Categoria / Grupo** | `<DES_CATEGORIA>` | `<DIM_ENTIDADE_1>` | Seleção múltipla com botão "Selecionar Tudo". |
| **Situação / Status** | `<DES_STATUS>` | `<DIM_STATUS>` | Botões horizontais ou segmentador de bloco com seleção simples. |
| **Indicador Binário (Flag)** | `<IND_FLAG>` | `<DIM_ENTIDADE_1>` | Botão alternador (Sim/Não) para análises de elegibilidade ou vigência. |

---

<a id="8-estrutura-visual-mockup"></a>
## 8. Proposta de Estrutura Visual para o Mockup / Páginas

Recomenda-se estruturar o relatório em **4 Páginas Temáticas**, respeitando as convenções corporativas de design analítico:

```text
┌────────────────────────────────────────────────────────────────────────┐
│ [CABEÇALHO] Logotipo do Órgão | Título do Painel | Filtros Globais     │
├────────────────────────────────────────────────────────────────────────┤
│ [CARDS KPI] [ Valor Total ] [ Qtd Entidades ] [ Tempo Médio ] [ % Meta]│
├──────────────────────────────────┬─────────────────────────────────────┤
│ [GRÁFICO 1] Evolução Mensal      │ [GRÁFICO 2] Comparativo com Metas   │
│ (Linha com tendência e projeção) │ (Barras horizontais com meta-guia)  │
├──────────────────────────────────┴─────────────────────────────────────┤
│ [MATRIZ ANALÍTICA] Detalhamento por Unidade / Categoria                │
│ (Com barras de dados condicionais e drill-through para nível analítico)│
└────────────────────────────────────────────────────────────────────────┘
```

### 📄 Página 1: Visão Executiva & Estratégica
* **Linha Superior:** 4 a 5 Cartões KPI com as métricas consolidadas (`[Valor Total]`, `[Total Entidades Distintas]`, `[Taxa de Resolucao %]`, `[% Atingimento Meta]`).
* **Corpo Principal:** 
  * Gráfico de Linha ou Área: Evolução histórica mensal com comparativo YoY.
  * Gráfico de Barras: Distribuição dos valores pelas principais secretarias ou departamentos.
  * Segmentador temporal corporativo sincronizado.

### 📄 Página 2: Prazos, SLA e Gestão de Metas
* **Foco:** Acompanhamento de eficiência operacional e conformidade com metas estipuladas.
* **Componentes:**
  * Indicadores de Velocímetro (*Gauge*) ou Cartões com Barra de Progresso (% de atingimento por edital/categoria).
  * Matriz de SLA: Tempo médio decorrido por tipo de ocorrência.
  * Gráfico de dispersão ou pareto para identificar onde estão concentrados os atrasos.

### 📄 Página 3: Detalhamento Operacional & Drill-Down
* **Foco:** Visão tática para coordenadores e analistas setoriais.
* **Componentes:**
  * Matriz analítica hierárquica: Órgão ➔ Departamento ➔ Responsável ➔ Volumes ➔ Valores.
  * Formatação condicional: Destaque em vermelho para casos estagnados há mais de 30 dias.
  * Botão de exportação para Excel dos dados sumarizados.

### 📄 Página 4: Auditoria de Dados e Governança
* **Foco:** Monitoramento da qualidade e atualização das fontes.
* **Componentes:**
  * Tabela de status da última carga no Oracle (via `TB_CONTROLE_CARGA`).
  * Contagem de registros órfãos ou classificados como `-1` (Não Informado).
  * Resumo de usuários inativos ou permissões expiradas.

---

<a id="9-consultas-conferencia"></a>
## 9. Consultas Rápidas de Conferência (Power BI vs. Oracle SQL)

Para validar a integridade matemática dos números exibidos no Power BI antes da homologação final, execute as consultas abaixo diretamente no banco de homologação Oracle (`SQL Developer` ou `DBeaver`):

```sql
-- 1. Conferência do Volume Total e Métricas Globais por Ano
SELECT 
    T.NUM_ANO,
    COUNT(*)                             AS TOTAL_REGISTROS,
    SUM(F.<COLUNA_METRICA_VALOR>)        AS VALOR_TOTAL_CONSOLIDADO,
    COUNT(DISTINCT F.<COLUNA_FK_ENTIDADE>) AS QTD_ENTIDADES_DISTINTAS
FROM <SCHEMA_OWNER>.<FATO_TABELA_1> F
JOIN <SCHEMA_OWNER>.<DIM_TEMPO> T 
  ON F.<COLUNA_DATA_FK> = T.DIMENSION_KEY
WHERE F.<COLUNA_FK_ENTIDADE> <> -1
GROUP BY T.NUM_ANO
ORDER BY T.NUM_ANO DESC;

-- 2. Conferência de SLA e Tempos Médios de Atendimento
SELECT 
    D.<NOM_CATEGORIA>,
    COUNT(*)                             AS QTD_CASOS_CONCLUIDOS,
    ROUND(AVG(F.<DIAS_ATENDIMENTO>), 2)  AS TEMPO_MEDIO_DIAS,
    COUNT(CASE WHEN F.<DIAS_PARADO> > 30 THEN 1 END) AS CASOS_CRITICOS_MAIOR_30D
FROM <SCHEMA_OWNER>.<FATO_TABELA_2> F
JOIN <SCHEMA_OWNER>.<DIM_ENTIDADE_1> D 
  ON F.<COLUNA_SK_1> = D.<COLUNA_SK_1>
GROUP BY D.<NOM_CATEGORIA>
ORDER BY TEMPO_MEDIO_DIAS DESC;

-- 3. Verificação de Registros Não Informados (Linha Sentinela -1)
SELECT 
    COUNT(CASE WHEN <COLUNA_SK_1> = -1 THEN 1 END) AS QTD_ORFAOS_ENTIDADE_1,
    COUNT(CASE WHEN <COLUNA_SK_2> = -1 THEN 1 END) AS QTD_ORFAOS_ENTIDADE_2
FROM <SCHEMA_OWNER>.<FATO_TABELA_1>;
```

---

<a id="10-checklist-qualidade"></a>
## 10. Checklist de Qualidade Pré-Publicação

Antes de submeter o painel à homologação dos gestores de negócio, certifique-se de que todos os itens abaixo foram cumpridos:

- [ ] **Relacionamentos:** Todos os relacionamentos configurados como **1 para Muitos (1:*)** e Direção de Filtro Cruzado **Única (Single)**.
- [ ] **Ocultação de Chaves:** Todas as Surrogate Keys (`DIMENSION_KEY`, `SK_*`) e chaves estrangeiras (`FK_*`) foram ocultadas na exibição de relatório.
- [ ] **Tabela de Data Oficial:** A dimensão calendário (`dCalendario`) está oficialmente marcada como *Tabela de Data* utilizando a coluna `DTC_COMPLETA`.
- [ ] **Classificação Cronológica:** As colunas `DES_MES`, `DES_MES_ANO` e `DES_SEMESTRE` foram classificadas pelas suas respectivas colunas numéricas (*Sort by Column*).
- [ ] **Tabela de Medidas Centralizada:** Todas as métricas foram criadas explicitamente no DAX dentro da tabela `_Medidas_<NOME_PROJETO>` e organizadas em pastas temáticas.
- [ ] **Divisões Seguras:** 100% das divisões matemáticas utilizam a função `DIVIDE(numerador, denominador, 0)`.
- [ ] **Tratamento de Linha -1:** Métricas de contagem distinta filtram explicitamente a chave `-1` para evitar distorções no cálculo de entidades atendidas.
- [ ] **Sincronização de Filtros:** Os segmentadores de ano, semestre e departamento estão sincronizados (*Sync Slicers*) entre as páginas do relatório.
- [ ] **Bate de Valores (Conciliação):** Os totais dos cartões KPI conferem rigorosamente com as consultas SQL executadas no Oracle.
- [ ] **Performance VertiPaq:** O arquivo `.pbix` está salvo em modo de importação e o tamanho total em disco é compatível com o workspace corporativo.
