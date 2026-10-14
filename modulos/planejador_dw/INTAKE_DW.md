# INTAKE_DW.md — Formulário de Entrada do Planejador de DW

Preencha este formulário com as informações do projeto. O **Planejador de DW** utilizará esses dados para projetar as camadas (`STG_*`, `ODI_DIM_*`, `DIM_*`, `FATO_*`), definir a estratégia de carga (Truncate & Load vs. MERGE), configurar as ferramentas de ingestão autorizadas e gerar os artefatos diretamente na pasta `saida/planejador_dw/`.

> ⚠️ **AVISO AO ENGENHEIRO DE DADOS:**  
> A IA iniciará o processo conferindo este formulário. Se campos obrigatórios ou as caixas de seleção de tecnologias estiverem vazios, a IA pausará o atendimento e solicitará o preenchimento deste link antes de prosseguir.

---

## Seção 0 — Identificação do Projeto & Ambiente

- **Nome do Projeto:** `[Ex: SEI_BAHIA, COAPS_FINOPS, DGO_DEIC, RH_BAHIA]`
- **Engenheiro de Dados Responsável:** `[Nome completo do engenheiro]`
- **Schema Alvo no Oracle:** `[Ex: SEIMUNICIPIO_OLAP, RH_BAHIA_OLAP]`
- **Tablespace de Dados:** `[Ex: SEIMUNICIPIO_DATA, RH_BAHIA_DATA]`
- **Tablespace de Índices:** `[Ex: SEIMUNICIPIO_IDX, RH_BAHIA_IDX (ou a mesma de dados)]`

### 0.1 Natureza da Execução
- [ ] **Projeto Novo do Zero:** Criação de novo DW completo no schema alvo.
- [ ] **Evolução / Adaptação:** Adição de novas fatos/dimensões a um schema já existente.

### 0.2 Tabela de Auditoria `TB_CONTROLE_CARGA`
- [ ] **Já existe no schema alvo** (reutilizar existente, não gerar script de criação).
- [ ] **Não existe** (gerar script `01_tb_controle_carga.sql` com estrutura corporativa).

---

## Seção 1 — Seleção de Tecnologias da Esteira (MANDATÓRIO)

> 🛑 **REGRA DE CONDICIONALIDADE DE CÓDIGO:**  
> A IA **SOMENTE** gerará código para as tecnologias marcadas com `[x]` abaixo.  
> Qualquer tecnologia desmarcada (`[ ]`) terá a sua geração de scripts **SUMARIAMENTE BLOQUEADA**, evitando criação de arquivos indesejados.

- [ ] **Oracle Data Integrator (ODI):**
  - Mapeamentos de carga direta banco-a-banco via DBLink / JDBC.
  - Orquestração de pacotes, cenários e tabelas auxiliares `ODI_DIM_*`.
  - Consultas SQL analíticas para interfaces/mappings com surrogate keys `SEQ_*.NEXTVAL`, SCD2 e lookups `NVL(dim.KEY, -1)`.
  - *(Se marcado: gera `03_create_odi_dim_tables.sql`, `selects_odi_dimensoes.sql` e `selects_odi_fatos.sql`).*

- [ ] **Apache Hop (.hpl / .hwf):**
  - Pipelines e workflows no Apache Hop 2.x para transformação de dados e orquestração.
  - *(Se marcado: gera arquivos na pasta `06_pipelines_hop/`).*
  - *(Se NÃO marcado: NENHUM arquivo Hop será gerado).*

- [ ] **Ingestão de Arquivos em Lote (SFTP / FTPS / FTP):**
  - Descoberta automatizada de arquivos remotos via Shell Script + `curl` seguro, manifesto CSV e pipeline/workflow Hop.
  - *(Se marcado: gera `extrair_metadados_ftps.sh`, `stg_meta.hpl` e DDL `STG_CONTROLE_ARQUIVOS_FTPS`).*

- [ ] **Extratores Python (.py):**
  - Scripts modulares para consumo de APIs Web REST, autenticação OAuth2 / Bearer Token, paginação e parse de JSON aninhado.
  - *(Se marcado: gera scripts na pasta `07_extratores_python/`).*
  - *(Se NÃO marcado: NENHUM script Python de API será gerado).*

- [ ] **Engenharia Reversa de Dashboard Legado (.pbix / Power BI):**
  - Desconstrução de relatórios Power BI existentes (Layout, visuais, filtros e medidas DAX) para projetar o modelo dimensional DW e produzir o Guia do Analista de BI.
  - *(Se marcado: analisa a pasta `entrega/planejador_dw/` e gera `regras_visuais_origem.md` e `GUIA_ANALISTA_BI_<PROJETO>.md`).*

- [ ] **Procedures PL/SQL Puras / Triggers:**
  - Carga, transformações e manutenção 100% internas no banco Oracle sem ferramentas externas.
  - *(Se marcado: inclui procedures dedicadas na pasta `05_procedimentos_manutencao/`).*

- [ ] **Ingestão Externa Já Existente / Legada:**
  - Os dados já chegam nas tabelas `STG_*` ou tabelas de origem por outra esteira legada já em produção.
  - *(Se marcado: a IA foca apenas na modelagem dimensional `DIM_*` e `FATO_*`, pulando pipelines de ingestão).*

---

## Seção 2 — O que o Cliente Quer (Perguntas & Casos de Uso)

> 💡 **LOCALIZAÇÃO DAS PERGUNTAS DE NEGÓCIO:**  
> As perguntas e casos de uso podem ser preenchidos diretamente aqui OU sinalizados em arquivos na pasta `entrega/planejador_dw/`.

### 2.0 Origem das Perguntas e Regras de Negócio
- [ ] **Opção 1: Perguntas listadas diretamente neste formulário** (preencha a lista 2.1 abaixo).
- [ ] **Opção 2: Perguntas e regras detalhadas em arquivos na pasta `entrega/planejador_dw/`**
  - Marque esta opção caso tenha depositado documentos como editais, regras ou perguntas avulsas.
  - **Arquivo(s) de referência na pasta entrega:** `[Ex: 05_perguntas_negocio.md, 04_regras_negocio.md, edital.md, documentacao.md]`
  - *(A IA inspecionará esses arquivos automaticamente para extrair as necessidades e regras de negócio).*

### 2.1 Perguntas de Negócio (Se Opção 1 selecionada)
1. `[Ex: Qual o percentual de cumprimento de SLA por indicador em cada ciclo mensal?]`
2. `[Ex: Quais chamados violaram o SLA de atendimento com horas excedidas?]`
3. `[Ex: Qual o valor total de glosa contratual apurado por ciclo de faturamento?]`
4. `...`

### 2.2 Público-Alvo Principal
- [ ] Diretoria / Gestão Executiva (Dashboards analíticos consolidados e KPIs estratégicos)
- [ ] Analistas Operacionais (Consultas ad-hoc analíticas no detalhe transacional)
- [ ] Modelos de IA / Data Science / LLMs Corporativos (Alimentação de agentes Text-to-SQL e analítica avançada)

### 2.3 Ferramenta de BI / Consumo Prevista
- [ ] **Power BI:** Import Mode, modelo Star Schema puro, medidas DAX explícitas (gera guia em `08_datasets_bi/`).
- [ ] **Apache Superset:** Datasets declarativos em YAML com métricas SQL compiladas (gera yaml em `08_datasets_bi/`).
- [ ] **Camada Semântica Corporativa:** Views `EVENTO` e metadados nas 8 tabelas `META_*` para IA e Text-to-SQL.
- [ ] **Outras Ferramentas SQL:** Metabase, Tableau, DBeaver.

---

## Seção 3 — Regras de Negócio e Estratégia de Carga (Dual Strategy)

### 3.1 Grão e Métricas da Fato
- [ ] **Extrair grão e fórmulas dos arquivos de entrega:** `[Ex: 04_regras_negocio.md, edital.md]`
- **Ou especificar manualmente abaixo:**
  - **Grão esperado da Fato principal:**  
    *Ex: "Uma linha para cada chamado atendido x ciclo de medição", "Uma linha por item faturado".*
  - **Medidas e Fórmulas de Cálculo:**
    - Medida 1: `[Ex: QTD_CHAMADO - Contagem unitária (valor 1)]`
    - Medida 2: `[Ex: VAL_GLOSA_TOTAL - Soma monetária das penalidades aplicadas]`
    - Medida 3: `[Ex: TEMPO_ATENDIMENTO_HORAS - Horas líquidas despendidas]`
    - Medida 4: `...`

### 3.2 Seleção da Estratégia de Carga da Fato
- [ ] **Estratégia A: Truncate & Load Massivo (Padrão SEI Bahia / OLTP)**
  - Carga em lote noturno (janela móvel ou ciclo completo).
  - Fatos indexadas com **BITMAP INDEX** nas FKs dimensionais (`DIM_*`) para habilitar o Star Transformation do Oracle.
  - Execução obrigatória de `PRC_POS_CARGA_FATO` pós-carga (rebuild NOLOGGING e `DBMS_STATS`).
- [ ] **Estratégia B: Incremental Idempotente via `MERGE INTO` (Padrão FinOps / Telemetria / APIs)**
  - Cargas intra-dia, diárias ou por lote contínuo.
  - Fatos indexadas exclusivamente com **B-TREE INDEX** em chaves compostas (sem Bitmaps para evitar deadlocks `ORA-00060`).
  - Lógica `WHEN MATCHED THEN UPDATE / WHEN NOT MATCHED THEN INSERT`.

### 3.3 Tipo de Processamento de Carga
- [ ] **Carga Inicial (First Load):** Carga histórica de arranque com desabilitação temporária de constraints e índices.
- [ ] **Carga Incremental Delta:** Filtro por coluna de watermark (`DT_ATUALIZACAO`, `LAST_MOD` ou ID sequencial).
- [ ] **Carga Completa Periódica (Full Reload):** Truncate total e recarga de toda a massa de dados.

### 3.4 Histórico e Vigência das Dimensões (SCD)
- [ ] **SCD Tipo 1:** Sobrescrita direta de atributos cadastrais sem histórico de versões.
- [ ] **SCD Tipo 2 Corporativo:** Versionamento histórico obrigatório com `DTC_EFETIVACAO`, `DTC_EXPIRACAO`, `DES_ATUALIZAR` e tabela auxiliar `ODI_DIM_*`.
- [ ] **Dimensões Degeneradas:** Chaves transacionais mantidas diretamente na Fato (ex: `NUM_PROTOCOLO`, `NUM_CHAMADO`).
- [ ] **Dimensões Conformes:** Reutilização de dimensões globais corporativas (ex: `DIM_TEMPO`, `DIM_ORGAO`, `DIM_LOCALIDADE`).

---

## Seção 4 — Otimizações Físicas e Tuning Oracle

- [ ] **Surrogate Keys Numéricas Sintéticas:** PKs de dimensões alimentadas por Sequences Oracle (`MINVALUE 1 CACHE 50 NOORDER`).
- [ ] **Registro Padrão Linha `-1` Obrigatório:** Surrogate Key `-1` ('NÃO INFORMADO' / 'NÃO SE APLICA') inicializada em todas as dimensões.
- [ ] **Índices B-Tree Exclusivos em Dimensões:** Terminantemente proibido criar índices Bitmap em dimensões (evita deadlocks em DMLs concorrentes).
- [ ] **Particionamento de Fato por Intervalo Mensal/Anual:** Recomendado para fatos com volume superior a 10 milhões de linhas.
- [ ] **Compressão de Dados Oracle:** Uso de `COMPRESS FOR QUERY HIGH` ou `ROW STORE COMPRESS BASIC` em tabelas fato históricas.

---

## Seção 5 — Inventário Técnico de Fontes de Dados

### 5.1 Fontes Banco de Dados (Direcionadas ao ODI)
*Deposite os DDLs correspondentes em `entrega/planejador_dw/ddl/` e amostras em `entrega/planejador_dw/amostras/`.*
- **Origem:** `[Ex: Oracle OLTP Sistema X, Postgres ERP Y]`
- **Tabelas de Origem:** `[Ex: TAB_PROCESSO, TAB_UNIDADE]`
- **Mecanismo de Conexão:** `[DBLink Oracle / Conexão JDBC direta no ODI]`
- **Coluna de Filtro Incremental (Watermark):** `[Ex: DT_ULTIMA_ALTERACAO, ID_SEQUENCIAL ou N/A]`

### 5.2 Fontes Arquivos e Planilhas em FTP/SFTP (Direcionadas ao Apache Hop)
*Deposite arquivos de exemplo em `entrega/planejador_dw/arquivos_ftp/`.*
- **Protocolo:** `[SFTP / FTP / Compartilhamento de Rede NFS / Local]`
- **Formato do Arquivo:** `[CSV, Excel (.xlsx/.xls), TXT com layout posicional]`
- **Frequência de Chegada:** `[Ex: Diário às 06h, Mensal no fechamento do ciclo]`
- **Delimitador & Encoding:** `[Ex: Ponto e vírgula (;), UTF-8 / ISO-8859-1]`

### 5.3 Fontes APIs Web & Tratamentos Complexos (Direcionadas ao Python)
*Deposite amostras de resposta JSON/XML em `entrega/planejador_dw/api_specs/`.*
- **Tipo de Serviço:** `[REST / JSON / SOAP / Webhook]`
- **Método de Autenticação:** `[Bearer Token, OAuth2 Client Credentials, API Key]`
- **Paginação:** `[Por offset (?offset=100), por página (?page=1), por cursor]`
- **Complexidade Estrutural:** `[JSON aninhado, necessidade de flattening, cálculo de horas úteis]`

---

## Seção 6 — Volumetria e Dimensionamento (Para Sizing dos DBAs)

- **Volume Total Atual na Origem (estimativa de linhas):** `[Ex: 5.000.000 de linhas]`
- **Volume Novo Esperado por Mês:** `[Ex: 100.000 linhas/mês]`
- **Tamanho Médio de Linha na Origem:** `[Ex: ~250 bytes]`
- **Tempo de Retenção Desejado no DW:** `[Ex: 5 anos, perpétuo]`

---

## Seção 7 — Entregáveis Desejados

Marque os artefatos que você deseja que a IA gere:
- [x] **DDLs de Staging (`02_staging/02_create_stg_tables.sql`)**
- [x] **DDLs de Dimensões e Sequences (`03_dimensoes/04_create_dim_tables.sql`)**
- [x] **Carga Inicial da Linha `-1` (`03_dimensoes/06_init_default_records.sql`)**
- [x] **DDLs de Fatos com Índices e Tuning (`04_fatos/05_create_fato_tables.sql`)**
- [ ] **Tabelas Auxiliares do ODI (`03_dimensoes/03_create_odi_dim_tables.sql`)** *(apenas se ODI selecionado)*
- [ ] **Procedure Pós-Carga `PRC_POS_CARGA_FATO` (`05_procedimentos_manutencao/`)** *(apenas se Estratégia A)*
- [ ] **Pipelines e Workflows do Apache Hop (`06_pipelines_hop/`)** *(apenas se Apache Hop selecionado)*
- [ ] **Extratores Python de API (`07_extratores_python/`)** *(apenas se Python API selecionado)*
- [x] **Guia de Consumo Power BI e Datasets Superset (`08_datasets_bi/`)**
- [x] **Relatório Técnico de Estratégias e Linhagem (`09_relatorio_estrategias/RELATORIO_ESTRATEGIAS.md`)**
- [x] **Suíte de Testes SQL de Integridade Analítica (`10_testes_integridade/13_testes_integridade.sql`)**
- [x] **Dicionário Interativo de Dados HTML (`11_dicionario_dados/dicionario_dados.html`)**
