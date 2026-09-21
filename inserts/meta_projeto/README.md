# Inserts — Meta Projeto

> **Atenção:** Este diretório contém os CREATE TABLE e INSERTs das 8 tabelas META_ para execução no banco.
> O engenheiro deve validar cada script antes de executar.

## Estrutura

| Arquivo | Conteúdo |
|---------|----------|
| `01_create_meta_tables.sql` | CREATE TABLE das 8 META_ + triggers de auditoria |
| `01_meta_glossario.sql` | INSERTs META_GLOSSARIO |
| `02_meta_metrica.sql` | INSERTs META_METRICA |
| `03_meta_objeto.sql` | INSERTs META_OBJETO |
| `04_meta_relacionamento.sql` | INSERTs META_RELACIONAMENTO |
| `05_meta_regra_negocio.sql` | INSERTs META_REGRA_NEGOCIO |
| `06_meta_consulta_negocio.sql` | INSERTs META_CONSULTA_NEGOCIO |
| `07_meta_orientacao_ia.sql` | INSERTs META_ORIENTACAO_IA |
| `08_meta_valor_dominio.sql` | INSERTs META_VALOR_DOMINIO |

## Ordem de Execução

```sql
-- 1. Criar tabelas (executar UMA VEZ apenas se o schema NÃO possuir as tabelas META_)
-- SE AS TABELAS META_* JÁ EXISTIREM NO SCHEMA, PULE ESTE PASSO:
@01_create_meta_tables.sql

-- 2. Inserir / Acrescentar dados (executar nesta ordem — scripts preparados com MERGE/idempotência)
@01_meta_glossario.sql
@02_meta_metrica.sql
@03_meta_objeto.sql
@04_meta_relacionamento.sql
@05_meta_regra_negocio.sql
@06_meta_consulta_negocio.sql
@07_meta_orientacao_ia.sql
@08_meta_valor_dominio.sql
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

- Comentários em TUDO — toda tabela e coluna gera `COMMENT ON`
- Sintaxe Oracle 12c+ (IDENTITY, VARCHAR2/CLOB)
- Triggers de auditoria incluídos no 01_create_meta_tables.sql
- Português nos conteúdos de negócio
