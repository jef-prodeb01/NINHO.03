# Inserts — Guia de Execução

> **Atenção:** Este diretório contém os scripts SQL gerados pela IA para execução no Oracle.
> O engenheiro deve validar cada script antes de executar.
> **TUDO EM MAIÚSCULAS** — views, tabelas, colunas, aliases.

## Estrutura

```
inserts/
├── vw_analiticas/           ← views DIM, EVENTO, KPI (um arquivo por view)
│   └── README.md
└── meta_projeto/            ← CREATE TABLE + INSERTs META_
    ├── README.md
    ├── 01_create_meta_tables.sql  ← CREATE TABLE das 8 META_ + triggers
    ├── 01_meta_glossario.sql      ← INSERTs META_GLOSSARIO
    ├── 02_meta_metrica.sql        ← INSERTs META_METRICA
    ├── 03_meta_objeto.sql         ← INSERTs META_OBJETO
    ├── 04_meta_relacionamento.sql ← INSERTs META_RELACIONAMENTO
    ├── 05_meta_regra_negocio.sql  ← INSERTs META_REGRA_NEGOCIO
    ├── 06_meta_consulta_negocio.sql ← INSERTs META_CONSULTA_NEGOCIO
    ├── 07_meta_orientacao_ia.sql  ← INSERTs META_ORIENTACAO_IA
    ├── 08_meta_valor_dominio.sql  ← INSERTs META_VALOR_DOMINIO
    ├── 02_rls.sql                 ← RLS opcional
    └── 09_validacoes.sql          ← validações
```

## Ordem de Execução

### 1. Views Analíticas

```sql
-- Executar de dentro da pasta inserts/
@vw_analiticas/VW_<PROJETO>_DIM_<NOME>.sql
@vw_analiticas/VW_<PROJETO>_EVENTO.sql
@vw_analiticas/VW_<PROJETO>_KPI_<NOME>.sql
```

### 2. Tabelas META_

```sql
-- Executar de dentro da pasta inserts/
@meta_projeto/01_create_meta_tables.sql
@meta_projeto/01_meta_glossario.sql
@meta_projeto/02_meta_metrica.sql
@meta_projeto/03_meta_objeto.sql
@meta_projeto/04_meta_relacionamento.sql
@meta_projeto/05_meta_regra_negocio.sql
@meta_projeto/06_meta_consulta_negocio.sql
@meta_projeto/07_meta_orientacao_ia.sql
@meta_projeto/08_meta_valor_dominio.sql
```

### 3. RLS (opcional)

```sql
@meta_projeto/02_rls.sql
```

### 4. Validações

```sql
@meta_projeto/09_validacoes.sql
```

## Fluxo de Validação

```
1. IA gera scripts (arquivos neste diretório)
2. Engenheiro revisa cada script
3. Engenheiro valida SQL das perguntas (06_meta_consulta_negocio.sql)
4. Engenheiro confirma execução
5. IA atualiza PROJETO_RESUMO.md
```

## Regras

- ❌ Nunca execute INSERTs sem validar primeiro
- ❌ Nunca altere INSERTs diretamente no Oracle
- ✅ Sempre valide SQL das perguntas antes de executar 06_meta_consulta_negocio.sql
- ✅ Sempre atualize PROJETO_RESUMO.md após execução
- ✅ INSERTs ficam em arquivos separados — nunca misture CREATE com INSERT
