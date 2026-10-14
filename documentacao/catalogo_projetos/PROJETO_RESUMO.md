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
>
> Para inicializar:
> 1. Preencha [`modulos/camada_semantica/INTAKE_SEMANTICA.md`](../../modulos/camada_semantica/INTAKE_SEMANTICA.md) e deposite os insumos em `entrega/camada_semantica/` (ou execute `/concluir-dw` se veio do Planejador de DW)
> 2. O agente gera `saida/camada_semantica/DOCUMENTO_ENTENDIMENTO_<PROJETO>.md` com o Radar Consultivo da IA
> 3. Após validação e geração dos scripts SQL em `saida/camada_semantica/`, este arquivo é consolidado automaticamente

---

## Instruções de Inicialização

1. Leia [README.md](../../README.md) para entender o processo
2. Encaminhe [GUIA_ENGENHEIRO_DW.md](../guias/GUIA_ENGENHEIRO_DW.md) ou [GUIA_ENGENHEIRO_SEMANTICA.md](../guias/GUIA_ENGENHEIRO_SEMANTICA.md) ao engenheiro
3. Aguarde os insumos em `entrega/camada_semantica/`
4. Confirme ao agente para gerar o documento de entendimento

---

## 0. Estrutura de Arquivos do Projeto

### 0.1 Scripts SQL

| Arquivo | Finalidade |
|---------|------------|
| `saida/camada_semantica/vw_analiticas/VW_<PROJETO>_DIM_<NOME>_ATUAL.sql` | Views DIM vigentes (uma por dimensão) |
| `saida/camada_semantica/vw_analiticas/VW_<PROJETO>_EVENTO.sql` | Views EVENTO (uma por fato) |
| `saida/camada_semantica/vw_analiticas/VW_<PROJETO>_KPI_<NOME>.sql` | Views KPI (consolidadas por indicador/recorte) |
| `saida/camada_semantica/meta_projeto/01_create_meta_tables.sql` | CREATE TABLE das 8 META_ + constraints + triggers |
| `saida/camada_semantica/meta_projeto/01_meta_glossario.sql` | MERGE/INSERTs META_GLOSSARIO |
| `saida/camada_semantica/meta_projeto/02_meta_metrica.sql` | MERGE/INSERTs META_METRICA |
| `saida/camada_semantica/meta_projeto/03_meta_objeto.sql` | MERGE/INSERTs META_OBJETO |
| `saida/camada_semantica/meta_projeto/04_meta_relacionamento.sql` | MERGE/INSERTs META_RELACIONAMENTO |
| `saida/camada_semantica/meta_projeto/05_meta_regra_negocio.sql` | MERGE/INSERTs META_REGRA_NEGOCIO |
| `saida/camada_semantica/meta_projeto/06_meta_consulta_negocio.sql` | MERGE/INSERTs META_CONSULTA_NEGOCIO |
| `saida/camada_semantica/meta_projeto/07_meta_orientacao_ia.sql` | MERGE/INSERTs META_ORIENTACAO_IA |
| `saida/camada_semantica/meta_projeto/08_meta_valor_dominio.sql` | MERGE/INSERTs META_VALOR_DOMINIO |
| `saida/camada_semantica/meta_projeto/02_rls.sql` | RLS opcional (só se houver acesso restrito) |
| `saida/camada_semantica/meta_projeto/09_validacoes.sql` | Checagens de integridade entre META_ e teste de execução |

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
