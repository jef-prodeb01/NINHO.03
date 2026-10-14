# Arquitetura de Governança de Dados Corporativa (PRODEB / Governo da Bahia)
## Origem Saneada pelo Cliente ➔ MongoDB Enterprise (Padrão PRODEB) ➔ AWS Glue & Amazon SageMaker Catalog

> **Status:** Arquitetura Oficial Consolidada  
> **Contexto:** Ecossistema Governamental Multi-Órgão (SAEB, SEFAZ, SSP, DETRAN, PLANSERV, SUPREV, BA.GOV.BR)  
> **Escopo da Equipe de Engenharia:** Transporte, Estruturação Canônica no MongoDB e Publicação de Governança na AWS  
> **Responsabilidade na Origem:** O Órgão Cliente é 100% responsável pela completude e qualidade dos dados na origem (Gate 0.5 de Devolução Obrigatória)  
> **Persistência Documental & Semântica:** MongoDB Enterprise (`tb_dataset`, `tb_sem_dominios`, `tb_sem_conceitos`, `tb_auditoria_eventos`)  
> **Catálogo e Governança em Nuvem (AWS):** **AWS Glue Data Catalog** + **Amazon SageMaker Unified Studio / SageMaker Catalog** *(evolução oficial que substitui o antigo Amazon DataZone standalone)*  
> **Ferramentas de Transporte:** Oracle Data Integrator (ODI 12c), Apache Hop e Python (`pymongo` / `boto3`)

---

## 1. Premissas Inegociáveis e Fronteira de Responsabilidade

1. **Gate 0.5 — Responsabilidade dos Dados na Origem é do Cliente:**
   - A equipe técnica atua **exclusivamente no transporte dos dados para o MongoDB e na integração final com a AWS**.
   - Se o cliente enviar planilhas de insumos (`Dados - Insumos` / `Dicionário de Dados`) com células obrigatórias em branco, textos evasivos (*"ver com sap"*, *"a definir"*, *"xxxx"*), sem classificação LGPD (`Anonimizar?`, `Sensibilidade`, `Sensível?`), ou arquivos de dados (`.csv`/`.xlsx`) com **registros vazios em chaves de negócio ou colunas fantasmas (`;;;`)**, o processo é **bloqueado na entrada** pelo script `inspecionar_insumos_governanca.py` e **devolvido ao cliente** para correção na fonte.
2. **Padronização Canônica PRODEB no MongoDB Enterprise:**
   - **Código do Dataset:** `SIGLA_ORGAO_UNIDADE_TEMA_VERSAO` em `UPPER_SNAKE_CASE` (ex.: `SAEB_SGC_ATENDIMENTO_V1`, `PLANSERV_BENEFICIARIO_CADASTRO_V1`).
   - **Nomenclatura de Atributos:** `snake_case` minúsculo, sem acentos, iniciado obrigatoriamente por prefixo semântico de 3 letras (`cod_`, `nom_`, `des_`, `num_`, `ind_`, `dtc_`, `dth_`, `val_`, `qtd_`, `prc_`, `sts_`, `tip_`, `ref_`, `lst_`, `jsn_`, `sig_`, `txt_`, `hor_`).
   - **Tipagem BSON Estrita (`validationLevel: "strict"`):**
     - Documentos e códigos (`CPF`, `CNPJ`, `RG`, `CEP`, `CNH`, `RENAVAM`, `Matrícula`, `Telefone`) são **sempre `"string"`** (preserva zeros à esquerda).
     - Valores monetários (`val_`) e percentuais (`prc_`) são **sempre `"decimal"` (`Decimal128`)** (proibido `double`/`float`).
     - Datas (`dtc_`, `dth_`) são **sempre `"date"` ISO-8601 UTC**.
3. **Evolução AWS — Do Amazon DataZone para o Amazon SageMaker Unified Studio / SageMaker Catalog:**
   - Como o Amazon DataZone standalone foi unificado pela AWS na nova geração do **Amazon SageMaker Unified Studio (SageMaker Catalog & SageMaker Lakehouse)**, toda a camada de governança em nuvem publica seus ativos técnicos no **AWS Glue Data Catalog** e governa Domínios, Glossários Semânticos, Metadata Forms (LGPD/LAI) e Produtos de Dados no **Amazon SageMaker Catalog**.

---

## 2. Topologia Ponta a Ponta (Origem ➔ Gate 0.5 ➔ MongoDB ➔ AWS SageMaker Catalog)

```mermaid
flowchart TD
    subgraph CLIENTE["1. Órgão Cliente (Responsável pelo Saneamento na Origem)"]
        INS["Planilha PRODEB (.xlsx)<br/>• Aba 'Dados - Insumos'<br/>• Aba 'Dicionário de Dados'"]
        DADOS["Fontes de Dados (CSV, API, BD)<br/>(Ex: SAP RH Bahia, Planserv, Detran, BA.GOV.BR)"]
    end

    subgraph GATE["2. Gate 0.5 — Auditoria de Entrada (inspecionar_insumos_governanca.py)"]
        AUD{"Dados e Metadados<br/>100% Completos?"}
        DEV["🛑 BLOQUEIO E DEVOLUÇÃO AO CLIENTE<br/>(relatorio_devolucao_cliente.md)<br/>• Registros vazios / NULL em chaves<br/>• Colunas fantasmas (;;;) no CSV<br/>• Falta de Tipo, Descrição ou LGPD"]
    end

    subgraph TRANSPORTE["3. Camada de Transporte (Apenas Dados Aprovados)"]
        ODI["👑 ODI 12c<br/>(Bancos Relacionais)"]
        HOP["🔄 Apache Hop<br/>(Arquivos CSV / Excel Saneados)"]
        PY["🐍 Python<br/>(APIs REST & Automação)"]
    end

    subgraph MONGO["4. MongoDB Enterprise (Persistência & Governança PRODEB)"]
        COL_DADOS["Coleções de Negócio (RAW / TRUSTED)<br/>• Validação $jsonSchema Strict<br/>• Envelope _org e _governance"]
        COL_CAT["Catálogo & Semântica Ativa:<br/>• tb_dataset (Metadados e Linhagem)<br/>• tb_sem_dominios (Domínios Corporativos)<br/>• tb_sem_conceitos (Conceitos Canônicos)"]
        COL_AUD["Auditoria & Quarentena:<br/>• tb_auditoria_eventos (TTL 5 anos)<br/>• tb_quarentena_<tema>_<yyyymmdd>"]
    end

    subgraph AWS["5. Governança Corporativa na AWS"]
        GLUE["⚙️ AWS Glue Data Catalog<br/>• Glue Connection / Crawler MongoDB<br/>• Tabelas Técnicas & Tipos BSON"]
        subgraph SAGEMAKER["🌐 Amazon SageMaker Unified Studio / SageMaker Catalog (ex-DataZone)"]
            SM_DOM["Domain Units por Órgão<br/>(SAEB, SEFAZ, SSP, DETRAN, PLANSERV)"]
            SM_GLOSS["Business Glossary<br/>(Sincronizado com tb_sem_dominios / tb_sem_conceitos)"]
            SM_FORMS["Metadata Forms<br/>• lgpd_compliance_form<br/>• lai_transparency_form<br/>• prodeb_provenance_form"]
            SM_LAKE["SageMaker Lakehouse & Data Sharing<br/>(Assinatura governada entre Secretarias)"]
        end
    end

    INS --> AUD
    DADOS --> AUD
    AUD -->|Reprovado (Dados/Metadados Vazios)| DEV
    DEV -.->|Cliente corrige na fonte| CLIENTE
    AUD -->|Aprovado| TRANSPORTE
    ODI & HOP & PY --> COL_DADOS
    ODI & HOP & PY --> COL_CAT
    ODI & HOP & PY --> COL_AUD
    COL_DADOS -.->|Glue Crawler / JDBC| GLUE
    COL_CAT -->|Sync via boto3| SM_GLOSS
    COL_CAT -->|Sync via boto3| SM_FORMS
    GLUE --> SM_DOM --> SM_LAKE
    SM_GLOSS --> SM_LAKE
    SM_FORMS --> SM_LAKE
```

---

## 3. Arquitetura das 5 Coleções Oficiais no MongoDB Enterprise

| Coleção MongoDB | Papel Arquitetural | Regras e Índices Obrigatórios |
| :--- | :--- | :--- |
| **`<colecao_negocio>`** *(RAW / TRUSTED)* | Armazena os documentos de negócio transportados da origem com atributos no padrão PRODEB (`cod_`, `nom_`, `val_`, `dtc_`) e blocos `_org` / `_governance`. | Validador `$jsonSchema` com `validationLevel: "strict"` e `validationAction: "error"`. |
| **`tb_dataset`** | Catálogo Técnico, Operacional, Custódia (`Data Owner`/`Steward`), Sensibilidade LGPD/LAI e Linhagem (`provenance`) de cada dataset. | Índice único em `cod_dataset` (`SIGLA_ORGAO_UNIDADE_TEMA_VERSAO`). |
| **`tb_sem_dominios`** | Catálogo de Domínios Semânticos Corporativos (ex.: `DOM_IDENTIFICACAO_CIVIL`, `DOM_VIDA_FUNCIONAL`, `DOM_PREVIDENCIA_SAUDE`). | Índice único em `cod_dominio`. |
| **`tb_sem_conceitos`** | Dicionário Semântico de Conceitos Canônicos (ex.: `CON_CPF_CIDADAO`, `CON_MATRICULA_SERVIDOR`) mapeando quais datasets/atributos implementam cada conceito. | Índice único em `cod_conceito` + índice em `cod_dominio`. |
| **`tb_auditoria_eventos`** | Trilha imutável de auditoria de cargas, acessos e mudanças de schema (conformidade Art. 37 LGPD). | **Índice TTL obrigatório de 5 anos (`expireAfterSeconds: 157680000`)** sobre `dth_evento`. |

> **Isolamento de Rejeições (`tb_quarentena_<tema>_<yyyymmdd>`):** Caso algum registro falhe na validação BSON durante a janela de transporte, ele jamais contamina a coleção principal nem é descartado silenciosamente; é gravado em coleção de quarentena com o motivo do erro para notificação ao órgão de origem.

---

## 4. Integração entre MongoDB e Amazon SageMaker Catalog & AWS Glue

| Elemento no MongoDB (PRODEB) | Equivalente no AWS Glue & Amazon SageMaker Catalog |
| :--- | :--- |
| `sig_orgao` (`SAEB`, `SEFAZ`, `SSP`, `DETRAN`, `PLANSERV`) | **Domain / Domain Unit** no Amazon SageMaker Unified Studio |
| Coleção de negócio validada (`$jsonSchema`) | **Glue Table** no AWS Glue Data Catalog + **Catalog Asset** no SageMaker Catalog |
| Documento em `tb_dataset` | **Metadata Forms** anexados ao ativo (`prodeb_provenance_form`, `lgpd_compliance_form`, `lai_transparency_form`) |
| Documentos em `tb_sem_dominios` | **Business Glossary** no Amazon SageMaker Catalog |
| Documentos em `tb_sem_conceitos` | **Business Glossary Terms** vinculados às colunas do ativo |
| `ind_dados_pessoais` / `ind_dados_sensiveis` | Governança de acesso e políticas de assinatura no **SageMaker Catalog / Lake Formation** |

---

## 5. Artefatos Gerados pelo Módulo (`saida/governanca_dados/`)

1. **`saida/governanca_dados/relatorio_devolucao_cliente_<ORGAO>.md`**: Emitido quando o Gate 0.5 detecta campos vazios, registros em branco ou omissões na planilha/amostra do cliente.
2. **`saida/governanca_dados/schemas_mongo/`**:
   - Script `.js` com `db.createCollection("<colecao>", { validator: { $jsonSchema: ... }, validationLevel: "strict" })` e índices compostos.
   - Script `.js` de registro do dataset em `tb_dataset`, `tb_sem_dominios`, `tb_sem_conceitos` e `tb_auditoria_eventos` (incluindo índice TTL de 5 anos).
3. **`saida/governanca_dados/aws_sagemaker_catalog/`** *(e espelho de compatibilidade em `aws_datazone/`)*:
   - Definições JSON dos Metadata Forms (`lgpd_compliance_form`, `lai_transparency_form`, `prodeb_provenance_form`), Glossário Semântico e script Python `boto3` para publicação no **AWS Glue Data Catalog** e **Amazon SageMaker Unified Studio / SageMaker Catalog**.
