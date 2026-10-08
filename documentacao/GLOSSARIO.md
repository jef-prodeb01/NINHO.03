# Glossário de Engenharia de Dados, DW & Analytics

Este documento é a referência conceitual unificada da plataforma **NINHO**, nivelando o vocabulário técnico entre Engenheiros de Dados, Arquitetos de DW, Analistas de BI e Gestores de Negócio.

---

## 🏛️ Conceitos Fundamentais de Data Warehouse

### 1. Modelo Estrela (Star Schema)
Arquitetura dimensional preconizada por Ralph Kimball onde uma ou mais **Tabelas Fato** ficam centralizadas e conectam-se diretamente às **Tabelas Dimensão**. É o padrão ouro para relatórios no Power BI e Apache Superset, pois elimina joins complexos em cascata (floco de neve) e maximiza a performance do motor colunar VertiPaq.

### 2. Tabela Fato (`FATO_*`)
Tabela que armazena os eventos quantitativos e transações do negócio (ex: *uma venda realizada, um processo judicial protocolado, um gasto de computação em nuvem*). Contém:
- **Chaves Estrangeiras (FKs):** Apontam para as Surrogate Keys das dimensões.
- **Métricas e Fatos:** Números que podem ser somados, calculados ou medidos (valores monetários, durações, contagens).
- **Grão (Granularidade):** O significado exato de uma linha na tabela (ex: *1 linha por item de nota fiscal*).

### 3. Tabela Dimensão (`DIM_*`)
Tabela que contém os atributos de contexto descritivo que qualificam o fato (ex: *quem comprou, onde ocorreu, qual status foi atribuído*). Responde às perguntas: *Quem? Onde? Quando? Qual tipo?*.

### 4. Surrogate Key (Chave Substituta / `DIMENSION_KEY`)
Chave primária artificial do tipo numérico inteiro gerada no Data Warehouse (geralmente via `SEQUENCE` no Oracle).  
*Por que usamos?* Desacopla o DW das chaves primárias dos sistemas transacionais de origem (que podem ser alteradas, recicladas ou reutilizadas), permitindo versionar o histórico da mesma entidade.

### 5. Dimensão de Alteração Lenta Tipo 2 (SCD Tipo 2 - Slowly Changing Dimension)
Técnica que preserva o histórico completo das alterações de um cadastro criando uma nova linha na dimensão a cada mudança relevante, mantendo:
- `DTC_EFETIVACAO`: Momento em que a versão passou a vigorar.
- `DTC_EXPIRACAO`: Momento em que a versão foi substituída (NULL ou `2999-12-31` para a versão atual).
- `DES_ATUALIZAR` / `SIN_ATIVO`: Flags técnicas para controle de vigência.

### 6. Linha Técnica `-1` (Kimball Unknown Record)
Registro padrão obrigatório presente em todas as tabelas dimensão corporativas com `DIMENSION_KEY = -1` e descrição `'NÃO INFORMADO'` ou `'NÃO SE APLICA'`.  
*Benefício:* Se uma transação da fato tiver uma dimensão ausente ou nula na origem, a chave estrangeira é preenchida com `-1` via `NVL()`. Isso impede que a carga quebre por erro de chave estrangeira (`ORA-02291`) e elimina valores em branco (`Blank`) indesejados no Power BI.

### 7. Dimensão Conformada (Conformed Dimension)
Uma dimensão compartilhada e consistente entre múltiplos Data Marts ou áreas da organização. O principal exemplo é a **`DIM_TEMPO`**, que garante que "Semestre", "Mês" e "Ano" tenham exatamente a mesma definição matemática para todas as secretarias e setores.

---

## ⚡ Estratégias de Carga & Performance (Dual Strategy)

### 8. Estratégia A: Truncate & Load Massivo
Estratégia onde a tabela fato tem seus dados limpos (`TRUNCATE`) e recarregados integralmente em cada ciclo de ETL.
- **Indicação:** Tabelas com volume moderado (< 5 a 10 milhões de linhas) que processam em poucos minutos.
- **Vantagem:** Permite o uso de **Índices Bitmap**, altamente comprimidos e velozes para consultas analíticas.
- **Requisito Obrigatório:** Execução da procedure `PRC_POS_CARGA_FATO` para rebuild `NOLOGGING` dos índices e atualização de estatísticas (`DBMS_STATS`).

### 9. Estratégia B: Incremental Idempotente via `MERGE INTO`
Estratégia onde o ETL identifica apenas os dados novos ou alterados (*Delta / CDC*) e aplica um comando `MERGE INTO` no Oracle.
- **Indicação:** Tabelas volumosas (dezenas ou centenas de milhões de linhas) onde recarregar tudo seria inviável.
- **Regra de Ouro:** Uso exclusivo de **Índices B-Tree**. O uso de Bitmap em tabelas sob `MERGE` causa travamento em nível de bloco e deadlocks (`ORA-00060`).

### 10. Idempotência
Propriedade de uma rotina de carga que pode ser executada múltiplas vezes para o mesmo período sem gerar dados duplicados, registros inconsistentes ou estados inválidos no banco de dados.

---

## 📊 Business Intelligence & Camada Semântica

### 11. VertiPaq Engine
Motor colunar de análise em memória utilizado pelo **Microsoft Power BI (Import Mode)**. Comprime colunas repetitivas em alta taxa e garante tempos de resposta sub-segundo para filtros e agregações.

### 12. Medida Explícita vs. Implícita (DAX)
- **Medida Implícita (Proibida):** Arrastar uma coluna crua da tabela para o gráfico e deixar o Power BI somar.
- **Medida Explícita (Obrigatória):** Escrever a fórmula formalmente em DAX (ex: `Total Vendas = SUM(FATO[VALOR])`). Permite reaproveitamento em cálculos temporais, documentação e formatação rigorosa.

### 13. Divisão Segura (`DIVIDE`)
Função DAX que trata nativamente divisões por zero ou valores nulos, evitando erros como `Infinity` ou `NaN` nos dashboards executivos (`DIVIDE(Numerador, Denominador, 0)`).

### 14. Inteligência Temporal (Time Intelligence)
Fórmulas analíticas avançadas para comparação de períodos no tempo:
- **YTD (Year-to-Date):** Acumulado do primeiro dia do ano até a data selecionada.
- **MoM (Month-over-Month):** Variação percentual ou nominal em relação ao mês anterior.
- **YoY (Year-over-Year):** Comparativo direto com o mesmo período do ano anterior.

### 15. Camada Semântica (`VW_EVENTO`, `VW_KPI_*`, `META_*`)
Camada de abstração corporativa composta por views pré-resolvidas e 8 tabelas de catálogo ativo que traduzem os nomes técnicos do banco de dados para a linguagem de negócios compreensível por humanos e modelos de Inteligência Artificial.

