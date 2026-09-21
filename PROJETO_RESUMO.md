# PROJETO_RESUMO.md — Documentação Central do Projeto

> **Schema Oracle:** `<SCHEMA_ALVO>`
> **Projeto:** `<NOME_DO_PROJETO>`
> **Data de criação:** `<DATA>`
> **Última atualização:** `<DATA>`
> **Versão:** `<versão>`

> **Regra:** Este arquivo deve ser atualizado SEMPRE que houver mudança no projeto.
> É a "fonte única da verdade" para a IA gerar SQL correto.

---

> **⚠️ PROJETO NÃO INICIALIZADO**
>
> Este arquivo será preenchido pela IA após validação do engenheiro.
> O modelo base está em `exemplo_tabelas/PROJETO_RESUMO_MODELO.md`.
>
> Para inicializar:
> 1. Encaminhe os insumos (DDL, amostras, regras) ao agente
> 2. O agente gera o conteúdo em `exemplo_tabelas/PROJETO_RESUMO_MODELO.md`
> 3. Após validação, o conteúdo é copiado para cá

---

## Instruções de Inicialização

1. Leia [README.md](README.md) para entender o processo
2. Encaminhe [GUIA_ENGENHEIRO_DADOS.md](GUIA_ENGENHEIRO_DADOS.md) ao engenheiro
3. Aguarde os insumos em `entrega/`
4. Confirme ao agente para gerar o documento de entendimento

---

## 0. Estrutura de Arquivos do Projeto

### 0.1 Scripts SQL

| Arquivo | Finalidade |
|---------|------------|
| `inserts/vw_analiticas/VW_<PROJETO>_DIM_<NOME>.sql` | Views DIM (uma por dimensão) |
| `inserts/vw_analiticas/VW_<PROJETO>_EVENTO.sql` | Views EVENTO (uma por fato) |
| `inserts/vw_analiticas/VW_<PROJETO>_KPI_<NOME>.sql` | Views KPI (uma por pergunta) |
| `inserts/meta_projeto/01_create_meta_tables.sql` | CREATE TABLE das 8 META_ |
| `inserts/meta_projeto/01_meta_glossario.sql` | INSERTs META_GLOSSARIO |
| `inserts/meta_projeto/02_meta_metrica.sql` | INSERTs META_METRICA |
| `inserts/meta_projeto/03_meta_objeto.sql` | INSERTs META_OBJETO |
| `inserts/meta_projeto/04_meta_relacionamento.sql` | INSERTs META_RELACIONAMENTO |
| `inserts/meta_projeto/05_meta_regra_negocio.sql` | INSERTs META_REGRA_NEGOCIO |
| `inserts/meta_projeto/06_meta_consulta_negocio.sql` | INSERTs META_CONSULTA_NEGOCIO |
| `inserts/meta_projeto/07_meta_orientacao_ia.sql` | INSERTs META_ORIENTACAO_IA |
| `inserts/meta_projeto/08_meta_valor_dominio.sql` | INSERTs META_VALOR_DOMINIO |
| `inserts/meta_projeto/02_rls.sql` | RLS opcional (só se houver acesso restrito) |
| `inserts/meta_projeto/09_validacoes.sql` | Checagens de integridade entre META_ e teste de execução |

### 0.2 Arquitetura em 3 Camadas

O projeto segue uma arquitetura em 3 camadas:

#### Camada 1 — VIEWS DIM (versão vigente)
- Filtram apenas a versão vigente de cada dimensão SCD Type 2 (`DTC_EXPIRACAO IS NULL`)
- Grao: um registro por objeto vigente
- São usadas como base para as views EVENTO
- Exemplo: `VW_<PROJETO>_DIM_<DIMENSAO>_ATUAL`

#### Camada 2 — VIEWS EVENTO (camada intermediária)
- Normalizam os dados brutos em registros analíticos
- FATO + JOINs com DIMs (incluindo dimensões temporais)
- Incluem: SKs, datas calculadas, medidas, indicadores (IND_CONCLUIDO, IND_EM_ABERTO)
- São a BASE para gerar views KPI
- Exemplo: `VW_<PROJETO>_EVENTO`

#### Camada 3 — VIEWS KPI (consolidadas)
- Consolidadas para responder perguntas específicas dos usuários
- Geradas a partir das views EVENTO e DIM
- Usam CTEs para cálculos (COUNT DISTINCT, SUM, AVG)
- Grao: depende do projeto (ex: por mês, por dia, por dimensão, etc.)
- Exemplo: `VW_<PROJETO>_KPI_<MEDIDA>_POR_<DIMENSAO>`
