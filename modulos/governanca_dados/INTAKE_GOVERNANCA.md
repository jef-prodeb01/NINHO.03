# INTAKE_GOVERNANCA.md — Formulário de Entrada de Governança de Dados

Preencha este formulário com as definições de arquitetura de governança, catálogo de metadados, classificação de dados (LAI, LGPD) e esteiras de catálogo corporativo.

> ⚠️ **AVISO AO ENGENHEIRO DE DADOS:**  
> A IA iniciará a sessão conferindo este formulário. Se campos obrigatórios estiverem em branco, a IA solicitará que você acesse este link e complete os dados antes de gerar os schemas de governança e catálogos.

---

## Seção 0 — Identificação do Órgão & Projeto

- **Nome do Órgão / Cliente:** `[Ex: PRODEB, SEC, SSP, SEFAZ]`
- **Nome do Projeto / Domínio:** `[Ex: RH_BAHIA, SEI_BAHIA, GESTAODIS]`
- **Engenheiro de Dados Responsável:** `[Nome completo do engenheiro]`
- **Data de Início:** `[AAAA-MM-DD]`

---

## Seção 1 — Seleção de Tecnologias de Governança (MANDATÓRIO)

> 🛑 **REGRA DE ESCOPO:** Marque com `[x]` as tecnologias utilizadas na esteira de governança.

- [ ] **MongoDB Lakehouse (Coleções de Metadados e Documentos Canônicos):**
  - Modelagem NoSQL com envelope canônico `_governance` e organização multi-órgão (`_org`).
  - *(Gera artefatos em `saida/governanca_dados/schemas_mongo/`).*

- [ ] **Amazon DataZone & AWS Glue Data Catalog:**
  - Catálogo corporativo de dados em nuvem, linhagem técnica, formulários de metadados e termos de negócio.
  - *(Gera artefatos em `saida/governanca_dados/aws_datazone/`).*

- [ ] **Apache Hop (.hpl / .hwf):**
  - Pipelines de ingestão e transformação para alimentar a base de governança.

- [ ] **Extratores e Validadores Python (.py):**
  - Automações de catalogação ativa, profiling de dados e checagem de qualidade.

---

## Seção 2 — Diretrizes de Conformidade Legal (LGPD & LAI)

Marque os requisitos regulatórios aplicáveis às fontes de dados:
- [ ] **Classificação de Dados Pessoais (LGPD - Art. 5º):** Identificação de CPF, Nome, E-mail, Matrícula, Endereço.
- [ ] **Classificação de Dados Sensíveis (LGPD - Art. 11º):** Origem racial/étnica, convicção religiosa, saúde, biometria.
- [ ] **Enquadramento na Lei de Acesso à Informação (LAI):**
  - [ ] Dado Público Irrestrito
  - [ ] Dado Reservado (5 anos)
  - [ ] Dado Secreto (15 anos)
  - [ ] Dado Ultrassecreto (25 anos)
- [ ] **Mascaramento e Anonimização Dinâmica:** Aplicação de hash SHA-256 ou ofuscação em visualizações.

---

## Seção 3 — Entregáveis de Governança Desejados

Marque os artefatos que devem ser gerados em `saida/governanca_dados/`:
- [x] **Schemas Canônicos de Validação MongoDB (`schemas_mongo/`)**
- [x] **Formulários de Metadados e Mapeamentos AWS DataZone (`aws_datazone/`)**
- [x] **Relatório de Conformidade e Classificação LGPD/LAI**
