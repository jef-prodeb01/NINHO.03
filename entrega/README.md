# Entrega de Dados — Insumos dos Engenheiros

Este diretório centraliza todos os insumos, arquivos brutos, DDLs e especificações fornecidos pelo engenheiro de dados para alimentar os módulos de IA.

---

## 📂 Subpastas por Módulo

- **[`planejador_dw/`](planejador_dw/)**: Insumos para modelagem e planejamento de DW.
  - `ddl/`: DDLs de tabelas legadas ou transacionais de origem.
  - `amostras/`: Amostras de dados das tabelas de origem (CSV, planilhas).
  - `arquivos_ftp/`: Layouts e arquivos exemplo recebidos via lote / FTP.
  - `api_specs/`: Documentação de APIs REST (Swagger, OpenAPI ou payloads JSON).
- **[`camada_semantica/`](camada_semantica/)**: Insumos para criação da camada semântica sobre DW.
  - `ddl/`: DDLs das tabelas Fato e Dimensão existentes no Oracle DW.
  - `amostras/`: Amostras com dados representativos das Fatos e Dimensões.
  - `relatorios_etl/`: Relatórios de carga, periodicidade e volumetria.
- **[`governanca_dados/`](governanca_dados/)**: Insumos para catálogo e governança.
  - Arquivos de regras de negócio, tabelas de classificação LAI e mapeamento de dados pessoais (LGPD).
