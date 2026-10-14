# Arquitetura de Fatos Híbridas (Dual / Multi-Fact Architecture)

Este documento estabelece o padrão arquitetural para cenários de **altíssima volumetria** (tabelas transacionais de origem com dezenas, centenas de milhões ou bilhões de linhas), inspirado no caso de produção do **SEI Bahia** (onde a tabela transacional de atividades acumula ~1 bilhão de registros em 9.5 anos).

---

## 🛑 O Problema da Fato Única ("Tudo em Um")

Em sistemas OLTP com alta taxa de transação (processos, logs, movimentações bancárias, chamados, eventos IoT), tentar criar uma única tabela fato no grão mais baixo (grão de evento atômico) para todo o histórico acarreta:
1. **Janelas de Carga Inviáveis:** O ETL estoura a janela noturna de processamento ou satura tablespaces temporárias (`UNDO`/`TEMP`).
2. **Degradação Severa no Power BI / BI Tools:** Consultas agregadas tornam-se lentas e o modelo estoura o limite de memória do engine VertiPaq.
3. **Conflito de Grãos:** Usuários precisam ao mesmo tempo de séries temporais de 10 anos e de rastreabilidade fina dos processos ativos recentes.

---

## 🏛️ A Solução: Divisão em 3 Fatos Especializadas

O padrão arquitetural divide o domínio em **três tabelas fato complementares**, cada uma atendendo a um propósito analítico e de performance bem definido:

| Tabela Fato | Granularidade / Escopo | Volumetria Estimada | Finalidade no BI / Dashboards |
| :--- | :--- | :--- | :--- |
| **1. Fato Histórica Agregada**<br>(`FATO_<PROJETO>_AGR_MENSAL`) | Grão Periódico:<br>**Mês x Unidade x Usuário x Categoria**<br>(Todo o histórico: 5 a 10+ anos) | Redução de até **98%**<br>(ex: de 1 bilhão para ~16 milhões de linhas) | **Paineis Executivos e Gerenciais:**<br>Tendências anuais, volume total, taxas de crescimento, produtividade e tempo médio. |
| **2. Fato Snapshot Recente**<br>(`FATO_<PROJETO>_SITUACAO_ATUAL`) | Grão de Entidade:<br>**1 linha por entidade ativa nos últimos N meses**<br>(Janela móvel: ex: 3 a 6 meses) | Compacta<br>(ex: ~1 milhão de linhas) | **Matriz de SLA e Operação:**<br>Última movimentação, dias parado na unidade atual, status de conclusão e tempo de vida. |
| **3. Fato Linha do Tempo**<br>(`FATO_<PROJETO>_ANDAMENTO`) | Grão de Evento Filtrado:<br>**Histórico de eventos relevantes** das entidades ativas (filtro de relevância funcional) | Moderada<br>(ex: ~25 a 30 milhões de linhas) | **Rastreabilidade e Detalhamento:**<br>Páginas de auditoria, histórico de tramitações e ações individuais por usuário. |

---

## 📐 Estrutura Detalhada de Cada Fato

### 1. Fato Histórica Agregada (`FATO_<PROJETO>_AGR_MENSAL`)
* **Grão Físico:** Um registro por Mês de Referência + Chaves Estrangeiras das Dimensões Centrais.
* **Técnica de Carga:** Agrupamento prévio (`GROUP BY TRUNC(DATA, 'MM'), FK_DIM1, FK_DIM2...`).
* **Métricas Pré-calculadas:**
  * `TOT_PROCESSOS_GERADOS`
  * `TOT_PROCESSOS_RECEBIDOS`
  * `TOT_PROCESSOS_CONCLUIDOS`
  * `VAL_SOMA_DIAS_ATENDIMENTO` (para cálculo ponderado de tempo médio no DAX)
  * `QTD_PROCESSOS_COM_SLA`
* **Performance:** Carregamento ultra-rápido; possibilita que os dashboards principais abram instantaneamente no Power BI.

---

### 2. Fato Snapshot de Estado Atual (`FATO_<PROJETO>_SITUACAO_ATUAL`)
* **Grão Físico:** Uma linha para cada entidade de negócio ativa.
* **Técnica de Carga:** Janela analítica na Staging com `ROW_NUMBER() OVER (PARTITION BY ID_ENTIDADE ORDER BY DTH_MOVIMENTACAO DESC) = 1`.
* **Atributos Chave:**
  * `DIM_UNIDADE_ATUAL`
  * `DIM_USUARIO_ATUAL`
  * `DIM_TAREFA_ULTIMA`
  * `DTH_ULTIMA_MOVIMENTACAO`
  * `NUM_DIAS_VIDA` (dias corridos desde a abertura)
  * `NUM_DIAS_PARADO_UNIDADE` (dias desde a última movimentação)
  * `DES_STATUS_CONCLUSAO` ('Em Andamento' / 'Concluído')
* **Finalidade:** Responder perguntas como: *"Quais processos estão travados há mais de 30 dias na secretaria X?"*.

---

### 3. Fato Linha do Tempo / Andamentos (`FATO_<PROJETO>_ANDAMENTO`)
* **Grão Físico:** Uma linha por evento ou transação relevante executada na entidade.
* **Filtro de Relevância Funcional:**
  * Descarte de micro-ações de sistema (ex: atualizações de índice de busca, notificações automáticas, logs de auditoria técnica interna).
  * Apenas ações com impacto de negócio (ex: `WHERE TAREFA.SIN_HISTORICO_RESUMIDO = 'S'`).
* **Relacionamento no BI:**
  * Conecta em formato Mestre-Detalhe com a Fato Snapshot (`FATO_SITUACAO_ATUAL [ID_ENTIDADE] 1:N FATO_ANDAMENTO [ID_ENTIDADE]`).

---

## 💡 Guia de Decisão para o Arquiteto

| Critério | Aplicar Star Schema Simples (1 Fato) | Aplicar Arquitetura de Fatos Híbridas (3 Fatos) |
| :--- | :--- | :--- |
| **Volumetria da Origem** | Abaixo de 20 milhões de linhas. | **Acima de 50 a 100 milhões de linhas (ou bilhões).** |
| **Período Histórico** | 1 a 3 anos. | **Mais de 5 a 10 anos de histórico acumulado.** |
| **Perfil de Acesso** | Consultas sempre no mesmo grão. | **Executivos querem visão macro anual; Operação quer a situação atual e SLA.** |
| **Complexidade de Eventos** | Evento pontual simples. | **Entidades de vida longa com dezenas de movimentações e andamentos.** |
