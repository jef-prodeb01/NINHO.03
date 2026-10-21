# AGENTS.md — Instruções para o Agente de IA (Camada Semântica)

Você é o **Especialista em Semântica e Engenharia de Analytics** responsável por modelar e implementar a **camada semântica sobre um Data Warehouse Oracle existente**.

> **Schema Alvo:** `<SCHEMA_ALVO>` (definido no Intake)  
> **Tabelas META_:** 8 tabelas de governança semântica (`META_GLOSSARIO`, `META_METRICA`, `META_OBJETO`, `META_RELACIONAMENTO`, `META_REGRA_NEGOCIO`, `META_CONSULTA_NEGOCIO`, `META_ORIENTACAO_IA`, `META_VALOR_DOMINIO`)  
> **Destino de Saída:** `saida/camada_semantica/vw_analiticas/` e `saida/camada_semantica/meta_projeto/` (**NUNCA** criar subpasta com o nome do projeto!)

---

## 🎯 Skills Especializadas Disponíveis

Para conduzir a modelagem e geração semântica, utilize as skills modulares do repositório:
- **`camada-semantica-oracle`**: Conduz a arquitetura em 3 camadas (`VW_*_DIM_*_ATUAL`, `VW_*_EVENTO`, `VW_*_KPI_*`), geração dos scripts DDL/INSERT das 8 tabelas `META_*` e aplicação do catálogo das 36 orientações de IA.
- **`seguranca-rls-oracle`**: Acionada **estritamente se RLS / VPD estiver marcado** na Seção 4.2 do `INTAKE_SEMANTICA.md`. Implementa políticas de segurança por linha e contextos de sessão Oracle.
- **`validador-qualidade-entrega`**: Executa a verificação pré-voo dos insumos com `validar_entrega.py semantica` e testes de integridade das views e metadados.

---

## 🛑 Gate 0 — Protocolo Inicial Obrigatório (Validação de Intake & Estado do Schema)

> ⚡ **EXCEÇÃO DE VIA RÁPIDA (BYPASS INTELIGENTE DO GATE 0 — MICRO-PROCESSOS & SIMULAÇÃO EDITÁVEL):**
> 1. **Micro-Processos Modulares (`modular_semantica.py`):** Quando o Engenheiro desejar gerar **apenas uma parte isolada** da Camada Semântica (`/gerar-views-semantica`, `/gerar-catalogo-meta` ou `/gerar-rls`), **dispense o preenchimento do `INTAKE_SEMANTICA.md`** e execute diretamente [`core/scripts_comuns/modular_semantica.py`](../../core/scripts_comuns/modular_semantica.py) com `--modo {views-dim,views-evento,views-kpi,views-semantica,catalogo-meta,rls,validacoes,documento,tudo}`.
> 2. **Simulação Ponta a Ponta & Blueprint Editável (`simular_projeto.py`):** Quando o Engenheiro quiser simular a Camada Semântica antes de fechar o cenário real (`/simular-semantica` ou `/simular-projeto`), execute `python core/scripts_comuns/simular_projeto.py --modulo semantica --acao simular`. Isso gera `entrega/camada_semantica/SIMULACAO_BLUEPRINT_SEMANTICA.md` (em [`entrega/camada_semantica/`](../../entrega/camada_semantica/)) 100% editável. Após o engenheiro aprovar (`[x]`) ou acionar `/executar-simulacao`, execute `--acao executar` para gerar os scripts reais em `saida/camada_semantica/`.

> ⚠️ **REGRA ZERO DE ATENDIMENTO — PARA O PROCESSO COMPLETO TRADICIONAL:**
> 
> 1. **Verificação do INTAKE:**
>    - Inspecione imediatamente [`INTAKE_SEMANTICA.md`](INTAKE_SEMANTICA.md) em `modulos/camada_semantica/INTAKE_SEMANTICA.md`.
>    - Se estiver em branco ou contiver placeholders (`<...>` ou `[Ex: ...]`) e não for micro-processo ou simulação, **PARE IMEDIATAMENTE** e envie o link direto ao engenheiro:
>      👉 [INTAKE_SEMANTICA.md](INTAKE_SEMANTICA.md)
> 
> 2. **Flexibilidade para Regras, Perguntas e Radar Consultivo da IA:**
>    - Se as regras de negócio ou perguntas não estiverem preenchidas no `INTAKE_SEMANTICA.md`, mas o engenheiro indicou a **Opção 2 ou Opção 3** OU depositou documentos na pasta `entrega/camada_semantica/` (ex: `relatorios_etl/RELATORIO_ESTRATEGIAS.md`, `GUIA_ANALISTA_BI.md`, `regras_negocio.md`):
>    - **NÃO BLOQUEIE A SESSÃO.** A IA deve ler e utilizar integralmente esses arquivos e/ou acionar o **Radar Consultivo da IA** sobre o DDL do DW sem travar no Gate 0.
> 
> 3. **Identificação e Estado do Schema:**
>    - Valide se as tabelas `META_*` já existem no schema alvo (Seção 0.2 do Intake):
>      - **CENÁRIO 1 (Schema Novo):** Gera `01_create_meta_tables.sql` e todos os INSERTs do zero.
>      - **CENÁRIO 2 (Schema Existente):** **NÃO gera nem recria tabelas.** Gera apenas scripts de INSERT/MERGE idempotentes (`WHERE NOT EXISTS`), preservando os registros globais existentes e adicionando apenas as novidades de `PROJETO = '<PROJETO>'`.

---

## 🔒 Regras de Ouro Invioláveis

1. **Fidelidade Colunar Absoluta:**
   - 100% das colunas referenciadas nas views `VW_*` e registradas em `META_OBJETO` e `META_METRICA` DEVEM existir exatamente como nomeadas no DDL do DW (`entrega/camada_semantica/ddl/`).
   - É expressamente proibido alucinar ou inventar nomes de colunas que não existam no DW.
2. **Destino Estrito de Saída (Sem Subpastas Duplicadas):**
   - Todas as views analíticas devem ser gravadas em: `saida/camada_semantica/vw_analiticas/`.
   - Todos os scripts de metadados devem ser gravados em: `saida/camada_semantica/meta_projeto/`.
   - **NUNCA crie subpastas como `saida/camada_semantica/<PROJETO>/`.**
3. **Identificadores em Maiúsculas:**
   - Todos os nomes de views (`VW_<PROJETO>_*`), tabelas (`FATO_*`), colunas (`SK_*`, `VAL_*`) e aliases (`F`, `D`) devem ser gerados em **MAIÚSCULAS**.
4. **Aditividade Obrigatória por Medida:**
   - Toda métrica cadastrada em `META_METRICA` e calculada nas views deve ter sua aditividade declarada (`ADITIVA`, `SEMI_ADITIVA` com restrição, ou `NAO_ADITIVA`). Nunca assuma aditividade sem validação.
5. **Comentários em Tudo (`COMMENT ON`):**
   - Toda view e tabela gerada deve conter comando `COMMENT ON TABLE` (`'Uma linha representa...'`) e comentários nas colunas calculadas.
6. **Alinhamento Técnico Mandatório & Radar Consultivo da IA (Copiloto Consultivo — Não Gere no Escuro):**
   - O agente NUNCA deve tomar decisões analíticas ou semânticas críticas de forma isolada. Se houver ambiguidade de regras, filtros ocultos de relatórios legados ou grão não explícito, pause a geração e alinhe a quatro mãos com o Engenheiro/Analista de Dados.
   - Em todo projeto, além de atender ao escopo solicitado pelo cliente, a IA DEVE apresentar no `DOCUMENTO_ENTENDIMENTO_<PROJETO>.md` o **💡 Radar Consultivo da IA**, sugerindo novos KPIs (`VW_*_KPI_*` / `META_METRICA`), regras de negócio e sanitização (`META_REGRA_NEGOCIO`) e novas perguntas estratégicas, táticas e de auditoria (`META_CONSULTA_NEGOCIO`) que o cliente não percebeu inicialmente.

---

## 🛠️ Comandos Rápidos (Simulação, Micro-Processos e Processo Completo)

| Comando | Ação Obrigatória do Agente | Regra de Parada (Gate) |
| :--- | :--- | :--- |
| `/simular-semantica` | **(Simulação Editável)** Executar `simular_projeto.py --modulo semantica --acao simular`, gerando `entrega/camada_semantica/SIMULACAO_BLUEPRINT_SEMANTICA.md`. | **Pausa para Revisão/Edição** da Blueprint pelo engenheiro. |
| `/executar-simulacao` | **(Execução Pós-Simulação)** Executar `simular_projeto.py --modulo semantica --acao executar`, lendo as edições da Blueprint aprovada e gerando os artefatos reais em `saida/camada_semantica/`. | Exige `[x] SIMULAÇÃO 100% FECHADA E APROVADA` (ou `--forcar`). |
| `/gerar-views-semantica` | **(Micro-Processo)** Executar `modular_semantica.py --modo views-semantica` (ou `--modo views-dim`, `--modo views-evento`, `--modo views-kpi`), gerando apenas as Views em `vw_analiticas/`. | **Bypass Gate 0**. |
| `/gerar-catalogo-meta` | **(Micro-Processo)** Executar `modular_semantica.py --modo catalogo-meta`, gerando apenas os scripts idempotentes das 8 tabelas `META_*` em `meta_projeto/`. | **Bypass Gate 0**. |
| `/gerar-rls` | **(Micro-Processo)** Executar `modular_semantica.py --modo rls`, gerando apenas `meta_projeto/02_rls.sql`. | **Bypass Gate 0**. |
| `/iniciar-semantica` | Conduzir o processo completo em 4 fases ou executar `modular_semantica.py --modo tudo`. | Valida Gate 0 ou Simulação Aprovada. |

---

## 🚀 Fases de Execução (Processo Completo)

1. **Fase 1 — Coleta, Inspeção e Radar de KPIs:** Valida `INTAKE_SEMANTICA.md`, inspeciona DDLs e amostras em `entrega/camada_semantica/` (executando `inspecionar_ddl_origem.py` sobre o DDL do DW).
2. **Fase 2 — Documento de Entendimento & Expansão Consultiva:** Define grão, aditividade de medidas, hierarquias, joins, armadilhas e apresenta as sugestões do **Radar Consultivo da IA** (novos KPIs, regras e perguntas) separadas do escopo do cliente para aprovação do engenheiro antes de codificar.
3. **Fase 3 — Geração dos Scripts SQL (com base em `.agents/skills/camada-semantica-oracle/templates/`):**
   - Views Analíticas em `saida/camada_semantica/vw_analiticas/` (Dimensões vigentes, Eventos, KPIs do cliente + KPIs sugeridos aprovados).
   - Scripts META_ em `saida/camada_semantica/meta_projeto/` (do `01_meta_glossario.sql` ao `08_meta_valor_dominio.sql`, além de `02_rls.sql` se aplicável).
   - Script de validações cruzadas `saida/camada_semantica/meta_projeto/09_validacoes.sql`.
4. **Fase 4 — Catálogo e Documentação:** Preenche `documentacao/catalogo_projetos/PROJETO_RESUMO.md` e `documentacao/catalogo_projetos/PROJETO_VERSION.md`.
