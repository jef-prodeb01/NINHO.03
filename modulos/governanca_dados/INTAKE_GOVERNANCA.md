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

### 2.0 Origem das Diretrizes
- [ ] **Opção 1: Selecionados nos checkboxes abaixo**
- [ ] **Opção 2: Documentados em arquivos na pasta `entrega/governanca_dados/`**
  - **Arquivo(s) de referência:** `[Ex: entrega/governanca_dados/politica_lgpd.md, classificacao_lai.xlsx]`
  - *(A IA lerá diretamente esses documentos para mapear termos, sensibilidade e retenção).*

### 2.1 Requisitos Regulatórios Aplicáveis
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

---

## Seção 4 — Informações Complementares, Regras Específicas e Observações Livres do Engenheiro

> 📝 **ESPAÇO ABERTO DO ENGENHEIRO DE DADOS:**  
> Utilize esta seção para registrar **qualquer regra específica de governança, decreto estadual/municipal de sigilo, política de retenção customizada, exceção de mascaramento ou orientação técnica** que não esteja contemplada nos campos acima.

- **Regras Específicas de Mascaramento / Anonimização ou Retenção:**
  - `[Ex: O campo NUM_PROCESSO_JUDICIAL deve ser mascarado apenas quando IND_SEGREDO_JUSTICA = 'S']`
- **Políticas Internas ou Decretos Específicos do Órgão/Cliente:**
  - `[Ex: Portaria Interna nº 123/2025 exige retenção mínima de 10 anos para logs de auditoria financeira]`
- **Contexto Adicional ou Instruções Livres para a IA:**
```text
[Escreva ou cole aqui livremente qualquer informação complementar, regra específica do projeto
ou instrução direta para o Agente considerar na Governança de Dados...]
```


