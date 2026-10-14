---
name: extrator-ftps-lote-hop
description: Gera esteiras de ingestão de arquivos recebidos em lote via FTPS/SFTP/FTP corporativo (Shell script com curl + metadados de lote + pipeline/workflow do Apache Hop 2.x). Use APENAS quando a opção Ingestão Arquivos em Lote (SFTP/FTPS) estiver marcada no INTAKE_DW.md ou houver arquivos em entrega/planejador_dw/arquivos_ftp/.
---

# Skill: Extrator em Lote via FTPS/SFTP e Apache Hop

Esta skill orienta o agente na geração de esteiras corporativas resilientes para descoberta, download, extração de metadados e ingestão de arquivos tabulares (`.xlsx`, `.csv`, `.txt`) disponibilizados por clientes via servidores **SFTP / FTPS / FTP**.

> 🛑 **REGRA CONDICIONAL:**  
> Esta skill **SÓ PODE SER ACIONADA** se a opção de ingestão por arquivos em lote for assinalada no INTAKE ou se arquivos de layout/FTP forem depositados em `entrega/planejador_dw/arquivos_ftp/`.

---

## 🎯 Arquitetura da Esteira em 3 Fases

1. **Fase 1 — Varredura e Extração de Metadados via Shell Script (`extrair_metadados_ftps.sh`):**
   - Utiliza `curl` seguro (`--ssl-reqd` para FTPS) com parâmetros de retry e timeout.
   - Lista o diretório remoto do FTP e extrai nome, data/hora da última modificação e tamanho dos arquivos.
   - Gera um arquivo CSV de manifesto do lote (`arquivos_ftps_<PROJETO>.csv`).
   - Grava logs de execução com `tee -a` em `${PROJECT_HOME}/logs/`.
2. **Fase 2 — Aterrissagem do Manifesto na Tabela Staging (`STG_CONTROLE_LOTE_FTP`):**
   - Criação da tabela DDL para auditar cada arquivo detectado no lote remoto (nome, tamanho, data de processamento, status).
3. **Fase 3 — Orquestração via Apache Hop 2.x:**
   - Pipeline `.hpl` para download dos arquivos novos (não processados) e carga nas tabelas Staging de negócio.
   - Workflow `.hwf` que encapsula o Shell Script e os pipelines em uma esteira agendável.

---

## 📂 Destino Canônico de Saída

Quando acionada, os artefatos devem ser salvos em:
- `saida/planejador_dw/06_pipelines_hop/scripts_ftp/extrair_metadados_ftps.sh`
- `saida/planejador_dw/06_pipelines_hop/pipeline_ingestao_ftps_<PROJETO>.hpl`
- `saida/planejador_dw/06_pipelines_hop/workflow_carga_ftps_<PROJETO>.hwf`
- `saida/planejador_dw/02_staging/02_stg_controle_lote_ftp.sql`

Consulte os modelos em [templates/extrair_metadados_ftps.sh](./templates/extrair_metadados_ftps.sh) e [templates/stg_meta.hpl](./templates/stg_meta.hpl).

