# 📰 Histórico de Versões e Novidades (Patch Notes) — Plataforma NINHO

> **Versão Atual:** `v0.9.0` *(Pré-Lançamento / Release Candidate)* | **Última Atualização:** `23/10/2026` | **Status da Suíte de Testes:** `✅ 13/13 Aprovados (E2E)`

Bem-vindo à página oficial de **Patch Notes** do **NINHO**!
Esta página foi escrita para ser **simples, direta e amigável para pessoas lerem** — seja você Engenheiro de Dados, DBA, Analista de BI ou Gestor. Aqui você acompanha tudo o que evoluiu na plataforma desde os primeiros testes (`v0.1.0`) até o estágio atual (`v0.9.0`), quais ferramentas novas entraram e quais dores de cabeça do dia a dia (erros de banco, travamentos no ODI/Hop ou retrabalho no Power BI) já foram resolvidas.

> 🎯 **Quando chegaremos na Versão `1.0.0`?**
> Os módulos de **Planejamento de Data Warehouse (Oracle + ODI 12c + Hop + BI)** e **Camada Semântica (`VW_*` + `META_*`)** já foram colocados à prova e aprimorados com projetos reais de ponta a ponta. A versão **`v1.0.0`** será oficializada quando o **Módulo de Governança de Dados (MongoDB PRODEB + AWS SageMaker Catalog)** passar pelo teste prático completo e for formalmente aprovado.

---

## 🗺️ Resumo Rápido das Versões (`v0.1.0` $\rightarrow$ `v0.9.0`)

| Versão | Data | Destaque Principal (Em uma frase) |
| :---: | :---: | :--- |
| 🎯 **`v1.0.0`** *(Planejada)* | *Em breve* | **Marco Oficial 1.0:** Homologação prática e aprovação final do Módulo de Governança de Dados (MongoDB + AWS SageMaker Catalog) em projeto real. |
| **[`v0.9.0`](#-versão-090--23102026-versão-atual)** | `23/10/2026` | **Padrão Ouro de Produção (ODI 12c, DBA Oracle & BI):** Guias do ODI no padrão *Dimension Pattern* passo a passo, Guia do Analista de BI completo (com medidas SCD2 e wireframe de 4 páginas), controle `ETA_ETAPAS_CARGA` e trava contra erros de nomes longos e índices no Oracle. |
| **[`v0.8.0`](#-versão-080--22102026)** | `22/10/2026` | **Integrações Reais de Campo:** Leitura de DDLs exportados em `.csv` (DBeaver/SQL Developer), suporte a Materialized Views (`MVW_*`), múltiplas datas na mesma Fato (*Role-Playing*) e leitura de planilhas `.xlsx` de indicadores para o Power BI. |
| **[`v0.7.0`](#-versão-070--21102026)** | `21/10/2026` | **Atalhos de Chat (`/comando`) e Blindagem Geral:** Criado o executável único `ninho.py` (`.\ninho`), instalador de comandos `/instalar-comandos` na IDE e correção de 12 bugs silenciosos de parser SQL e HTML. |
| **[`v0.6.0`](#-versão-060--19102026)** | `19/10/2026` | **Experiência Guiada e Playground (`/demo`):** Assistente de boas-vindas (`/comecar`), bússola de progresso (`/onde-estou`), auto-organizador de pastas (`/doctor`) e suíte automatizada de testes (`/testar-ninho`). |
| **[`v0.5.0`](#-versão-050--16102026)** | `16/10/2026` | **Simulador Editável & Modo Fast-Track:** Possibilidade de simular e editar todo o projeto em uma tabela antes de gerar os scripts reais, além de gerar recortes isolados (só comentários, só índices, só dicionário) sem precisar preencher formulários longos. |
| **[`v0.3.0`](#-versão-030--15102026)** | `15/10/2026` | **Estrutura de Governança (MongoDB + AWS) e Auditores Inteligentes:** Auditoria automática de arquivos do cliente (Gate 0.5), engenharia reversa de `.pbix` e auditores preditivos para ODI 12c e Apache Hop. |
| **[`v0.2.0`](#-versão-020--13102026)** | `13/10/2026` | **Arquitetura em Skills Modulares e Esteira Completa ETL:** Divisão da inteligência em 10 especialistas (`.agents/skills/`), suporte a FTPS em lote, extratores Python e segurança RLS/VPD no Oracle. |
| **[`v0.1.0`](#-versão-010--21092026-a-08102026)** | `08/10/2026` | **Versão Inicial de Testes e Protótipo do NINHO:** Primeiros testes do Planejador de DW, da Camada Semântica em 3 níveis com 8 tabelas `META_*`, 36 orientações de IA e organização nas 3 pastas (`entrega/`, `modulos/`, `saida/`). |

---

## 🚀 Versão `0.9.0` — `23/10/2026` *(Versão Atual)*

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

---

## 💡 Como Manter esta Página Atualizada?

Sempre que uma nova versão ou melhoria for publicada no repositório:
1. Adicione uma nova seção no topo (seguindo o formato `## 🚀 Versão X.Y.Z — DD/MM/AAAA`).
2. Atualize a linha correspondente na tabela **[Resumo Rápido das Versões](#️-resumo-rápido-das-versões-v010--v090)**.
3. Descreva as mudanças pensando em **quem vai ler**: explique **o que entrou**, **o que melhorou** e **qual problema real foi resolvido**!
