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

## Seção 4 — Regras de Negócio e Segurança de Acesso (RLS)

### 4.1 Regras de Negócio do Negócio
1. `[Ex: Medida VAL_GLOSA só pode ser apurada após fechamento formal do ciclo mensal]`
2. `[Ex: Chamados cancelados não devem ser contabilizados no tempo médio de atendimento]`
3. `...`

### 4.2 Segurança por Linha (Row-Level Security - RLS)
- [ ] **Sem RLS (Acesso Total):** Todos os usuários autorizados no banco enxergam a base integral.
- [ ] **RLS Baseado em Views com Filtro:** Views analíticas segregadas por segmento ou órgão.
- [ ] **RLS Baseado em VPD (Virtual Private Database / SYS_CONTEXT):** Filtro dinâmico via contexto de sessão Oracle.

---

## Seção 5 — Perguntas de Negócio para o Catálogo (`META_CONSULTA_NEGOCIO`)

> *Liste as perguntas típicas que os analistas de negócio ou gestores farão:*

1. `[Ex: Qual o percentual de cumprimento de SLA por módulo no último ciclo?]`
2. `[Ex: Quais são os 10 chamados mais ofensores do tempo de atendimento?]`
3. `...`

---

## Seção 6 — Entregáveis da Camada Semântica

Marque os artefatos que devem ser gerados em `saida/camada_semantica/`:
- [x] **Documento de Entendimento Semântico (`DOCUMENTO_ENTENDIMENTO_<PROJETO>.md`)**
- [x] **DDLs das Views Analíticas (`saida/camada_semantica/vw_analiticas/`)**
- [ ] **DDL de Criação das Tabelas `META_*` (`01_create_meta_tables.sql`)** *(apenas se não existirem)*
- [x] **Carga do Glossário de Termos (`01_meta_glossario.sql`)**
- [x] **Carga do Catálogo de Métricas (`02_meta_metrica.sql`)**
- [x] **Carga do Dicionário de Objetos e Colunas (`03_meta_objeto.sql`)**
- [x] **Carga da Matriz de Relacionamentos (`04_meta_relacionamento.sql`)**
- [x] **Carga das Regras de Negócio (`05_meta_regra_negocio.sql`)**
- [x] **Carga das Consultas Prontas de Negócio (`06_meta_consulta_negocio.sql`)**
- [x] **Carga das Orientações e Guardrails de IA (`07_meta_orientacao_ia.sql`)**
- [x] **Carga dos Valores de Domínio (`08_meta_valor_dominio.sql`)**
- [x] **Suíte de Testes e Validações SQL (`09_validacoes.sql`)**
