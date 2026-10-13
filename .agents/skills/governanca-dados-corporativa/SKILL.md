---
name: governanca-dados-corporativa
description: >-
  Gera artefatos de governança de dados: catálogo de dados, mapeamento de conformidade
  LGPD/LAI, contratos de dados, esquemas MongoDB e integração com AWS DataZone / Glue.
---

# Skill: Governança Corporativa de Dados

Esta skill orienta a documentação, catalogação e aplicação de diretrizes de conformidade jurídica (LGPD e Lei de Acesso à Informação - LAI) para ativos de dados institucionais.

## 1. Fluxo de Trabalho de Governança

1. **Mapeamento de Conformidade:**
   - Classifique cada coluna em um dos 4 níveis de sensibilidade (Público, Interno, Pessoal, Sensível) conforme detalhado em [diretrizes_lgpd.md](./references/diretrizes_lgpd.md).
   - Defina regras de retenção (temporalidade documental) e descarte.
2. **Geração de Esquemas MongoDB:**
   - Para projetos com catálogo baseado em documentos NoSQL (MongoDB), gere os JSON Schemas de validação e documentos de metadados em `saida/governanca_dados/schemas_mongo/`.
3. **Integração com AWS DataZone / Glue:**
   - Gere os formulários de metadados de formulário (`formType`), dicionários de ativos (`AssetType`) e scripts de carga em `saida/governanca_dados/aws_datazone/`.

---

## 2. Destino Canônico de Saída

Gere os artefatos diretamente nas pastas:
- `saida/governanca_dados/schemas_mongo/`
- `saida/governanca_dados/aws_datazone/`
- `saida/governanca_dados/relatorio_governanca_<PROJETO>.md`

