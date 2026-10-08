# INTAKE_DW.md — Formulário de Entrada do Planejador de DW

Preencha este formulário com as informações do novo projeto. O **Planejador de DW** utilizará esses dados para projetar as camadas (`STG_*`, `ODI_DIM_*`, `DIM_*`, `FATO_*`), definir a estratégia de carga (Truncate & Load vs. MERGE), configurar as ferramentas de ingestão (ODI, Hop, Python) e gerar os DDLs otimizados na pasta `saida/planejador_dw/<NOME_PROJETO>/`.

---

## Seção 0 — Identificação do Projeto & Ambiente

- **Nome do Projeto:** `[Ex: SEI_BAHIA, COAPS_FINOPS, DGO_DEIC, FINANCEIRO_CENTRAL]`
- **Engenheiro Responsável:** `[Nome completo]`
- **Schema Alvo no Oracle:** `[Ex: SEIMUNICIPIO_OLAP, GESTAODIS_OLAP]`
- **Tablespace de Dados:** `[Ex: SEIMUNICIPIO_DATA, GESTAODIS_DATA]`
- **Tablespace de Índices:** `[Ex: SEIMUNICIPIO_IDX, GESTAODIS_IDX (ou a mesma de dados)]`
- **Tabela `TB_CONTROLE_CARGA` já existe no schema?**
  - [ ] Sim (reutilizar)
  - [ ] Não (gerar no script `01_tb_controle_carga.sql`)

---

## Seção 1 — O que o Cliente Quer (Perguntas & Casos de Uso)

> *Liste de 5 a 15 perguntas de negócio que o DW deve responder com precisão.*

1. `[Ex: Quantos documentos foram gerados por órgão e unidade no último mês?]`
2. `[Ex: Qual o custo diário de infraestrutura e memória por cluster e projeto?]`
3. `[Ex: Qual a quantidade de ações policiais com apreensão de armas por município?]`
4. `...`

- **Público-alvo principal:**
  - [ ] Diretoria / Gestão Executiva (Dashboards analíticos consolidados)
  - [ ] Analistas Operacionais (Consultas ad-hoc analíticas no detalhe)
  - [ ] Modelos de IA / Data Science (Alimentação de algoritmos e LLMs corporativos)
- **Ferramenta de BI / Consumo Final Prevista:**
  - [ ] Power BI (Import Mode, Star Schema puro, medidas DAX explícitas)
  - [ ] Apache Superset (Datasets declarativos em YAML com métricas SQL)
  - [ ] Módulo de Camada Semântica Corporativa (Views `EVENTO` e 8 tabelas `META_*`)

---

## Seção 2 — Regras de Negócio e Estratégia de Carga

### 2.1 Grão e Métricas da Fato
- **Grão esperado da Fato principal:**  
  *Ex: "Uma linha para cada documento gerado", "Uma linha para cada combinação de dia, cluster e projeto".*
- **Medidas e Fórmulas de Cálculo:**
  - Medida 1: `[Ex: TOT_DOCUMENTO - Contagem simples de ocorrências (valor 1)]`
  - Medida 2: `[Ex: VAL_CUSTO_TOTAL - Soma monetária de custos diretos e distribuídos]`
  - Medida 3: `[Ex: QTD_CPU_CORES - Consumo médio de núcleos de processador]`
  - Medida 4: `...`

### 2.2 Seleção da Estratégia de Carga da Fato
- **Qual estratégia atende melhor o caso de uso?**
  - [ ] **Estratégia A: Truncate & Load Massivo (Padrão SEI Bahia / OLTP)**
    - Carga em lote noturno (D-1 ou janela móvel de N meses).
    - Tabelas indexadas com **BITMAP INDEX** nas FKs (`DIM_*`) para Star Transformation no Oracle CBO.
    - Execução obrigatória da procedure `PRC_POS_CARGA_FATO` pós-carga (rebuild NOLOGGING e stats).
  - [ ] **Estratégia B: Incremental Idempotente via `MERGE INTO` (Padrão FinOps / Telemetria)**
    - Carga contínua intra-dia ou diária a partir de APIs e microsserviços.
    - Tabelas indexadas exclusivamente com **B-TREE INDEX** em chaves compostas (sem Bitmaps para evitar deadlocks `ORA-00060`).
    - Lógica `WHEN MATCHED THEN UPDATE / WHEN NOT MATCHED THEN INSERT`.

### 2.3 Histórico e Vigência das Dimensões (SCD - Slowly Changing Dimensions)
- Se um atributo descritivo mudar (ex: órgão do usuário, nome da unidade), o cliente deseja:
  - [ ] Manter histórico completo de versões (SCD Tipo 2 com `DTC_EFETIVACAO`, `DTC_EXPIRACAO` e `ODI_DIM_*`) — *(Padrão Corporativo Obrigatório)*
  - [ ] Apenas sobrescrever o valor corrigido (SCD Tipo 1)

### 2.4 Retenção e Particionamento
- Quantos anos de histórico devem ser mantidos no DW? `[Ex: 5 anos, perpétuo]`
- Particionamento desejado?
  - [ ] Sim (Range ou Interval por `DIM_TEMPO` para fatos > 10M linhas)
  - [ ] Não (tabela monolítica padrão)

---

## Seção 3 — Inventário Técnico de Fontes de Dados

### 3.1 Fontes Banco de Dados (Direcionadas ao ODI)
*Coloque os DDLs correspondentes em `modulos/planejador_dw/entrada/ddl/` e amostras em `entrada/amostras/`.*
- **Origem:** `[Ex: Oracle OLTP Sistema X, Postgres ERP Y]`
- **Tabelas de Origem:** `[Ex: TAB_PROCESSO, TAB_UNIDADE]`
- **Mecanismo de Leitura:** `[Ex: DBLink Oracle, Conexão JDBC direta no ODI]`
- **Campos de Controle de Carga:** `[Ex: Possui coluna DT_ATUALIZACAO? Sim / Não]`

### 3.2 Fontes Arquivos e Planilhas em FTP/SFTP (Direcionadas ao Apache Hop)
*Coloque amostras de arquivos em `modulos/planejador_dw/entrada/arquivos_ftp/`.*
- **Protocolo:** `[SFTP / FTP / Compartilhamento de Rede / S3]`
- **Formato:** `[CSV, Excel (.xlsx/.xls), TXT]`
- **Frequência de Chegada:** `[Ex: Diário às 06h, Semanal]`
- **Delimitador & Encoding:** `[Ex: Ponto e vírgula (;), UTF-8 / ISO-8859-1]`

### 3.3 Fontes APIs Web & Tratamentos Complexos (Direcionadas ao Python)
*Coloque exemplos reais de payload JSON de resposta em `modulos/planejador_dw/entrada/api_specs/`.*
- **Tipo de Serviço:** `[REST / JSON / Webhook]`
- **Método de Autenticação:** `[Bearer Token, OAuth2 Client Credentials, API Key]`
- **Paginação:** `[Por offset (?offset=100), por página (?page=1), por cursor]`
- **Complexidade:** `[Estruturas JSON aninhadas, necessidade de regex avançado]`

---

## Seção 4 — Volumetria e Dimensionamento (Para Sizing dos DBAs)

- **Volume Total Atual na Origem (estimativa de linhas):** `[Ex: 5.000.000 de linhas]`
- **Volume Novo Esperado por Dia/Mês:** `[Ex: 100.000 linhas/mês]`
- **Tamanho Médio de Linha na Origem (ou anexe amostras):** `[Ex: ~250 bytes]`

---

## Seção 5 — Parâmetros de Disparo Remoto (`OdiOSCommand`)

*Informações para geração automática do comando de disparo SSH no ODI:*
- **Host / Servidor de Execução:** `[Ex: srv-etl-hop01.empresa.gov.br]`
- **Usuário SSH:** `[Ex: usr_odi_exec]`
- **Caminho dos Scripts no Servidor:** `[Ex: /opt/etl/hop/pipelines/ ou /opt/etl/python/]`
