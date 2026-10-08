# Core — Núcleo Compartilhado

Este diretório contém os padrões, convenções corporativas e componentes reutilizáveis compartilhados por todos os módulos do framework.

---

## 📁 Estrutura do Diretório

- **`convencoes/`**
  - **`CONVENCOES_DW.md`**: Padrões de modelagem dimensional para DW Oracle (prefixos `DIM_`, `FATO_`, chaves `SK_`, SCD Tipo 2, particionamento e índices).
  - **`CONVENCOES_SEMANTICA.md`**: Padrões da camada semântica e catálogo de metadados (prefixos `VW_*`, medidas aditivas/semi-aditivas, tabelas `META_*`).
- **`scripts_comuns/`**: Scripts utilitários de banco, auditoria e automação transversal.
