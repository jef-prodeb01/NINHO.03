# Saída da Camada Semântica — Meta Projeto

> **Atenção:** Este diretório contém os CREATE TABLE e INSERTs das 8 tabelas META_ para execução no banco.
> O engenheiro deve validar cada script antes de executar.

## Estrutura

| Arquivo | Conteúdo |
|---------|----------|
| `01_create_meta_tables.sql` | CREATE TABLE das 8 META_ + constraints + triggers de auditoria |
| `01_meta_glossario.sql` | MERGE/INSERTs META_GLOSSARIO |
| `02_meta_metrica.sql` | MERGE/INSERTs META_METRICA |
| `03_meta_objeto.sql` | MERGE/INSERTs META_OBJETO |
| `04_meta_relacionamento.sql` | MERGE/INSERTs META_RELACIONAMENTO |
| `05_meta_regra_negocio.sql` | MERGE/INSERTs META_REGRA_NEGOCIO |
| `06_meta_consulta_negocio.sql` | MERGE/INSERTs META_CONSULTA_NEGOCIO |
| `07_meta_orientacao_ia.sql` | MERGE/INSERTs META_ORIENTACAO_IA (36 diretrizes globais + projeto) |
| `08_meta_valor_dominio.sql` | MERGE/INSERTs META_VALOR_DOMINIO |
| `02_rls.sql` | Segurança RLS/VPD opcional (gerado apenas se RLS marcado no Intake) |
| `09_validacoes.sql` | Auditoria pós-carga (contagens, órfãos, grão, comentários e smoke test) |

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

-- 3. Aplicar RLS/VPD (somente quando houver restrição de acesso por linha)
-- @02_rls.sql

-- 4. Executar bateria de validação cruzada
@09_validacoes.sql
```

## Fluxo de Validação

```
1. IA gera scripts (arquivos neste diretório)
2. Engenheiro revisa cada script
3. Engenheiro valida SQL das perguntas (06_meta_consulta_negocio.sql)
4. Engenheiro confirma execução
5. IA atualiza documentacao/catalogo_projetos/PROJETO_RESUMO.md
```

## Regras

- Comentários em TUDO — toda tabela e coluna gera `COMMENT ON`
- Sintaxe Oracle 12c+ (IDENTITY, VARCHAR2/CLOB)
- Triggers de auditoria incluídos no 01_create_meta_tables.sql
- Português nos conteúdos de negócio
