# Módulo: Camada Semântica & Metadados

Este módulo automatiza a criação de uma camada semântica robusta e auto-explicativa sobre um Data Warehouse Oracle existente.

---

## 📋 Como Funciona

1. **Insumos:** O engenheiro de dados deposita DDLs e amostras em `entrega/camada_semantica/` e preenche `INTAKE_SEMANTICA.md`.
2. **Entendimento:** A IA analisa as regras de aditividade, grãos de fato e hierarquias, gerando um documento de alinhamento.
3. **Geração Incremental:** A IA gera script a script:
   - Views Analíticas em 3 Camadas (`saida/camada_semantica/vw_analiticas/`)
   - Scripts DDL e Inserts das 8 tabelas `META_*` (`saida/camada_semantica/meta_projeto/`)
4. **Governança:** A documentação do projeto é registrada em `documentacao/catalogo_projetos/`.

Consulte o manual operacional em [`documentacao/guias/GUIA_ENGENHEIRO_SEMANTICA.md`](../../documentacao/guias/GUIA_ENGENHEIRO_SEMANTICA.md) e as convenções em [`core/convencoes/CONVENCOES_SEMANTICA.md`](../../core/convencoes/CONVENCOES_SEMANTICA.md).

