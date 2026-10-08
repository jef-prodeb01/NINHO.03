# INTAKE_DW.md — Formulário de Entrada do Planejador de DW

Preencha este formulário com as informações do novo projeto. O **Planejador de DW** utilizará esses dados para projetar as camadas (STG, ODI_DIM, DIM, FATO), definir as esteiras de ingestão (ODI, Hop, Python) e gerar os DDLs otimizados.

---

## Seção 0 — Identificação do Projeto & Ambiente

- **Nome do Projeto:** `[Ex: SEI_MUNICIPAL, DGO_DEIC, FINANCEIRO_CENTRAL]`
- **Engenheiro Responsável:** `[Nome completo]`
- **Schema Alvo no Oracle:** `[Ex: SEIMUNICIPIO_OLAP, DGO_OLAP]`
- **Tablespace de Dados:** `[Ex: SEIMUNICIPIO_DATA, DGO_DATA]`
- **Tablespace de Índices:** `[Ex: SEIMUNICIPIO_IDX, DGO_IDX (ou a mesma de dados)]`
- **Tabela `TB_CONTROLE_CARGA` já existe no schema?**
  - [ ] Sim
  - [ ] Não (gerar no script de DDL)

---

## Seção 1 — O que o Cliente Quer (Perguntas & Casos de Uso)

> *Liste de 5 a 15 perguntas de negócio que o DW deve responder perfeitamente.*

1. `[Ex: Quantos documentos foram gerados por órgão e unidade no último mês?]`
2. `[Ex: Qual a quantidade de ações policiais com apreensão de drogas por município?]`
3. `[Ex: Quantos flagrantes ocorreram por fase de operação?]`
4. `...`

- **Público-alvo principal:**
  - [ ] Diretoria / Gestão (Dashboards executivos consolidados)
  - [ ] Analistas Operacionais (Consultas ad-hoc analíticas no detalhe)
  - [ ] Modelos de IA / Data Science (Alimentação de algoritmos e LLMs)
- **Janela e Frequência de Atualização Desejada:**
  - [ ] Carga Noturna Diária (D-1)
  - [ ] Micro-lotes intra-dia (ex: a cada 1 hora)
  - [ ] Carga Mensal / Fechamento

---

## Seção 2 — Regras de Negócio do Cliente

### 2.1 Grão e Métricas
- **Grão esperado da Fato principal:**  
  *Ex: "Uma linha para cada documento gerado", "Uma linha para cada ação policial realizada".*
- **Medidas e Fórmulas de Cálculo:**
  - Medida 1: `[Ex: QTD_DOCUMENTO - Contagem simples de ocorrências (valor 1)]`
  - Medida 2: `[Ex: QTD_ARMAS - Soma das armas apreendidas constantes na ação]`
  - Medida 3: `...`

### 2.2 Histórico e Vigência (SCD - Slowly Changing Dimensions)
- Se um atributo cadastral mudar (ex: órgão do usuário, nome da unidade), o cliente deseja:
  - [ ] Manter histórico completo de versões (SCD Tipo 2 com `DTC_EFETIVACAO` e `DTC_EXPIRACAO`) — *(Padrão Corporativo)*
  - [ ] Apenas sobrescrever o valor corrigido (SCD Tipo 1)

### 2.3 Retenção de Dados
- Quantos anos de histórico devem ser mantidos no DW? `[Ex: 5 anos, histórico perpétuo]`

---

## Seção 3 — Inventário Técnico de Fontes de Dados

### 3.1 Fontes Banco de Dados (Direcionadas ao ODI)
*Coloque os DDLs correspondentes em `entrega/ddl/`.*
- **Origem:** `[Ex: Oracle OLTP Sistema X, Postgres ERP Y]`
- **Tabelas de Origem:** `[Ex: TAB_PROCESSO, TAB_ORGAO]`
- **Mecanismo de Leitura:** `[Ex: DBLink Oracle, Conexão JDBC direta no ODI]`
- **Campos de Controle de Carga:** `[Ex: Possui coluna DT_ATUALIZACAO? Sim / Não]`

### 3.2 Fontes Arquivos e Planilhas em FTP/SFTP (Direcionadas ao Apache Hop)
*Coloque amostras de arquivos em `entrega/arquivos_ftp/`.*
- **Protocolo:** `[SFTP / FTP / Pasta de Rede]`
- **Formato:** `[CSV, Excel (.xlsx/.xls), TXT]`
- **Frequência de Chegada:** `[Ex: Diário às 06h, Semanal]`
- **Delimitador & Encoding:** `[Ex: Ponto e vírgula (;), UTF-8 / ISO-8859-1]`

### 3.3 Fontes APIs Web & Tratamentos Complexos (Direcionadas ao Python)
*Coloque amostras de JSON de resposta em `entrega/api_specs/`.*
- **Tipo de Serviço:** `[REST / SOAP / Webhook]`
- **Método de Autenticação:** `[Bearer Token, OAuth2, Basic, API Key]`
- **Paginação:** `[Ex: Por página (?page=1), por offset (?offset=100), cursor]`
- **Complexidade:** `[Ex: JSON com listas aninhadas, necessidade de regex avançado]`

---

## Seção 4 — Volumetria e Dimensionamento (Para Sizing dos DBAs)

- **Volume Total Atual na Origem (estimativa de linhas):** `[Ex: 2.000.000 de linhas]`
- **Volume Novo Esperado por Dia/Mês:** `[Ex: 50.000 linhas/mês]`
- **Tamanho Médio de Linha na Origem (ou anexe amostras):** `[Ex: ~200 bytes]`

---

## Seção 5 — Parâmetros de Disparo Remoto (`OdiOSCommand`)

*Informações para geração automática do comando de disparo SSH no ODI:*
- **Host / Servidor de Execução:** `[Ex: srv-etl-hop01.empresa.gov.br]`
- **Usuário SSH:** `[Ex: usr_odi_exec]`
- **Caminho dos Scripts no Servidor:** `[Ex: /opt/etl/hop/pipelines/ ou /opt/etl/python/]`
