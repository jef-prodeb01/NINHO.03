# 🔬 Revisão Técnica Completa do NINHO — Auditoria nas 4 Frentes & Checklist de Projeto 100% Completo

> **Data da atualização:** 21/10/2026 · **Escopo:** releitura integral dos 16 scripts Python (~13.200 linhas), 30+ templates SQL/Hop/Python/HTML, 49 skills (`.agents/skills/`) e toda a documentação Markdown (~10.000 linhas).
> **Método:** análise estática via AST, comparação SHA-256/diff entre templates, varredura de links e comandos, execução da suíte oficial ([`testar_ninho.py`](file:///c:/Users/jeferson.ressurreica/Downloads/Projetos/NINHO/core/scripts_comuns/testar_ninho.py) — **`11/11 PASS`**) e verificação empírica de casos de borda.

---

## 1. Diagnóstico Geral (Nota Atual por Dimensão)

| Dimensão Avaliada | Antes (v03 original) | Pós 1ª Rodada (`E1`–`E4`) | **Agora (`E1`–`E12` + `T11`)** | Resumo do Estado Atual |
| :--- | :---: | :---: | :---: | :--- |
| **1. Domínio DW / Kimball / ODI / Hop** | 8,0 / 10 | 8,5 / 10 | **9,5 / 10** | Base conceitual completa (linha `-1`, SCD2 B-Tree, `RELY DISABLE NOVALIDATE`, `TRUNC` em datas, `DIM_TEMPO` de 24 colunas e `TB_CONTROLE_CARGA`). |
| **2. Motores Core Python (DDL, Simulador, Semântica)** | 5,0 / 10 | 6,5 / 10 | **9,5 / 10** | Parser DDL resiliente (`E3`), classificador explicável (`E4`), catálogo `META_*` 100% alinhado ao DDL `01_create_meta_tables.sql` (`E5`), scripts ODI com `DTC_EFETIVACAO` e FKs OLTP resolvidas (`E6`) e escape HTML/SQL (`E9`). |
| **3. Auditores Especializados (ODI, Hop, PBIX, Gov)** | 4,5 / 10 | 7,0 / 10 | **9,2 / 10** | Auditores ODI (`E1`/`E2`) e Power BI (`E8`) 100% dinâmicos e livres de hardcodes de clientes (`SEI`/`SAEB`/`PRODEB`/`URBIS`). |
| **4. Templates SQL / ETL & Validador (`validar_entrega.py`)** | 5,5 / 10 | 6,0 / 10 | **9,5 / 10** | `01_create_meta_tables.sql` unificado com constraints `CHECK`/`UNIQUE` (`E10`), validação cruzada de colunas `MERGE INTO` contra `CREATE TABLE` (`esquema_meta_ddl`) e templates FTPS/ODI parametrizados (`E12`). |
| **5. Testes, CI/CD & Empacotamento** | 5,0 / 10 | 6,5 / 10 | **9,5 / 10** | Suíte E2E expandida para **`11/11 PASS`** (`T01` a `T11`) sem mutar timestamps de arquivos versionados inalterados (`E12`). |
| **6. Documentação, UX & Configuração de Agentes** | 6,0 / 10 | 7,5 / 10 | **9,5 / 10** | [`AGENTS.md`](file:///c:/Users/jeferson.ressurreica/Downloads/Projetos/NINHO/AGENTS.md) enxuto, dispatcher CLI [`ninho.py`](file:///c:/Users/jeferson.ressurreica/Downloads/Projetos/NINHO/ninho.py) (`ninho.bat`) com todas as rotas do `README.md`, 20 skills de comandos e 0 links quebrados (`E11`). |

---

## 2. Correções Implementadas (`E1` a `E12` + `T10` + `T11`)

| ID | Correção Implementada | Arquivos Auditados | Status |
| :--- | :--- | :--- | :---: |
| **E1** | Remoção dos textos fixos do projeto SEI Municipal (`BD_SEIMUN`, `MERGE_ODI_CTRL`, `MAP_CARGA_FATO_TRAMITACAO`) e condicionalização real das heurísticas `H2`, `H3` e `H9` no auditor ODI. | [`auditar_mapa_odi.py`](file:///c:/Users/jeferson.ressurreica/Downloads/Projetos/NINHO/core/scripts_comuns/auditar_mapa_odi.py) | ✅ |
| **E2** | Alinhamento da prescrição `H7` (`DES_ATUALIZAR`) ao tipo `CHAR(1 CHAR)` por comparação de hash (`CASE WHEN <hash_stg> <> <hash_dim> THEN 'S' ELSE 'N' END`) ou coluna dedicada `HSH_SCD2`. | [`auditar_mapa_odi.py`](file:///c:/Users/jeferson.ressurreica/Downloads/Projetos/NINHO/core/scripts_comuns/auditar_mapa_odi.py) | ✅ |
| **E3** | Parser de DDL corrigido para: (a) não descartar colunas iniciadas por `KEY_`/`CHECK_`/`INDEX_`; (b) remover comentários `--` e `/* */` respeitando aspas; (c) suportar identificadores com espaço entre `"..."` ou `[...]`; (d) expandir FKs compostas e FKs inline (`REFERENCES`). | [`inspecionar_ddl_origem.py`](file:///c:/Users/jeferson.ressurreica/Downloads/Projetos/NINHO/core/scripts_comuns/inspecionar_ddl_origem.py) | ✅ |
| **E4** | Classificação Fato vs. Dimensão reescrita por pontuação explicável (FKs declaradas/implícitas, grau de entrada/saída, métricas por prefixo e vocabulário), preservando tabelas `DIM_*`/`FATO_*` já existentes quando misturadas a tabelas OLTP. | [`simular_projeto.py`](file:///c:/Users/jeferson.ressurreica/Downloads/Projetos/NINHO/core/scripts_comuns/simular_projeto.py) | ✅ |
| **E5** | Alinhamento integral entre `01_create_meta_tables.sql` e os scripts `MERGE INTO` gerados por `modular_semantica.py` (`01_meta_glossario.sql`, `02_meta_metrica.sql`, `03_meta_objeto.sql`, `04_meta_relacionamento.sql`, `05_meta_regra_negocio.sql`, `06_meta_consulta_negocio.sql`, `07_meta_orientacao_ia.sql`, `08_meta_valor_dominio.sql` e `09_validacoes.sql`), além de validação cruzada `esquema_meta_ddl` em `validar_entrega.py`. | [`modular_semantica.py`](file:///c:/Users/jeferson.ressurreica/Downloads/Projetos/NINHO/core/scripts_comuns/modular_semantica.py), [`simular_projeto.py`](file:///c:/Users/jeferson.ressurreica/Downloads/Projetos/NINHO/core/scripts_comuns/simular_projeto.py), [`validar_entrega.py`](file:///c:/Users/jeferson.ressurreica/Downloads/Projetos/NINHO/core/scripts_comuns/validar_entrega.py) | ✅ |
| **E6** | Correção dos 3 bugs de geração SQL nas consultas do ODI (`construir_scripts_odi`): (1) detecção dinâmica de `DTC_EFETIVACAO`/`DTC_INICIO` no índice de `ODI_DIM_*`; (2) exclusão de colunas de controle SCD2 (`DTC_EFETIVACAO`, `DTC_EXPIRACAO`, `SIN_ATIVO`, `DES_ATUALIZAR`) na leitura da `STG_*` e projeção correta no `SELECT` externo; (3) resolução de FKs de Fato via `identificar_fks_fato()` (incluindo colunas `ID_*` vindas de OLTP) e suporte a `schema_stg`. | [`melhorar_dw_existente.py`](file:///c:/Users/jeferson.ressurreica/Downloads/Projetos/NINHO/core/scripts_comuns/melhorar_dw_existente.py) | ✅ |
| **E7** | Geração automática das 4 colunas corporativas SCD2 (`SIN_ATIVO`, `DTC_EFETIVACAO`, `DTC_EXPIRACAO`, `DES_ATUALIZAR`), do script `01_controle_carga/01_tb_controle_carga.sql` e da dimensão `DIM_TEMPO` corporativa de 24 colunas no simulador DW. | [`simular_projeto.py`](file:///c:/Users/jeferson.ressurreica/Downloads/Projetos/NINHO/core/scripts_comuns/simular_projeto.py) | ✅ |
| **E8** | Generalização de `inspecionar_pbix.py` (`PBIX-H1` a `PBIX-H5` e tabela de catálogo da Seção 2), substituindo referências fixas a `SEI`/`SAEB`/`PRODEB`/`URBIS`/`dadosConsolidados` por detecção estrutural dinâmica. | [`inspecionar_pbix.py`](file:///c:/Users/jeferson.ressurreica/Downloads/Projetos/NINHO/core/scripts_comuns/inspecionar_pbix.py) | ✅ |
| **E9** | Escape de aspas simples em `COMMENT ON` e `html.escape(..., quote=True)` em todos os campos interpolados do `dicionario_dados.html`. | [`melhorar_dw_existente.py`](file:///c:/Users/jeferson.ressurreica/Downloads/Projetos/NINHO/core/scripts_comuns/melhorar_dw_existente.py) | ✅ |
| **E10** | Unificação de `modulos/camada_semantica/templates/01_create_meta_tables.sql` com a versão completa de 374 linhas (contendo todas as constraints `CHECK` e `UNIQUE` e `ID_CONSULTA VARCHAR2(50)`). | [`01_create_meta_tables.sql`](file:///c:/Users/jeferson.ressurreica/Downloads/Projetos/NINHO/modulos/camada_semantica/templates/01_create_meta_tables.sql) | ✅ |
| **E11** | Correção dos 4 links Markdown para `SIMULACAO_BLUEPRINT_*.md`, adição dos 5 comandos faltantes (`desafiar-grao`, `classificar-scd`, `definir-estrategia-carga`, `gerar-governanca`, `diagnosticar-erro-carga`) em `ninho.py` e atualização da contagem para 11 baterias E2E no `README.md`. | [`ninho.py`](file:///c:/Users/jeferson.ressurreica/Downloads/Projetos/NINHO/ninho.py), [`README.md`](file:///c:/Users/jeferson.ressurreica/Downloads/Projetos/NINHO/README.md) | ✅ |
| **E12** | Preservação do `mtime` de arquivos versionados inalterados durante o snapshot de `testar_ninho.py`, parametrização de `CURL_TLS_OPTS` em `extrair_metadados_ftps.sh` e cálculo de `DES_ATUALIZAR` via `STANDARD_HASH` em `template_selects_odi.sql`. | [`testar_ninho.py`](file:///c:/Users/jeferson.ressurreica/Downloads/Projetos/NINHO/core/scripts_comuns/testar_ninho.py), [`extrair_metadados_ftps.sh`](file:///c:/Users/jeferson.ressurreica/Downloads/Projetos/NINHO/.agents/skills/extrator-ftps-lote-hop/templates/extrair_metadados_ftps.sh), [`template_selects_odi.sql`](file:///c:/Users/jeferson.ressurreica/Downloads/Projetos/NINHO/.agents/skills/gerador-consultas-odi/templates/template_selects_odi.sql) | ✅ |
| **T10 / T11** | Adição das baterias de regressão `T10` (`E1`–`E4` + parser DDL + ODI condicional + classificador OLTP) e `T11` (`E5`–`E12` + compatibilidade DDL `META_*` + `04_select_odi_fato.sql` OLTP + `html.escape` + PBIX agnóstico) na suíte oficial (`11/11 PASS`). | [`testar_ninho.py`](file:///c:/Users/jeferson.ressurreica/Downloads/Projetos/NINHO/core/scripts_comuns/testar_ninho.py) | ✅ |

---

## 3. Checklist de Critérios de Aceite (Blocos A e B Concluídos)

### Bloco A — Fidelidade de Execução SQL & Motores
- [x] **A1 (`E5`).** Alinhar 100% dos nomes de tabelas e colunas em `modular_semantica.py` (`construir_catalogo_meta` e `09_validacoes.sql`) ao DDL `01_create_meta_tables.sql` (`META_OBJETO`, `META_CONSULTA_NEGOCIO`, coluna `PROJETO` etc.) e adicionar teste em `validar_entrega.py` + `testar_ninho.py` que verifica se toda tabela/coluna alvo de `MERGE INTO`/`INSERT INTO` em `01..08` existe no `01_create_meta_tables.sql`.
- [x] **A2 (`E6`).** Corrigir `construir_scripts_odi()` em `melhorar_dw_existente.py` para: (1) usar `DTC_EFETIVACAO` (ou a coluna SCD2 real da dimensão) no índice de `ODI_DIM_*`; (2) não selecionar colunas exclusivas do DW (`DTC_EFETIVACAO`, `DTC_EXPIRACAO`, `SIN_ATIVO`, `DES_ATUALIZAR`) a partir da `STG_*`; (3) gerar os `LEFT JOIN` nas dimensões em `04_select_odi_fato.sql` usando `identificar_fks_fato()` (funcionando tanto para `SK_*`/`DIM_*` quanto para `ID_*` vindo de OLTP) e qualificar a Stage com `schema_stg`.
- [x] **A3 (`E7`).** Fazer `_converter_oltp_para_dw_se_necessario` e `_gerar_scripts_ddl_completos_dw` em `simular_projeto.py` gerarem as colunas corporativas completas (`SIN_ATIVO`, `DES_ATUALIZAR`), o script `01_tb_controle_carga.sql` e a `DIM_TEMPO` (quando aplicável).
- [x] **A4 (`E8`).** Generalizar `inspecionar_pbix.py` (`PBIX-H1` a `PBIX-H5`), removendo os nomes fixos `'PRODEB'`, `'URBIS'`, `'SAEB'`, `'SESAB'`, `'SEFAZ'`, `dadosConsolidados`, `id_tarefa IN (2, 13)` e `FATO_TRAMITACAO`, e substituindo por detecção estrutural dinâmica.
- [x] **A5 (`E9`).** Adicionar escape de aspas simples (`.replace("'", "''")`) em `construir_script_comentarios()` e `html.escape()` em `construir_dicionario_html()` em `melhorar_dw_existente.py`.

### Bloco B — Higiene de Repositório, CLI & Documentação
- [x] **B1 (`E10`).** Unificar `modulos/camada_semantica/templates/01_create_meta_tables.sql` com a versão de 374 linhas (com constraints `CHECK`/`UNIQUE`).
- [x] **B2 (`E11`).** Corrigir os 4 links Markdown quebrados para `SIMULACAO_BLUEPRINT_*.md`, mapear os 5 comandos faltantes (`/desafiar-grao`, `/classificar-scd`, `/definir-estrategia-carga`, `/gerar-governanca`, `/diagnosticar-erro-carga`) em `ninho.py` e atualizar a contagem para `11` baterias de testes no `README.md`.
- [x] **B3 (`E12`).** Evitar que `testar_ninho.py` altere o `mtime` de arquivos inalterados ao restaurar o snapshot (só regravar se `arq.read_bytes() != conteudo_orig`), parametrizar o TLS no `extrair_metadados_ftps.sh` e substituir `'S' AS DES_ATUALIZAR` por expressão dinâmica de comparação de hash em `template_selects_odi.sql`.

### Bloco C — Evoluções Futuras Opcionais (Roadmap de Engenharia)
- [ ] **C1.** Extrair utilitário compartilhado `core/scripts_comuns/_comum.py` + `pyproject.toml` (`ruff`).
- [ ] **C2.** Pipeline de CI (`.github/workflows/ci.yml`) executando `testar_ninho.py` a cada push/PR.
- [ ] **C3.** Flag `--json` nos inspetores e auditores para consumo estruturado em pipelines externos.

