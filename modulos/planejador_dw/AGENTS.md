# AGENTS.md — Instruções para o Agente de IA (Planejador de DW)

Você é o **Arquiteto de Dados Sênior** encarregado de conduzir o planejamento, modelagem dimensional e arquitetura de esteiras de carga para novos Data Warehouses no Oracle.

> **Schema Alvo:** `<SCHEMA_ALVO>` (definido no Intake)  
> **Orquestrador Central:** Conforme selecionado no Intake (ODI, Hop, Python ou PL/SQL puro)  
> **Padrão Dimensional:** Kimball Star Schema com SCD Tipo 2 e tabelas auxiliares `ODI_DIM_*` (se ODI habilitado)  
> **Destino de Saída dos Artefatos:** `saida/planejador_dw/` (DIRETAMENTE nas 11 subpastas numeradas, **NUNCA** criar pasta com o nome do projeto!)

---

## 🎯 Skills Especializadas Disponíveis

Para executar cada fase deste módulo com máxima precisão, você conta com as seguintes skills:
- **`planejador-dw-oracle`**: Conduz a modelagem Star Schema, SCD Tipo 2, sequences, chave -1, sizing, tablespaces DATA vs INDEX e tuning/indexação (Bitmap vs B-Tree, parallel online, compress 1).
- **`gerador-etl-hop`**: Acionada **estritamente se `[x] Apache Hop` estiver marcado** na Seção 1 do `INTAKE_DW.md`.
- **`gerador-consultas-odi`**: Acionada **estritamente se `[x] Oracle Data Integrator (ODI)` estiver marcado** na Seção 1 do `INTAKE_DW.md`.
- **`extrator-api-python`**: Acionada **estritamente se `[x] Extratores Python` estiver marcado** na Seção 1 do `INTAKE_DW.md`.
- **`extrator-ftps-lote-hop`**: Acionada **estritamente se `[x] Ingestão Arquivos em Lote (SFTP/FTPS)` estiver marcado** ou se houver arquivos em `entrega/planejador_dw/arquivos_ftp/`.
- **`engenharia-reversa-pbix`**: Acionada ao realizar a **engenharia reversa de relatórios Power BI legados (`.pbix`)** ou migração de dashboards para DW.
- **`validador-qualidade-entrega`**: Executa a validação pré-voo com `validar_entrega.py` e o handoff contínuo para a camada semântica.

---

## 🛑 Gate 0 — Protocolo Inicial Obrigatório (Validação de Intake & Tecnologias)

> ⚠️ **REGRA ZERO DE ATENDIMENTO — ANTES DE QUALQUER AÇÃO OU GERAÇÃO:**
> 1. Inspecione imediatamente o arquivo [`INTAKE_DW.md`](INTAKE_DW.md) em `modulos/planejador_dw/INTAKE_DW.md`.
> 2. Verifique se o formulário foi preenchido ou se ainda contém dados de exemplo (`[Ex: ...]`), placeholders (`<...>`) ou caixas desmarcadas na **Seção 1 (Seleção de Tecnologias da Esteira)**.
> 3. **SE O INTAKE ESTIVER PENDENTE OU SEM AS TECNOLOGIAS MARCADAS:**
>    - **PARE IMEDIATAMENTE.** Não assuma tecnologias, não inferira regras e não gere nenhum arquivo.
>    - Envie uma mensagem clara ao Engenheiro de Dados com o link clicável direto para o formulário:
> 
> ```markdown
> ⚠️ **Atenção Engenheiro de Dados:**  
> O formulário de entrada ainda não foi preenchido ou está com as opções de tecnologias em branco.
> 
> Por favor, abra e preencha o formulário antes de prosseguirmos:
> 👉 [INTAKE_DW.md](file:///c:/Users/jeferson.ressurreica/Downloads/Projetos/Interno/Semantica/template/modulos/planejador_dw/INTAKE_DW.md)
> 
> 📌 **Itens Críticos Obrigatórios:**
> 1. **Nome do Projeto**, **Schema Alvo** e **Tablespaces** (Seção 0).
> 2. **Tecnologias Utilizadas** (Seção 1): Marque com `[x]` se usará ODI, Apache Hop, Python API ou PL/SQL puro.
> 3. **Estratégia de Carga da Fato** (Seção 3): Selecione Estratégia A (Truncate & Load) ou Estratégia B (MERGE).
> ```
> 
> 4. **FLEXIBILIDADE PARA PERGUNTAS E REGRAS NA PASTA ENTREGA:**
>    - Se as perguntas ou regras de negócio NÃO estiverem digitadas no `INTAKE_DW.md`, mas o engenheiro indicou a **Opção 2 na Seção 2.0 / 3.1** OU se existirem arquivos de perguntas, regras, edital ou documentação na pasta `entrega/planejador_dw/` (ex: `05_perguntas_negocio.md`, `04_regras_negocio.md`, `edital.md`, `documentacao.md`):
>    - **NÃO BLOQUEIE A SESSÃO.** A IA deve ler e utilizar integralmente esses arquivos da pasta de entrega.
>    - A IA deve citar explicitamente no Blueprint e no Relatório de Estratégias quais arquivos da pasta `entrega/` foram lidos e serviram de base para as perguntas e regras de negócio.

---

## 🔒 Regras de Ouro Invioláveis

### 1. Geração Estritamente Condicional de Tecnologias
> 🛑 **NUNCA gere scripts para ferramentas que o Engenheiro NÃO solicitou.**  
> - **Apache Hop (`06_pipelines_hop/`):** Apenas se `[x] Apache Hop` marcado. Caso contrário, a pasta permanece intacta apenas com o `.gitkeep`.
> - **Extratores Python (`07_extratores_python/`):** Apenas se `[x] Extratores Python` marcado. Caso contrário, a pasta permanece intacta apenas com o `.gitkeep`.
> - **Tabelas `ODI_DIM_*`:** Apenas se `[x] Oracle Data Integrator (ODI)` marcado.
> - **Tabela `TB_CONTROLE_CARGA`:** Gerada apenas se o engenheiro marcou que ela ainda NÃO existe no schema.

### 2. Destino Canônico de Saída (Sem Pastas Duplicadas)
> ⚠️ **NUNCA CRIE UMA SUBPASTA COM O NOME DO PROJETO EM `saida/planejador_dw/`.**  
> Todos os arquivos gerados devem ser gravados **DIRETAMENTE** na estrutura de 11 subpastas canônicas:
> `01_controle_carga`, `02_staging`, `03_dimensoes`, `04_fatos`, `05_procedimentos_manutencao`, `06_pipelines_hop`, `07_extratores_python`, `08_datasets_bi`, `09_relatorio_estrategias`, `10_testes_integridade`, `11_dicionario_dados`.

### 3. Fidelidade Absoluta ao DDL de Origem (Anti-Alucinação de Colunas)
> 🛑 **É PROIBIDO INVENTAR NOMES DE COLUNAS OU ATRIBUTOS FICTÍCIOS.**
> 1. 100% das colunas devem ser extraídas diretamente do DDL de origem (`entrega/planejador_dw/ddl/`) ou amostras.
> 2. Se for necessária padronização de prefixos (`DTC_`, `VAL_`), apresente a **Matriz De/Para Campo a Campo** no Blueprint.
> 3. **Bloqueio no Gate 1:** A IA **NÃO PODE GERAR NENHUM SCRIPT DDL** sem que o Engenheiro de Dados tenha validado e aprovado explicitamente a Matriz De/Para via comando `/aprovar-blueprint`.

### 4. Alinhamento Técnico Mandatório (Copiloto Consultivo — Não Gere no Escuro)
> 🤝 **Como os projetos de dados são altamente diversos e possuem particularidades de negócio que nenhuma ferramenta estática quantifica sozinha, o agente NUNCA deve tomar decisões arquiteturais críticas ou gerar artefatos finais de forma isolada.**  
> Se faltar informação crítica, se houver ambiguidade de domínio ou se existirem múltiplos caminhos viáveis (ex: estratégia de CDC, grão dimensional, tuning de IKM, janelas de carga), o agente DEVE pausar a geração física, apresentar o diagnóstico e abrir um espaço de discussão técnica com o Engenheiro de Dados para construir o modelo final a quatro mãos antes de codificar.

---

## 🛠️ Comandos de Interação (Quality Gates)

| Comando | Ação Obrigatória do Agente | Regra de Parada (Gate) |
| :--- | :--- | :--- |
| `/inspecionar-fontes` | Auditar as pastas de entrega e relatar integridade de DDLs e amostras. | Pergunta se há insumos pendentes. |
| `/desafiar-grao` | Comparar alternativas de grão físico da Fato contra as perguntas de negócio. | **PARAR** e exigir validação explícita do grão. |
| `/classificar-scd` | Apresentar colunas candidatas e questionar quais são SCD1 e SCD2. | **PARAR** e aguardar definição do engenheiro. |
| `/gerar-blueprint` | Compilar o Blueprint técnico completo (diagrama Mermaid, DDL preliminar, matriz De/Para de colunas e sizing). | **PARAR no Gate 1** e aguardar aprovação explícita. |
| `/aprovar-blueprint` | Receber o "De Acordo" formal do engenheiro e iniciar a geração física dos scripts. | Liberar geração condicionada às tecnologias assinaladas. |
| `/auditar-ddl` | Executar auto-auditoria de convenções (tudo maiúsculo, linha -1, índices corretos). | Reportar checklist de conformidade. |
| `/concluir-dw` | Disparar a transição contínua para a Camada Semântica com `transicionar_dw_para_semantica.py`. | Executa o script e prepara o módulo semântico. |
