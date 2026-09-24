# Planejador de Data Warehouses (DW Planner)

Módulo corporativo para **planejamento, arquitetura e modelagem dimensional de Data Warehouses Oracle** a partir de fontes heterogêneas de dados (Bancos Relacionais, Arquivos/Planilhas em FTP/SFTP e APIs Web).

> **Papel do Módulo:** Atuar como um **Arquiteto de Dados Sênior Automatizado**.  
> Ele **não executa** a carga massiva dos dados, mas projeta toda a solução:
> 1. Modela as tabelas em camadas: `STG_*` -> `ODI_DIM_*` -> `DIM_*` -> `FATO_*`.
> 2. Recomenda a esteira híbrida de ingestão: **ODI** (Banco), **Apache Hop** (Arquivos) e **Python** (APIs).
> 3. Gera a especificação de disparo centralizada no ODI via `OdiOSCommand` (SSH).
> 4. Produz os DDLs otimizados para Oracle (B-Tree, Bitmaps, SCD2, Particionamento e linha `-1`).
> 5. Entrega o relatório de linhagem e estratégias (*"Como chegar em cada valor"*).
> 6. Gera a ponte automática com o **Módulo de Camada Semântica**.

---

## 1. Visão Geral da Arquitetura Híbrida

O planejamento segue a esteira corporativa onde o **Oracle Data Integrator (ODI)** atua como maestro geral do pacote de cargas:

```mermaid
flowchart TD
    subgraph INGEST["1. Ingestão Híbrida Externa"]
        F_DB["Bancos Relacionais (OLTP)"] -->|ODI Mapping Direto| STG["Tabelas STG_*<br/>(Oracle Staging)"]
        F_FTP["Arquivos CSV/Excel (FTP/SFTP)"] -->|Apache Hop Pipeline| STG
        F_API["APIs Web (REST/JSON)"] -->|Script Python| STG
    end

    subgraph ORCH["2. Orquestração Centralizada (ODI)"]
        ODI_CMD["OdiOSCommand (SSH)<br/>Dispara Hop / Python no servidor remoto"]
        ODI_CMD -.->|Trigger| F_FTP
        ODI_CMD -.->|Trigger| F_API
    end

    subgraph CORE_DW["3. Modelagem Dimensional In-Database (ODI)"]
        STG -->|Módulo Dimensões & Cubos| ODI_DIM["Tabelas Auxiliares<br/>ODI_DIM_*"]
        ODI_DIM -->|SCD Tipo 2 (Merge / Expirar)| DIM["Dimensões Oficiais<br/>DIM_* (DIMENSION_KEY)"]
        
        STG -->|Lookup de SKs nas Dimensões| FATO["Fatos Oficiais<br/>FATO_* (DIM_*, QTD_*, DTC_CARGA)"]
    end

    subgraph AUDIT["4. Auditoria & Liberação"]
        FATO --> CTRL["TB_CONTROLE_CARGA<br/>(ID_CARGA, NOME_PROJETO, DATA_CARGA)"]
    end

    subgraph SEMANTIC["5. Camada Semântica (Consumo)"]
        DIM -->|dtc_expiracao IS NULL| V_DIM["VW_DIM_*_ATUAL"]
        V_DIM --> V_EVT["VW_EVENTO"]
        FATO --> V_EVT
        V_EVT --> V_KPI["VW_KPI_*"]
        V_KPI --> META["8 Tabelas META_* (IA & BI)"]
    end

    style INGEST fill:#f0f7ff,stroke:#0066cc,stroke-width:2px
    style ORCH fill:#fff0f6,stroke:#eb2f96,stroke-width:2px
    style CORE_DW fill:#fffbe6,stroke:#faad14,stroke-width:2px
    style AUDIT fill:#e6fffb,stroke:#13c2c2,stroke-width:2px
    style SEMANTIC fill:#f6ffed,stroke:#52c41a,stroke-width:2px
```

---

## 2. Estrutura de Diretórios do Módulo

```text
planejador_dw/
├── README.md                      # Esta visão geral
├── GUIA_ENGENHEIRO_DADOS.md       # Manual prático do engenheiro + biblioteca de prompts
├── AGENTS.md                      # Protocolo de raciocínio e regras estritas para a IA
├── INTAKE_DW.md                   # Formulário de entrada (fontes, regras, o que o cliente quer)
├── CONVENCOES_DW.md               # Padrões de nomes, DDLs, índices e auditoria
│
├── entrega/                       # Pasta onde o engenheiro coloca os insumos do projeto
│   ├── ddl/                       # DDLs das fontes OLTP
│   ├── amostras/                  # Amostras das tabelas (10-20 linhas)
│   ├── arquivos_ftp/              # Modelos de CSV, TXT e planilhas Excel
│   └── api_specs/                 # Exemplos de retorno JSON ou Swagger
│
└── templates/                     # Modelos canônicos de DDLs e relatórios
    ├── 01_tb_controle_carga.sql   # DDL padrão corporativo de controle de cargas
    ├── 02_stg_template.sql        # Modelo de tabela STG_*
    ├── 03_odi_dim_template.sql    # Modelo de tabela auxiliar ODI_DIM_*
    ├── 04_dim_template.sql        # Modelo de dimensão oficial com SCD2 e índices
    ├── 05_fato_template.sql       # Modelo de fato dimensional com FKs e particionamento
    ├── 06_init_default_records.sql # Inserção automática do registro -1 (Desconhecido)
    └── RELATORIO_ESTRATEGIAS_MODELO.md # Template do relatório de linhagem e SSH
```

---

## 3. Entregáveis de Cada Projeto de DW Planejado

Ao submeter os insumos de um novo projeto pelo `INTAKE_DW.md`, o agente produzirá:

1. **Scripts SQL DDL Otimizados:**
   - Criação das tabelas de Staging (`STG_*`).
   - Criação das tabelas auxiliares de Dimensão (`ODI_DIM_*`).
   - Criação das Dimensões oficiais (`DIM_*`) com índices B-Tree, Bitmaps e SCD2.
   - Criação das Fatos (`FATO_*`) com chaves compostas, medidas `QTD_*`, auditoria `DTC_CARGA` e particionamento quando volumosa.
   - Script de carga inicial da linha `-1` em todas as dimensões.
2. **Relatório de Estratégias & Linhagem (`RELATORIO_ESTRATEGIAS.md`):**
   - Matriz De/Para detalhando **como chegar em cada valor**.
   - Especificação do comando `OdiOSCommand` para disparo do Hop e Python via SSH.
   - Regras de Lookup de Surrogate Keys no ODI.
3. **Estimativa de Sizing e Storage:**
   - Projeção de volumetria anual em GB para o time de DBA e infraestrutura.
4. **Ponte Direta para a Camada Semântica:**
   - Arquivo pronto para plugar no módulo de Camada Semântica existente.
