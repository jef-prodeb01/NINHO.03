# NINHO — Plataforma de Engenharia, Modelagem & Governança de Dados

> *"Onde os dados brutos são acolhidos, cuidados e preparados para ganhar asas."*

Bem-vindo ao **NINHO**, um framework corporativo para automação de engenharia de dados, modelagem dimensional em Data Warehouse (Oracle), geração de camadas semânticas para IAs analíticas e governança de dados em nuvem.

---

## 🏛️ Arquitetura em 5 Pilares

O repositório está estruturado em 5 áreas principais, desacoplando o núcleo de regras, os módulos de execução, os insumos de entrada, a documentação centralizada e os artefatos de saída gerados:

```text
NINHO /
│
├── core/                                   # 🧠 NÚCLEO COMPARTILHADO
│   ├── convencoes/                         # Convenções e padrões corporativos (DW e Semântica)
│   └── scripts_comuns/                     # Scripts utilitários reutilizáveis
│
├── modulos/                                # ⚙️ MÓDULOS DE EXECUÇÃO
│   ├── planejador_dw/                      # Módulo 1: Planejamento e Modelagem de DW (Oracle)
│   ├── camada_semantica/                   # Módulo 2: Camada Semântica & Metadados Ativos
│   └── governanca_dados/                   # Módulo 3: Lakehouse MongoDB + AWS Glue & DataZone
│
├── entrega/                                # 📥 ENTRADA DE DADOS (Insumos dos Engenheiros)
│   ├── planejador_dw/                      # DDLs de origem, amostras brutas, FTP e APIs
│   ├── camada_semantica/                   # DDLs do DW, amostras de fatos/dims e relatórios ETL
│   └── governanca_dados/                   # Classificações de sigilo LAI e inventários LGPD
│
├── documentacao/                           # 📚 DOCUMENTAÇÃO & GOVERNANÇA CONSOLIDADA
│   ├── guias/                              # Manuais operacionais para o engenheiro (DW e Semântica)
│   ├── checklists/                         # Checklists de validação e QA pré-entrega
│   └── catalogo_projetos/                  # Ficha viva (PROJETO_RESUMO) e versionamento (PROJETO_VERSION)
│
└── saida/                                  # 📤 SAÍDA DE CADA MÓDULO (Artefatos Finais Gerados)
    ├── planejador_dw/                      # Scripts gerados: Controle de Carga, STG, DIMs e Fatos
    ├── camada_semantica/                   # Scripts gerados: Views Analíticas e Tabelas META_
    └── governanca_dados/                   # Artefatos gerados: Schemas Mongo e Forms DataZone
```

---

## 🚀 Os Módulos da Plataforma

### 1. [Planejador de DW (`modulos/planejador_dw/`)](modulos/planejador_dw/)
- **Objetivo:** Projetar e modelar um Data Warehouse relacional Oracle a partir de fontes heterogêneas (APIs, arquivos, bancos legados).
- **Entregáveis:** Estratégia de orquestração (ODI via SSH, Apache Hop, Python), tabelas de staging (`STG_`), dimensões SCD Tipo 2 (`DIM_`), tabelas fato particionadas (`FATO_`), tabela corporativa de controle (`TB_CONTROLE_CARGA`) e relatório executivo de arquitetura.

### 2. [Camada Semântica (`modulos/camada_semantica/`)](modulos/camada_semantica/)
- **Objetivo:** Construir uma camada analítica e catálogo de metadados ativos sobre um DW Oracle já existente.
- **Entregáveis:** Views analíticas em 3 camadas (`VW_*_DIM_*_ATUAL`, `VW_*_EVENTO`, `VW_*_KPI_*`) e carga de metadados nas 8 tabelas `META_*` (Glossário, Métrica, Objeto, Relacionamento, Regra de Negócio, Consultas de Negócio, Orientações de IA e Domínios).

### 3. [Governança de Dados (`modulos/governanca_dados/`)](modulos/governanca_dados/)
- **Objetivo:** Estabelecer um Data Lakehouse ágil em MongoDB e governança ativa no ecossistema AWS (sem uso de Amazon S3).
- **Entregáveis:** Particionamento lógico por órgãos (`gov_*`), envelope canônico com hierarquia organizacional (`_org`) e conformidade legal (`_governance`: LAI e LGPD), catalogação via AWS Glue Data Catalog e governança no Amazon DataZone.

---

## 🛠️ Fluxo de Trabalho do Engenheiro de Dados

1. **Escolha o Módulo:** Identifique se o desafio atual é criar/reformular um DW (`planejador_dw`), construir camada semântica (`camada_semantica`) ou governar o lakehouse (`governanca_dados`).
2. **Deposite os Insumos:** Coloque os arquivos e amostras na subpasta correspondente dentro de [`entrega/`](entrega/).
3. **Consulte os Guias:** Siga os roteiros práticos disponíveis em [`documentacao/guias/`](documentacao/guias/).
4. **Receba e Valide os Scripts:** As saídas geradas pela IA serão salvas de forma incremental e validada em [`saida/`](saida/).
