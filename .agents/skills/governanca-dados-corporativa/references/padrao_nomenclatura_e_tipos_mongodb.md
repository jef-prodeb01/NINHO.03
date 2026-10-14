# Padrão Corporativo de Nomenclatura, Tipagem BSON e Barreira de Qualidade no MongoDB (Padrão PRODEB / SAEB)

Este documento define as regras obrigatórias para nomenclatura de datasets, coleções, atributos, conversão de tipos BSON e a **Regra Inviolável de Responsabilidade de Qualidade na Origem (Cliente)**.

---

## 1. Regra de Ouro Zero: Responsabilidade Estrita do Cliente na Origem (Bloqueio e Devolução)

> 🛑 **DIRETRIZ INVIOLÁVEL DE TRANSPORTE E GOVERNANÇA:**
> A equipe de Engenharia e Governança de Dados atua **exclusivamente no transporte seguro (via ODI, Apache Hop ou Python), catalogação e governança** dos dados para o **MongoDB Enterprise** e posterior disponibilização/catalogação na **AWS (AWS Glue & Amazon SageMaker Catalog)**.
> **A integridade, completude e veracidade dos dados e metadados na origem são 100% de responsabilidade do Órgão/Cliente produtor.**

### 1.1 Quando Devolver Imediatamente ao Cliente (Pré-Voo / Levantamento)
O processo de construção da esteira de transporte **DEVE SER BLOQUEADO E DEVOLVIDO AO CLIENTE** (gerando o artefato `saida/governanca_dados/relatorio_devolucao_cliente_<ORGAO>.md`) sempre que:
1. **Planilha de Levantamento (`Dados - Insumos`) Incompleta:**
   - Campos obrigatórios vazios ou preenchidos com textos evasivos como `"ver com SAP"`, `"a definir"`, `"XXXX"`, `"não sei"`.
   - Ausência de *Data Owner* / *Data Steward* nominal ou institucional, ausência de volume estimado, frequência de atualização ou sistema/banco de origem.
2. **Dicionário de Dados com Lacunas ou Contradições LGPD:**
   - Qualquer campo listado na aba de Dicionário de Dados que esteja com **Descrição vazia**, **Tipo de dado vazio**, ou com as colunas **`Anonimizar? (S/N)`**, **`Sensibilidade (Público, Interno, Confidencial)`** ou **`Sensível? (S/N)`** em branco.
   - Campos claramente pessoais/sensíveis (ex: `CPF`, `Nome`, `Salário`, `CID/Deficiência`, `Placa/Chassi`, `E-mail`, `Telefone`) marcados como `Público` sem justificativa legal explícita.
3. **Amostras de Dados (`.csv`, `.xlsx`, `.json`) com Registros Vazios ou Corrompidos:**
   - Linhas inteiras em branco, colunas obrigatórias (chaves primárias/negócio como CPF, Matrícula, Código) com valores vazios/nulos, colunas extras sem cabeçalho (`;;;;`) ou formatos corrompidos.
   - **A Engenharia NÃO faz "limpeza mágica" nem inventa valores padrão para encobrir falha cadastral do cliente:** o arquivo de amostra é rejeitado no Gate 0 com evidência exata das linhas/colunas vazias para que o cliente corrija na origem antes do transporte.

---

## 2. Padrão de Nomenclatura de Datasets dos Órgãos

Todo dataset catalogado deve possuir um código único e imutável seguindo a estrutura:

```text
SIGLA_ORGAO_UNIDADE_TEMA_VERSAO
```

- **Regras Estritas:**
  - Apenas letras **MAIÚSCULAS**, números e underscore (`_`).
  - Proibido o uso de acentos, espaços, hifens ou caracteres especiais.
  - Incrementar a versão (`_V1`, `_V2`) sempre que houver mudança estrutural homologada.
- **Exemplos Oficiais:**
  - `SAEB_SGI_IDENTIDADE_CIDADAO_V1`
  - `DETRAN_HABILITACAO_RENACH_V1`
  - `DETRAN_VEICULOS_RENAVAM_V1`
  - `PLANSERV_ASSISTENCIA_BENEFICIARIOS_V1`
  - `SAEB_SUPREV_INATIVOS_PENSIONISTAS_V1`

---

## 3. Padrão de Nomenclatura Física no MongoDB (`snake_case`)

Diferente do Oracle (que utiliza `UPPER_CASE`), todos os objetos físicos no MongoDB utilizam **`snake_case` estritamente em letras minúsculas**, sem acentos ou caracteres especiais.

### 3.1 Prefixos de Coleções (`tb_`)
- **Catálogo Técnico de Ativos:** `tb_dataset`, `tb_orgao`, `tb_sistema`
- **Camada Semântica Governamental:** `tb_sem_dominios`, `tb_sem_conceitos`
- **Observabilidade e Auditoria Operacional:** `tb_auditoria_eventos`
- **Quarentena (Rejeições de Carga):** `tb_quarentena_<tema>_<yyyymmdd>`

### 3.2 Tabela Oficial de Prefixos de Atributos (Campos BSON)

Todo atributo escalar de negócio deve iniciar com um prefixo de 3 letras seguido de underscore (`_`):

| Prefixo MongoDB | Significado / Categoria | Origem Equivalente (PRODEB) | Exemplos Físicos no MongoDB |
| :--- | :--- | :--- | :--- |
| **`ide_`** | Identificador interno / técnico | `ID_`, `IDE_` | `ide_registro`, `ide_evento` |
| **`cod_`** | Código estruturado ou chave de negócio | `COD_`, `CD_` | `cod_dataset`, `cod_orgao`, `cod_dominio`, `cod_conceito` |
| **`nom_`** | Nome próprio (pessoa, órgão, sistema, dataset) | `NOME_`, `NM_` | `nom_cidadao`, `nom_orgao`, `nom_sistema`, `nom_dataset` |
| **`des_`** | Descrição textual livre, endereço, e-mail, motivo | `DESC_`, `DS_` | `des_finalidade`, `des_email`, `des_endereco_rua`, `des_motivo` |
| **`num_`** | Número de documento ou string numérica | `NUM_`, `NR_` | `num_cpf`, `num_cnpj`, `num_cep`, `num_telefone`, `num_matricula` |
| **`tip_`** | Tipo ou natureza | `TIP_`, `TP_` | `tip_dado`, `tip_fonte`, `tip_acesso`, `tip_relacionamento` |
| **`sts_`** | Status ou situação do ciclo de vida | `STS_`, `ST_` | `sts_dataset`, `sts_registro`, `sts_execucao` |
| **`ind_`** | Indicador booleano (`true` / `false`) | `IND_`, `FL_` | `ind_obrigatorio`, `ind_dado_pessoal`, `ind_dado_sensivel`, `ind_ativo` |
| **`ref_`** | Referência externa ou competência | `REF_` | `ref_competencia`, `ref_orgao` |
| **`qtd_`** | Quantidade contável (inteiro) | `QTD_`, `QT_` | `qtd_registros_lidos`, `qtd_registros_rejeitados`, `qtd_matriculas` |
| **`prc_`** | Percentual ou taxa | `PRC_`, `PCT_` | `prc_crescimento_mensal`, `prc_meta_qualidade` |
| **`val_`** | Valor monetário ou financeiro (`Decimal128`) | `VAL_`, `VL_` | `val_salario_bruto`, `val_liquido`, `val_beneficio` |
| **`dtc_`** | Data pura (armazenada em UTC `ISODate`) | `DT_`, `DTC_` | `dtc_nascimento`, `dtc_cadastro`, `dtc_vigencia` |
| **`dth_`** | Data e Hora completa (Timestamp UTC `ISODate`) | `DTH_`, `DH_` | `dth_evento`, `dth_ingestao`, `dth_inicio_carga` |
| **`hor_`** | Hora isolada | `HOR_` | `hor_evento` |
| **`sig_`** | Sigla institucional ou UF | `SG_`, `SIG_` | `sig_orgao`, `sig_uf` |
| **`txt_`** | Texto longo / observação extensa | `TXT_`, `CLOB` | `txt_observacao`, `txt_regra_transformacao` |
| **`lst_`** | Lista / Array de subdocumentos ou itens | `LST_` | `lst_termos`, `lst_atributos`, `lst_relacionamentos`, `lst_campos` |
| **`jsn_`** | Objeto JSON livre / payload | `JSN_` | `jsn_payload_origem` |

### 3.3 Campos Mínimos de Auditoria em Documentos Persistidos
Todo registro governado deve manter rastreabilidade mínima:
- `ide_registro` (ou `_id`)
- `sts_registro` (`"ATIVO"`, `"INATIVO"`)
- `num_versao` (ex: `"1.0"`)
- `dth_criacao` / `dtc_criacao` (UTC `ISODate`)
- `des_usuario_criacao` (ou `cod_job_ingestao`)
- `dth_atualizacao` / `dtc_atualizacao` (UTC `ISODate`)
- `des_usuario_atualizacao`

---

## 4. Matriz Oficial de Conversão de Tipos (Origem ➔ BSON MongoDB)

| Tipo na Origem (Relacional / CSV / SAP / JSON) | Tipo BSON Oficial (`bsonType`) | Regra de Transporte e Qualidade Obrigatória |
| :--- | :--- | :--- |
| `CHAR`, `VARCHAR`, `VARCHAR2`, `TEXT`, `CLOB` | `"string"` | Remover espaços nas extremidades (`TRIM`) e caracteres de controle invisíveis; proibir string vazia `""` quando obrigatório (converter/rejeitar). |
| **`CPF`, `CNPJ`, `CEP`, `Telefone`, `Matrícula`, `CNH`, `Processo`** | **`"string"`** | **REGRA ESPECIAL INVIOLÁVEL:** Mesmo que na origem esteja como numérico (`NUMBER`/`INT`), armazenar **SEMPRE como `"string"`** para preservar zeros à esquerda. Higienizar pontuação na camada TRUSTED (ex: CPF com exatos 11 dígitos numéricos). |
| `INTEGER`, `SMALLINT`, `TINYINT`, `NUMBER(p,0)` (até 9 dígitos) | `"int"` (`Int32`) | Validar formato estritamente numérico. |
| `BIGINT`, `NUMBER(p,0)` (10+ dígitos) | `"long"` (`Int64`) | Validar formato numérico de 64 bits. |
| **`DECIMAL`, `NUMBER(p,s)` (Valores Monetários / Financeiros)** | **`"decimal"` (`Decimal128`)** | **REGRA FINANCEIRA INVIOLÁVEL:** Valores de salário, arrecadação, benefício ou taxas financeiras **DEVEM usar `Decimal128` (`"decimal"`)** e NUNCA `double`/`float`, evitando erros de arredondamento de ponto flutuante. |
| `FLOAT`, `DOUBLE`, Índices Científicos | `"double"` | Apenas para métricas estatísticas não-monetárias. |
| `DATE`, `DATETIME`, `TIMESTAMP` | `"date"` (`ISODate` UTC) | Converter obrigatoriamente para **UTC (`ISODate("YYYY-MM-DDTHH:mm:ssZ")`)**. Rejeitar datas inválidas (ex: `00/00/0000` ou `31/02`). |
| `BOOLEAN`, Flags `S/N`, `SIM/NAO`, `0/1`, `X/vazio` | `"bool"` | Converter durante o transporte ETL para booleano nativo (`true` ou `false`). |
| Estrutura Aninhada / JSON / XML | `"object"` | Validar estrutura interna e presença dos campos obrigatórios. |
| Lista / Coleção de Itens | `"array"` | Validar tipo dos elementos internos e cardinalidade mínima quando exigida. |

---

## 5. Arquitetura de Camadas do Data Lake e Barreira de 4 Etapas

O transporte de dados entre os órgãos, o MongoDB e a nuvem AWS segue o fluxo:

```text
[Origem do Cliente (Saneada)] 
      │
      ▼ (Transporte via ODI 12c / Apache Hop / Python)
[Camada RAW (Bronze - Imutável)]
      │
      ▼ (Barreira Automatizada de Qualidade em 4 Etapas)
      ├──► (Registros Reprovados / Vazios) ──► [tb_quarentena_<dataset>_<YYYYMMDD>] ──► Devolução ao Data Owner do Cliente!
      │
      ▼ (Registros 100% Conformes)
[Camada TRUSTED (Silver - MongoDB Enterprise Governado)]
      │
      ▼ (Integração de Catálogo e Consumo Analítico)
[AWS Glue Data Catalog & Amazon SageMaker Unified Studio / SageMaker Catalog]
```

### As 4 Etapas da Barreira Automatizada (RAW ➔ TRUSTED)
1. **Etapa 1 — Validação Técnica:** Verifica integridade estrutural do payload, encoding UTF-8 e conectividade.
2. **Etapa 2 — Validação de Metadados:** Confere se o esquema recebido bate com a versão ativa em `tb_dataset` (detecção de *Schema Drift* — colunas removidas ou não catalogadas).
3. **Etapa 3 — Validação de Qualidade de Dados:**
   - **Completude:** Rejeita qualquer registro com campo obrigatório (`ind_obrigatorio: true`) nulo ou vazio (`""`).
   - **Conformidade:** Valida dígito verificador e tamanho (ex: CPF com 11 dígitos, UF válida, `Decimal128` válido).
   - **Unicidade:** Impede duplicação da chave de negócio no lote.
   - **Validade Temporal:** Impede datas futuras indevidas (ex: data de nascimento ou óbito no futuro).
4. **Etapa 4 — Validação de Governança e LGPD:** Confirma se todos os campos pessoais/sensíveis possuem classificação registrada e aplica pseudonimização/mascaramento quando exigido para o destino.

