# INTAKE_GOVERNANCA.md — Formulário de Entrada de Governança de Dados (PRODEB / MongoDB & AWS SageMaker)

Preencha este formulário com as definições de arquitetura de governança, catálogo de metadados e camada semântica no MongoDB, classificação regulatória (LAI, LGPD) e publicação corporativa na AWS (**Amazon SageMaker Unified Studio / SageMaker Catalog & AWS Glue Data Catalog**).

> ⚠️ **AVISO CRÍTICO AO ENGENHEIRO DE DADOS — GATE DE QUALIDADE NA ORIGEM:**  
> 1. **Responsabilidade dos Dados na Origem é do Cliente:** A equipe de Engenharia/Governança atua **exclusivamente no transporte, estruturação canônica no MongoDB e catalogação final no AWS SageMaker Catalog / Glue**.
> 2. **Bloqueio e Devolução Obrigatória:** Se a planilha de insumos (`Dados - Insumos` / `Dicionário de Dados`) ou as amostras de dados (`.csv`/`.xlsx`) enviadas pelo cliente apresentarem **registros vazios em chaves/campos obrigatórios, colunas sem nome (`;;;`), tipos/descrições ausentes ou classificações LGPD em branco**, a esteira **NÃO DEVE SER GERADA**. O script `inspecionar_insumos_governanca.py` e o Agente emitirão o **Relatório de Devolução ao Cliente** para saneamento na origem.

---

## Seção 0 — Identificação do Órgão, Unidade & Dataset (Padrão PRODEB)

- **Sigla do Órgão / Cliente (`SIGLA_ORGAO`):** `[Ex: SAEB, PLANSERV, SUPREV, DETRAN, SEFAZ]`
- **Unidade / Coordenação / Sistema (`UNIDADE`):** `[Ex: SGC, BENEFICIARIO, RHBH, CNH, CIDADAO]`
- **Tema de Negócio (`TEMA`):** `[Ex: ATENDIMENTO, CADASTRO, SERVIDOR, PENSIONISTAS]`
- **Versão do Esquema (`VERSAO`):** `[Ex: V1]`
- **Código Canônico do Dataset (`SIGLA_ORGAO_UNIDADE_TEMA_VERSAO`):** `[Ex: SAEB_SGC_ATENDIMENTO_V1]`
- **Data Owner (Gestor de Negócio no Órgão):** `[Nome completo e cargo — Obrigatório]`
- **Data Steward (Responsável Técnico na Origem):** `[Nome completo e contato — Obrigatório]`
- **Engenheiro de Dados Responsável:** `[Nome completo do engenheiro]`
- **Data de Início:** `[AAAA-MM-DD]`

---

## Seção 1 — Seleção de Tecnologias de Transporte, Persistência e Catálogo (MANDATÓRIO)

> 🛑 **REGRA DE ESCOPO:** Marque com `[x]` apenas as tecnologias utilizadas na esteira deste projeto.

### 1.1 Persistência e Governança Documental (MongoDB Enterprise)
- [ ] **MongoDB Lakehouse & Camada Semântica (`tb_dataset`, `tb_sem_dominios`, `tb_sem_conceitos`, `tb_auditoria_eventos`):**
  - Modelagem NoSQL seguindo o padrão de nomenclatura PRODEB (`snake_case` com prefixos de 3 letras `cod_`, `nom_`, `val_`, `dtc_`, etc.), `$jsonSchema` com `validationLevel: "strict"`, tipagem BSON rigorosa (`Decimal128` para valores monetários, `string` para CPF/CNPJ/Matrícula/CEP) e coleções de quarentena.
  - *(Gera artefatos em `saida/governanca_dados/schemas_mongo/`).*

### 1.2 Governança e Catálogo Corporativo em Nuvem (AWS)
- [ ] **Amazon SageMaker Unified Studio / SageMaker Catalog (ex-DataZone) & AWS Glue Data Catalog:**
  - Evolução do antigo Amazon DataZone para o **Amazon SageMaker Catalog / SageMaker Lakehouse** integrado ao **AWS Glue Data Catalog** (sem dependência de S3 para dados brutos quando persistidos no MongoDB).
  - Publicação de Domínios por Órgão, Glossário Semântico espelhado do MongoDB (`tb_sem_dominios` / `tb_sem_conceitos`), Metadata Forms (LGPD, LAI, Custódia/Provenance) e Data Products.
  - *(Gera artefatos em `saida/governanca_dados/aws_sagemaker_catalog/` e `saida/governanca_dados/aws_datazone/`).*

### 1.3 Ferramentas de Transporte (Origem Saneada ➔ MongoDB ➔ AWS)
- [ ] **Oracle Data Integrator (ODI 12c):** Transporte de bancos relacionais legados para o MongoDB.
- [ ] **Apache Hop (.hpl / .hwf):** Transporte de arquivos tabulares saneados (CSV/Excel) e cargas estruturadas para o MongoDB.
- [ ] **Extratores e Automação Python (.py / `boto3`):** Transporte de APIs REST para o MongoDB e sincronização de metadados ativos com o AWS Glue / Amazon SageMaker Catalog.

---

## Seção 2 — Gate de Qualidade dos Insumos do Cliente & Diretrizes Legais (LGPD / LAI)

### 2.0 Origem dos Insumos e Planilhas do Cliente
- [ ] **Opção 1: Planilha Padrão PRODEB (`.xlsx`) e/ou amostras (`.csv`) depositadas em `entrega/governanca_dados/`**
  - **Arquivo(s) de referência:** `[Ex: entrega/governanca_dados/Dados - Insumos.xlsx, amostra_sistema.csv]`
  - *(Execute `python core/scripts_comuns/inspecionar_insumos_governanca.py` antes de prosseguir para auditar campos vazios e gerar a Matriz DE/PARA).*
- [ ] **Opção 2: Selecionados nos checkboxes abaixo + Mapeamento assistido pela IA**
- [ ] **Opção 3: Solicitar sugestões do 💡 Radar Consultivo da IA (Enriquecimento de Conceitos Semânticos, Regras de Qualidade no Transporte e Alertas LGPD)**

### 2.1 Checklist de Qualidade na Origem (Responsabilidade do Cliente)
> Se qualquer item abaixo estiver reprovado na inspeção, o processo **pausa imediatamente** e gera o **Relatório de Devolução ao Cliente** (`saida/governanca_dados/relatorio_devolucao_cliente_<ORGAO>.md`):
- [ ] Aba `Dados - Insumos` 100% preenchida (sem campos em branco ou textos evasivos como *"ver com sap"*, *"a definir"*, *"xxxx"*).
- [ ] Aba `Dicionário de Dados` com todos os campos contendo `Nome do Campo`, `Descrição`, `Tipo`, `Anonimizar?`, `Sensibilidade` e `Sensível?`.
- [ ] Amostras de dados (`.csv` / `.xlsx`) livres de registros vazios em chaves de negócio e livres de colunas fantasmas (`;;;`).

### 2.2 Requisitos Regulatórios Aplicáveis
- [ ] **Classificação de Dados Pessoais (LGPD - Art. 5º, I):** Identificação de CPF, RG, Nome, E-mail, Telefone, Matrícula, Endereço, Placa/RENAVAM.
- [ ] **Classificação de Dados Pessoais Sensíveis (LGPD - Art. 5º, II e Art. 11º):** Dados de saúde/CID (ex: Planserv/Junta Médica), deficiência, biometria, origem racial/étnica, filiação sindical.
- [ ] **Enquadramento na Lei de Acesso à Informação (LAI - Lei nº 12.527/2011):**
  - [ ] Dado Público / Ostensivo
  - [ ] Dado Restrito / Pessoal (Art. 31 LAI — 100 anos)
  - [ ] Dado Reservado (5 anos) / Secreto (15 anos) / Ultrassecreto (25 anos)
- [ ] **Estratégia de Proteção no Transporte para MongoDB/AWS:**
  - [ ] Hash Criptográfico (`SHA-256` com Salt)
  - [ ] Mascaramento Parcial (ex: `***.456.789-**`)
  - [ ] Tokenização / Pseudonimização reversível em cofre seguro
  - [ ] Supressão (não transportar coluna para o Lakehouse)

---

## Seção 3 — Entregáveis de Governança Desejados

Marque os artefatos que devem ser gerados em `saida/governanca_dados/`:
- [x] **Diagnóstico de Inspeção / Relatório de Devolução ao Cliente (se houver pendências na origem)**
- [x] **Matriz DE/PARA de Padronização MongoDB (`snake_case` + Prefixos PRODEB + Tipos BSON)**
- [x] **Scripts MongoDB (`schemas_mongo/`): DDL `$jsonSchema` Strict, Índices, Registro em `tb_dataset`, `tb_sem_dominios`, `tb_sem_conceitos` e `tb_auditoria_eventos`**
- [x] **Artefatos AWS (`aws_sagemaker_catalog/` e `aws_datazone/`): Metadata Forms, Glossário Semântico e Script `boto3` para AWS Glue & Amazon SageMaker Catalog**
- [x] **Relatório de Conformidade LGPD/LAI e Contrato de Transporte de Dados**

---

## Seção 4 — Informações Complementares, Regras Específicas e Observações Livres do Engenheiro

> 📝 **ESPAÇO ABERTO DO ENGENHEIRO DE DADOS:**  
> Utilize esta seção para registrar **qualquer regra específica de governança, decreto estadual/municipal, política de retenção customizada, topologia de rede MongoDB/AWS ou orientação técnica** que não esteja contemplada nos campos acima.

- **Regras Específicas de Mascaramento / Anonimização ou Retenção:**
  - `[Ex: Os campos de remuneração líquida e descontos consignados devem ser marcados como Sensibilidade Pessoal Confidencial no SageMaker Catalog]`
- **Políticas Internas ou Decretos Específicos do Órgão/Cliente:**
  - `[Ex: Decreto Estadual nº 12.345 exige retenção de 5 anos em tb_auditoria_eventos com índice TTL automático]`
- **Contexto Adicional ou Instruções Livres para a IA:**
```text
[Escreva ou cole aqui livremente qualquer informação complementar, regra específica do projeto
ou instrução direta para o Agente considerar na Governança de Dados...]
```
