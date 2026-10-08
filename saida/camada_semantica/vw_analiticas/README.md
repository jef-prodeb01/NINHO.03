# Inserts — Views Analíticas

> **Atenção:** Este diretório contém as views analíticas geradas pela IA.
> O engenheiro deve validar cada view antes de executar.

## Como a IA gera as views

```
1. IA usa exemplo_tabelas/01_views_analiticas.sql como base
2. IA gera um arquivo por view (ex: VW_PROJETO_DIM_CIDADE.sql)
3. Engenheiro valida a view
4. Engenheiro confirma execução
5. IA gera próxima view
```

## Ordem de Execução

### Executando de dentro da pasta vw_analiticas/

```sql
-- 1. Executar views DIM (uma por uma)
@VW_PROJETO_DIM_CIDADE.sql
@VW_PROJETO_DIM_ORGAO.sql

-- 2. Executar views EVENTO
@VW_PROJETO_EVENTO.sql

-- 3. Executar views KPI
@VW_PROJETO_KPI_CONTAS_PAGAR_POR_MES.sql
@VW_PROJETO_KPI_CONTAS_A_RECEBER_POR_MES.sql
```

### Executando de fora (caminho absoluto)

```sql
-- Executar de dentro da pasta inserts/
@vw_analiticas/VW_PROJETO_DIM_CIDADE.sql
```

## Fluxo de Validação

```
1. IA gera view (arquivo neste diretório)
2. Engenheiro revisa SQL
3. Engenheiro valida lógica de negócio
4. Engenheiro confirma execução
5. Próxima view
```

## Regras

- Cada view é um arquivo separado
- **TUDO EM MAIÚSCULAS** — views, tabelas, colunas, aliases
- Comentários em TUDO — toda tabela, view e coluna gera `COMMENT ON`
- SQL das consultas em `q'[...]'` indentado — legível no DBeaver
- Sintaxe Oracle 12c+
- Português nos conteúdos de negócio
