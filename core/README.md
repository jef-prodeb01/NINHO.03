# Core — Núcleo Compartilhado

Este diretório contém os padrões, convenções corporativas e componentes reutilizáveis compartilhados por todos os módulos do framework.

---

## 📁 Estrutura do Diretório

- **`convencoes/`**
  - **`CONVENCOES_DW.md`**: Padrões de modelagem dimensional para DW Oracle (prefixos `DIM_`, `FATO_`, chave artificial `DIMENSION_KEY`, SCD Tipo 2, linha `-1`, particionamento e índices).
  - **`CONVENCOES_SEMANTICA.md`**: Padrões da camada semântica e catálogo de metadados (prefixos `VW_*`, medidas aditivas/semi-aditivas, 8 tabelas `META_*`).
- **`scripts_comuns/`**: Scripts utilitários de banco, auditoria, engenharia reversa e automação transversal:
  - `melhorar_dw_existente.py`: Motor Fast-Track para DWs já construídos (`--modo {comentarios,indices,patch,tudo}`, sem alterar a carga ETL).
  - `inspecionar_ddl_origem.py`: Extrator determinístico de DDLs de origem e Radar Consultivo de KPIs.
  - `validar_entrega.py`: Auditor pré-voo e pós-geração das Regras de Ouro (suporta `dw`, `fast-track`, `semantica`, `governanca`, `saida`, `all`).
  - `auditar_mapa_odi.py`: Auditor preditivo de tuning e anti-padrões (`H1` a `H9`) para projetos ODI 12c.
  - `auditar_esteira_hop.py`: Auditor de segurança e qualidade (`HOP-H1` a `HOP-H8`) para Apache Hop 2.x, FTPS e Python.
  - `inspecionar_pbix.py`: Engenharia reversa de arquivos `.pbix` do Power BI (`PBIX-H1` a `PBIX-H5`).
  - `inspecionar_insumos_governanca.py`: Auditoria Gate 0.5 de planilhas/CSVs do cliente e geração da Matriz DE/PARA MongoDB PRODEB.
  - `transicionar_dw_para_semantica.py`: Handoff automatizado do Planejador DW para a Camada Semântica.
  - `gerenciar_projeto.py`: Exportação de pacotes `.zip` e limpeza segura do workspace (`--status`, `--exportar`, `--resetar`).
  - `gerar_mock_dados.py`: Gerador de dados sintéticos para testes de painéis no Power BI.


