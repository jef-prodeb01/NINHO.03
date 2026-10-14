# Integração MongoDB Enterprise ➔ AWS Glue & Amazon SageMaker Unified Studio (SageMaker Catalog)

> 📌 **NOTA DE ATUALIZAÇÃO TECNOLÓGICA AWS:**
> O antigo **Amazon DataZone** foi descontinuado como produto isolado e unificado pela AWS dentro do **Amazon SageMaker Unified Studio / Amazon SageMaker Catalog (e SageMaker Lakehouse)**.
> Toda catalogação ativa em nuvem, glossário de negócios, Metadata Forms (LGPD/LAI) e descoberta de dados transportados para o MongoDB deve ser projetada para o **Amazon SageMaker Catalog + AWS Glue Data Catalog**.

---

## 1. Arquitetura do Fluxo de Transporte Ponta a Ponta

A atuação da equipe de Engenharia e Governança de Dados compreende:

1. **Validação na Origem (Responsabilidade do Cliente):**
   - O órgão produtor entrega o formulário de insumos e os dados 100% preenchidos e sem registros obrigatórios vazios.
   - Se houver dados/metadados vazios na origem, **o processo é interrompido e devolvido ao cliente** antes do transporte.
2. **Transporte para o MongoDB Enterprise (ODI 12c / Apache Hop / Python):**
   - Os dados aprovados são transportados da origem para o MongoDB (`RAW` ➔ Barreira de 4 Etapas ➔ `TRUSTED`) e registrados nas coleções de governança (`tb_dataset`, `tb_sem_dominios`, `tb_sem_conceitos`, `tb_auditoria_eventos`).
3. **Catalogação e Governança na AWS (Glue Data Catalog ➔ Amazon SageMaker Catalog):**
   - **AWS Glue Connection & Crawlers:** Conectam às coleções `trusted_*` e às coleções de catálogo do MongoDB para registrar os esquemas técnicos no **AWS Glue Data Catalog**.
   - **Amazon SageMaker Catalog (no SageMaker Unified Studio):**
     - Importa os ativos técnicos do Glue Catalog.
     - Estrutura os **Domains / Domain Units** por Órgão/Secretaria (`SAEB`, `DETRAN`, `PLANSERV`, `SESAB`, `SEFAZ`).
     - Aplica os **Metadata Forms** corporativos (`Form_LGPD_LAI`, `Form_Custodia_Gov`, `Form_Qualidade_Transporte`) alimentados diretamente pelos metadados de `tb_dataset` e `tb_sem_conceitos`.

---

## 2. Estrutura dos Artefatos Gerados em `saida/governanca_dados/aws_sagemaker_catalog/` (ou `aws_datazone/`)

Quando a integração AWS estiver marcada no `INTAKE_GOVERNANCA.md`, gere:

### 2.1 Metadata Form de Conformidade LGPD e LAI (`form_lgpd_lai_sagemaker.json`)
```json
{
  "platform": "AMAZON_SAGEMAKER_UNIFIED_STUDIO_CATALOG",
  "formName": "FormGovernancaLgpdLaiBahia",
  "description": "Formulário obrigatório de conformidade LGPD, LAI e responsabilidade na origem para ativos transportados do MongoDB.",
  "fields": [
    {
      "name": "cod_dataset_prodeb",
      "type": "STRING",
      "required": true,
      "description": "Código padronizado SIGLA_ORGAO_UNIDADE_TEMA_VERSAO no tb_dataset"
    },
    {
      "name": "sig_orgao_proprietario",
      "type": "STRING",
      "required": true,
      "description": "Sigla do órgão responsável pelo saneamento na origem (ex: SAEB, DETRAN)"
    },
    {
      "name": "nom_data_owner_origem",
      "type": "STRING",
      "required": true,
      "description": "Cargo e titular responsável pelos dados na origem"
    },
    {
      "name": "des_nivel_sensibilidade_global",
      "type": "ENUM",
      "allowedValues": ["PUBLICO", "INTERNO", "CONFIDENCIAL", "RESTRITO"],
      "required": true
    },
    {
      "name": "des_grau_sigilo_lai",
      "type": "ENUM",
      "allowedValues": ["OSTENSIVO", "RESERVADO_5_ANOS", "SECRETO_15_ANOS", "ULTRASSECRETO_25_ANOS"],
      "required": true
    },
    {
      "name": "ind_contem_dados_pessoais_lgpd",
      "type": "BOOLEAN",
      "required": true
    },
    {
      "name": "ind_contem_dados_sensiveis_art11",
      "type": "BOOLEAN",
      "required": true
    },
    {
      "name": "des_base_legal_lgpd",
      "type": "STRING",
      "required": true
    },
    {
      "name": "sts_validacao_origem_cliente",
      "type": "ENUM",
      "allowedValues": ["APROVADO_SEM_REGISTROS_VAZIOS", "DEVOLVIDO_AO_CLIENTE_PARA_CORRECAO"],
      "required": true
    }
  ]
}
```

### 2.2 Mapeamento de Ativo e Glossário para o SageMaker Catalog (`asset_payload_<PROJETO>.json`)
Sincroniza os termos de `tb_sem_conceitos` (`lst_termos`) e as colunas de `tb_dataset` (`metadados_campos`) com o catálogo da AWS via `boto3` (API do SageMaker Catalog / Glue).

