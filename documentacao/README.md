# Documentação & Governança Consolidada

Este diretório reúne todos os manuais, checklists de qualidade e a documentação histórica dos projetos atendidos pela plataforma.

---

## 📁 Estrutura do Diretório

- **`guias/`**
  - 👋 [**`GUIA_INICIAL_ENGENHEIRO.md`**](guias/GUIA_INICIAL_ENGENHEIRO.md): **Guia de Boas-Vindas & Onboarding para Iniciantes**. Explica de forma acessível como o projeto funciona, os atalhos conversacionais de UX (`/comecar`, `/demo`, `/onde-estou`, `/duvida`, `/doctor`, `/help`), os 7 cenários práticos de uso (incluindo Simulação Editável e Modo Fast-Track), o que cada pasta/script/skill faz e como executar a primeira tarefa passo a passo.
  - ⚡ [**`GUIA_COMANDOS_RAPIDOS.md`**](guias/GUIA_COMANDOS_RAPIDOS.md): **Central Oficial de Comandos Rápidos & Cheat Sheet**. Possui sumário interativo 100% ancorado cobrindo o Catálogo do Chat (`/help`), Assistente de Onboarding (`/comecar`), Simulador de Blueprints Editáveis (`simular_projeto.py`), Micro-Processos Independentes (`melhorar_dw_existente.py` e `modular_semantica.py`), DDLs/DMLs do DW, Views e Catálogo das 8 tabelas `META_*`, Apache Hop CLI, Shell/ODI, diagnósticos de DBA no Oracle e fórmulas DAX.
  - 📘 [**`GUIA_ENGENHEIRO_DW.md`**](guias/GUIA_ENGENHEIRO_DW.md): Manual operacional passo a passo para o engenheiro utilizar o módulo Planejador de DW, incluindo comandos ODI, Hop, Python e queries de validação.
  - 🧠 [**`GUIA_ENGENHEIRO_SEMANTICA.md`**](guias/GUIA_ENGENHEIRO_SEMANTICA.md): Manual operacional para o módulo Camada Semântica e Metadados Ativos.
  - 📊 [**`GUIA_ANALISTA_BI.md`**](guias/GUIA_ANALISTA_BI.md): Especificação e padrão corporativo de handoff para Business Intelligence (Power BI, DAX canônico, Star Schema e Calendário) que orienta a geração do entregável do DW para a equipe externa de BI.
- **`GLOSSARIO.md`**: Glossário conceitual unificado de Engenharia de Dados, DW e Analytics (SCD2, VertiPaq, Linha -1, Star Schema, Dual Strategy).
- **`checklists/`**
  - **`CHECKLIST_VALIDACAO.md`**: Checklist de integridade e qualidade para validação pré-entrega e pós-execução no banco.
- **`catalogo_projetos/`**
  - **`PROJETO_RESUMO.md`**: Ficha técnica viva do projeto atual (fonte única da verdade de esquemas, medidas e regras).
  - **`PROJETO_VERSION.md`**: Registro de versionamento e histórico de alterações incrementais.

