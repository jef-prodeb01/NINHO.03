# Saídas de Governança de Dados (`saida/governanca_dados/`)

Esta pasta armazena os artefatos oficiais gerados pelo módulo de Governança de Dados (**NUNCA crie subpastas com o nome do projeto**):

- **`relatorio_devolucao_cliente_<ORGAO>.md`**: *(Gerado quando o Gate 0.5 reprova os insumos)* Checklist detalhado de campos vazios, registros em branco ou omissões de LGPD na planilha/amostra para devolução e saneamento pelo cliente na origem.
- **`schemas_mongo/`**:
  - Scripts `.js`/`.json` de criação de coleções de negócio com `$jsonSchema` (`validationLevel: "strict"`), tipagem BSON PRODEB (`Decimal128`, `string`, `date`) e índices compostos.
  - Scripts `.js` de carga nas coleções centrais de governança: `tb_dataset`, `tb_sem_dominios`, `tb_sem_conceitos` e `tb_auditoria_eventos` (com índice TTL de 5 anos).
- **`aws_sagemaker_catalog/`** *(e `aws_datazone/` para compatibilidade)*:
  - Especificações JSON de Metadata Forms (`lgpd_compliance_form`, `lai_transparency_form`, `prodeb_provenance_form`), Glossário de Negócio Semântico e scripts Python (`boto3`) para publicação ativa no **AWS Glue Data Catalog** e **Amazon SageMaker Unified Studio / SageMaker Catalog (ex-DataZone)**.
