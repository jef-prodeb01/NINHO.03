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

> ⚠️ **REGRA ZERO DE ATENDIMENTO — ANTES DE QUALQUER AÇÃO OU GERAÇÃO:**
> 
> 1. **Verificação do INTAKE:**
>    - Inspecione imediatamente [`INTAKE_SEMANTICA.md`](INTAKE_SEMANTICA.md) em `modulos/camada_semantica/INTAKE_SEMANTICA.md`.
>    - Se estiver em branco ou contiver placeholders (`<...>` ou `[Ex: ...]`), **PARE IMEDIATAMENTE** e envie o link direto ao engenheiro:
>      👉 [INTAKE_SEMANTICA.md](file:///c:/Users/jeferson.ressurreica/Downloads/Projetos/Interno/Semantica/template/modulos/camada_semantica/INTAKE_SEMANTICA.md)
> 
> 2. **Flexibilidade para Regras e Perguntas na Pasta Entrega:**
>    - Se as regras de negócio ou perguntas não estiverem preenchidas no `INTAKE_SEMANTICA.md`, mas o engenheiro indicou arquivos ou depositou documentos na pasta `entrega/camada_semantica/` (ex: `relatorios_etl/RELATORIO_ESTRATEGIAS.md`, `GUIA_ANALISTA_BI.md`, `regras_negocio.md`):
>    - **NÃO BLOQUEIE A SESSÃO.** A IA deve ler e utilizar integralmente esses arquivos sem travar no Gate 0.
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
   - Toda view e tabela gerada deve conter comando `COMMENT ON TABLE` e comentários nas colunas calculadas.

---

## 🚀 Fases de Execução

1. **Fase 1 — Coleta e Inspeção:** Valida `INTAKE_SEMANTICA.md`, inspeciona DDLs e amostras em `entrega/camada_semantica/`.
2. **Fase 2 — Documento de Entendimento:** Define grão, aditividade de medidas, hierarquias, joins e armadilhas. Valida com o engenheiro antes de codificar.
3. **Fase 3 — Geração dos Scripts SQL:**
   - Views Analíticas em `saida/camada_semantica/vw_analiticas/` (Dimensões vigentes, Eventos, KPIs).
   - Scripts META_ em `saida/camada_semantica/meta_projeto/` (do `01_meta_glossario.sql` ao `08_meta_valor_dominio.sql`).
   - Script de validações cruzadas `09_validacoes.sql`.
4. **Fase 4 — Catálogo e Documentação:** Preenche `documentacao/catalogo_projetos/PROJETO_RESUMO.md` e `PROJETO_VERSION.md` com base nos modelos de `templates/`.
