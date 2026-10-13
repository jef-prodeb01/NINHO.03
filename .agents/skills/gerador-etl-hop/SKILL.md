---
name: gerador-etl-hop
description: >-
  Gera pipelines (.hpl) e workflows (.hwf) do Apache Hop para esteiras de carga de DW.
  Use APENAS quando a opção Apache Hop estiver explicitamente marcada no INTAKE_DW.md.
---

# Skill: Gerador de Pipelines Apache Hop

Esta skill orienta a geração estritamente condicional de artefatos do Apache Hop (`.hpl` - pipelines de transformação de dados e `.hwf` - workflows de orquestração).

> 🛑 **REGRA DE ATIVAÇÃO CONDICIONAL:**  
> Esta skill **NUNCA** deve gerar arquivos se o Engenheiro de Dados não tiver marcado `[x] Apache Hop` na Seção 1 do `INTAKE_DW.md`.  
> Se desmarcado, a pasta `saida/planejador_dw/06_pipelines_hop/` DEVE permanecer intacta contendo apenas seu `.gitkeep`.

---

## 1. Estrutura de Artefatos no Apache Hop

Ao ser acionada, os arquivos gerados devem ser salvos diretamente em:
`saida/planejador_dw/06_pipelines_hop/`

### 1.1 Pipelines Típicos a Gerar
1. **Pipeline de Ingestão de Arquivo / SFTP para Staging:**
   - Leitura de arquivo CSV/Excel (`CSV file input` / `Microsoft Excel input`).
   - Mapeamento e normalização de campos.
   - Carga na tabela de staging Oracle (`Table output` apontando para `STG_*`).
2. **Workflow de Execução (.hwf):**
   - Start -> Executa Pipeline de Ingestão -> Verifica Sucesso -> Grava Log / Atualiza `TB_CONTROLE_CARGA` -> Fim.

---

## 2. Padrões de Conexão e Nomenclatura no Apache Hop

- **Nome da Conexão:** Usar variável `${ORACLE_DW_CONN}` ou `${DB_DW}`.
- **Tipagem de Dados:**
  - Garantir conversão de strings vazias para `NULL`.
  - Tratamento de datas com máscara padrão `yyyy-MM-dd HH:mm:ss`.
- **Tratamento de Erros:**
  - Habilitar `error handling` nos steps de saída para direcionar linhas com falha para arquivo de descarte (`rejected_rows.csv`).

---

## 3. Template XML Base de Pipeline (.hpl)

Consulte o modelo estrutural XML em [template_pipeline.hpl](./templates/template_pipeline.hpl) para manter compatibilidade com as versões 2.x do Apache Hop.

