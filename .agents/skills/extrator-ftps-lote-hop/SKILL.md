---
name: extrator-ftps-lote-hop
description: >-
  Gera esteiras corporativas de ingestão de arquivos recebidos em lote via FTPS/SFTP/FTP (Shell script com
  curl seguro, controle de modificação em CONTROLE_MODIFICACAO_ARQUIVOS via stg_meta.hpl, descompactação
  UNZIP/DELETE_FILES, captura de log WorkflowLogging e notificação HTML de ausência de arquivo). Use quando
  Ingestão Arquivos em Lote (SFTP/FTPS) estiver marcada no INTAKE_DW.md ou houver arquivos em
  entrega/planejador_dw/arquivos_ftp/.
---

# Skill: Extrator em Lote via FTPS/SFTP e Apache Hop 2.x

Esta skill orienta o agente na geração e auditoria de esteiras corporativas resilientes para descoberta, verificação de modificação, download seguro, descompactação e ingestão de arquivos tabulares (`.xlsx`, `.csv`, `.txt`, `.zip`) e binários (`.png`, `.jpg`) via servidores **FTPS / SFTP / FTP**.

> 🛑 **REGRA CONDICIONAL:**  
> Esta skill **SÓ PODE SER ACIONADA** se a opção de ingestão por arquivos em lote for assinalada no INTAKE ou se arquivos de layout/FTP forem depositados em `entrega/planejador_dw/arquivos_ftp/`.

---

## 🎯 Arquitetura da Esteira FTPS Corporativa em 4 Fases (Padrão PRODEB)

1. **Fase 1 — Descoberta Remota e Download Condicional via Shell + `curl` (`ftps_script.hwf` / `extrair_metadados_ftps.sh`):**
   - Resolve a senha de forma segura via Variable Resolver (`#{hop-pwd:ENV_FTP_PASS}`) ou pipeline `decrypt_pass.hpl` (`Encr.decryptPasswordOptionallyEncrypted`).
   - Utiliza `curl --ftp-ssl -k -s` com tratamento de URL-encode para nomes de arquivos com espaços/acentos.
   - Consulta `MDTM` (data de modificação remota) e `SIZE`, gravando o manifesto `arquivos_ftps_<PROJETO>.csv` ordenado pela data de modificação mais recente.
   - Caso se trate de lote compactado (ex: base CNPJ ou lote multiparte), executa a action `UNZIP` (`wildcardSource = .*\.zip`) seguida de `DELETE_FILES` para limpar os `.zip` após extração.

2. **Fase 2 — Controle de Versão de Arquivo no Banco (`stg_meta.hpl` $\rightarrow$ `CONTROLE_MODIFICACAO_ARQUIVOS`):**
   - Lê `arquivos_ftps_<PROJETO>.csv` (`CSVInput`), filtra a linha mais recente com `SampleRows` (`linesrange = 1`), converte `DATA_MODIFICACAO` (`yyyy-MM-dd HH:mm:ss`) e executa `InsertUpdate` na tabela `CONTROLE_MODIFICACAO_ARQUIVOS` (chave `NOME_PROJETO`).

3. **Fase 3 — Gate de Existência de Arquivo (`FILE_EXISTS`) e Alerta de Ausência (`montar_html_email_sem_arquivo.hpl`):**
   - Antes de iniciar as cargas Staging, a action `FILE_EXISTS` verifica `${ENV_DIR_TARGET}/${ENV_NOM_ARQUIVO}` (**Atenção à regra `HOP-H5`:** sempre incluir `/` entre `${ENV_DIR_TARGET}` e `${ENV_NOM_ARQUIVO}`!).
   - **Se o arquivo existir (`evaluation = Y`):** segue para a validação/carga das Stagings e, ao final com sucesso (`evaluation = Y`), limpa o arquivo temporário (`DELETE_FILE`) ou move para `Processados/` (`MOVE_FILES`). **Nunca** ligar o `DELETE_FILE` no caminho de falha (`evaluation = N` — anti-padrão `HOP-H3`).
   - **Se o arquivo NÃO existir (`evaluation = N`):** atualiza `ETA_ETAPAS_CARGA` com `DES_STATUS = 'ERRO'` e `DES_ERRO = 'Nenhum arquivo foi modificado na origem'`, monta o e-mail HTML de alerta (`montar_html_email_sem_arquivo.hpl`) usando `${ENV_NOM_ARQUIVO}` parametrizado (evitando hardcode de outro projeto — `HOP-H2`) e envia via `enviar_email.hwf`.

4. **Fase 4 — Captura Automática de Falhas de Rede/FTPS (`capturar_log_ftps.hpl`):**
   - Vinculado via `metadata/workflow-log/workflow_log_ftps.json`, intercepta qualquer falha de conexão/autenticação FTPS via `WorkflowLogging` e grava o erro detalhado em `ETA_ETAPAS_CARGA.DES_ERRO`.

---

## 📂 Destino Canônico de Saída

Quando acionada, os artefatos devem ser salvos em:
- `saida/planejador_dw/06_pipelines_hop/scripts_ftp/extrair_metadados_ftps.sh`
- `saida/planejador_dw/06_pipelines_hop/stg_meta.hpl`
- `saida/planejador_dw/06_pipelines_hop/pipeline_ingestao_ftps_<PROJETO>.hpl`
- `saida/planejador_dw/06_pipelines_hop/workflow_carga_ftps_<PROJETO>.hwf`
- `saida/planejador_dw/02_staging/02_stg_controle_lote_ftp.sql`

Consulte os modelos em [templates/extrair_metadados_ftps.sh](./templates/extrair_metadados_ftps.sh) e [templates/stg_meta.hpl](./templates/stg_meta.hpl).
