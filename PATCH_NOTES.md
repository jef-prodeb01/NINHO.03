# 📰 Histórico de Versões e Novidades (Patch Notes) — Plataforma NINHO

> **Versão Atual:** `v0.13.1` *(Pré-Lançamento / Release Candidate)* | **Última Atualização:** `28/10/2026` | **Status da Suíte de Testes:** `✅ E2E (18/18 em sandbox) + pytest (14/14) + ruff no CI`

Bem-vindo à página oficial de **Patch Notes** do **NINHO**!
Esta página foi escrita para ser **simples, direta e amigável para pessoas lerem** — seja você Engenheiro de Dados, DBA, Analista de BI ou Gestor. Aqui você acompanha tudo o que evoluiu na plataforma desde os primeiros testes (`v0.1.0`) até o estágio atual (`v0.13.1`), quais ferramentas novas entraram e quais dores de cabeça do dia a dia (erros de banco, travamentos no ODI/Hop ou retrabalho no Power BI) já foram resolvidas.

---

## 🗺️ Resumo Rápido das Versões (`v0.1.0` → `v0.13.1`)

> 🎯 **Quando chegaremos na Versão `1.0.0`?**
> Os módulos de **Planejamento de Data Warehouse (Oracle + ODI 12c + Hop + BI)** e **Camada Semântica (`VW_*` + `META_*`)** já foram colocados à prova e aprimorados com projetos reais de ponta a ponta. A versão **`v1.0.0`** será oficializada quando o **Módulo de Governança de Dados (MongoDB PRODEB + AWS SageMaker Catalog)** passar pelo teste prático completo e for formalmente aprovado.

| Versão | Data | Destaque Principal (Em uma frase) |
| :---: | :---: | :--- |
| 🎯 **`v1.0.0`** *(Planejada)* | *Em breve* | **Marco Oficial 1.0:** Homologação prática e aprovação final do Módulo de Governança de Dados (MongoDB + AWS SageMaker Catalog) em projeto real. |
| **[`v0.13.1`](#-versão-0131--28102026-versão-atual)** | `28/10/2026` | **Pureza Estrita das Tabelas Fato (`FATO_*`):** Adequação das tabelas Fato para conterem estritamente chaves de dimensão (`DIM_*`, `SK_*`, `DIMENSION_KEY`) e métricas numéricas (`VAL_*`, `QTD_*` etc.), proibindo colunas de texto (`VARCHAR2`) ou datas brutas (`DATE`) nas Fatos na Demonstração (`/demo`), no Simulador (`/simular-dw`) e na Execução Direta (`/executar-dw`). |
| **[`v0.13.0`](#-versão-0130--27102026)** | `27/10/2026` | **Fase 3 — Perguntas de Negócio, MCP e Ferramentas DBA:** catálogo com no mínimo 30 perguntas da IA (com SQL) + perguntas do cliente, servidor MCP, `/comparar-modelo`, `/estimar-volumetria`, `/inspecionar-banco` e `/simular-governanca`. |
| **[`v0.12.0`](#-versão-0120--27102026)** | `27/10/2026` | **Esteira de Governança Real, Testes Seguros & Fundação de Engenharia:** `/executar-governanca` passa a gerar de fato a matriz LGPD (4 níveis), os scripts MongoDB PRODEB (01 a 08) e o catálogo AWS Glue/SageMaker; `/testar-ninho` roda em sandbox sem apagar seus arquivos; `pytest`, `ruff` e CI. |
| **[`v0.11.1`](#-versão-0111--27102026)** | `27/10/2026` | **Correção de Convenções no Simulador e Validador:** Adequação 100% do modo Simulador às convenções `CONVENCOES_DW.md` (`DIMENSION_KEY`, `SIN_ATIVO`, `DIM_TEMPO` 24 colunas, FKs `DIM_<ENTIDADE>`, `<PROJETO>_DATA`, `DES_STATUS_REGISTRO` em `ODI_DIM_*`) e remoção do bypass em `validar_entrega.py`. |
| **[`v0.11.0`](#-versão-0110--27102026)** | `27/10/2026` | **Comandos de Execução Direta & Governança Modular:** Inclusão dos comandos `/executar-dw`, `/executar-semantica`, `/executar-projeto` e `/executar-governanca` (geração direta sem exigir simulação) e protótipo de Governança em 5 etapas validado fora do repositório (incorporado à plataforma na `v0.12.0`). |
| **[`v0.10.0`](#-versão-0100--26102026)** | `26/10/2026` | **Suíte Visual, Documentos Office/PDF Nativos, Scanner PII (`*Craft`), 5 Motores Apache Hop & Prova Real Pós-Carga:** Mockup BI (`SVG` + *Dev Mode Redlines* + `PNG 2x`), diagramas Star Schema/ODI/Hop Canvas, gerador `.xlsx`/`.pptx`/`.docx`/`.pdf`, leitura `.ods`/`.pdf`/`.docx`/`.odt`, scanner LGPD em linhas, `hop-lint`, migrador Kettle, `THREAT_MODEL.md`, `OraBulkLoader` e `/validar-medidas-bi`. |
| **[`v0.9.0`](#-versão-090--23102026)** | `23/10/2026` | **Padrão Ouro de Produção (ODI 12c, DBA Oracle & BI):** Guias do ODI no padrão *Dimension Pattern* passo a passo, Guia do Analista de BI completo (com medidas SCD2 e wireframe de 4 páginas), controle `ETA_ETAPAS_CARGA` e trava contra erros de nomes longos e índices no Oracle. |
| **[`v0.8.0`](#-versão-080--22102026)** | `22/10/2026` | **Integrações Reais de Campo:** Leitura de DDLs exportados em `.csv` (DBeaver/SQL Developer), suporte a Materialized Views (`MVW_*`), múltiplas datas na mesma Fato (*Role-Playing*) e leitura de planilhas `.xlsx` de indicadores para o Power BI. |
| **[`v0.7.0`](#-versão-070--21102026)** | `21/10/2026` | **Atalhos de Chat (`/comando`) e Blindagem Geral:** Criado o executável único `ninho.py` (`.\ninho`), instalador de comandos `/instalar-comandos` na IDE e correção de 12 bugs silenciosos de parser SQL e HTML. |
| **[`v0.6.0`](#-versão-060--19102026)** | `19/10/2026` | **Experiência Guiada e Playground (`/demo`):** Assistente de boas-vindas (`/comecar`), bússola de progresso (`/onde-estou`), auto-organizador de pastas (`/doctor`) e suíte automatizada de testes (`/testar-ninho`). |
| **[`v0.5.0`](#-versão-050--16102026)** | `16/10/2026` | **Simulador Editável & Modo Fast-Track:** Possibilidade de simular e editar todo o projeto em uma tabela antes de gerar os scripts reais, além de gerar recortes isolados (só comentários, só índices, só dicionário) sem precisar preencher formulários longos. |
| **[`v0.3.0`](#-versão-030--15102026)** | `15/10/2026` | **Estrutura de Governança (MongoDB + AWS) e Auditores Inteligentes:** Auditoria automática de arquivos do cliente (Gate 0.5), engenharia reversa de `.pbix` e auditores preditivos para ODI 12c e Apache Hop. |
| **[`v0.2.0`](#-versão-020--13102026)** | `13/10/2026` | **Arquitetura em Skills Modulares e Esteira Completa ETL:** Divisão da inteligência em 10 especialistas (`.agents/skills/`), suporte a FTPS em lote, extratores Python e segurança RLS/VPD no Oracle. |
| **[`v0.1.0`](#-versão-010--21092026-a-08102026)** | `08/10/2026` | **Versão Inicial de Testes e Protótipo do NINHO:** Primeiros testes do Planejador de DW, da Camada Semântica em 3 níveis com 8 tabelas `META_*`, 36 orientações de IA e organização nas 3 pastas (`entrega/`, `modulos/`, `saida/`). |

---

## 🔧 Versão `0.13.1` — `28/10/2026` *(Versão Atual)*

### 🎯 Em poucas palavras
As tabelas Fato (`FATO_*`) passam a obedecer à **Regra de Pureza Estrita**: toda `FATO_*` contém **exclusivamente** as chaves das dimensões (`DIM_<ENTIDADE>`, `DIM_TEMPO`, `SK_*`, `DIMENSION_KEY`) e as **métricas numéricas** (`VAL_*`, `QTD_*` etc.), sem colunas de texto (`VARCHAR2`/`CHAR`) nem datas brutas (`DATE`) na Fato.

### 🐛 Correções e Ajustes de Processo
* **Pureza Estrita das Tabelas Fato (`FATO_*`):**
  * **Motor de Conversão OLTP $\rightarrow$ Star Schema (`simular_projeto.py`):** Colunas textuais (`VARCHAR2`, `CHAR`, `CLOB`), datas brutas (`DATE`) e códigos não-métricos deixam de entrar na `FATO_*` (permanecendo apenas na `STG_*` para join de carga e nas respectivas `DIM_*`).
  * **Staging (`02_create_stg_tables.sql`) & Carga ODI (`04_select_odi_fato.sql`):** A `STG_*` preserva a coluna de data da origem (ex: `DTC_ASSINATURA DATE`) para resolver `TRUNC(S.DTC_ASSINATURA) = D3.DTC_COMPLETA` e gravar apenas `DIM_TEMPO NUMBER(38,0) NOT NULL` na Fato.
  * **Particionamento e Eixo Temporal Semântico (`DIM_TEMPO`):** O recomendador de particionamento (`PARTITION BY RANGE (DIM_TEMPO) INTERVAL (100)`) e o gerador de perguntas de negócio da IA (`META_CONSULTA_NEGOCIO`) operam nativamente sobre a chave `DIM_TEMPO` (`YYYYMMDD`).
  * **Validador de Qualidade (`validar_entrega.py`):** Bloqueia qualquer `CREATE TABLE FATO_*` que contenha colunas `VARCHAR2`, `CHAR` ou `CLOB`.

---

## 🚀 Versão `0.13.0` — `27/10/2026`

### 🎯 Em poucas palavras
A Camada Semântica passa a entregar um catálogo de perguntas de negócio de verdade (mínimo de 30 propostas pela IA, todas com SQL, mais as perguntas do cliente), a Governança ganha simulação e teste ponta a ponta, e chegam as primeiras funcionalidades da Fase 3: servidor MCP e ferramentas de DBA.

### ✨ Novidades
* **Catálogo de perguntas de negócio (`META_CONSULTA_NEGOCIO`):**
  * No mínimo **30 perguntas propostas pela IA** (não solicitadas pelo cliente), geradas do modelo real: Fatos, dimensões, métricas, data de negócio, situação e chave degenerada.
  * 3 horizontes: **Executiva** (volume, tendência, MoM, YoY, totais, YTD, top 10, curva ABC), **Tática** (médias por dimensão, cruzamentos, cobertura sem eventos, sazonalidade, dia da semana, outliers, média móvel) e **Auditoria** (chave `-1`, métricas inválidas, data futura, frescor, duplicidade, conciliação KPI x Evento).
  * Todo SQL usa só as views semânticas (`VW_EVENTO`, `VW_KPI`, `VW_DIM`), sem `SELECT *`.
  * **Perguntas do cliente** da Seção 5.1 do `INTAKE_SEMANTICA.md` (e de `entrega/camada_semantica/perguntas_cliente.md`) entram sempre, com a pergunta da IA mais parecida indicada como ponto de partida do SQL.
  * A Blueprint Semântica (Seção 6.2) lista o catálogo completo para o engenheiro desmarcar ou ajustar; a Seção 6.3 mostra as perguntas do cliente.
* **`/simular-governanca`:** prévia do Gate 0.5 e da classificação LGPD sem gravar scripts MongoDB/AWS.
* **Servidor MCP (`ninho_mcp_server.py` + `.mcp.json`):** todos os comandos do NINHO como ferramentas para Claude Code, Cursor, Antigravity e agentes internos.
* **`/comparar-modelo`:** DW em produção x modelo novo, com ALTERs incrementais seguros (alargamentos ativos; estreitamentos, remoções e `NOT NULL` com backfill comentados).
* **`/estimar-volumetria`:** tamanho de tabelas e índices, crescimento em 5 anos, recomendação de particionamento e script de tablespaces.
* **`/inspecionar-banco`:** extrai o DDL real de um schema Oracle via `DBMS_METADATA` (com `oracledb`) ou gera o script de extração para o DBA.
* **Suíte E2E T18:** esteira de Governança de ponta a ponta (simulação, MongoDB 01..08, AWS, pendências e devolução ao cliente).

---

## 🚀 Versão `0.12.0` — `27/10/2026`

### 🎯 Em poucas palavras
O módulo de Governança deixou de ser só auditoria: `/executar-governanca` agora entrega os artefatos que a documentação prometia. Ao mesmo tempo, a plataforma ganhou uma base de engenharia para crescer sem quebrar: testes que não apagam seus arquivos, testes unitários, lint e CI.

### ✨ Novidades
* **Esteira determinística de Governança (`gerar_artefatos_governanca.py`):**
  * Reprovado no Gate 0.5 → grava `relatorio_devolucao_cliente_<ORGAO>.md` e para.
  * Aprovado → `matriz_de_para_lgpd_<DATASET>.csv`, `relatorio_governanca_<DATASET>.md` e, conforme o Intake, `schemas_mongo/01..08` (coleções centrais extraídas das referências oficiais, documento do `tb_dataset`, coleção `trusted_*` com `$jsonSchema` estrito, barreira de quarentena e evento de auditoria) e `aws_sagemaker_catalog/` (Metadata Form, payload do ativo, tabela Glue e publicação `boto3` em dry-run).
  * Nada é inventado: o que falta sai como `<INFORMAR: ...>`, aparece no relatório e é reprovado por `/validar-entrega saida`.
* **Classificação LGPD em 4 níveis** (`PUBLICO`, `INTERNO`, `CONFIDENCIAL`, `RESTRITO`) com base legal e técnica de anonimização; o cliente nunca rebaixa um campo pessoal detectado.
* **Cruzamento Dicionário x Amostras no Gate 0.5:** coluna não catalogada e PII encontrada em coluna declarada não sensível passam a bloquear e voltar ao cliente.
* **`--json`** no `/inspecionar-governanca` e no `/executar-governanca`, para agentes e pipelines.
* **`ninho_core`**: utilitários compartilhados (`console`, `paths`, `xml_seguro`).
* **`/doctor`** checa Python, pacotes opcionais, skills instaladas e a proteção LGPD do `.gitignore`.
* **Comando digitado errado** agora recebe sugestão (`Você quis dizer: /simular-dw?`).
* **Testes unitários (`pytest`)**, **lint (`ruff`)**, `pyproject.toml`, `requirements*.txt`, `CONTRIBUTING.md` e CI para GitHub Actions e GitLab.

### 🐛 Erros e Problemas Resolvidos
* **`/testar-ninho` apagava os arquivos reais de `entrega/` e `saida/`.** Agora roda numa cópia temporária do projeto (`--sem-sandbox` mantém o modo antigo).
* **Sem `openpyxl`, a planilha do cliente era reprovada** como se fosse culpa do órgão. Agora há leitor `.xlsx` nativo.
* **Nomenclatura MongoDB fora da norma PRODEB:** documentos (CPF, CNPJ, matrícula, telefone…) saem com `num_` (antes `cod_`), identificadores com `ide_`, inteiros de 10+ dígitos como `long` e prefixos legados por extenso (`data_`, `valor_`…) não se repetem (`dtc_nascimento`, não `dtc_data_nascimento`).
* **Dados de cliente podiam ir para o Git:** `entrega/` e `saida/` agora estão no `.gitignore`.
* **Credenciais:** template do extrator API sem senha padrão; script FTPS usa `--netrc-file` em vez de senha na linha de comando.
* **XML de terceiros** (ODI, Hop, PBIX, Office) lido com proteção contra expansão de entidades.
* **Cores ANSI** (`[93m`) não poluem mais a saída no chat da IDE.
* **Skills de comando** com instrução neutra de IDE (antes presas ao `run_command`).
* **RLS/VPD gerado (`/gerar-rls`) reescrito por segurança:**
  * antes, quem tinha `EXECUTE` no pacote podia se conceder acesso total (`PRC_SET_CONTEXTO(..., 'S')`) e o predicado concatenava o valor do contexto (injeção de SQL);
  * agora a identidade é resolvida pelo banco: `CLIENT_IDENTIFIER` (pool do Power BI/IA) só vale para contas cadastradas em `RLS_CONTAS_SERVICO`; qualquer outra sessão usa `SESSION_USER`;
  * predicado com subconsulta e `DBMS_ASSERT.ENQUOTE_LITERAL` (sem `LISTAGG`, sem limite de 4000 bytes / ORA-01489), política `DYNAMIC` e fail-closed em qualquer erro.
* **Fatos do DW eram criadas sem nenhuma FK:** o patch considerava "já existentes" as FKs do DDL de origem, que o `CREATE TABLE` não declara. Agora todas saem como `ENABLE NOVALIDATE`, inclusive a de `DIM_TEMPO`.
* **`VW_EVENTO`:** `IND_SITUACAO_EVENTO` era sempre `'REGULAR'` (`CASE WHEN 1 = 1`), e a pergunta-gabarito do Radar filtrava `'ATIVO'`, retornando sempre zero. Agora vem da coluna real de status da Fato (ou não é gerada).
* **`VW_KPI`:** ganhou eixo temporal (mês da data de negócio ou `DIM_TEMPO`) e participação percentual por período; antes somava todos os anos numa linha só.
* **Aliases de colunas** não são mais cortados às cegas em 30 caracteres (sem `_` no final e sem colisão).
* **Parser da Blueprint** tolera edições manuais (crases opcionais, `||` em fórmulas SQL, `|` em comentários) e avisa quando ignora uma linha; antes a coluna sumia do DDL em silêncio.
* **`--resetar` e `/limpar-demo` apagavam arquivos versionados** (`PROJETO_RESUMO.md`/`PROJETO_VERSION.md`); agora restauram o modelo em branco.
* **Zip bomb:** leitura de `.xlsx`, `.ods`, `.docx`, `.odt` e `.pbix` com limite de descompactação.
* **Templates duplicados unificados** (RLS, extrator API e `09_validacoes`), com teste que impede nova divergência. O extrator API passa a cumprir o contrato da skill (escrita atômica `.tmp`, `_REJEITADOS.csv`, linha `STATUS:SUCCESS`/`STATUS:ERROR` para o Hop).
* **DDL de Fato** traz recomendação comentada de particionamento mensal por intervalo e compressão (com as exigências de licença).

### 🧱 Engenharia
* **Golden files** (`tests/golden/`): 22 scripts SQL de referência congelados; qualquer mudança no SQL gerado aparece como diff.
* **Desmembramento dos arquivos gigantes (Fase 2), sem alterar nenhum SQL gerado (golden files idênticos):**
  * `gerador_artefatos_visuais.py`: 4.777 → ~290 linhas. Novos módulos `ninho_core/`: `leitores`, `lgpd`, `visual_comum`, `pdf`, `prova_dax`, `mockup_bi`, `diagramas`, `office`.
  * `melhorar_dw_existente.py`: 3.871 → ~600 linhas. Novos módulos: `dw_modelo`, `dw_patches`, `odi`, `guia_bi` (e o Fast-Track deixou de carregar o gerador visual inteiro).
  * `auditar_esteira_hop.py`: 1.867 → ~1.050 linhas. Gerador de pacote e migrador Kettle em `ninho_core/hop_gerador.py`.
  * Fachadas mantêm todos os imports antigos funcionando; `tests/test_arquitetura.py` impede que `ninho_core` dependa dos scripts e que os arquivos desmembrados voltem a crescer.
* **35 blocos `except: pass` silenciosos** passaram a registrar a exceção em log de depuração (`NINHO_LOG_LEVEL=DEBUG`), sem mudar o comportamento padrão.
* **`/testar-ninho`** roda todas as baterias e mostra o placar completo (`--parar-no-erro` para o modo antigo).
* **Radar da Governança** sugere conceitos canônicos `CNC_*`/`DOM_*` para `tb_sem_conceitos`.

---

## 🛠️ Versão `0.11.1` — `27/10/2026`

### 🎯 Em poucas palavras
Esta atualização resolve os desvios de convenção identificados durante testes de validação no **Modo Simulador (`simular_projeto.py`)** e remove a trava de exceção que existia no validador (`validar_entrega.py`), garantindo que 100% dos artefatos gerados (seja por simulação ou por execução direta) sigam rigorosamente o padrão corporativo de [`CONVENCOES_DW.md`](core/convencoes/CONVENCOES_DW.md).

### 🐛 Erros e Problemas Resolvidos
* **Corrigida Chave Substituta (`DIMENSION_KEY`) nas Dimensões do Simulador:**
  * Antes, ao converter tabelas transacionais (`TB_*`) para `DIM_*`, o simulador nomeava a PK como `SK_<ENTIDADE>`. Agora gera obrigatoriamente **`DIMENSION_KEY NUMBER(38,0) NOT NULL`**.
* **Corrigidas as 4 Colunas de Controle SCD Tipo 2 nas Dimensões:**
  * Adicionada a coluna obrigatória **`SIN_ATIVO CHAR(1 CHAR) DEFAULT 'S' NOT NULL`** junto com `DTC_EFETIVACAO DATE NOT NULL`, `DTC_EXPIRACAO DATE NULL` e `DES_ATUALIZAR CHAR(1 CHAR) DEFAULT 'S' NOT NULL` (preservando os constraints `NOT NULL` também no parser reverso da Blueprint).
* **Corrigida Nomenclatura de FKs na Tabela Fato (`DIM_<ENTIDADE>`):**
  * As chaves estrangeiras na `FATO_*` agora adotam o padrão **`DIM_<ENTIDADE> NUMBER(38,0) NOT NULL`** (ex.: `DIM_ORGAO_PUBLICO`, `DIM_FORNECEDOR`), preservando internamente a chave natural de origem para montar automaticamente os `LEFT JOIN` no script `04_select_odi_fato.sql`.
* **Incluída Geração da `DIM_TEMPO` Canônica (24 Colunas) e Vínculo na Fato:**
  * O script `03_create_dim_tables.sql` passa a emitir a `DIM_TEMPO` corporativa completa de 24 colunas (quando `REUSAR_DIM_TEMPO = NAO`), adicionando a FK `DIM_TEMPO` na tabela Fato e o `LEFT JOIN` com fallback `NVL(..., -1)` no `04_select_odi_fato.sql`.
* **Corrigido Padrão de Tablespaces (`<PROJETO>_DATA` e `<PROJETO>_INDEX`):**
  * Substituído o formato antigo `TBS_<PROJETO>_DADOS` pelo padrão oficial `<PROJETO>_DATA` e `<PROJETO>_INDEX`.
* **Corrigida Estrutura das Tabelas `STG_*` e `ODI_DIM_*`:**
  * As tabelas de Staging (`02_create_stg_tables.sql`) agora restauram as colunas naturais da fonte sem `NOT NULL`/`DEFAULT` e incluem `DTC_EXTRACAO DATE DEFAULT SYSDATE` e `ID_LOTE NUMBER`.
  * As tabelas `ODI_DIM_*` (`03_create_odi_dim_tables.sql`) garantem todas as colunas `NULL` sem `DEFAULT` e adicionam a coluna obrigatória `DES_STATUS_REGISTRO CHAR(1 CHAR)`.
* **Removido Bypass `is_simulacao_dw` em `validar_entrega.py`:**
  * O validador de qualidade não ignora mais nenhuma regra quando os arquivos vêm do simulador, validando 100% das convenções e aprovando a nova suíte **T17 (`17/17 E2E`)**.

---

## 🚀 Versão `0.11.0` — `27/10/2026`

### 🎯 Em poucas palavras
Esta atualização adiciona os **comandos de Execução Direta / Normal** (para quando o engenheiro quer gerar todo o projeto diretamente em `saida/` sem precisar passar pela etapa intermediária de simulação), além de introduzir a **Arquitetura Modular em 5 Etapas com Orquestrador** para projetos de Governança de Dados e scripts utilitários de extração de DDL em banco.

### ✨ O que há de novo
* **Novos Comandos de Execução Direta (`/executar-dw`, `/executar-semantica`, `/executar-projeto`, `/executar-governanca`):**
  * **`/executar-dw`** *(aliases: `/gerar-dw`, `/construir-dw`)*: Lê os insumos de `entrega/planejador_dw/` e gera diretamente todas as pastas `01` a `11` em `saida/planejador_dw/` (`--modulo dw --acao direto`).
  * **`/executar-semantica`** *(aliases: `/gerar-semantica`, `/iniciar-semantica`)*: Gera diretamente as 3 camadas de Views (`VW_DIM`, `VW_EVENTO`, `VW_KPI`), as 8 tabelas `META_*` e RLS em `saida/camada_semantica/` (`--modulo semantica --acao direto`).
  * **`/executar-projeto`** *(aliases: `/gerar-projeto`, `/construir-projeto`)*: Constrói **DW + Camada Semântica** de ponta a ponta em 1 único comando (`--modulo ambos --acao direto`).
  * **`/executar-governanca`** *(aliases: `/gerar-governanca`, `/iniciar-governanca`)*: Executa diretamente o Gate 0.5 e a esteira de Governança Corporativa.
* **Protótipo de Governança de Dados em 5 Etapas (piloto de identidade, fora do repositório):**
  * Validou em projeto piloto a divisão em extração, higienização LGPD, geração das coleções MongoDB padrão PRODEB (`tb_dataset`, `tb_sem_dominios`, `tb_sem_conceitos`, `tb_auditoria_eventos`, `tb_quarentena`) e carga condicional (`OFFLINE_JSON` vs `MONGO_DIRETO`).
  * > **Nota de correção (v0.12.0):** esse protótipo ficava na pasta local `ideias/` (não versionada) e nunca fez parte do repositório. A esteira oficial e versionada é `core/scripts_comuns/gerar_artefatos_governanca.py` (`/executar-governanca`), entregue na `v0.12.0`.

---

## 🎨 Versão `0.10.0` — `26/10/2026`

### 🎯 Em poucas palavras
Esta versão incorpora ao NINHO uma **suíte visual, de documentos Office/PDF e auditoria LGPD 100% nativa** (inspirada nas ferramentas de código aberto *FigCraft*, *GridCraft*, *DeckCraft*, *WordCraft*, *PdfCraft* e *PhotoCraft*, sem depender de nenhuma biblioteca externa). Agora, além dos scripts e guias técnicos, o NINHO desenha sozinho a **imagem/mockup do painel Power BI sugerido** (com modo de especificação técnica *Dev Mode* e botão para baixar em `PNG` de alta resolução), gera diagramas vetoriais do **Star Schema** e do **Canvas ODI 12c**, produz apresentações executivas **`.pptx`**, documentos Word **`.docx`**, relatórios **`.pdf`** oficiais prontos para SEI/Ofício e planilhas Excel **`.xlsx`** com listas suspensas e formatação condicional, lê arquivos **`.ods`**, **`.pdf`**, **`.docx`** e **`.odt`**, e escaneia dados pessoais escondidos dentro das linhas de amostra.

### ✨ O que há de novo
* **Gerador de Imagem/Mockup Visual do Painel BI (`/gerar-mockup-bi`):**
  * Gera automaticamente em `saida/planejador_dw/08_datasets_bi/` o protótipo visual Full HD (`1440×960`) do dashboard sugerido para o projeto:
    * `mockup_painel_bi.svg`: Visão executiva com cabeçalho institucional, barra de filtros (*Slicers*) sincronizados a partir das `DIM_*` reais, 4 cartões de KPI (com variação e *sparklines*), gráficos analíticos e matriz detalhada.
    * `mockup_painel_bi_devmode.svg`: Visão **Dev Mode (*Redlines & Callouts `①..⑦`*)** com cotas em pixels, espaçamentos de grid e anotações de medidas DAX para orientar o desenvolvedor de Power BI.
    * `preview_painel_bi.html`: Visualizador interativo com alternância entre **Visão Executiva / Dev Mode**, **Tema Claro / Escuro** e botão **"📸 Baixar Imagem PNG (Alta Resolução 2880×1920)"**.
* **Diagramas Vetoriais em SVG do Star Schema e do Canvas ODI 12c:**
  * `11_dicionario_dados/diagrama_star_schema.svg`: Diagrama entidade-relacionamento em estrela com a Fato no centro e as Dimensões ao redor exibindo PKs, FKs, cardinalidade `1 : N` e colunas SCD2.
  * `09_relatorio_estrategias/mapa_canvas_odi.svg`: Desenho vetorial do pacote `PACK_CARGA_<SIGLA>_DW` e do fluxo no Canvas do ODI 12c (`STG -> EXPR_RN_DEDUP -> FLT_RN_IGUAL_1 -> Lookups -> FATO`).
* **Planilha `Indicadores_PowerBI_<PROJETO>.xlsx` com Listas Suspensas (Dropdowns) e Formatação Condicional:**
  * Cria automaticamente a planilha Excel nativa com 3 abas (`Catalogo_Indicadores`, `Metas_e_Thresholds` e `Guia_Preenchimento`), cabeçalho congelado, auto-filtro e larguras automáticas.
  * **Novo (extraído do `gridcraft/xlsx`):** Inclui **listas suspensas nativas do Excel (`<dataValidation type="list">`)** nas colunas de *Origem*, *Formato*, *Visual Recomendado*, *Polaridade* e *Periodicidade* (impedindo erros de digitação do cliente), além de **formatação condicional (`<conditionalFormatting>` + `<dxfs>`)** que destaca em vermelho claro qualquer célula obrigatória deixada em branco.
* **Gerador Nativo de `.pdf` Oficial (`/exportar-pdf`), Apresentação `.pptx` (`/gerar-apresentacao`) e Word `.docx` (`/exportar-docx`):**
  * **Novo (extraído do `pdfcraft/create`):** Exporta os relatórios técnicos e de devolução diretamente em **`.pdf` multi-página (`%PDF-1.4`)** com cabeçalho institucional marinho, fontes vetoriais padrão e paginação no rodapé (`GUIA_ANALISTA_BI_<PROJETO>.pdf`, `RELATORIO_ESTRATEGIAS.pdf` e `RELATORIO_DEVOLUCAO_GOVERNANCA.pdf`) — pronto para anexar em processos SEI ou ofícios sem precisar abrir o Word.
  * Gera também o deck executivo `apresentacao_executiva_<PROJETO>.pptx` + `apresentacao_slides.html` (`16:9` interativo) e os documentos Word `.docx`.
* **Leitura Universal de Documentos do Cliente (`.ods`, `.pdf`, `.docx` e `.odt`):**
  * **Novo (extraído do `wordcraft/formats`):** Caso o cliente envie especificações de indicadores, dicionários ou DDLs dentro de arquivos **Word (`.docx`)**, **LibreOffice Writer (`.odt`)**, **LibreOffice Calc (`.ods`)** ou **`.pdf`**, o NINHO extrai parágrafos e tabelas automaticamente nos módulos de DW e Governança.
* **Scanner LGPD de Dados Pessoais Escondidos nas Linhas da Amostra (`pdfcraft/redact`):**
  * **Novo:** No Gate 0.5 da Governança (`/inspecionar-governanca`), além de auditar o nome das colunas, o inspetor agora varre o **conteúdo real das células e textos** em busca de **CPF, CNPJ, E-mail, Telefone/Celular BR e Cartão de Crédito (validação de Luhn)** escondidos dentro de colunas aparentemente inocentes (como `TXT_OBSERVACAO` ou `DES_HISTORICO`). Quando encontra, bloqueia a carga e exibe no relatório de devolução a evidência já **mascarada** (`***.456.789-**`, `jo***@ba.gov.br`).
* **5 Mecanismos Nativos do Apache Hop (`hop-main`) Integrados ao NINHO:**
  * **1. Desenhador Visual de Pipelines (`.hpl`) e Workflows (`.hwf`) em SVG + Auto-Documentação (`PipelineSvgPainter` / `DocBuilder`):** Lê as coordenadas `<gui><xloc>/<yloc>` e `<notepads>` dos XMLs do Apache Hop e desenha `diagrama_esteira_hop.svg` (com cores semânticas para hops de sucesso, erro `<transform_error_handling>`, incondicionais e desabilitados, além de badges para etapas órfãs) e `DOCUMENTACAO_HOP.md` com Sumário (TOC), parâmetros e inventário técnico.
  * **2. Catálogo Oficial `hop-lint` (`hop-lint-core.yml`) + Gerador `hop-lint.yml`:** Expande o `/auditar-hop` com as regras oficiais do linter do Hop (`TRANS-002` transform órfão, `WORKFLOW-002` action órfã, `NAMING-004` nome genérico padrão da GUI, `SQL-002` `SELECT *` irrestrito em `TableInput`, `STRUCT-003` hop desabilitado, `DOC-001` ausência de `<description>`/`<notepad>` e `META-001` subpasta `metadata/` fora de `kebab-case`) e gera `hop-lint.yml` na raiz do projeto.
  * **3. Migrador Automático de Pentaho Kettle Legado (`.ktr` / `.kjb` / `shared.xml`) para Apache Hop 2.x (`/migrar-kettle-hop`):** Baseado no motor `KettleConst.java` do Apache Hop, converte recursivamente transformações `.ktr` em `.hpl` e jobs `.kjb` em `.hwf`, renomeia plugins legados (`TextFileInput` $\rightarrow$ `TextFileInput2`, `TRANS` $\rightarrow$ `PIPELINE`, `JOB` $\rightarrow$ `WORKFLOW`, `ModifiedJavaScriptValue` $\rightarrow$ `ScriptValueMod`), atualiza variáveis internas (`Internal.Transformation.*` $\rightarrow$ `Internal.Pipeline.*`) e extrai conexões `<connection>` embutidas para `metadata/rdbms/<CONEXAO>.json` usando `#{hop-pwd:...}`.
  * **4. Blindagem de Segurança do `THREAT_MODEL.md` (`HopTwoWayPasswordEncoder` + `HOP-SEC-01/02`):** Implementa em Python puro o codificador/decificador oficial `HopTwoWayPasswordEncoder` (semente hexadecimal `0933910847463829827159347601486730416058`) para detectar ofuscações reversíveis `Encrypted 2be98afc...` (`HOP-SEC-01`) e injeção de variáveis `${VAR}` em consultas SQL (`HOP-SEC-02`), gerando automaticamente `metadata/variable-resolver/hop-pwd.json`.
  * **5. Template de Alta Volumetria `OraBulkLoader` (`SQL*Loader DIRECT=TRUE`) & Gerador de Pacote Hop (`/gerar-pacote-hop`):** Novo comando `/gerar-pacote-hop` (com suporte a `--orabulkloader`) e template `template_pipeline_orabulkloader.hpl` para cargas de milhões de linhas em tabelas `STG_* NOLOGGING` via `SQL*Loader` (`DIRECT=TRUE`, `LOAD_METHOD=AUTO_CONCURRENT`).
* **Motor de Prova Real Pós-Carga (`DIM_*` + `FATO_*`), Auditoria de Medidas DAX (`MED-01..06`), Ciclo de Vida do Guia do Analista e 3 Layouts de Mockup (`/validar-medidas-bi`):**
  * Permite fornecer os DDLs e uma amostra real de dados pós-carga das tabelas `DIM_*` e `FATO_*` (em `.csv`/`.tsv`, `.sql` com `INSERT INTO`, `.xlsx`, `.ods` ou `.dax` na pasta `entrega/planejador_dw/amostras/`) para testar na prática o que foi construído.
  * **Ciclo de Vida do Guia do Analista em 2 Estágios (Arquivo Único `GUIA_ANALISTA_BI_<PROJETO>.md`):**
    * **Estágio 1 — Versão Prévia (`Pré-Carga`):** Gerada inicialmente a partir do DDL antes da carga com o título `Guia do Analista de BI (VERSÃO PRÉVIA — PRÉ-CARGA)` e banner orientando a validação pós-carga.
    * **Estágio 2 — Versão Oficial (`Homologada Pós-Carga`):** Ao rodar `/validar-medidas-bi` com a amostra real, o mesmo arquivo é promovido automaticamente para `Guia Oficial do Analista de BI (VERSÃO OFICIAL — HOMOLOGADA PÓS-CARGA)`, substituindo medidas parcialmente corretas pelo DAX corrigido, injetando os valores reais da amostra nas fichas técnicas e adicionando a **Seção 10 (`Prova Real Pós-Carga e Conciliação de Medidas DAX`)**.
  * **Ficha Técnica Individual Detalhada para 100% das Medidas DAX:** Cada medida do guia possui sua própria ficha técnica explicando *O que calcula (Definição Funcional)*, *Por que esta medida existe (Objetivo de Negócio no Painel)*, *Por que a fórmula DAX foi construída assim (Racional Técnico Detalhado)*, *Onde utilizar & Formatação* e bloco DAX individual.
  * **3 Layouts Interativos no Mockup HTML (`preview_painel_bi.html`):** Permite alternar em 1 clique entre **Layout 1: Executivo Governamental (Top Navigation)**, **Layout 2: Analítico Menu Lateral Escuro (Sidebar Dark)** e **Layout 3: Sala de Situação & Auditoria Pós-Carga (Conciliação)**.
  * Sobe o Star Schema em memória (`sqlite3`), executa e concilia todas as medidas DAX contra consultas SQL reais sobre a amostra e aplica **6 heurísticas (`MED-01` a `MED-06`)** que detectam e auto-corrigem medidas "parcialmente corretas":
    * `MED-01`: `SUMMARIZE` SCD2 Safe sem proteção `NOT(ISBLANK(RELATED('DIM'[NK])))` (que infla +1 quando há FK órfã ou NK nula na amostra);
    * `MED-02`: `DISTINCTCOUNT` contando `SK` histórica na Fato em vez da Chave Natural (`NK`) em dimensões SCD Tipo 2;
    * `MED-03`: `% Atingimento de Meta` dividindo grandezas incompatíveis;
    * `MED-04`: Medida rotulada como `% Relacao ...` dividindo Valor Monetário (`VAL_*`) por Quantidade (`QTD_*`), reclassificada automaticamente para `Valor Medio ... por ...`;
    * `MED-05`: `SUM()` indevido sobre coluna de percentual/taxa (`PER_*` / `PRC_*`), corrigido para `AVERAGE()`;
    * `MED-06`: Conciliação de medidas filtradas de negócio (`CALCULATE` com predicados de dimensão/fato).
  * Gera `saida/planejador_dw/08_datasets_bi/RELATORIO_PROVA_REAL_MEDIDAS.md` e popula o Mockup Visual (`mockup_painel_bi.svg`, `mockup_painel_bi_devmode.svg` e `preview_painel_bi.html`) com os números reais calculados na amostra pós-carga.

---

## 🚀 Versão `0.9.0` — `23/10/2026`

### 🎯 Em poucas palavras
Esta atualização nasceu da comparação prática com projetos reais entregues de ponta a ponta (como o *Gestão à Vista de Sustentação*). Reformulamos completamente os dois documentos mais importantes para quem constrói e consome o DW — o **Guia Passo a Passo de Construção no ODI 12c** e o **Guia do Analista de BI** — além de blindar os scripts SQL contra os erros mais comuns que acontecem ao rodar no banco Oracle da PRODEB.

### ✨ O que há de novo
* **Guia do ODI 12c no Padrão *Dimension Pattern* (1 Mapa por Dimensão):**
  * Antes, o guia do ODI era resumido demais e sugeria dois mapas separados por dimensão. Agora, cada dimensão ganha um manual completo que ensina exatamente onde clicar no ODI Studio: como configurar o objeto em *Dimensões e Cubos* (`Asterisco` + `Dimension Pattern`), onde vincular a tabela de teste `ODI_DIM_*`, qual regra SCD2 marcar em cada coluna (`Chave Substituta`, `Histórico de Triggers`, `Inicializar com Efetivação`, `Preencher na Expiração`) e quais 3 colunas devem ficar com a **seta branca (sem ligação)** no Canvas para o ODI preencher sozinho.
* **Guia da Tabela Fato no ODI com Desenho do Canvas e Dica contra Erro de Janela:**
  * O guia de cada Fato agora traz a consulta SQL completa com deduplicação (`ROW_NUMBER() OVER ...`), o desenho visual do fluxo (`STG` $\rightarrow$ `EXPR_RN_DEDUP` $\rightarrow$ `FLT_RN_IGUAL_1` $\rightarrow$ `Lookups` $\rightarrow$ `FATO`), a tabela numerada de todas as colunas da Fato e o aviso explícito para marcar **`[x] Generate Inline View`** na aba *Physical* (evitando o erro `ORA-30483`).
* **Relatório Consolidado do ODI com Diagrama do Pacote Completo:**
  * O arquivo `RELATORIO_ESTRATEGIAS.md` agora inclui uma tabela de conferência de tamanho de nomes (`<= 30 caracteres`), o desenho completo do pacote `PACK_CARGA_<SIGLA>_DW` (Fase 1 Dimensões + Procedure da Linha `-1` + Fase 2 Fatos + Procedures de Índices) e a matriz de dependências `ok`/`ko`.
* **Guia do Analista de BI Profissional (Pronto para entregar ao time de Power BI):**
  * O documento `GUIA_ANALISTA_BI_<PROJETO>.md` deixou de ser básico e passou a ter 9 seções profundas: diagrama visual do modelo estrela, aviso de **proibição de relacionamento bidirecional**, medidas DAX prontas **protegidas contra duplicação de versões históricas (SCD2)** usando `SUMMARIZE` pela chave natural (`NK`), layout desenhado de 4 páginas de dashboard, guia de sincronização de filtros (*Sync Slicers*) e uma consulta SQL com `JOIN` pronta para o analista bater os números do Power BI com o banco Oracle (`100% de conciliação`).
* **Tabela Corporativa `ETA_ETAPAS_CARGA` Automática:**
  * O script `01_tb_controle_carga.sql` agora cria automaticamente a tabela `ETA_ETAPAS_CARGA` (padrão usado pelas esteiras Apache Hop e ODI), com bloco seguro que não dá erro se a tabela já existir no banco (`ORA-00955`), comentários nas 5 colunas e carga inicial (`MERGE INTO`) das etapas do projeto.
* **Opção de Reuso da `DIM_TEMPO` Corporativa (`REUSAR_DIM_TEMPO = SIM`):**
  * Quando o schema Oracle já possui uma `DIM_TEMPO` compartilhada por vários projetos, basta marcar `REUSAR_DIM_TEMPO = SIM` na simulação para que o NINHO use a tabela existente sem tentar recriá-la.

### 🛠️ O que ficou melhor
* **Padrão DBA de Índices no Oracle (`COMPRESS 1` e `NOPARALLEL`):**
  * Os índices de vigência das dimensões agora usam `COMPRESS 1` (economizando espaço e acelerando buscas por registros ativos), são criados rapidamente com `PARALLEL 4 NOLOGGING` e imediatamente revertidos para `NOPARALLEL LOGGING` para não travar consultas do Power BI.
* **Índice Automático para Acelerar o `MERGE` da Fato (`IDX_<FATO>_GRAO`):**
  * O gerador agora cria automaticamente um índice composto nas colunas que formam a chave de atualização da Fato, evitando lentidão (*Full Table Scan*) durante a carga incremental no ODI.
* **Tabelas de Stage (`STG_*`) mais rápidas e 100% documentadas:**
  * Todas as tabelas em `02_create_stg_tables.sql` agora saem com `NOLOGGING` (carga mais rápida no Hop) e com `COMMENT ON TABLE` e `COMMENT ON COLUMN` em todas as colunas.
* **Sequences Otimizadas (`CACHE 1000 NOORDER NOCYCLE`):**
  * Todas as Sequences de Dimensões e Fatos (quando a Fato possui chave própria) usam `CACHE 1000`, evitando gargalos de leitura em disco durante cargas grandes.

### 🐛 Erros e Problemas Resolvidos (Bugs Corrigidos)
* **Corrigido erro `ORA-01400 (cannot insert NULL)` na etapa `STG_DIM` do ODI:** As tabelas auxiliares `ODI_DIM_*` agora são geradas **100% `NULLABLE` e sem PK**. Antes, como o ODI grava na `ODI_DIM_*` antes de gerar a `DIMENSION_KEY` e as datas de vigência, a presença de `NOT NULL` fazia o mapa falhar.
* **Corrigido erro `ORA-00972 (identifier is too long)` no ODI 12c:** O ODI adiciona prefixos internos como `TGT_INS_` (8 letras) e `C$_0` nas tabelas temporárias, estourando o limite de 30 caracteres do Oracle quando o nome da tabela é longo. Agora o NINHO abrevia automaticamente nomes de dimensões (`<= 22` letras) e fatos (`<= 26` letras) já na simulação.
* **Corrigido erro `ORA-00904 (invalid identifier)` em criação de índices:** O gerador e o validador (`/validar-entrega`) agora conferem todas as colunas do `CREATE INDEX` contra o `CREATE TABLE` real, impedindo que um índice tente apontar para uma coluna com nome diferente na tabela Fato.
* **Corrigido erro `ORA-01543 (tablespace already exists)`:** Quando dados e índices usam a mesma Tablespace (ex: `PRODBA_OLAP`), o script `01_create_tablespaces.sql` emite apenas um `CREATE TABLESPACE` em vez de dois comandos repetidos.
* **Corrigido erro `ORA-00942 (table or view does not exist)` entre Hop e Stage (`HOP-H9`):** O validador agora cruza o nome da tabela configurada dentro do arquivo `.hpl` do Apache Hop com o nome criado no `02_create_stg_tables.sql`, avisando imediatamente se houver divergência de sigla.
* **Corrigido problema de registros duplicados ou órfãos por diferença de espaços/maiúsculas:** Os `JOINs` e `Lookups` entre Stage, Dimensões e Fato agora aplicam `UPPER(TRIM(...))` dos dois lados da comparação.
* **Corrigido alerta de Camada Semântica esquecida vazia:** O `/validar-entrega` agora avisa se a pasta `saida/camada_semantica/` contiver apenas o script base `01_create_meta_tables.sql` sem as Views analíticas e sem os metadados do projeto.

---

## 🧩 Versão `0.8.0` — `22/10/2026`

### 🎯 Em poucas palavras
Trouxemos melhorias práticas inspiradas no uso de ferramentas de banco (como DBeaver e SQL Developer) e na construção de painéis que cruzam dados do DW com metas em planilhas Excel.

### ✨ O que há de novo
* **Leitura Direta de DDLs Exportados em `.csv`:**
  * Exportou a lista de tabelas e colunas do DBeaver ou SQL Developer em `.csv` (`OWNER, TABLE_NAME, COLUMN_NAME, DATA_TYPE`)? Agora basta soltar o `.csv` na pasta `entrega/planejador_dw/ddl/` que o NINHO reconstrói o modelo exatamente como se fosse um arquivo `.sql`.
* **Leitura Automática de Planilhas `.xlsx` de Indicadores e Metas:**
  * Se você colocar uma planilha `.xlsx` com o catálogo de indicadores ou metas do cliente em `entrega/planejador_dw/amostras/`, o NINHO lê todas as abas nativamente (sem precisar instalar bibliotecas externas) e inclui uma seção dedicada no **Guia do Analista de BI** com as fórmulas DAX de cada indicador.
* **15 Novos Atalhos Diretos de Chat (`/gerar-...`):**
  * Novos comandos rápidos no menu `/` da IDE para rodar tarefas únicas em 1 segundo: `/gerar-guia-bi`, `/gerar-mock-bi`, `/gerar-selects-odi`, `/gerar-guia-odi`, `/gerar-dicionario`, `/gerar-comentarios`, `/gerar-indices`, `/gerar-linha-default`, `/gerar-constraints`, `/gerar-testes-dw`, `/gerar-views-semantica`, `/gerar-catalogo-meta` e `/gerar-rls`.

### 🛠️ O que ficou melhor
* **Suporte a *Role-Playing Dimensions* (Múltiplas Datas na mesma Fato):**
  * Quando uma tabela Fato possui várias datas (ex: *Data de Abertura*, *Data de Encerramento*, *Data de Pagamento*), a Camada Semântica agora cria um `LEFT JOIN` para cada data na `DIM_TEMPO` com apelidos claros (`dt_abertura`, `dt_encerramento`) e expõe Ano, Mês e Data de cada evento sem sobrescrever colunas.
* **Modo Isolado no Guia de BI (`--modo guia-bi`):**
  * Quando você pede apenas para gerar o Guia do Analista de BI, o NINHO gera exclusivamente o guia na pasta `08_datasets_bi/` sem criar arquivos extras que você não pediu.

### 🐛 Erros e Problemas Resolvidos (Bugs Corrigidos)
* **Corrigido descarte de Materialized Views (`MVW_*`) de origem:** Tabelas de origem que começam com `MVW_` (muito comuns em integrações corporativas) antes eram ignoradas por engano como se fossem views analíticas de saída. Agora são reconhecidas corretamente como fontes de dados e convertidas em `DIM_*` ou `FATO_*`.

---

## ⚡ Versão `0.7.0` — `21/10/2026`

### 🎯 Em poucas palavras
Focamos em tornar os comandos de barra (`/`) nativos na IDE, criar um ponto único de execução no terminal (`ninho.py`) e eliminar 12 falhas técnicas encontradas em uma auditoria profunda de código.

### ✨ O que há de novo
* **Executável Unificado `ninho.py` e `ninho.bat`:**
  * Agora você pode rodar qualquer comando do projeto digitando `python ninho.py <comando>` ou `.\ninho <comando>` na raiz do projeto.
* **Instalador de Comandos na IDE (`/instalar-comandos`):**
  * Registra e sincroniza automaticamente os comandos do NINHO como *Skills* nativas em `.agents/skills/`, fazendo com que apareçam no menu de autocompletar ao digitar `/` no chat da IDE.
* **Comandos `/ajuda` e `/onde-estou` sem Conflito com a IDE:**
  * Criados os atalhos `/ajuda` e `/onde-estou` para não baterem de frente com os comandos `/help` e `/status` reservados pelas próprias IDEs (Antigravity, Cursor, Claude Code).

### 🐛 Erros e Problemas Resolvidos (Bugs Corrigidos)
* **Corrigido parser SQL para tipos `TIMESTAMP(6)` e `RAW(16)`:** Colunas com parênteses seguidos de palavras-chave (como `TIMESTAMP(6) WITH TIME ZONE` ou `NUMBER GENERATED BY DEFAULT AS IDENTITY`) não são mais cortadas na leitura do DDL.
* **Corrigida classificação entre Dimensão e Fato em tabelas transacionais:** Tabelas de movimento que não tinham o prefixo `FATO_` mas possuíam chaves estrangeiras (`FKs`), datas e valores numéricos passaram a ser identificadas corretamente como tabelas Fato.
* **Corrigida padronização da coluna SCD2 `DES_ATUALIZAR`:** Unificado o nome `DES_ATUALIZAR` em todos os templates, validadores e geradores (eliminando a variação antiga `DES_ATUALIZA`).
* **Corrigida proteção contra caracteres especiais no Dicionário HTML:** Comentários de tabelas ou colunas contendo sinais como `<`, `>` ou `&` agora passam por escape seguro (`html.escape`), evitando quebras visuais no `dicionario_dados.html`.
* **Corrigida preservação da coluna `SIN_ATIVO` no histórico SCD2:** Nas views de evento da Camada Semântica, o `JOIN` com dimensões históricas passou a ser feito pela chave substituta (`SK`) sem forçar `SIN_ATIVO = 'S'`, preservando a fotografia exata da época em que o fato aconteceu.

---

## 🧭 Versão `0.6.0` — `19/10/2026`

### 🎯 Em poucas palavras
Transformamos a experiência de quem usa o NINHO pela primeira vez, criando ferramentas visuais de navegação, um modo de demonstração instantâneo e uma bateria automática de testes de qualidade.

### ✨ O que há de novo
* **Modo Playground em 1 Comando (`/demo` e `/limpar-demo`):**
  * Quer ver o NINHO funcionando sem ter nenhum arquivo em mãos? O comando `/demo` cria sozinho um projeto de exemplo completo (Licitações Públicas), roda a simulação, gera o DW, a Camada Semântica, o Dicionário HTML e a massa de testes para Power BI em 3 segundos. Depois, `/limpar-demo` deixa tudo limpo.
* **Assistente de Boas-Vindas (`/comecar`) e Bússola (`/onde-estou`):**
  * O `/comecar` mostra as 5 trilhas do projeto em 3 passos simples. O `/onde-estou` lê as pastas do projeto e mostra uma barra de progresso visual indicando exatamente o que já foi feito e qual o próximo comando a rodar.
* **Oráculo de Dúvidas (`/duvida`) e Auto-Organizador (`/doctor`):**
  * Esqueceu a diferença entre Estratégia A e B, ou por que usamos a linha `-1`? Digite `/duvida estrategia-carga` ou `/duvida linha-default`. Soltou um arquivo `.sql` ou `.pbix` na pasta errada? Digite `/doctor --corrigir` que ele arruma sozinho.
* **Suíte Automatizada de Testes Ponta a Ponta (`/testar-ninho`):**
  * Criado o script `testar_ninho.py`, que testa todos os motores da plataforma automaticamente e garante que nenhuma atualização quebre o que já funcionava.

### 🐛 Erros e Problemas Resolvidos (Bugs Corrigidos)
* **Corrigida renderização de diagramas Mermaid no GitLab:** Convertidos os fluxogramas da documentação para a sintaxe `graph TD` vertical, resolvendo erros de visualização no GitLab corporativo.

---

## 🧪 Versão `0.5.0` — `16/10/2026`

### 🎯 Em poucas palavras
Uma das maiores evoluções do projeto: o engenheiro ganhou controle total para **simular e editar** tudo antes de gerar código, além do **Modo Fast-Track** para trabalhar em DWs que já existem no banco sem burocracia.

### ✨ O que há de novo
* **Simulador com Blueprint 100% Editável (`/simular-dw`, `/simular-semantica`, `/executar-simulacao`):**
  * Agora você pode gerar uma prévia completa do projeto (`SIMULACAO_BLUEPRINT_DW.md` e `SIMULACAO_BLUEPRINT_SEMANTICA.md`), abrir no editor, desmarcar `[ ]` colunas ou entregáveis que não quiser, renomear tabelas, mudar tipos de dados ou adicionar novos KPIs, e só então disparar `/executar-simulacao` para gerar os arquivos finais exatamente como você editou.
* **Modo Fast-Track para DWs Já Construídos (`/melhorar-dw-existente`):**
  * Já tem um DW pronto no Oracle e precisa apenas gerar o Dicionário de Dados HTML, os comentários (`COMMENT ON`), os índices de performance, a linha default `-1` ou os scripts do ODI? Agora você roda direto sobre o DDL das tabelas, sem precisar preencher o formulário `INTAKE_DW.md` e sem risco de alterar a estrutura existente.
* **Dicionário de Dados Interativo em HTML (`dicionario_dados.html`):**
  * Geração automática de uma página HTML moderna, com busca instantânea por tabela ou coluna, filtros por camada (`DIM` / `FATO`) e botão de exportar para CSV.

---

## 🛡️ Versão `0.3.0` — `15/10/2026`

### 🎯 Em poucas palavras
Construção da base do **Módulo de Governança de Dados Corporativa** (integrado ao MongoDB e AWS SageMaker Catalog — *aguardando homologação prática para o lançamento `1.0.0`*) e dos 4 motores de inspeção automática para auditar insumos antes do trabalho começar.

### ✨ O que há de novo
* **Módulo de Governança de Dados e Gate 0.5 (`/inspecionar-governanca`):**
  * Valida automaticamente as planilhas `.xlsx` e amostras `.csv` enviadas pelo cliente. Se houver campos sem descrição, sem classificação LGPD/LAI ou colunas fantasmas (`;;;`), o NINHO bloqueia o processamento e gera um **Relatório de Devolução ao Cliente** pronto para envio. Quando aprovado, gera os esquemas do **MongoDB PRODEB** (`tb_dataset`, `tb_sem_dominios`, `tb_sem_conceitos`) e o manifesto para o **AWS Glue / Amazon SageMaker Catalog**.
* **Engenharia Reversa de Power BI (`/inspecionar-pbix`):**
  * Descompacta arquivos `.pbix` legados, extrai todas as tabelas, medidas DAX e filtros ocultos nos visuais, aponta gargalos (`PBIX-H1` a `PBIX-H5`) e projeta o modelo estrela no DW.
* **Auditor de Mapas do ODI 12c (`/auditar-mapa-odi`) e Apache Hop (`/auditar-hop`):**
  * Inspeciona XMLs exportados do ODI 12c (`H1` a `H9`) e projetos do Apache Hop 2.x (`HOP-H1` a `HOP-H8`), encontrando gargalos de performance, falta de `COMMIT`, senhas expostas ou ausência de tratamento de erro.
* **Radar Consultivo da IA (`/inspecionar-fontes`):**
  * Ao ler os DDLs de origem, a plataforma sugere proativamente novos indicadores de negócio (Ticket Médio, Lead Time, Taxa de Qualidade) e regras de higienização para enriquecer o projeto.

---

## 🧱 Versão `0.2.0` — `13/10/2026`

### 🎯 Em poucas palavras
Reorganização do cérebro do NINHO em **Skills Modulares Especializadas** e expansão para cobrir toda a esteira de ingestão (APIs Python, arquivos FTPS em lote, Apache Hop, ODI 12c e segurança RLS).

### ✨ O que há de novo
* **10 Skills Modulares em `.agents/skills/`:**
  * Cada especialidade (Planejador DW, ETL Hop, Consultas ODI, Extrator Python, FTPS em Lote, Camada Semântica, Segurança RLS, Governança, Engenharia Reversa PBIX e Validador de Qualidade) ganhou seu próprio módulo enxuto e especializado.
* **Regra Arquitetural Canônica (`STG` $\rightarrow$ `DIM/FATO` unicamente no ODI 12c):**
  * Padronização do fluxo corporativo: a chegada do dado na `STG_*` pode vir via Python, Apache Hop ou arquivo, mas a transformação da `STG_*` para `DIM_*` e `FATO_*` ocorre exclusivamente no **ODI 12c**, com chave substituta padronizada `DIMENSION_KEY` e presença obrigatória da `DIM_TEMPO`.

---

## 🌱 Versão `0.1.0` — `21/09/2026` a `08/10/2026` *(Versão Inicial de Testes)*

### 🎯 Em poucas palavras
O nascimento e os primeiros testes experimentais da plataforma **NINHO**, unificando o planejamento de Data Warehouses no Oracle e a Camada Semântica orientada a Inteligência Artificial.

### ✨ O que foi construído nos primeiros testes
* **Estrutura nas 3 Pastas Canônicas:** Organização limpa separando onde o engenheiro coloca insumos (`entrega/`), onde ficam os motores e formulários (`modulos/`) e onde os scripts prontos são gerados (`saida/`).
* **Planejador de DW Oracle (Kimball Star Schema):** Primeiros templates e regras para criação de Tablespaces, Controle de Carga, Staging (`STG_*`), Dimensões SCD Tipo 2 (`DIM_*`), Fatos (`FATO_*`), Linha Default `-1` (`'Não Informado'`) e Procedures de manutenção de índices Bitmap.
* **Camada Semântica em 3 Camadas + 8 Tabelas `META_*`:**
  * Arquitetura de Views Analíticas (`VW_DIM_*`, `VW_EVENTO_*`, `VW_KPI_*`) acoplada às 8 tabelas de metadados ativos (`META_PROJETO`, `META_DOMINIO`, `META_OBJETO`, `META_ATRIBUTO`, `META_METRICA`, `META_RELACIONAMENTO`, `META_CONSULTA_NEGOCIO` e `META_ORIENTACAO_IA` com 36 diretrizes para agentes Text-to-SQL).
* **Handoff Automatizado (`/concluir-dw` $\rightarrow$ `/iniciar-semantica`):** Transição automática dos DDLs gerados no DW para a entrada da Camada Semântica, acompanhada do gerador de dados sintéticos (`gerar_mock_dados.py`) e validador pré-voo (`validar_entrega.py`).
