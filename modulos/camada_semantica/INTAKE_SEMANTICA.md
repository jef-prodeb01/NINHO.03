# INTAKE_SEMANTICA.md — Formulário de Entrada da Camada Semântica

Preencha este formulário com as informações do projeto para a construção da **Camada Semântica Corporativa** sobre um Data Warehouse Oracle existente.

> ⚠️ **AVISO AO ENGENHEIRO DE DADOS:**  
> A IA iniciará a sessão conferindo este formulário. Se campos obrigatórios estiverem em branco, a IA solicitará que você acesse este link e complete os dados antes de iniciar a modelagem semântica e geração das views analíticas.

---

## Seção 0 — Identificação do Projeto & Ambiente

- **Nome do Projeto (Sigla em maiúsculas):** `[Ex: SEI, SIPAR, RH_BAHIA]`
- **Engenheiro de Dados Responsável:** `[Nome completo do engenheiro]`
- **Schema Alvo no Oracle:** `[Ex: SEIMUNICIPIO_OLAP, RH_BAHIA_OLAP]`
- **Data de Início:** `[AAAA-MM-DD]`

### 0.1 Estado do Schema Alvo
- [ ] **Primeira execução neste schema** (schema novo, sem objetos semânticos prévios).
- [ ] **Schema já contém execuções de outros projetos** (compartilhamento de schema multi-projeto).

### 0.2 Estado das 8 Tabelas `META_*`
- [ ] **Tabelas `META_*` NÃO existem** (a IA gerará o DDL de criação `01_create_meta_tables.sql` + inserts completos).
- [ ] **Tabelas `META_*` JÁ existem** (a IA NÃO recriará as tabelas; utilizará `MERGE INTO` para acrescentar apenas os novos metadados do projeto).

---

## Seção 1 — Seleção de Tecnologias e Ferramentas de Consumo (MANDATÓRIO)

> 🛑 **REGRA DE ESCOPO:** Marque com `[x]` as ferramentas que consumirão as views e metadados.

- [ ] **Power BI:** Views analíticas otimizadas para Import Mode / DirectQuery, com nomes amigáveis e chaves dimensionais explícitas.
- [ ] **Apache Superset:** Datasets relacionais com métricas SQL compiladas e filtros nativos.
- [ ] **Modelos de IA / Agentes Text-to-SQL (LLMs):** Metadados ricos nas 8 tabelas `META_*` com regras de negócio, glossário e orientações de IA (`META_ORIENTACAO_IA`).
- [ ] **Ferramentas SQL Ad-Hoc:** DBeaver, Metabase, Oracle SQL Developer.

---

## Seção 2 — Arquitetura de Views Analíticas Desejada

Marque o padrão arquitetural de entrega das views em `saida/camada_semantica/vw_analiticas/`:
- [ ] **Arquitetura Canônica em 3 Camadas (Padrão Corporativo):**
  - **Camada 1 (DIM):** Views `VW_<PROJETO>_DIM_*` filtrando apenas registros vigentes (`DTC_EXPIRACAO IS NULL`).
  - **Camada 2 (EVENTO):** Views `VW_<PROJETO>_<EVENTO>` desnormalizando fatos atômicas com suas dimensões correspondentes.
  - **Camada 3 (KPI):** Views `VW_<PROJETO>_KPI_*` agregando métricas por período (mês, ciclo, unidade).
- [ ] **Materialized Views com Refresh Programado:**
  - Criação de MVs com `BUILD IMMEDIATE REFRESH COMPLETE ON DEMAND` para queries analíticas pesadas.
- [ ] **Tratamento de Nulos com Coalesce / Fallback:**
  - `COALESCE` em campos textuais para 'NÃO INFORMADO' e valores numéricos para `0`.

---

## Seção 3 — DDL e Amostras de Dados das Fatos e Dimensões

*Deposite os DDLs do DW em `entrega/camada_semantica/ddl/` e amostras em `entrega/camada_semantica/amostras/`.*

- **Caminho do DDL Consolidado:** `entrega/camada_semantica/ddl/`
- **Caminho das Amostras de Dados:** `entrega/camada_semantica/amostras/`

### 3.1 Características dos Dados Identificadas nas Amostras
- [ ] Existem linhas de total/subtotal misturadas ao detalhe (ex: "Total Geral").
- [ ] Existem códigos hierárquicos (ex: código `2110.01` filho de `2110`).
- [ ] Existem colunas de vigência temporal (`DTC_EFETIVACAO` e `DTC_EXPIRACAO`).
- [ ] Existem flags de exclusão lógica (`SIN_ATIVO = 'S'/'N'`).

---

## Seção 4 — Regras de Negócio, Expansão Consultiva da IA e Segurança (RLS)

### 4.0 Origem e Expansão das Regras de Negócio
- [ ] **Opção 1: Digitadas diretamente na lista 4.1 abaixo**
- [ ] **Opção 2: Documentadas em arquivos na pasta `entrega/camada_semantica/` ou derivados do DW**
  - **Arquivo(s) de referência:** `[Ex: entrega/camada_semantica/relatorios_etl/RELATORIO_ESTRATEGIAS.md, regras_negocio.md]`
  - *(A IA extrairá as regras diretamente desses arquivos).*
- [ ] **Opção 3: Descoberta Consultiva pela IA a partir do DDL/Amostras do DW**
  - Marque esta opção quando o cliente não definiu todas as regras de negócio de antemão e deseja que a IA proponha as regras de integridade, filtros e métricas a partir do modelo físico do DW.
- [x] **💡 Habilitar Radar Consultivo da IA para Regras e KPIs (Recomendado — Ativo por Padrão):**
  - Além das regras informadas pelo cliente, a IA analisará as Fatos e Dimensões do DW para sugerir proativamente no `DOCUMENTO_ENTENDIMENTO_<PROJETO>.md`:
    - **Novas Métricas e Views `VW_<PROJETO>_KPI_*`** (ex: Lead Time, Backlog Ativo, Aging de Fila, Taxa de Vazão/Throughput, Cumprimento de SLA, Variação Mensal MoM e Curva ABC/Pareto).
    - **Novas Regras para `META_REGRA_NEGOCIO` e `META_ORIENTACAO_IA`** (ex: tratamento de datas invertidas, segregação entre estoque aberto e fluxo concluído, proteção contra divisão por zero e mapeamento da linha `-1`).

### 4.1 Regras de Negócio e Exceções Específicas do Projeto
1. `[Ex: Medida VAL_GLOSA só pode ser apurada após fechamento formal do ciclo mensal]`
2. `[Ex: Chamados cancelados não devem ser contabilizados no tempo médio de atendimento]`
3. `[Ex: Ignorar registros de homologação ou unidades de teste nas Views EVENTO e KPI]`
4. `...`

### 4.2 Segurança por Linha (Row-Level Security - RLS)
- [ ] **Sem RLS (Acesso Total):** Todos os usuários autorizados no banco enxergam a base integral.
- [ ] **RLS Baseado em Views com Filtro:** Views analíticas segregadas por segmento ou órgão.
- [ ] **RLS Baseado em VPD (Virtual Private Database / SYS_CONTEXT):** Filtro dinâmico via contexto de sessão Oracle.

---

## Seção 5 — Perguntas de Negócio & Sugestões da IA (`META_CONSULTA_NEGOCIO`)

### 5.0 Origem e Expansão das Perguntas de Negócio
- [ ] **Opção 1: Listadas diretamente na lista 5.1 abaixo**
- [ ] **Opção 2: Extraídas de documentos na pasta de entrega ou guias do DW**
  - **Arquivo(s) de referência:** `[Ex: entrega/camada_semantica/relatorios_etl/GUIA_ANALISTA_BI.md, perguntas.md]`
- [ ] **Opção 3: Geradas integralmente pelo Radar Consultivo da IA a partir do DW**
- [x] **💡 Expandir Catálogo com Novas Perguntas Sugeridas pela IA (Recomendado — Ativo por Padrão):**
  - Mesmo quando o cliente fornece uma lista inicial de perguntas, a IA proporá perguntas adicionais de alto valor divididas em 3 horizontes (**Executivas/Estratégicas**, **Táticas/Operacionais** e **Auditoria/Qualidade**) para enriquecer a tabela `META_CONSULTA_NEGOCIO` e o treinamento de agentes Text-to-SQL.

### 5.1 Lista de Perguntas Solicitadas pelo Cliente
1. `[Ex: Qual o percentual de cumprimento de SLA por módulo no último ciclo?]`
2. `[Ex: Quais são os 10 chamados mais ofensores do tempo de atendimento?]`
3. `...`

---

## Seção 6 — Entregáveis da Camada Semântica

Marque os artefatos que devem ser gerados em `saida/camada_semantica/`:
- [x] **Documento de Entendimento Semântico (`DOCUMENTO_ENTENDIMENTO_<PROJETO>.md`)**
- [x] **DDLs das Views Analíticas (`saida/camada_semantica/vw_analiticas/`)**
- [ ] **DDL de Criação das Tabelas `META_*` (`01_create_meta_tables.sql`)** *(apenas se não existirem)*
- [ ] **Script de Segurança RLS / VPD (`02_rls_template.sql`)** *(se RLS selecionado na Seção 4.2)*
- [x] **Carga do Glossário de Termos (`01_meta_glossario.sql`)**
- [x] **Carga do Catálogo de Métricas (`02_meta_metrica.sql`)**
- [x] **Carga do Dicionário de Objetos e Colunas (`03_meta_objeto.sql`)**
- [x] **Carga da Matriz de Relacionamentos (`04_meta_relacionamento.sql`)**
- [x] **Carga das Regras de Negócio (`05_meta_regra_negocio.sql`)**
- [x] **Carga das Consultas Prontas de Negócio (`06_meta_consulta_negocio.sql`)**
- [x] **Carga das Orientações e Guardrails de IA (`07_meta_orientacao_ia.sql`)**
- [x] **Carga dos Valores de Domínio (`08_meta_valor_dominio.sql`)**
- [x] **Suíte de Testes e Validações SQL (`09_validacoes.sql`)**

---

## Seção 7 — Informações Complementares, Particularidades e Observações Livres do Engenheiro

> 📝 **ESPAÇO ABERTO DO ENGENHEIRO DE DADOS:**  
> Utilize esta seção para registrar **qualquer regra específica do projeto, sinônimo/jargão de negócio do cliente, guardrail extra para o Agente Text-to-SQL, filtro especial de view ou restrição técnica** que não esteja contemplada nos campos acima.

- **Sinônimos, Siglas ou Jargões Específicos do Cliente (para `META_GLOSSARIO`):**
  - `[Ex: O cliente chama 'Unidade Geradora' de 'Setor Protocolizante' e 'Processo Sobrestado' de 'Processo Suspenso']`
- **Guardrails ou Restrições Específicas para Text-to-SQL (`META_ORIENTACAO_IA`):**
  - `[Ex: Nunca cruzar FATO_TRAMITACAO com FATO_DOCUMENTO diretamente sem usar CTE por protocolo; sempre filtrar ANO >= 2022 por padrão]`
- **Padrões de Nomenclatura de Views ou Exigências do Time de BI:**
  - `[Ex: O time de Power BI pediu que as colunas de data nas views tenham sufixo _DT e valores monetários _VLR]`
- **Contexto Adicional, Regras Específicas ou Instruções Livres para a IA:**
```text
[Escreva ou cole aqui livremente qualquer informação complementar, regra específica do projeto,
exceção de cálculo ou instrução direta para o Agente considerar na Camada Semântica...]
```

