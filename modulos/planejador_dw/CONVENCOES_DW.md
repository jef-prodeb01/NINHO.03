# CONVENCOES_DW.md — Padrões e Convenções de Modelagem Dimensional

> **Documento Oficial Central:** Consulte o documento normativo completo em [`../../core/convencoes/CONVENCOES_DW.md`](file:///c:/Users/jeferson.ressurreica/Downloads/Projetos/Interno/Semantica/template/core/convencoes/CONVENCOES_DW.md).

Este documento resume as regras inegociáveis do **Planejador de DW** para o Engenheiro de Dados e a IA:

---

## 1. Regras Inegociáveis do Pipeline

### 1.1 Fidelidade 100% aos Nomes de Coluna da Origem (Zero Alucinação)
- **NUNCA** alterar, abreviar ou inventar nomes de colunas presentes no DDL de origem (`ddl_origem.sql` ou `ddl_completo.csv`).
- Se a coluna na origem chama-se `ID_CHAMADO`, seu nome no DW é `ID_CHAMADO` (e não `NUM_CHAMADO`).
- Se a coluna na origem chama-se `INDICADOR`, seu nome no DW é `INDICADOR` (e não `IND_STATUS`).
- As únicas colunas com nomes padronizados introduzidas pelo framework são as colunas técnicas dimensionais Kimball (`DIMENSION_KEY`, `DTC_EFETIVACAO`, `DTC_EXPIRACAO`, `SIN_ATIVO`, `DES_ATUALIZAR`, `DTC_CARGA`).

### 1.2 Disciplina Estrita de Pastas de Saída (Sem Subpastas de Projeto)
- Todos os arquivos gerados DEVEM ser salvos diretamente dentro das 11 pastas numeradas em `saida/planejador_dw/`:
  - `01_controle_carga/`
  - `02_staging/`
  - `03_dimensoes/`
  - `04_fatos/`
  - `05_procedimentos_manutencao/`
  - `06_pipelines_hop/` (se aplicável)
  - `07_extratores_python/` (se aplicável)
  - `08_datasets_bi/`
  - `09_relatorio_estrategias/`
  - `10_testes_integridade/`
  - `11_dicionario_dados/`
- **PROIBIDO** criar pastas com o nome do projeto (ex: `saida/planejador_dw/<PROJETO>/`).

### 1.3 Geração Condicional de Tecnologias
- O agente SOMENTE pode gerar código e pipelines para as tecnologias marcadas com `[x]` na Seção 1 do [`INTAKE_DW.md`](INTAKE_DW.md).
- Se **Apache Hop** NÃO for marcado, `06_pipelines_hop/` permanece apenas com `.gitkeep`.
- Se **Python (API)** NÃO for marcado, `07_extratores_python/` permanece apenas com `.gitkeep`.

---

## 2. Nomenclatura e Padrões Oracle

- **Caixa Alta Obrigatória:** Todos os nomes de tabelas, colunas, constraints, índices e procedures devem ser em **MAIÚSCULAS**.
- **Prefixos de Tabelas:**
  - `TB_CONTROLE_CARGA`: Auditoria central
  - `STG_<SISTEMA>_<DOMINIO>_<NOME>`: Aterrissagem
  - `ODI_DIM_<SISTEMA>_<DOMINIO>_<NOME>`: Auxiliar do módulo Dimensões e Cubos do ODI (sem constraints)
  - `DIM_<SISTEMA>_<DOMINIO>_<NOME>`: Dimensão oficial com SCD Tipo 2 e Surrogate Key (`DIMENSION_KEY`)
  - `DIM_TEMPO`: Dimensão conformada de calendário
  - `FATO_<SISTEMA>_<DOMINIO>_<NOME>`: Fato analítica com FKs `NOT NULL`
- **Índices em Dimensões:** **EXCLUSIVAMENTE B-TREE**. É terminantemente proibido criar índice Bitmap em tabelas Dimensão (risco de deadlock `ORA-00060`).
- **Registro Padrão `-1`:** Toda dimensão DEVE conter a linha `-1` (`NAO INFORMADO`) para evitar violação de FK no ETL.
- **FKs da Fato:** Nenhuma FK pode aceitar nulo. Utilizar `NVL(LOOKUP.DIMENSION_KEY, -1)`.

---

## 3. Gestão de Tablespace e Tuning

- **Tablespaces Separadas:** Sempre que possível, separar tabelas (`TABLESPACE "<SCHEMA>_DATA"`) e índices (`TABLESPACE "<SCHEMA>_INDEX"`).
- **Tablespace Única:** Em schemas com tablespace única (ex: `SEIMUNICIPIO_DATA`), limitar índices aos estritamente necessários para não esgotar a cota.
- **Estratégia A (Truncate & Load):** Índices BITMAP apenas nas FKs e colunas de baixa cardinalidade da Fato. Executar `PRC_POS_CARGA_FATO` com rebuild `NOLOGGING` e `DBMS_STATS(CASCADE => TRUE)`.
- **Estratégia B (MERGE Incremental):** Índices B-Tree compostos nas chaves do `ON (...)`. Índices Bitmap proibidos.

