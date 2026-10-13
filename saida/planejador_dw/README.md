# Saídas do Planejador de DW

Esta pasta armazena os scripts SQL, procedimentos, pipelines, extratores e relatórios gerados pela IA durante o processo de planejamento e modelagem dimensional do DW.

---

## 📂 Estrutura de Pastas Canônica

> ⚠️ **REGRA MANDATÓRIA DE SAÍDA:**  
> Os artefatos do projeto ativo são gerados **DIRETAMENTE** nesta pasta e em suas 11 subpastas numeradas abaixo.  
> **NUNCA** crie subpastas com o nome do projeto (ex: `saida/planejador_dw/<NOME_PROJETO>/`). O template como um todo já representa a instância de trabalho do projeto.

| Subpasta | Conteúdo Gerado | Ferramenta / Condição |
| :--- | :--- | :--- |
| `01_controle_carga/` | `01_tb_controle_carga.sql` (auditoria e execução). | Gerado se `TB_CONTROLE_CARGA` não existir no schema. |
| `02_staging/` | `02_create_stg_tables.sql` (tabelas e views de staging). | Obrigatório para aterrissagem de dados brutos. |
| `03_dimensoes/` | `03_create_odi_dim_tables.sql`, `04_create_dim_tables.sql`, `06_init_default_records.sql`. | `03_create_odi_dim_tables.sql` apenas se ODI for selecionado. Dimensões e linha `-1` sempre. |
| `04_fatos/` | `05_create_fato_tables.sql` (fatos, particionamento e índices). | Bitmap para Estratégia A, B-Tree para Estratégia B. |
| `05_procedimentos_manutencao/` | `07_prc_pos_carga_fato.sql` (rebuild NOLOGGING e stats). | Gerado para a Estratégia A (Truncate & Load). |
| `06_pipelines_hop/` | Pipelines (`.hpl`) e workflows (`.hwf`) do Apache Hop. | **CONDICIONAL:** Apenas gerado se **Apache Hop** for assinalado no INTAKE. |
| `07_extratores_python/` | Extratores Python (`.py`) para APIs REST / OAuth2. | **CONDICIONAL:** Apenas gerado se **Extratores Python** for assinalado no INTAKE. |
| `08_datasets_bi/` | `superset_dataset_<fato>.yaml` e `GUIA_ANALISTA_BI_<PROJETO>.md`. | Handoff analítico para Power BI e Apache Superset. |
| `09_relatorio_estrategias/` | `RELATORIO_ESTRATEGIAS.md` (topologia, matriz De/Para, sizing). | Relatório técnico completo de arquitetura. |
| `10_testes_integridade/` | `13_testes_integridade.sql` (validação de FKs e integridade). | Suíte de validação e qualidade pós-carga. |
| `11_dicionario_dados/` | `dicionario_dados.html` (dicionário interativo de dados). | Documentação HTML navegável de tabelas e colunas. |

---

## 🔒 Regras Estritas de Geração
1. **Fidelidade Colunar Absoluta:** Todas as colunas de negócio devem corresponder 1:1 ao DDL e amostras da origem. É proibido inventar colunas.
2. **Geração Condicional:** Pipelines do Apache Hop (`06_`) e Extratores Python (`07_`) **NUNCA** devem ser gerados se as tecnologias correspondentes não estiverem marcadas com `[x]` no [`INTAKE_DW.md`](../../modulos/planejador_dw/INTAKE_DW.md).
