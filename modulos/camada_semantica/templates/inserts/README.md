# Inserts da Camada Semântica — REFERÊNCIA

> **Atenção:** Este diretório contém REFERÊNCIAS dos INSERTs das tabelas META_.
> Os scripts executáveis estão em `inserts/meta_projeto/`.
> Os INSERTs são gerados pela IA a partir dos insumos do INTAKE.

## Estrutura

| Arquivo | Conteúdo |
|---------|----------|
| `01_meta_glossario.sql` | INSERTs para META_GLOSSARIO |
| `02_meta_metrica.sql` | INSERTs para META_METRICA |
| `03_meta_objeto.sql` | INSERTs para META_OBJETO |
| `04_meta_relacionamento.sql` | INSERTs para META_RELACIONAMENTO |
| `05_meta_regra_negocio.sql` | INSERTs para META_REGRA_NEGOCIO |
| `06_meta_consulta_negocio.sql` | INSERTs para META_CONSULTA_NEGOCIO |
| `07_meta_orientacao_ia.sql` | INSERTs para META_ORIENTACAO_IA |
| `08_meta_valor_dominio.sql` | INSERTs para META_VALOR_DOMINIO |

## Fluxo de Validação

```
1. IA gera INSERTs em inserts/meta_projeto/
2. Engenheiro revisa cada INSERT
3. Engenheiro valida SQL das perguntas (06_meta_consulta_negocio.sql)
4. Engenheiro confirma execução
5. IA atualiza PROJETO_RESUMO.md
```

## Ordem de Execução (scripts em inserts/meta_projeto/)

### Executando de dentro da pasta inserts/meta_projeto/

```sql
-- 1. Criar tabelas (executar uma vez)
@01_create_meta_tables.sql

-- 2. Inserir dados (executar nesta ordem)
@01_meta_glossario.sql
@02_meta_metrica.sql
@03_meta_objeto.sql
@04_meta_relacionamento.sql
@05_meta_regra_negocio.sql
@06_meta_consulta_negocio.sql
@07_meta_orientacao_ia.sql
@08_meta_valor_dominio.sql
```

### Executando de fora (caminho absoluto)

```sql
-- 1. Criar tabelas
@C:\caminho\para\inserts\meta_projeto\01_create_meta_tables.sql

-- 2. Inserir dados
@C:\caminho\para\inserts\meta_projeto\01_meta_glossario.sql
@C:\caminho\para\inserts\meta_projeto\02_meta_metrica.sql
-- ... etc
```

### Executando de fora (caminho relativo)

```sql
-- 1. Criar tabelas
@inserts/meta_projeto/01_create_meta_tables.sql

-- 2. Inserir dados
@inserts/meta_projeto/01_meta_glossario.sql
@inserts/meta_projeto/02_meta_metrica.sql
-- ... etc
```

## Regras

- ❌ Nunca execute INSERTs sem validar primeiro
- ❌ Nunca altere INSERTs diretamente no Oracle
- ✅ Sempre valide SQL das perguntas antes de executar 06_meta_consulta_negocio.sql
- ✅ Sempre atualize PROJETO_RESUMO.md após execução
