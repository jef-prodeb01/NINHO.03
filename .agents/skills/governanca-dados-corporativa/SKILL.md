---
name: governanca-dados-corporativa
description: >-
  Gera artefatos de governança de dados, auditoria de qualidade de insumos na origem
  (com bloqueio e devolução ao cliente em caso de dados/metadados vazios), modelagem
  MongoDB Enterprise no padrão PRODEB/SAEB (tb_dataset, tb_sem_dominios, tb_sem_conceitos,
  tb_auditoria_eventos, tb_quarentena) e integração de transporte para AWS Glue e
  Amazon SageMaker Unified Studio / SageMaker Catalog (substituto do antigo DataZone).
---

# Skill: Governança Corporativa de Dados (Transporte Cliente ➔ MongoDB ➔ AWS SageMaker Catalog)

Esta skill orienta a auditoria rigorosa dos insumos enviados pelo cliente, a modelagem das coleções de Governança e Camada Semântica no **MongoDB Enterprise (Padrão PRODEB/SAEB)** e o catálogo ativo no **AWS Glue Data Catalog & Amazon SageMaker Unified Studio / SageMaker Catalog** (que substituiu o antigo Amazon DataZone).

---

## 🛑 1. Regra Inviolável de Responsabilidade na Origem (Gate de Saneamento do Cliente)

> ⚠️ **ATUAÇÃO ESTRITA NO TRANSPORTE (CLIENTE ➔ MONGODB ➔ AWS):**
> A equipe de Engenharia e Governança de Dados **só atua no transporte, catalogação e governança** dos dados para o MongoDB e para a AWS (SageMaker Catalog).
> **Manter os dados e metadados corretos, completos e sem registros vazios é responsabilidade exclusiva do Cliente (Órgão Produtor).**

### Protocolo Obrigatório de Auditoria e Devolução ao Cliente:
1. Antes de gerar os esquemas finais de transporte, execute o inspetor automatizado:
   ```bash
   python core/scripts_comuns/inspecionar_insumos_governanca.py
   ```
2. **Critérios de Bloqueio e Devolução Imediata ao Cliente:**
   - **Planilha de Levantamento (`Dados - Insumos`) com campos vazios ou evasivos:** ex: `Data Owner` em branco, `Volume` em branco ou preenchido com `"ver com SAP"`, `"a definir"`, `"XXXX"`.
   - **Dicionário de Dados incompleto:** qualquer coluna sem `Descrição`, sem `Tipo`, ou com as marcações de LGPD (`Anonimizar? (S/N)`, `Sensibilidade`, `Sensível? (S/N)`) vazias.
   - **Amostras de Dados (`.csv`, `.xlsx`, `.json`) com registros vazios:** linhas em branco, chaves de negócio (CPF, Matrícula, Código) vazias/nulas, colunas sem cabeçalho (`;;;;`) ou tipos corrompidos.
3. **Ação em Caso de Falha na Origem:**
   - **NÃO invente dados, NÃO assuma valores padrão para cobrir falhas do cliente e NÃO prossiga com o transporte definitivo.**
   - Gere imediatamente o **Relatório Formal de Devolução ao Cliente** (`saida/governanca_dados/relatorio_devolucao_cliente_<ORGAO>.md`) listando linha por linha e coluna por coluna o que está vazio/incorreto para que o cliente corrija na origem e reenvie.

---

## 📚 2. Referências Técnicas Obrigatórias da Skill

Consulte sempre os documentos de referência desta skill antes de gerar qualquer artefato:
1. [**`padrao_nomenclatura_e_tipos_mongodb.md`**](./references/padrao_nomenclatura_e_tipos_mongodb.md):
   - Código de dataset (`SIGLA_ORGAO_UNIDADE_TEMA_VERSAO`), prefixos PRODEB em `snake_case` (`tb_`, `cod_`, `nom_`, `des_`, `num_`, `ind_`, `dtc_`, `dth_`, `lst_`, `val_`), conversão de tipos BSON (`Decimal128` para valores monetários, `string` para CPF/CNPJ/CEP/Matrícula, `date` UTC) e **Barreira de Qualidade em 4 Etapas (RAW ➔ TRUSTED)**.
2. [**`arquitetura_colecoes_mongodb.md`**](./references/arquitetura_colecoes_mongodb.md):
   - Schemas `$jsonSchema` (corrigidos para suportar subdocumentos com `additionalProperties`) e scripts `mongosh` para:
     - `tb_dataset` (Catálogo técnico unificado com `orgao_responsavel`, `sistema_origem`, `governanca`, `metadados_campos`, `regras_qualidade`, `linhagem_origem` e `consumo_autorizado`).
     - `tb_auditoria_eventos` (Monitoramento Write-Heavy das 4 categorias de evento com **índice TTL de 5 anos / 157.680.000s**).
     - `tb_quarentena_<tema>_<yyyymmdd>` (Isolamento de registros reprovados na barreira de qualidade para devolução ao cliente).
3. [**`camada_semantica_mongodb.md`**](./references/camada_semantica_mongodb.md):
   - Modelagem Híbrida Centrada no Conceito (Cenário C): coleções `tb_sem_dominios` (`DOM_*`) e `tb_sem_conceitos` (`CNC_*` com `lst_termos`, `lst_atributos`, `lst_relacionamentos` e `lst_dataset_conceitos` para interoperabilidade entre órgãos).
4. [**`integracao_aws_sagemaker_glue.md`**](./references/integracao_aws_sagemaker_glue.md):
   - Integração do MongoDB com o **AWS Glue Data Catalog** e **Amazon SageMaker Unified Studio / SageMaker Catalog** (substituto oficial do antigo Amazon DataZone).
5. [**`diretrizes_lgpd.md`**](./references/diretrizes_lgpd.md):
   - Classificação em 4 níveis (`PUBLICO`, `INTERNO`, `CONFIDENCIAL`, `RESTRITO`), bases legais do setor público (Art. 7º, III e Art. 11, II da LGPD), LAI e regras de anonimização/mascaramento.

---

## 🔄 3. Fluxo de Trabalho Passo a Passo

1. **Fase 1 — Gate 0 e Auditoria de Saneamento dos Dados do Cliente:**
   - Verifique [`modulos/governanca_dados/INTAKE_GOVERNANCA.md`](../../../modulos/governanca_dados/INTAKE_GOVERNANCA.md) e rode `python core/scripts_comuns/inspecionar_insumos_governanca.py`.
   - Se houver dados ou metadados vazios enviados pelo cliente, emita o **Relatório de Devolução ao Cliente** e aguarde a correção na origem.
2. **Fase 2 — Blueprint de Governança, Matriz DE/PARA BSON e 💡 Radar Consultivo da IA:**
   - Com os dados do cliente 100% íntegros, apresente o Blueprint contendo:
     - **Matriz DE/PARA Completa:** `Campo Origem` ➔ `Campo Destino MongoDB (prefixo PRODEB)` ➔ `Tipo Origem` ➔ `Tipo BSON` ➔ `Classificação LGPD/LAI`.
     - **💡 Radar Consultivo da IA:** Alertas de risco LGPD implícito, regras adicionais para a Barreira de 4 Etapas e sugestões de Conceitos Canônicos (`CNC_*`) para cruzamento entre órgãos.
3. **Fase 3 — Geração Física dos Artefatos MongoDB e AWS SageMaker Catalog:**
   - Execute a esteira determinística `python ninho.py executar-governanca` (`core/scripts_comuns/gerar_artefatos_governanca.py`). Ela refaz o Gate 0.5, lê o Intake e gera os arquivos abaixo. Não escreva esses scripts à mão: revise o `relatorio_governanca_<DATASET>.md` e resolva as pendências `<INFORMAR: ...>` com o engenheiro.
   - Os scripts das coleções centrais (01 a 04) são extraídos dos blocos `// Script:` destas referências; para mudar o padrão, edite a referência.
   - Scripts gerados em `saida/governanca_dados/schemas_mongo/`:
     - `01_schema_tb_dataset.js`
     - `02_schema_tb_sem_dominios.js`
     - `03_schema_tb_sem_conceitos.js`
     - `04_schema_tb_auditoria_eventos.js`
     - `05_regras_barreira_quarentena_<DATASET>.js`
     - `06_documento_tb_dataset_<DATASET>.js` (upsert idempotente do dataset catalogado)
     - `07_colecao_trusted_<DATASET>.js` (`$jsonSchema` estrito + índice da chave de negócio)
     - `08_evento_auditoria_<DATASET>.js`
   - Se AWS estiver marcada no Intake, gere os payloads e Metadata Forms do **Amazon SageMaker Catalog & AWS Glue** em `saida/governanca_dados/aws_sagemaker_catalog/` (ou `aws_datazone/`).
   - Gere o relatório executivo e matriz DE/PARA em `saida/governanca_dados/relatorio_governanca_<PROJETO>.md`.

---

## 📂 4. Destino Canônico de Saída

Grave todos os arquivos estritamente nas pastas oficiais (sem criar subpastas com nome de projeto):
- `saida/governanca_dados/schemas_mongo/`
- `saida/governanca_dados/aws_sagemaker_catalog/` *(ou `saida/governanca_dados/aws_datazone/` para retrocompatibilidade)*
- `saida/governanca_dados/relatorio_governanca_<PROJETO>.md`
- `saida/governanca_dados/relatorio_devolucao_cliente_<ORGAO>.md` *(quando houver bloqueio por dados/metadados vazios na origem)*
