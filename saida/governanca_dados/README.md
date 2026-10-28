# Saídas de Governança de Dados (`saida/governanca_dados/`)

Gerado por `/executar-governanca` (`python ninho.py executar-governanca`). **Nunca crie subpastas com o nome do projeto.** Esta pasta não é versionada no Git (dados de cliente, LGPD).

| Arquivo | Quando é gerado | Conteúdo |
| --- | --- | --- |
| `relatorio_devolucao_cliente_<ORGAO>.md` | Gate 0.5 reprovado | Pendências linha a linha para o cliente sanear na origem. Nada mais é gerado. |
| `relatorio_governanca_<DATASET>.md` | Gate 0.5 aprovado | Classificação LGPD por nível, pendências `<INFORMAR>` do engenheiro, Radar Consultivo e lista de artefatos. |
| `matriz_de_para_lgpd_<DATASET>.csv` | Gate 0.5 aprovado | Campo origem → campo MongoDB (prefixo PRODEB) → tipo BSON → nível LGPD, base legal e anonimização. |
| `schemas_mongo/01..04_schema_*.js` | MongoDB marcado no Intake | Coleções centrais `tb_dataset`, `tb_sem_dominios`, `tb_sem_conceitos` e `tb_auditoria_eventos` (TTL de 5 anos), extraídas das referências oficiais da skill. |
| `schemas_mongo/05_regras_barreira_quarentena_<DATASET>.js` | MongoDB marcado | Barreira de qualidade: move registros reprovados da RAW para `tb_quarentena_<dataset>_<yyyymmdd>`. |
| `schemas_mongo/06_documento_tb_dataset_<DATASET>.js` | MongoDB marcado | Upsert idempotente do dataset no catálogo (campos, LGPD, regras de qualidade, linhagem). |
| `schemas_mongo/07_colecao_trusted_<DATASET>.js` | MongoDB marcado | Coleção TRUSTED com `$jsonSchema` estrito e índice único da chave de negócio. |
| `schemas_mongo/08_evento_auditoria_<DATASET>.js` | MongoDB marcado | Evento `ALTERACAO_METADADOS` na trilha de auditoria. |
| `aws_sagemaker_catalog/form_lgpd_lai_sagemaker.json` | AWS marcado | Metadata Form oficial de LGPD/LAI. |
| `aws_sagemaker_catalog/asset_payload_<DATASET>.json` | AWS marcado | Valores do formulário para o ativo do dataset. |
| `aws_sagemaker_catalog/glue_table_<DATASET>.json` | AWS marcado | Definição da tabela no Glue Data Catalog (tipos e nível LGPD por coluna). |
| `aws_sagemaker_catalog/publicar_catalogo_<DATASET>.py` | AWS marcado | Publicação via `boto3` (dry-run por padrão; `--aplicar` para publicar). |

Valores que nem o cliente nem o Intake informaram saem como `<INFORMAR: ...>`. O `/validar-entrega saida` reprova os artefatos até que todos sejam preenchidos.
