---
name: gerador-etl-hop
description: >-
  Gera e audita pipelines (.hpl), workflows (.hwf) e metadados (.json) do Apache Hop 2.x para esteiras
  corporativas de carga de DW Oracle, incluindo auditoria em ETA_ETAPAS_CARGA, captura nativa via
  WorkflowLogging, Gate de Qualidade com tabela TAB_*_ERRO e devolução por e-mail HTML, Variable Resolver
  hop-pwd e motor preditivo HOP-H1 a HOP-H8. Use quando Apache Hop estiver marcado no INTAKE_DW.md ou ao
  auditar projetos Hop.
---

# Skill: Gerador & Auditor de Esteiras Apache Hop 2.x

Esta skill orienta a geração estritamente condicional e a auditoria preditiva de artefatos do Apache Hop 2.x (`.hpl` — pipelines de transformação, `.hwf` — workflows de orquestração e `.json` — configurações de ambiente e metadados).

> 🛑 **REGRA DE ATIVAÇÃO CONDICIONAL (GERAÇÃO):**  
> Esta skill **NUNCA** deve gerar arquivos em `saida/` se o Engenheiro de Dados não tiver marcado `[x] Apache Hop` na Seção 1 do `INTAKE_DW.md`.  
> Se desmarcado, a pasta `saida/planejador_dw/06_pipelines_hop/` DEVE permanecer intacta contendo apenas seu `.gitkeep`.  
> *(Nota: Para auditoria de esteiras Hop existentes depositadas pelo usuário, utilize `python core/scripts_comuns/auditar_esteira_hop.py <caminho>`).*

---

## 🏗️ 1. Arquitetura Corporativa PRODEB para Esteiras Apache Hop 2.x

Os projetos corporativos no Apache Hop 2.x seguem uma arquitetura de **5 camadas de resiliência e rastreabilidade**:

### 1.1 Ciclo de Vida e Auditoria no Banco (`ETA_ETAPAS_CARGA`)
Todo workflow principal (`CARGA_PRINCIPAL.hwf` / `carga_stages.hwf`) registra seu ciclo de vida na tabela corporativa `ETA_ETAPAS_CARGA`:
1. **Geração do ID de Execução (`utils/sequence_etapas_carga.hpl`):**
   - Executa `SELECT ETA_ETAPAS_CARGA_SEQ.NEXTVAL AS V_SEQ FROM DUAL` via `TableInput`.
   - Publica `${V_SEQ}` no escopo `PARENT_WORKFLOW` via transform `SetVariable`.
2. **Abertura da Carga (Action `SQL`):**
   ```sql
   INSERT INTO ${ENV_DB_SCHEMA}.ETA_ETAPAS_CARGA
     (IDE_EXECUCAO, DES_PROCEDURE, DTC_INICIO, DTC_FIM, DES_ASSUNTO, DES_PROJETO, DES_STATUS)
   VALUES
     (${V_SEQ}, 'CARGA_HOP', SYSDATE, NULL, 'STAGING', '${HOP_PROJECT_NAME}', 'CARREGANDO');
   COMMIT;
   ```
3. **Encerramento da Carga (Action `SQL` por caminho):**
   - **Sucesso:** `UPDATE ... SET DTC_FIM = SYSDATE, DES_STATUS = 'SUCESSO' WHERE IDE_EXECUCAO = ${V_SEQ};`
   - **Erro Técnico:** `UPDATE ... SET DTC_FIM = SYSDATE, DES_STATUS = 'ERRO' WHERE IDE_EXECUCAO = ${V_SEQ};`
   - **Erro de Negócio / Planilha Inválida:** `UPDATE ... SET DTC_FIM = SYSDATE, DES_STATUS = 'ERRO_MAPEADO', DES_ERRO = 'Erro de validação nos dados de entrada' WHERE IDE_EXECUCAO = ${V_SEQ};`

### 1.2 Captura Automática de Falhas via `WorkflowLogging` (`utils/capturar_log_ftps.hpl`)
- Configurado em `metadata/workflow-log/workflow_log_<projeto>.json` com `"logLevel": "ERROR"`, `"executingAtEnd": true`.
- O pipeline `capturar_log_ftps.hpl` usa o transform nativo **`WorkflowLogging`** (`logTransforms = Y`), filtra actions com `actionErrors > 1`, extrai `actionLoggingText` / `actionReason` via `ScriptValueMod` (truncando em 4.000 caracteres para caber em `VARCHAR2(4000)`) e executa `ExecSql` gravando o motivo exato na coluna `ETA_ETAPAS_CARGA.DES_ERRO`.

### 1.3 Gate de Qualidade no Hop com Quarentena (`TAB_<PROJETO>_ERRO`) e E-mail HTML
Quando a fonte é planilha Excel (`ExcelInput` com `<spreadsheet_type>SAX_POI</spreadsheet_type>`) ou CSV externo:
1. **`VALIDAR_PLANILHAS.hpl`:** Lê os campos críticos como `String` e aplica `SelectValues` (`<meta>`) com `<date_format_lenient>N</date_format_lenient>` para validar datas/números.
2. **`<transform_error_handling>`:** Desvia apenas as linhas com erro (capturando `campo_erro` e `descricao_erro`), adiciona constante de origem (`COD_ORIGEM`) e grava na tabela `TAB_<PROJETO>_ERRO` (`TableOutput` com `truncate = Y`, `use_batch = Y`, `specify_fields = Y`).
3. **`CONSULTAR_ENVIO_EMAIL.hpl`:** Conta `SELECT COUNT(*) AS QTD_ERROS FROM TAB_<PROJETO>_ERRO`.
   - Se `QTD_ERROS = 0`: prossegue para os pipelines de carga das Stagings (`CARGA_STAGINGS_*.hpl`).
   - Se `QTD_ERROS > 0`: desvia para `MONTAR_EMAIL_ERRO.hpl`, que monta tabela HTML no padrão visual COGID/PRODEB (`Planilha | ID | Campo com Erro | Valor Informado`), seta `${HTML_CORPO}` no `ROOT_WORKFLOW` e dispara `enviar_email.hwf`.

### 1.4 Gestão Segura de Senhas (`HopPassword` Variable Resolver vs `decrypt_pass.hpl`)
- **Padrão Moderno Recomendado (Hop 2.x):** Criar `metadata/variable-resolver/hop-pwd.json` (`HopPassword`) e referenciar senhas em actions Shell/REST/Mail usando `#{hop-pwd:ENV_API_PASS}` ou `${ENV_DB_PASS}` (com valor `Encrypted ...` no arquivo de ambiente `ambiente_prod.json`).
- **Regra Inviolável (`HOP-H1`):** **NUNCA** gravar senhas em texto puro em `<auth_password>`, `<password>` ou variáveis JSON.

### 1.5 Modalidades Adicionais Suportadas
- **Ingestão REST Encadeada (`CARGA_STAGINGS_API.hpl`):** `RowGenerator` (1 linha) $\rightarrow$ `Rest` (GET com retry em `429, 500, 502, 503, 504`) $\rightarrow$ `JsonInput` (`$.*.campo`) $\rightarrow$ `SelectValues` (remove payload bruto) $\rightarrow$ `TableOutput`.
- **Ingestão Binária de Imagens/Anexos (`Fotos.hpl`):** `LoadFileInput` (`element_type = content`, `type = Binary`) $\rightarrow$ `Formula` (extrai código identificador do nome do arquivo) $\rightarrow$ `InsertUpdate` em coluna `BLOB`/`RAW`.

---

## 🚨 2. Catálogo de Heurísticas e Anti-Padrões (`HOP-H1` a `HOP-H8`)

Sempre execute `python core/scripts_comuns/auditar_esteira_hop.py <pasta>` para auditar esteiras existentes ou validar artefatos gerados:

| Código | Severidade | Anti-Padrão Detectado | Correção Obrigatória |
| :---: | :---: | :--- | :--- |
| **`HOP-H1`** | 🔴 Crítico | Senha em texto aberto em `<auth_password>`, `<password>` ou JSON de ambiente | Usar `Encrypted ...` no `ambiente_*.json` ou `#{hop-pwd:VAR}` |
| **`HOP-H2`** | 🔴 Crítico | Vazamento de Copy-Paste entre projetos (ex: `DES_PROJETO = 'CFPC_FISC'` ou `/DHPP/entrada/` dentro de outro projeto) ou `<name>` divergente do arquivo | Usar `${HOP_PROJECT_NAME}` e `${PROJECT_HOME}` com `<name_sync_with_filename>Y</name_sync_with_filename>` |
| **`HOP-H3`** | 🔴 Crítico | Hop de workflow com avaliação invertida (`evaluation=N`, `unconditional=N`) apontando para etapa produtiva (ex: `Delete file`) | Configurar `<evaluation>Y</evaluation>` para fluxo de sucesso e `<evaluation>N</evaluation>` apenas para tratamento de erro |
| **`HOP-H4`** | 🟠 Alto | Pipelines `.hpl` 100% duplicados na mesma esteira ou caminho de arquivo hardcoded ignorando `${ENV_NOM_ARQUIVO}` | Remover etapa redundante e usar `${ENV_DIR_TARGET}/${ENV_NOM_ARQUIVO}` |
| **`HOP-H5`** | 🟠 Alto | Concatenação de variáveis sem barra (`${ENV_DIR_TARGET}${ENV_NOM_ARQUIVO}`) ou referência `${PROJECT_HOME}/...` para arquivo inexistente | Padronizar sempre com barra explícita: `${ENV_DIR_TARGET}/${ENV_NOM_ARQUIVO}` |
| **`HOP-H6`** | 🟡 Médio | `PipelineExecutor` / `WorkflowExecutor` com `<inherit_all_vars>N</inherit_all_vars>` | Definir `<inherit_all_vars>Y</inherit_all_vars>` para propagar `${V_SEQ}` e variáveis de sessão |
| **`HOP-H7`** | 🟡 Médio | `TableOutput` sem `use_batch=Y` / `specify_fields=Y` ou `InsertUpdate` com identificadores entre aspas duplas (`"SCHEMA"."TABELA"`) | Habilitar `use_batch=Y`, `specify_fields=Y` e remover aspas duplas de schema/tabela |
| **`HOP-H8`** | 🟡 Médio | `metadata/schema-definition/*.json` com campos corrompidos (`decimalSymbol="binary-string"`) | Validar JSON e alinhar propriedades do Schema Definition |

---

## 📂 3. Destino Canônico de Saída e Templates

Quando acionada para geração, salve os artefatos em `saida/planejador_dw/06_pipelines_hop/` utilizando como base estrutural [template_pipeline.hpl](./templates/template_pipeline.hpl).
