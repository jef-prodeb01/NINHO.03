# 👋 Guia Inicial do Engenheiro — Bem-vindo ao NINHO!

> **Nunca usou o NINHO antes? Comece por aqui!**  
> Este guia foi escrito em linguagem direta e acessível para que qualquer pessoa da equipe entenda, em poucos minutos, **como o projeto funciona**, **o que cada ferramenta faz** e **como executar sua primeira tarefa passo a passo**.

---

## 📌 Sumário Rápido

1. [A Ideia Central em 1 Minuto & Atalhos Interativos no Chat](#1-ideia-central)
2. [O Que o NINHO Pode Fazer por Você? (Os 7 Cenários do Dia a Dia)](#2-seis-cenarios)
3. [Mapa Explicado: O Que Cada Pasta, Script, Skill e Comando Faz](#3-mapa-explicado)
   - [🛠️ 3.1 Os 14 Scripts Python (`core/scripts_comuns/`)](#31-scripts-python)
   - [🧩 3.2 As 10 Skills da IA (`.agents/skills/`)](#32-skills-ia)
   - [💬 3.3 Dicionário Completo de Comandos Rápidos do Chat (`/comando`)](#33-dicionario-comandos-chat)
4. [Passo a Passo: Sua Primeira Vez Usando o Projeto](#4-passo-a-passo)
5. [Perguntas Frequentes de Quem Está Começando (FAQ)](#5-faq)

---

<a id="1-ideia-central"></a>
## 1. A Ideia Central em 1 Minuto & Atalhos Interativos no Chat

O **NINHO** é uma plataforma corporativa criada para **Engenheiros de Dados**. O objetivo dele é eliminar o trabalho braçal, padronizar entregas da equipe e auditar códigos legados usando uma combinação de **Scripts Python Determinísticos** (que leem arquivos pesados sem errar) + **Agentes de IA Especializados** (que projetam modelos, escrevem SQL/Python/Documentação e sugerem melhorias).

> 🚀 **Pegou o projeto pela primeira vez agora? Você não precisa decorar nada! Basta digitar um destes 6 comandos no chat:**
> - **`/comecar`** *(ou `/onboarding`)*: Mostra as **5 trilhas guiadas em 3 passos simples** (*Onde colocar seu arquivo* $\rightarrow$ *Qual comando rodar para simular* $\rightarrow$ *Qual comando rodar para gerar*).
> - **`/demo`** *(e depois `/limpar-demo`)*: **Quer ver o NINHO funcionando antes de usar seus arquivos?** Digite `/demo`! Em 3 segundos ele cria um projeto completo de demonstração (*Licitações SAEB*), gera as Blueprints editáveis, o DW, a Camada Semântica, o Dicionário HTML interativo e um CSV sintético para Power BI. Quando terminar de olhar, digite `/limpar-demo` para deixar tudo limpo.
> - **`/onde-estou`** *(ou `/status`)*: Mostra a **Bússola Contextual** com barra de progresso (`[███░░] Fase X/5`), o que já foi detectado nas pastas e qual o próximo comando ideal.
> - **`/duvida listar`** *(ou `/duvida <tema>`)*: Abre o **Oráculo de Arquitetura** para tirar dúvidas conceituais na hora (`estrategia-carga`, `scd`, `linha-default`, `camadas-views`, `arquitetura-etl`, `gate-governanca`, `simulacao`, `fast-track`, `rls`).
> - **`/doctor`**: Colocou algum arquivo `.sql`, `.pbix` ou `.xlsx` na pasta errada dentro de `entrega/`? O `/doctor` avisa e move automaticamente para a subpasta certa (`--corrigir`).
> - **`/help`**: Mostra a tabela completa de todos os comandos disponíveis.

Para usar o NINHO no dia a dia, você só precisa entender a **Regra das 3 Pastas**:

```mermaid
graph LR
    E["1. entrega/<br/>O que voce TEM"] --> M["2. modulos/ ou Blueprint<br/>O que voce QUER"]
    M --> S["3. saida/<br/>O que sai PRONTO"]
```

1. **📥 Pasta [`entrega/`](../../entrega/README.md) (Entrada):** É onde você solta os arquivos brutos do seu projeto (tabelas SQL/DDL de origem, planilhas Excel/CSV, arquivos `.pbix` do Power BI, XMLs do ODI ou pipelines `.hpl`/`.hwf` do Apache Hop).
2. **⚙️ Pasta [`modulos/`](../../modulos/README.md) ou Blueprint Editável (Configuração):** Você pode simular o projeto com `/simular-projeto` (que gera os arquivos editáveis `SIMULACAO_BLUEPRINT_DW.md` e `SIMULACAO_BLUEPRINT_SEMANTICA.md` dentro de `entrega/` para você marcar/desmarcar colunas `[x]`/`[ ]`, mudar tipos e aprovar KPIs) ou preencher os formulários `INTAKE_*.md` em `modulos/`.
3. **📤 Pasta [`saida/`](../../saida/README.md) (Resultado Final):** É onde o NINHO grava todos os scripts SQL, procedures, extratores, dicionário HTML, relatórios de auditoria e guias de Power BI prontos para você implantar.

### 🛡️ Por que o NINHO é seguro e não "inventa moda"?
Diferente de um chat de IA comum que tenta adivinhar coisas e gera código errado, o NINHO trabalha com **3 travas de segurança**:
- **Leitura Exata via Python:** Antes da IA falar qualquer coisa, scripts em Python leem os seus arquivos (DDL, Excel, XML do ODI, Hop, Power BI) e extraem 100% das colunas, tipos e problemas reais.
- **Não Gera no Escuro (Simulação / Blueprint 100% Editável Primeiro):** Antes de gerar código definitivo, você pode rodar `/simular-projeto` para ver uma prévia completa (com 3 linhas de exemplo + linha `-1` e o **💡 Radar Consultivo da IA**). Você edita o que quiser na tabela Markdown e o NINHO lê todas as suas edições ao rodar `/executar-simulacao`.
- **Só Gera o que Você Marcou:** Se você não marcou Apache Hop ou Python, o NINHO **nunca** vai gerar arquivos extras sem necessidade.

---

<a id="2-seis-cenarios"></a>
## 2. O Que o NINHO Pode Fazer por Você? (Os 7 Cenários do Dia a Dia)

Você **não precisa** usar o projeto inteiro de uma vez! Dependendo da sua tarefa no dia, você pode usar o NINHO de **7 formas diferentes**:

---

### 🏗️ Cenário 1: Criar um Data Warehouse (DW) Novo no Oracle (Com Simulação Editável)
- **Para que serve:** Você tem tabelas de um sistema transacional (OLTP), planilhas via SFTP ou uma API REST, e precisa criar o modelo Star Schema (Kimball) completo no Oracle (`STG_*`, `DIM_*` com histórico SCD Tipo 2, `FATO_*`, índices, sequences, procedure pós-carga, dicionário HTML e guia para o time de Power BI).
- **Onde colocar os arquivos:** [`entrega/planejador_dw/ddl/`](../../entrega/planejador_dw/ddl/) (ou pastas `amostras/`, `arquivos_ftp/`, `api_specs/`).
- **Como acionar (Caminho Recomendado com Blueprint Editável):**
  1. No chat: digite **`/simular-dw`** (ou **`/simular-projeto`** para simular DW + Camada Semântica juntos).
  2. Abra o arquivo gerado `entrega/planejador_dw/SIMULACAO_BLUEPRINT_DW.md`, revise/edite nomes de tabelas, marque `[ ]` nas colunas que não quiser levar, escolha a estratégia de carga e marque `- [x] SIMULAÇÃO 100% FECHADA E APROVADA PARA EXECUÇÃO REAL`.
  3. No chat: digite **`/executar-simulacao`**.
- **O que sai pronto:** Todos os scripts numerados e organizados nas 11 pastas de [`saida/planejador_dw/`](../../saida/planejador_dw/README.md), incluindo o guia do analista de BI (`08_datasets_bi/`), o dicionário de dados interativo (`11_dicionario_dados/dicionario_dados.html`) e dados sintéticos opcionais (`/gerar-mock-bi`).

---

### ⚡ Cenário 2: Melhorar um DW Já Construído no Banco (Modo Fast-Track & Micro-Processos)
- **Para que serve:** Você **já construiu** suas tabelas `DIM_*` e `FATO_*` no Oracle e não quer recriar o DW do zero, mas precisa gerar rapidamente o **Dicionário de Dados HTML**, **Comentários (`COMMENT ON`)**, **Índices de Tuning**, **Linha Default `-1`**, **Constraints `NOVALIDATE`**, **Consultas SQL do ODI** ou o **Guia do Analista de BI**.
- **Onde colocar os arquivos:** Coloque o `.sql` das suas tabelas `DIM_*` e `FATO_*` atuais em [`entrega/planejador_dw/ddl/`](../../entrega/planejador_dw/ddl/). *(Não precisa preencher formulário `INTAKE_DW.md`!)*
- **Como acionar:**
  - Para gerar o pacote completo de melhorias não-destrutivas: digite **`/melhorar-dw-existente`** no chat (ou `python core/scripts_comuns/melhorar_dw_existente.py --modo tudo`).
  - Para gerar **apenas um item específico** em segundos: digite `/gerar-dicionario`, `/gerar-comentarios`, `/gerar-indices`, `/gerar-linha-default`, `/gerar-constraints`, `/gerar-selects-odi`, `/gerar-guia-odi`, `/gerar-guia-bi` ou `/gerar-mock-bi`.

---

### 🦅 Cenário 3: Auditar e Fazer Tuning de Projetos no ODI 12c (Legado ou Novo)
- **Para que serve:** Você tem um projeto no **Oracle Data Integrator (ODI 12c)** que está lento, dando erro ou precisa passar por revisão de qualidade antes de ir para produção. O motor lê pastas inteiras de exportação XML do ODI (`Mapas/`, `Cenas/`, `Pacotes/`, `Procedures/`, `Variaveis/`).
- **O que ele descobre sozinho (Heurísticas `H1` a `H9`):**
  - Tabelas sem filtro incremental (Full Scan), falta de chave primária na Staging, joins com dimensões SCD2 que esqueceram de filtrar o registro vigente (`FLG_ATUAL = 1`), falso SCD2 com valores fixos `'X'`, uso de `TRUNC(data)` que anula índices no Oracle, procedures com `COMMIT` dentro de loop e variáveis com `select *`.
- **Como rodar (direto no terminal ou pelo chat):**
  ```bash
  python core/scripts_comuns/auditar_mapa_odi.py <caminho_da_pasta_ou_xml_do_odi>
  ```
  *(Ou digite `/auditar-mapa-odi` no chat da IA para que ela analise o relatório e já escreva os SQLs corrigidos para você).*

---

### 🐝 Cenário 4: Auditar Esteiras Apache Hop 2.x, FTPS e Extratores Python
- **Para que serve:** Você ou alguém da equipe construiu um projeto no **Apache Hop** (arquivos `.hpl`, `.hwf`, `.json`), scripts Shell de FTPS (`.sh`) ou extratores Python (`.py`), e quer verificar se há falhas graves antes do deploy.
- **O que ele descobre sozinho (Heurísticas `HOP-H1` a `HOP-H8`):**
  - **Segurança (`HOP-H1`):** Senhas do banco/FTP/API salvas em texto aberto em vez de criptografadas ou via `HopPassword`.
  - **Esquecimento de Copy-Paste (`HOP-H2`):** Quando alguém clona um projeto (ex: copia o projeto `CFPC` para criar o `DHPP`) e esquece nomes da tabela antiga ou do e-mail antigo escondidos dentro do código.
  - **Setas Invertidas (`HOP-H3`):** Hops vermelhos (`evaluation=N`) no workflow apontando para etapas que deveriam rodar no sucesso.
  - **Caminhos Quebrados e Duplicatas (`HOP-H4` a `HOP-H8`):** Arquivos `.hpl` que não existem mais, variáveis coladas sem barra (`${DIR}${ARQ}`), `PipelineExecutor` que não herda variáveis (`inherit_all_vars=N`) e `TableOutput` sem `use_batch`.
  - **Checklist Corporativo:** Confere se o projeto usa a tabela de telemetria `ETA_ETAPAS_CARGA`, controle de arquivos `CONTROLE_MODIFICACAO_ARQUIVOS`, `WorkflowLogging` e quarentena de erros `TAB_*_ERRO`.
- **Como rodar:**
  ```bash
  python core/scripts_comuns/auditar_esteira_hop.py <caminho_da_pasta_do_projeto_hop>
  ```
  *(Ou digite `/auditar-hop` no chat da IA).*

---

### 📊 Cenário 5: Engenharia Reversa de Dashboards Power BI Legados (`.pbix`)
- **Para que serve:** O cliente ou setor de negócio tem um painel `.pbix` antigo (muitas vezes lento, puxando dados direto de tabelas transacionais ou planilhas soltas) e pede para migrar esse painel para um Data Warehouse oficial.
- **O que ele faz sozinho:**
  - Você não precisa abrir o Power BI Desktop para caçar medidas! O script abre o arquivo `.pbix` nativo, extrai todas as tabelas, colunas, relacionamentos, medidas DAX, parâmetros M e **traduz todos os filtros escondidos nos visuais e páginas**.
  - Detecta os 5 anti-padrões clássicos (`PBIX-H1` a `PBIX-H5`: relacionamentos Muitos-para-Muitos, filtro bidirecional, falta de `DIM_TEMPO`, colunas numéricas sem medida DAX explícita e `AutoDateTime` ativado).
- **Como rodar:**
  ```bash
  python core/scripts_comuns/inspecionar_pbix.py <caminho_do_arquivo_ou_pasta_pbix>
  ```
  *(Ou digite `/inspecionar-pbix` no chat da IA para gerar o modelo Star Schema do DW a partir do `.pbix`).*

---

### 🧠 Cenário 6: Criar a Camada Semântica Oracle e Metadados Ativos (`META_*`)
- **Para que serve:** Depois que o DW está pronto, você precisa expor os dados de forma limpa para o Power BI e para agentes de IA (Text-to-SQL / Chatbots Analíticos), além de aplicar segurança por linha (**RLS / VPD** para que cada secretaria/órgão veja apenas seus próprios dados).
- **Como funciona:**
  - Se você acabou de criar o DW no Cenário 1, basta digitar `/concluir-dw` (ou rodar `python core/scripts_comuns/transicionar_dw_para_semantica.py`). Ele copia os DDLs do DW e já prepara a entrada da Camada Semântica sozinho!
  - Se o DW já existia no banco, coloque os DDLs dele em [`entrega/camada_semantica/sql_fontes/`](../../entrega/camada_semantica/) e digite **`/simular-semantica`** (para revisar KPIs antes) ou **`/iniciar-semantica`**.
  - Se quiser gerar apenas uma parte isolada, use `/gerar-views-semantica`, `/gerar-views-kpi`, `/gerar-catalogo-meta` ou `/gerar-rls`.
- **O que sai pronto em [`saida/camada_semantica/`](../../saida/camada_semantica/):**
  - **Views em 3 Camadas:** `VW_DIM_*_ATUAL` (apenas registros vigentes da SCD2), `VW_EVENTO_*` (fato enriquecida com descrições) e `VW_KPI_*` (indicadores oficiais + KPIs aprovados do Radar com `NULLIF`).
  - **As 8 Tabelas `META_*`:** Scripts DDL e `MERGE INTO` idempotentes com dicionário semântico, sinônimos de negócio, métricas certificadas e 36 regras para guiar agentes Text-to-SQL.

---

### 🛡️ Cenário 7: Governança de Dados, MongoDB PRODEB & AWS SageMaker Catalog
- **Para que serve:** Receber planilhas de dicionário de dados (`.xlsx`) e amostras (`.csv`) enviadas pelo cliente/órgão, validar a qualidade, gerar as coleções de metadados no **MongoDB Enterprise (Padrão PRODEB)** e publicar no **AWS Glue / Amazon SageMaker Catalog**.
- **Destaque — O "Porteiro" Automático (Gate 0.5):**
  - Na governança, preencher dicionário e classificação LGPD/LAI é **obrigação do cliente**.
  - Ao rodar o inspetor sobre a pasta [`entrega/governanca_dados/`](../../entrega/governanca_dados/), se o cliente tiver deixado descrições vazias, classificação LGPD em branco ou CSV com colunas fantasmas (`;;;`), o NINHO **bloqueia o processo na hora** e gera automaticamente um **Relatório Formal de Devolução ao Cliente** listando exatamente quais linhas o cliente precisa corrigir!
- **Como rodar:**
  ```bash
  python core/scripts_comuns/inspecionar_insumos_governanca.py
  ```
  *(Ou digite `/inspecionar-governanca` no chat da IA).*

---

<a id="3-mapa-explicado"></a>
## 3. Mapa Explicado: O Que Cada Pasta, Script, Skill e Comando Faz

Para você nunca se perder navegando nas pastas do projeto, aqui está o dicionário completo de cada componente:

<a id="31-scripts-python"></a>
### 🛠️ 3.1 Os 14 Scripts Python em [`core/scripts_comuns/`](../../core/scripts_comuns/)
Estes scripts são seus melhores amigos. Eles podem ser executados diretamente no seu terminal a qualquer momento:

| Script Python | Para que serve? | Comando para rodar no terminal |
| :--- | :--- | :--- |
| **[`ajuda_ninho.py`](../../core/scripts_comuns/ajuda_ninho.py)** | **Central UX, Onboarding, Bússola, Oráculo, Doctor & Demo:** Fornece `/help`, `/comecar` (`--onboarding`), `/onde-estou` (`--onde-estou`), `/duvida` (`--explicar`), `/doctor` (`--doctor --corrigir`) e `/demo` (`--demo` / `--limpar-demo`). | `python core/scripts_comuns/ajuda_ninho.py --onboarding` |
| **[`simular_projeto.py`](../../core/scripts_comuns/simular_projeto.py)** | **Simulador & Blueprint 100% Editável:** Gera `SIMULACAO_BLUEPRINT_DW.md` e `SIMULACAO_BLUEPRINT_SEMANTICA.md` com prévia de dados e Radar da IA (`--acao simular`) e lê suas edições para gerar os arquivos físicos (`--acao executar`). | `python core/scripts_comuns/simular_projeto.py --modulo ambos --acao simular` |
| **[`melhorar_dw_existente.py`](../../core/scripts_comuns/melhorar_dw_existente.py)** | **Motor Fast-Track & Micro-Processos DW/ODI:** Gera comentários, dicionário HTML, índices, linha `-1`, constraints `NOVALIDATE`, selects ODI e Guia BI sem mexer na carga atual. | `python core/scripts_comuns/melhorar_dw_existente.py --modo tudo` |
| **[`modular_semantica.py`](../../core/scripts_comuns/modular_semantica.py)** | **Motor Modular da Camada Semântica:** Gera isoladamente ou em conjunto as Views analíticas (`views-dim`, `views-evento`, `views-kpi`), as 8 tabelas `META_*` (`catalogo-meta`) e segurança VPD (`rls`). | `python core/scripts_comuns/modular_semantica.py --modo tudo` |
| **[`validar_entrega.py`](../../core/scripts_comuns/validar_entrega.py)** | **Checklist Pré-Voo e Pós-Entrega:** Verifica se o formulário `INTAKE` foi preenchido (`all`), audita o modo `fast-track` e valida todos os scripts gerados em `saida/` (`saida`). | `python core/scripts_comuns/validar_entrega.py saida` |
| **[`testar_ninho.py`](../../core/scripts_comuns/testar_ninho.py)** | **Suíte Automatizada de Testes E2E:** Roda todas as baterias de ponta a ponta em poucos segundos numa cópia temporária do projeto (sandbox), certificando todos os motores sem tocar nos seus arquivos de `entrega/` e `saida/`. | `python core/scripts_comuns/testar_ninho.py` |
| **[`inspecionar_ddl_origem.py`](../../core/scripts_comuns/inspecionar_ddl_origem.py)** | **Leitor de Tabelas SQL (DDL):** Lê os arquivos `.sql` da origem, lista todas as colunas/tipos/PKs e sugere KPIs automaticamente. | `python core/scripts_comuns/inspecionar_ddl_origem.py` |
| **[`auditar_mapa_odi.py`](../../core/scripts_comuns/auditar_mapa_odi.py)** | **Auditor de ODI 12c:** Analisa XMLs ou pastas completas do ODI e aponta gargalos de performance e erros (`H1` a `H9`). | `python core/scripts_comuns/auditar_mapa_odi.py <pasta_odi>` |
| **[`auditar_esteira_hop.py`](../../core/scripts_comuns/auditar_esteira_hop.py)** | **Auditor de Apache Hop, FTPS e Python:** Analisa `.hpl`, `.hwf`, `.json`, `.py` e `.sh`, detectando senhas abertas e bugs (`HOP-H1` a `HOP-H8`). | `python core/scripts_comuns/auditar_esteira_hop.py <pasta_hop>` |
| **[`inspecionar_pbix.py`](../../core/scripts_comuns/inspecionar_pbix.py)** | **Desconstrutor de Power BI:** Abre arquivos `.pbix`, extrai DAX, relacionamentos, filtros visuais e aponta anti-padrões (`PBIX-H1` a `PBIX-H5`). | `python core/scripts_comuns/inspecionar_pbix.py <caminho_pbix>` |
| **[`inspecionar_insumos_governanca.py`](../../core/scripts_comuns/inspecionar_insumos_governanca.py)** | **Fiscal da Governança (Gate 0.5):** Audita planilhas `.xlsx` e `.csv` do cliente. Se houver falhas, gera o Relatório de Devolução; se aprovado, gera o DE/PARA MongoDB. | `python core/scripts_comuns/inspecionar_insumos_governanca.py` |
| **[`transicionar_dw_para_semantica.py`](../../core/scripts_comuns/transicionar_dw_para_semantica.py)** | **Ponte Automática DW $\rightarrow$ Semântica:** Pega tudo que foi gerado no DW e prepara automaticamente a entrada da Camada Semântica. | `python core/scripts_comuns/transicionar_dw_para_semantica.py --projeto <NOME>` |
| **[`gerar_mock_dados.py`](../../core/scripts_comuns/gerar_mock_dados.py)** | **Gerador Dinâmico de Dados de Teste BI:** Lê as tabelas reais do seu projeto e cria um CSV sintético com ~3% de chaves `-1` Kimball para o Power BI. | `python core/scripts_comuns/gerar_mock_dados.py --linhas 150` |
| **[`gerenciar_projeto.py`](../../core/scripts_comuns/gerenciar_projeto.py)** | **Empacotador e Limpador:** Mostra o status do workspace, exporta tudo em um arquivo `.zip` para entrega e limpa as pastas para o próximo projeto. | `python core/scripts_comuns/gerenciar_projeto.py --status` |

---

<a id="32-skills-ia"></a>
### 🧩 3.2 As 10 Skills da IA em [`.agents/skills/`](../../.agents/skills/)
Você **não precisa mexer** nessa pasta, mas é ótimo saber como ela funciona: em vez de a IA tentar saber tudo ao mesmo tempo e se confundir, o arquivo central [`AGENTS.md`](../../AGENTS.md) funciona como um **coordenador** que chama apenas o "especialista" (Skill) necessário para o seu pedido:

1. **`planejador-dw-oracle`:** Especialista em modelagem Kimball Star Schema, SCD Tipo 2, linha `-1`, índices Bitmap/B-Tree e tablespaces no Oracle.
2. **`gerador-consultas-odi`:** Especialista em ODI 12c (IKM, LKM, pacotes, procedures, cenários e tuning das heurísticas `H1` a `H9`).
3. **`gerador-etl-hop`:** Especialista em Apache Hop 2.x (`.hpl`, `.hwf`, telemetria `ETA_ETAPAS_CARGA`, `WorkflowLogging`, `TAB_*_ERRO` e heurísticas `HOP-H1` a `HOP-H8`).
4. **`extrator-api-python`:** Especialista em scripts Python para consumir APIs REST (OAuth2, paginação, escrita atômica `.tmp` $\rightarrow$ `.csv` e higienização de planilhas com quarentena `_REJEITADOS.csv`).
5. **`extrator-ftps-lote-hop`:** Especialista em buscar arquivos via FTPS/SFTP usando `curl` seguro e controlar modificação via `CONTROLE_MODIFICACAO_ARQUIVOS`.
6. **`engenharia-reversa-pbix`:** Especialista em traduzir relatórios `.pbix` legados em modelos Star Schema de DW e guias para analistas de BI.
7. **`camada-semantica-oracle`:** Especialista nas 3 camadas de Views semânticas e nas 8 tabelas `META_*` para IA e BI.
8. **`seguranca-rls-oracle`:** Especialista em segurança de linha no Oracle (`DBMS_RLS` / VPD e `SYS_CONTEXT`).
9. **`governanca-dados-corporativa`:** Especialista no padrão MongoDB PRODEB (`tb_dataset`, `tb_sem_dominios`, `tb_sem_conceitos`), LGPD/LAI e AWS SageMaker Catalog.
10. **`validador-qualidade-entrega`:** Especialista em rodar testes pré-voo e garantir que nenhum arquivo saia incompleto.

---

<a id="33-dicionario-comandos-chat"></a>
### 💬 3.3 Dicionário Completo de Comandos Rápidos do Chat (`/comando`)

Estes são todos os comandos rápidos que você pode digitar diretamente no chat com a IA. Você pode mandar **apenas o comando** (ex: `/comecar` ou `/onde-estou`) ou **o comando seguido de um tema ou caminho** (ex: `/duvida estrategia-carga` ou `/auditar-hop ideias/DGO`):

#### 🧭 Grupo 0 — Experiência Guiada, Onboarding, Bússola, Oráculo & Playground
*(Perfeitos para quem está abrindo o projeto pela primeira vez ou quer saber o próximo passo)*

| Comando no Chat | Quando Usar | O que a IA Executa por Trás | O que Você Recebe no Chat | Exemplo Prático de Uso no Chat |
| :--- | :--- | :--- | :--- | :--- |
| **`/comecar`** *(ou `/onboarding`)* | Na sua primeira vez usando o NINHO ou ao iniciar uma nova demanda. | Roda `ajuda_ninho.py --onboarding`. | As **5 trilhas guiadas em 3 passos** (*Onde soltar o arquivo* $\rightarrow$ *Comando para simular* $\rightarrow$ *Comando para gerar*) com links clicáveis. | `/comecar` |
| **`/onde-estou`** *(ou `/status`)* | A qualquer momento, para saber em que fase o projeto está e o que fazer agora. | Roda `ajuda_ninho.py --onde-estou`. | **Bússola Contextual** com barra de progresso (`[███░░] Fase X/5`), arquivos detectados em `entrega/` e `saida/` e recomendação do próximo comando. | `/onde-estou` |
| **`/duvida <tema>`** *(ou `/explicar`)* | Quando tiver qualquer dúvida técnica ou conceitual sobre o funcionamento do NINHO. | Roda `ajuda_ninho.py --explicar <tema>`. | Explicação didática com tabelas e exemplos sobre `estrategia-carga`, `scd`, `linha-default`, `camadas-views`, `arquitetura-etl`, `gate-governanca`, `simulacao`, `fast-track` ou `rls`. | `/duvida listar` ou `/duvida estrategia-carga` |
| **`/doctor`** | Se achar que soltou algum arquivo na pasta errada dentro de `entrega/`. | Roda `ajuda_ninho.py --doctor --corrigir`. | Detecta arquivos fora da subpasta canônica e os **move automaticamente** para a pasta certa (ex: `.sql` $\rightarrow$ `entrega/planejador_dw/ddl/`). | `/doctor` |
| **`/demo`** e **`/limpar-demo`** | Quando quiser ver o NINHO funcionando na prática sem precisar ter arquivos próprios. | Roda `ajuda_ninho.py --demo` (e `--limpar-demo`). | Cria um projeto completo de demonstração (*Licitações SAEB*) em 3 segundos (Blueprints + DW + Semântica + Dicionário HTML + Mock CSV BI) e depois limpa tudo com `/limpar-demo`. | `/demo` |
| **`/help`** *(ou `/help <topico>`)* | Quando quiser consultar a lista rápida de comandos disponíveis. | Roda `ajuda_ninho.py`. | Catálogo completo de comandos organizado por tópico (`ux`, `simulacao`, `micro`, `auditoria`, `dw`, `semantica`, `governanca`, `qualidade`). | `/help` ou `/help micro` |

#### 🔍 Grupo A — Inspeção de Fontes, Engenharia Reversa e Auditoria de Legado
*(Não exigem preenchimento prévio de formulário para diagnósticos pontuais)*

| Comando no Chat | Quando Usar | O que a IA Executa por Trás | O que Você Recebe no Chat | Exemplo Prático de Uso no Chat |
| :--- | :--- | :--- | :--- | :--- |
| **`/inspecionar-fontes`** | Assim que você colocar DDLs (`.sql`), CSVs ou JSONs em `entrega/planejador_dw/`. | Roda `inspecionar_ddl_origem.py` e analisa amostras e regras depositadas. | Inventário de tabelas, colunas, PKs, FKs, sugestão de CDC incremental e prévia do Radar de KPIs. | `/inspecionar-fontes` |
| **`/inspecionar-pbix`** | Quando você receber um arquivo `.pbix` do Power BI e quiser extrair medidas/regras ou migrá-lo para um DW. | Roda `inspecionar_pbix.py` e ativa a skill `engenharia-reversa-pbix`. | Todas as tabelas, medidas DAX, relacionamentos, filtros ocultos traduzidos e anti-padrões (`PBIX-H1` a `PBIX-H5`). | `/inspecionar-pbix entrega/planejador_dw/pbix/Painel.pbix` |
| **`/auditar-mapa-odi`** | Quando quiser revisar performance ou achar bugs em projetos do **ODI 12c** (`Mapas`, `Cenas`, `Pacotes`, `Procedures`, `Variaveis`). | Roda `auditar_mapa_odi.py` e ativa a skill `gerador-consultas-odi`. | Relatório das heurísticas `H1` a `H9` (Full scan, falta de PK, falso SCD2 `'X'`, `TRUNC` em datas) + SQL corrigido. | `/auditar-mapa-odi entrega/planejador_dw/odi` |
| **`/auditar-hop`** | Quando quiser revisar segurança e qualidade de esteiras **Apache Hop 2.x** (`.hpl`, `.hwf`, `.json`), scripts FTPS (`.sh`) e Python (`.py`). | Roda `auditar_esteira_hop.py` e ativa a skill `gerador-etl-hop`. | Diagnóstico das heurísticas `HOP-H1` a `HOP-H8` (senhas vazadas, copy-paste entre projetos, setas invertidas, caminhos sem `/`). | `/auditar-hop entrega/planejador_dw/hop` |
| **`/inspecionar-governanca`** | Assim que você depositar a planilha `.xlsx` e amostras `.csv` do cliente em `entrega/governanca_dados/`. | Roda `inspecionar_insumos_governanca.py` (Fiscal do **Gate 0.5**). | Se houver campos/LGPD em branco, gera o **Relatório de Devolução ao Cliente**; se 100% preenchido, gera a Matriz DE/PARA MongoDB. | `/inspecionar-governanca` |

#### 🧪 Grupo B — Simulação Editável, Modelagem Dimensional e Fast-Track do DW
*(Usados para simular, editar, construir um DW novo ou melhorar um DW já existente)*

| Comando no Chat | Quando Usar | O que a IA Executa por Trás | O que Você Recebe no Chat | Exemplo Prático de Uso no Chat |
| :--- | :--- | :--- | :--- | :--- |
| **`/simular-projeto`** *(ou `/simular-dw`, `/simular-semantica`)* | **Caminho Mais Fácil:** Após colocar o `.sql` de origem em `entrega/planejador_dw/ddl/`. | Roda `simular_projeto.py --modulo ambos --acao simular`. | Gera `SIMULACAO_BLUEPRINT_DW.md` e `SIMULACAO_BLUEPRINT_SEMANTICA.md` 100% editáveis com Matriz De/Para (`[x]`/`[ ]`), amostra de 3 linhas + `-1` e Radar da IA. | `/simular-projeto` |
| **`/executar-simulacao`** | Depois que você revisou/editou a Blueprint e marcou `[x] SIMULAÇÃO 100% FECHADA E APROVADA`. | Roda `simular_projeto.py --modulo ambos --acao executar`. | Lê todas as suas edições na Blueprint e gera todos os scripts SQL, Dicionário HTML, Guia BI, Views Semânticas e `META_*` em `saida/`. | `/executar-simulacao` |
| **`/melhorar-dw-existente`** | Quando você **já construiu** as tabelas `DIM_*` e `FATO_*` e quer apenas gerar melhorias sem tocar na carga. | Roda `melhorar_dw_existente.py --modo tudo` (Bypass automático do `INTAKE_DW.md`). | Gera patches `90_patch_comentarios`, `91_patch_ajustes_dim` (linha `-1`), `92_patch_tuning_constraints`, Dicionário HTML, Selects ODI e Guia BI. | `/melhorar-dw-existente` |
| **`/gerar-dicionario`** / **`/gerar-comentarios`** / **`/gerar-indices`** / **`/gerar-selects-odi`** / **`/gerar-mock-bi`** | Quando você quer rodar **apenas 1 micro-processo isolado** em segundos. | Roda `melhorar_dw_existente.py --modo <modo>` ou `gerar_mock_dados.py`. | Gera exclusivamente o artefato pedido em `saida/planejador_dw/`. | `/gerar-dicionario` ou `/gerar-mock-bi` |
| **`/desafiar-grao`** / **`/classificar-scd`** / **`/definir-estrategia-carga`** | Durante discussões arquiteturais sobre granularidade da Fato, histórico SCD2 ou Bitmap vs B-Tree. | Ativa `planejador-dw-oracle`. | Comparativo técnico justificado para tomada de decisão com o engenheiro. | `/definir-estrategia-carga` |
| **`/gerar-blueprint`** / **`/aprovar-blueprint`** / **`/auditar-ddl`** | Fluxo clássico via `INTAKE_DW.md` e auditoria sintática dos DDLs gerados. | Ativa `planejador-dw-oracle` e gera/audita as 11 pastas de `saida/planejador_dw/`. | Blueprint técnica no chat, geração física dos scripts e checklist de conformidade Oracle. | `/gerar-blueprint` |

#### 🧠 Grupo C — Handoff Contínuo, Camada Semântica e Governança Cloud
*(Usados para avançar do DW para a Camada Semântica ou gerar os pacotes de Governança)*

| Comando no Chat | Quando Usar | O que a IA Executa por Trás | O que Você Recebe no Chat | Exemplo Prático de Uso no Chat |
| :--- | :--- | :--- | :--- | :--- |
| **`/concluir-dw`** *(ou `/transicionar-semantica`)* | Assim que o DW estiver pronto e validado, para não precisar copiar arquivos manualmente para a Camada Semântica. | Roda `transicionar_dw_para_semantica.py`, consolida os DDLs, move amostras, preenche o `INTAKE_SEMANTICA.md` e atualiza o catálogo do projeto. | Confirmação de que toda a pasta `entrega/camada_semantica/` e o formulário já foram preparados automaticamente. | `/concluir-dw` |
| **`/iniciar-semantica`** *(ou `/gerar-views-semantica`, `/gerar-catalogo-meta`, `/gerar-rls`)* | Para gerar toda a Camada Semântica ou apenas um componente específico (Views, `META_*` ou RLS). | Roda `modular_semantica.py` e ativa `camada-semantica-oracle` / `seguranca-rls-oracle`. | Gera as Views em 3 camadas (`VW_DIM_*_ATUAL`, `VW_EVENTO_*`, `VW_KPI_*`), políticas RLS/VPD e os scripts DDL/MERGE das **8 tabelas `META_*`** em `saida/camada_semantica/`. | `/iniciar-semantica` |
| **`/gerar-governanca`** | Após os insumos do cliente passarem sem erros pelo `/inspecionar-governanca` (Gate 0.5 aprovado). | Ativa `governanca-dados-corporativa` e lê o `INTAKE_GOVERNANCA.md`. | Gera os scripts das 5 coleções MongoDB padrão PRODEB (`tb_dataset`, `tb_sem_dominios`, `tb_sem_conceitos`, etc.), matriz LGPD/LAI e artefatos para **AWS Glue & SageMaker Catalog** em `saida/governanca_dados/`. | `/gerar-governanca` |

#### ✅ Grupo D — Qualidade, Testes E2E, Operação em Produção e Empacotamento Final
*(Usados para validar entregas, rodar a suíte de testes E2E, investigar erros de carga no banco e exportar o `.zip` final)*

| Comando no Chat | Quando Usar | O que a IA Executa por Trás | O que Você Recebe no Chat | Exemplo Prático de Uso no Chat |
| :--- | :--- | :--- | :--- | :--- |
| **`/validar-entrega`** | Antes de começar (pré-voo) ou depois que a IA gerou todos os arquivos em `saida/`. | Roda `validar_entrega.py all`, `fast-track` ou `saida`. | Relatório de auditoria confirmando `[SUCESSO] 0 erros` ou apontando exatamente qual arquivo/regra precisa de ajuste. | `/validar-entrega` |
| **`/testar-ninho`** | Quando quiser testar se todos os motores Python da plataforma estão 100% íntegros. | Roda `testar_ninho.py` (9 suítes End-to-End automatizadas). | Executa os 9 testes em ~4 segundos e garante que o workspace termine com `0 arquivos residuais`. | `/testar-ninho` |
| **`/diagnosticar-erro-carga`** | Quando uma carga falhar em produção/homologação no Oracle, ODI ou Hop e você tiver a mensagem de erro (`ORA-xxxxx` ou log). | Analisa o erro contra as convenções do DW e esteiras ETL. | Causa raiz explicada, comando SQL/ETL de correção e passo a passo para reprocessar sem duplicar dados. | `/diagnosticar-erro-carga ORA-01654: unable to extend index` |
| **`/empacotar-projeto`** | Ao finalizar o projeto, para gerar o arquivo `.zip` de entrega e/ou limpar o workspace para o próximo cliente. | Roda `gerenciar_projeto.py --exportar` (e `--resetar` se solicitado). | Caminho do pacote `.zip` gerado em `pacotes_exportados/` e confirmação do status do workspace. | `/empacotar-projeto PROJETO_SSP` |

---

<a id="4-passo-a-passo"></a>
## 4. Passo a Passo: Sua Primeira Vez Usando o Projeto

Quer experimentar o NINHO agora mesmo sem errar? Siga este roteiro:

### 🎮 Passo 0 (Opcional — Recomendado na 1ª Vez!): Rode o Modo Playground (`/demo`)
Se você acabou de baixar o repositório e ainda não tem arquivos do seu projeto em mãos, digite no chat:
```text
/demo
```
*(Ou no terminal: `python core/scripts_comuns/ajuda_ninho.py --demo`)*.  
Em **3 segundos**, o NINHO cria um DDL de exemplo (*Licitações e Contratos Públicos*), gera as Blueprints de Simulação, constrói todos os scripts de DW e Camada Semântica, gera o **Dicionário de Dados HTML interativo** e cria um **CSV sintético para Power BI**. Depois de explorar os arquivos gerados, basta digitar **`/limpar-demo`** para deixar tudo limpo!

---

### 🏗️ Passo 1: Verifique onde você está (`/onde-estou`)
Antes de começar um projeto real, digite **`/onde-estou`** no chat (ou `python core/scripts_comuns/ajuda_ninho.py --onde-estou` no terminal) para ver a **Bússola Contextual** e confirmar que a bancada está na `Fase 0/5 — Workspace Limpo`.

### 📥 Passo 2: Coloque seus arquivos na pasta `entrega/` correspondente
- Vai criar ou melhorar um **DW**? Coloque seus `.sql` em [`entrega/planejador_dw/ddl/`](../../entrega/planejador_dw/ddl/).
- Vai fazer **Camada Semântica**? Coloque os DDLs do DW em [`entrega/camada_semantica/sql_fontes/`](../../entrega/camada_semantica/).
- Vai fazer **Governança**? Coloque a planilha `.xlsx` em [`entrega/governanca_dados/planilhas/`](../../entrega/governanca_dados/) e amostras `.csv` em [`entrega/governanca_dados/amostras/`](../../entrega/governanca_dados/).
- > 🩺 **Soltou o arquivo na pasta errada sem querer?** Sem problema! Digite **`/doctor`** no chat e o NINHO encontra o arquivo e o move automaticamente para a subpasta certa.

### 🧪 Passo 3: Simule, Edite a Blueprint e Gere os Arquivos!
Escolha o comando de acordo com a sua necessidade:
- **Se for criar um DW novo + Camada Semântica:** Digite **`/simular-projeto`**. Abra os arquivos `SIMULACAO_BLUEPRINT_DW.md` e `SIMULACAO_BLUEPRINT_SEMANTICA.md` gerados em `entrega/`, edite livremente colunas (`[x]`/`[ ]`), tipos, SCD e KPIs do Radar da IA, marque `[x] SIMULAÇÃO 100% FECHADA E APROVADA` e digite **`/executar-simulacao`**.
- **Se o DW já está construído no banco (Modo Fast-Track):** Digite direto **`/melhorar-dw-existente`** (ou apenas o micro-processo desejado, como `/gerar-dicionario`, `/gerar-indices` ou `/gerar-selects-odi`).
- **Se for auditar Governança (Gate 0.5):** Digite **`/inspecionar-governanca`**.

### ✅ Passo 4: Valide e Empacote sua Entrega
Assim que os arquivos forem gravados na pasta `saida/`, confira se está tudo perfeito e gere o pacote `.zip` final:
```bash
# 1. Valida se todos os artefatos obrigatórios foram gerados sem erros
python core/scripts_comuns/validar_entrega.py saida

# 2. Empacota tudo em um arquivo .zip limpo dentro da pasta pacotes_exportados/
python core/scripts_comuns/gerenciar_projeto.py --exportar MEU_PROJETO
```

---

<a id="5-faq"></a>
## 5. Perguntas Frequentes de Quem Está Começando (FAQ)

**1. "Estou com dúvida sobre um conceito do NINHO (ex: quando usar Estratégia A vs B, o que é a linha `-1` ou como funciona o SCD2). Onde pergunto?"**
> Digite **`/duvida listar`** diretamente no chat (ou `python core/scripts_comuns/ajuda_ninho.py --explicar listar`)! O **Oráculo de Arquitetura** do NINHO explica na hora qualquer um dos 9 temas essenciais (`estrategia-carga`, `scd`, `linha-default`, `camadas-views`, `arquitetura-etl`, `gate-governanca`, `simulacao`, `fast-track`, `rls`).

**2. "Eu já tenho meu DW construído (`DIM_*` e `FATO_*`) ou quero apenas auditar um mapa do ODI / Hop / `.pbix`. Preciso preencher o formulário `INTAKE_DW.md`?"**
> **Não!** Tanto as auditorias técnicas (`/auditar-mapa-odi`, `/auditar-hop`, `/inspecionar-pbix`), quanto a Simulação Editável (`/simular-projeto`) e o Modo Fast-Track (`/melhorar-dw-existente`, `/gerar-dicionario`, `/gerar-indices`, `/gerar-selects-odi`) possuem **Bypass Inteligente do Gate 0** e dispensam o preenchimento prévio do `INTAKE_DW.md`.

**3. "E se eu quiser tirar uma coluna ou mudar um KPI antes do NINHO gerar os scripts SQL?"**
> Basta rodar **`/simular-projeto`**! Ele cria os arquivos `SIMULACAO_BLUEPRINT_DW.md` e `SIMULACAO_BLUEPRINT_SEMANTICA.md`. Lá dentro, cada coluna e cada KPI sugerido pela IA tem um checkbox `[x]`. Se você mudar para `[ ]`, renomear uma coluna na tabela Markdown ou editar a fórmula SQL de um KPI, o comando **`/executar-simulacao`** vai ler exatamente o que você editou!

**4. "O Analista de Power BI também usa o NINHO?"**
> **Não.** O NINHO é exclusivo para a equipe de **Engenharia de Dados e Governança**. Porém, quando você gera um DW no NINHO, ele cria automaticamente o arquivo `saida/planejador_dw/08_datasets_bi/GUIA_ANALISTA_BI_<PROJETO>.md` (com todas as medidas DAX prontas e o desenho do Star Schema) e, se você rodar `/gerar-mock-bi`, gera também o `mock_dados_bi.csv` com dados sintéticos e chaves `-1` para o Analista de BI já ir montando o painel antes mesmo da carga oficial terminar.

**5. "Onde encontro uma cola rápida de todos os comandos SQL, Python, Hop e ODI?"**
> Digite **`/help`** no chat a qualquer momento ou acesse o [**Guia Central de Comandos Rápidos & Cheat Sheet (`GUIA_COMANDOS_RAPIDOS.md`)**](GUIA_COMANDOS_RAPIDOS.md).

---

### 🔗 Próximas Leituras Recomendadas (Aprofundamento por Módulo)

Quando quiser se aprofundar nos detalhes técnicos de cada módulo específico, consulte:
- 📘 [**Guia Detalhado do Engenheiro de DW**](GUIA_ENGENHEIRO_DW.md)
- 🧠 [**Guia Detalhado da Camada Semântica**](GUIA_ENGENHEIRO_SEMANTICA.md)
- 🛡️ [**Manual de Governança de Dados (MongoDB & SageMaker)**](../../modulos/governanca_dados/README.md)
- ⚡ [**Cheat Sheet de Comandos Rápidos**](GUIA_COMANDOS_RAPIDOS.md)
- 📖 [**Glossário de Termos Técnicos (SCD2, Linha -1, Star Schema)**](../GLOSSARIO.md)


