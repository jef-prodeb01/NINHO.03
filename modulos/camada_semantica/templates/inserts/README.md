# Inserts da Camada Semântica — REFERÊNCIA

> **Atenção:** Este diretório contém MODELOS/REFERÊNCIAS dos INSERTs das tabelas META_.
> Os scripts executáveis gerados para o projeto ficam em `saida/camada_semantica/meta_projeto/`.
> Os INSERTs são gerados pela IA a partir dos insumos do INTAKE_SEMANTICA.

## Estrutura

| Arquivo | Conteúdo |
|---------|----------|
| `01_meta_glossario.sql` | Modelo de INSERTs para META_GLOSSARIO |
| `02_meta_metrica.sql` | Modelo de INSERTs para META_METRICA |
| `03_meta_objeto.sql` | Modelo de INSERTs para META_OBJETO |
| `04_meta_relacionamento.sql` | Modelo de INSERTs para META_RELACIONAMENTO |
| `05_meta_regra_negocio.sql` | Modelo de INSERTs para META_REGRA_NEGOCIO |
| `06_meta_consulta_negocio.sql` | Modelo de INSERTs para META_CONSULTA_NEGOCIO |
| `07_meta_orientacao_ia.sql` | Modelo de INSERTs para META_ORIENTACAO_IA |
| `08_meta_valor_dominio.sql` | Modelo de INSERTs para META_VALOR_DOMINIO |

## Fluxo de Validação

```
1. IA gera INSERTs em saida/camada_semantica/meta_projeto/
2. Engenheiro revisa cada INSERT
3. Engenheiro valida SQL das perguntas (06_meta_consulta_negocio.sql)
4. Engenheiro confirma execução
5. IA atualiza documentacao/catalogo_projetos/PROJETO_RESUMO.md
```

## Ordem de Execução (scripts em saida/camada_semantica/meta_projeto/)

### Executando de dentro da pasta saida/camada_semantica/meta_projeto/

```sql
-- 1. Criar tabelas (executar uma vez se ainda não existirem)
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
@C:\caminho\para\saida\camada_semantica\meta_projeto\01_create_meta_tables.sql

-- 2. Inserir dados
@C:\caminho\para\saida\camada_semantica\meta_projeto\01_meta_glossario.sql
@C:\caminho\para\saida\camada_semantica\meta_projeto\02_meta_metrica.sql
-- ... etc
```

### Executando de fora (caminho relativo)

```sql
-- 1. Criar tabelas
@saida/camada_semantica/meta_projeto/01_create_meta_tables.sql

-- 2. Inserir dados
@saida/camada_semantica/meta_projeto/01_meta_glossario.sql
@saida/camada_semantica/meta_projeto/02_meta_metrica.sql
-- ... etc
```

## Regras

- ❌ Nunca execute INSERTs sem validar primeiro
- ❌ Nunca altere INSERTs diretamente no Oracle
- ✅ Sempre valide SQL das perguntas antes de executar 06_meta_consulta_negocio.sql
- ✅ Sempre atualize documentacao/catalogo_projetos/PROJETO_RESUMO.md após execução
