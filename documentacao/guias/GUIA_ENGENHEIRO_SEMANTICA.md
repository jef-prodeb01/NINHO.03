# Guia de Entrega — Preparar insumos para a camada semântica

Este roteiro orienta o **engenheiro de dados** responsável pelo DW a gerar e
fornecer todas as informações necessárias para a construção da camada
semântica (views analíticas + tabelas `META_`) sobre um DW Oracle existente.

> **Público**: quem conhece o DW e o ETL (você).
> **Objetivo**: entregar um pacote de insumos completo, sem idas e vindas.
> **Resultado**: a camada semântica é gerada a partir do que você entregar aqui.

---

## Sumário

**Parte 1 — O que entregar (siga esta ordem na primeira entrega)**
- [Visão geral do que você vai entregar](#visao-geral-entrega)
- [Seção 1 — DDL das tabelas](#secao-1-ddl)
- [Seção 2 — Amostras e perfil dos dados](#secao-2-amostras)
- [Seção 3 — Documentação do ETL](#secao-3-etl)
- [Seção 4 — Regras de negócio](#secao-4-regras)
- [Seção 5 — Perguntas dos usuários](#secao-5-perguntas)
- [Empacotamento e entrega](#empacotamento-e-entrega)
- [Checklist final antes de entregar](#checklist-final-entrega)
- [O que acontece depois da entrega](#depois-da-entrega)

**Parte 2 — Como o projeto funciona no dia a dia**
- [Visão completa do projeto](#visao-completa-projeto)
- [PROJETO_RESUMO.md — A fonte única da verdade](#projeto-resumo-fonte-verdade)
- [Manutenção do projeto](#manutencao-do-projeto)
- [Transferência de responsabilidade](#transferencia-responsabilidade)
- [Checklist final antes de entregar (2)](#checklist-final-projeto)
- [Checklist de manutenção](#checklist-manutencao)
- [O que NÃO fazer](#o-que-nao-fazer)

**Parte 3 — Biblioteca de prompts prontos (copiar/colar para a IA)**
- [1. Geração Inicial do Projeto](#prompt-1-geracao-inicial)
- [2. Manutenção — Nova Tabela](#prompt-2-nova-tabela)
- [3. Manutenção — Coluna Nova](#prompt-3-coluna-nova)
- [4. Manutenção — Regras de Negócio](#prompt-4-regras-negocio)
- [5. Manutenção — Perguntas de Negócio](#prompt-5-perguntas-negocio)
- [6. Manutenção — Views](#prompt-6-views)
- [7. Validação e Auditoria](#prompt-7-validacao-auditoria)
- [8. Transferência de Responsabilidade](#prompt-8-transferencia)
- [9. Situações Especiais](#prompt-9-situacoes-especiais)
- [10. Comandos Rápidos](#prompt-10-comandos-rapidos)
- [11. Regras de RLS (Row Level Security)](#prompt-11-rls)
- [12. Validação de Perguntas de Negócio](#prompt-12-validacao-perguntas)

**Parte 4 — Arquitetura e fluxo de referência**
- [Camada 1 — VIEWS DIM](#camada-1-dim)
- [Camada 2 — VIEWS EVENTO](#camada-2-evento)
- [Camada 3 — VIEWS KPI](#camada-3-kpi)
- [Views Materializadas](#views-materializadas)
- [Fluxo de Dependência](#fluxo-dependencia)
- [Como a IA gera as views](#como-ia-gera-views)
- [Quando atualizar o PROJETO_RESUMO.md](#quando-atualizar-resumo)
- [Dicas de Uso dos Prompts](#dicas-uso-prompts)
- [Fluxo de Trabalho com Prompts](#fluxo-trabalho-prompts)

---

<a id="visao-geral-entrega"></a>
## Visão geral do que você vai entregar

| # | Insumo | Formato | Esforço estimado |
|---|--------|---------|:---:|
| 1 | DDL das fatos e dimensões (com comentários) | Arquivo `.sql` ou texto | 15 min |
| 2 | Amostras e perfil dos dados | Resultado de queries prontas (abaixo) | 30 min |
| 3 | Documentação do ETL | O que existir + resposta a 6 perguntas | 20 min |
| 4 | Regras de negócio | Resposta ao questionário | 20 min |
| 5 | Perguntas dos usuários | Lista em linguagem livre | 15 min |

Total: ~1h30 de trabalho. Siga as seções na ordem — cada uma já está no
formato de entrega.

---

<a id="secao-1-ddl"></a>
## Seção 1 — DDL das tabelas (obrigatório)

### O que gerar

Um **arquivo único** (`ddl_completo.sql`) com o `CREATE TABLE`, constraints
(PK/FK/UK) e comentários (`COMMENT ON`) de TODAS as fatos e dimensões do
schema — sem precisar rodar tabela por tabela.

### Select único — DDL + comentários de todo o schema

```sql
SELECT table_name, ordem, ddl_texto
FROM (
    SELECT table_name, 1 AS ordem, DBMS_METADATA.GET_DDL('TABLE', table_name) AS ddl_texto
    FROM user_tables
    UNION ALL
    SELECT table_name, 2 AS ordem, DBMS_METADATA.GET_DEPENDENT_DDL('COMMENT', table_name) AS ddl_texto
    FROM user_tables
    WHERE table_name IN (
        SELECT table_name FROM user_tab_comments WHERE comments IS NOT NULL
        UNION
        SELECT table_name FROM user_col_comments WHERE comments IS NOT NULL
    )
)
ORDER BY table_name, ordem;
```

> Retorna, para cada tabela, o `CREATE TABLE` seguido dos `COMMENT ON`
> (tabela e colunas). O filtro do `WHERE` evita erro em tabelas sem
> nenhum comentário — `DBMS_METADATA.GET_DEPENDENT_DDL('COMMENT', ...)`
> lança exceção se não houver comentário a extrair.

> No SQL Developer/DBeaver: rode a query e exporte o resultado (botão
> direito no grid → **Export**) como `ddl_completo.sql`, ou copie o
> conteúdo da coluna `ddl_texto` linha a linha para o arquivo.

### Variante — apenas uma lista específica de tabelas

Se o schema tem tabelas de outros projetos/domínios que não interessam à
camada semântica, filtre pela lista de fatos/dimensões relevantes em vez de
trazer o schema inteiro:

```sql
SELECT table_name, ordem, ddl_texto
FROM (
    SELECT table_name, 1 AS ordem, DBMS_METADATA.GET_DDL('TABLE', table_name) AS ddl_texto
    FROM user_tables
    WHERE table_name IN ('FATO_PROCESSO', 'DIM_ORGAO', 'DIM_TEMPO', 'DIM_STATUS')
    UNION ALL
    SELECT table_name, 2 AS ordem, DBMS_METADATA.GET_DEPENDENT_DDL('COMMENT', table_name) AS ddl_texto
    FROM user_tables
    WHERE table_name IN ('FATO_PROCESSO', 'DIM_ORGAO', 'DIM_TEMPO', 'DIM_STATUS')
      AND table_name IN (
          SELECT table_name FROM user_tab_comments WHERE comments IS NOT NULL
          UNION
          SELECT table_name FROM user_col_comments WHERE comments IS NOT NULL
      )
)
ORDER BY table_name, ordem;
```

> Ajuste a lista de nomes em `IN (...)` às tabelas reais do projeto (a
> mesma lista nas duas metades da `UNION ALL`). Use o **inventário de
> tabelas** da seção 2.1 para decidir quais tabelas pertencem ao domínio
> antes de montar essa lista.

### Onde entregar

```
entrega/ddl/ddl_completo.sql
```

### Checklist de qualidade

- [ ] Todas as fatos estão incluídas
- [ ] Todas as dimensões estão incluídas
- [ ] Constraints de PK/FK presentes (é delas que sai o mapa de joins)
- [ ] Comentários existentes incluídos (mesmo que incompletos)

---

<a id="secao-2-amostras"></a>
## Seção 2 — Amostras e perfil dos dados (obrigatório)

Não precisa exportar massa de dados — precisamos entender **o que os dados
contêm**. Rode as queries abaixo e salve os resultados em
`entrega/amostras/`.

### 2.1 Inventário de tabelas (select único)

Visão executiva de todo o schema antes de entrar no detalhe: tabela,
comentário, qtde de colunas, qtde de linhas, PK e para onde apontam as FKs.

```sql
SELECT
    t.table_name,
    tc.comments                                    AS comentario_tabela,
    t.num_rows                                      AS qtde_linhas_aprox,
    t.last_analyzed                                 AS estatisticas_de,
    (SELECT COUNT(*) FROM user_tab_columns c
      WHERE c.table_name = t.table_name)            AS qtde_colunas,
    (SELECT LISTAGG(acc.column_name, ', ') WITHIN GROUP (ORDER BY acc.position)
       FROM user_constraints ac
       JOIN user_cons_columns acc ON acc.constraint_name = ac.constraint_name
      WHERE ac.table_name = t.table_name AND ac.constraint_type = 'P')  AS colunas_pk,
    (SELECT LISTAGG(acc.column_name || ' -> ' || r_ac.table_name, '; ') WITHIN GROUP (ORDER BY acc.column_name)
       FROM user_constraints ac
       JOIN user_cons_columns acc ON acc.constraint_name = ac.constraint_name
       JOIN user_constraints r_ac ON r_ac.constraint_name = ac.r_constraint_name
      WHERE ac.table_name = t.table_name AND ac.constraint_type = 'R') AS fks_para
FROM user_tables t
LEFT JOIN user_tab_comments tc ON tc.table_name = t.table_name AND tc.table_type = 'TABLE'
ORDER BY t.table_name;
```

> Cole o resultado (texto) em `entrega/amostras/inventario_tabelas.txt`.
> `num_rows`/`last_analyzed` vêm das estatísticas do otimizador — se
> estiverem vazias ou desatualizadas, rode antes:
> `EXEC DBMS_STATS.GATHER_SCHEMA_STATS(ownname => USER, cascade => TRUE);`

### 2.2 Candidatos a colunas categóricas (select único, heurística automática)

Em vez de decidir manualmente quais colunas perfilar, esta query usa as
estatísticas do otimizador (`NUM_DISTINCT`) para sugerir colunas de baixa
cardinalidade (candidatas a tipo, status, categoria, região etc.):

```sql
SELECT
    c.table_name,
    c.column_name,
    c.data_type,
    s.num_distinct,
    s.num_nulls,
    t.num_rows,
    ROUND(s.num_distinct / NULLIF(t.num_rows, 0) * 100, 2) AS pct_cardinalidade,
    cc.comments AS comentario_coluna
FROM user_tab_columns c
JOIN user_tables t ON t.table_name = c.table_name
LEFT JOIN user_tab_col_statistics s ON s.table_name = c.table_name AND s.column_name = c.column_name
LEFT JOIN user_col_comments cc ON cc.table_name = c.table_name AND cc.column_name = c.column_name
WHERE s.num_distinct IS NOT NULL
  AND (s.num_distinct <= 50 OR (t.num_rows > 0 AND s.num_distinct / t.num_rows <= 0.05))
ORDER BY c.table_name, s.num_distinct;
```

> Depende de estatísticas atualizadas (mesmo `DBMS_STATS` da seção 2.1).
> O resultado é uma **lista de sugestões** — use-a para decidir em quais
> colunas rodar o `GROUP BY` da seção 2.4. Nem toda coluna sugerida é
> categórica de negócio (ex.: chaves substitutas com poucos valores por
> coincidência) — revise antes de perfilar.

### 2.3 Volume e período de cada fato

```sql
SELECT COUNT(*) AS qtde_linhas,
       MIN(<coluna_periodo>) AS periodo_ini,
       MAX(<coluna_periodo>) AS periodo_fim
FROM <fato>;
```

### 2.4 Valores distintos das colunas categóricas

Para cada coluna sinalizada na seção 2.2 (ou outra que você julgue
relevante):

```sql
SELECT <coluna>, COUNT(*) AS qtde
FROM <dimensao>
GROUP BY <coluna>
ORDER BY qtde DESC;
```

### 2.5 Amostra de linhas

10–20 linhas de cada tabela (o bastante para ver o padrão dos dados):

```sql
SELECT * FROM <tabela> FETCH FIRST 20 ROWS ONLY;
```

### Onde entregar

```
entrega/amostras/inventario_tabelas.txt   <- 2.1
entrega/amostras/colunas_categoricas.txt  <- 2.2
entrega/amostras/amostras_dados.txt       <- 2.3, 2.4, 2.5 + respostas abaixo
```

### Perguntas que você deve responder olhando as amostras

Responda **explicitamente** (é aqui que moram as armadilhas):

1. Existem **linhas de total/subtotal** misturadas ao detalhe?
   (ex.: uma linha "Total Geral" ou código `0` na fato/dimensão)
2. Alguma dimensão tem **hierarquia** embutida no código?
   (ex.: `2110.01` é filho de `2110`)
3. Se sim, **somar o detalhe recompõe o total**? Ou o total oficial
   vem da linha agregada?
4. Há códigos/valores **sintéticos** criados pelo ETL (que não existem
   na fonte)? Quais?
5. Medidas percentuais/razões: são **pré-calculadas** na fonte ou
   derivadas? De quais colunas?

### Checklist de qualidade

- [ ] Inventário de tabelas gerado (2.1)
- [ ] Candidatos a colunas categóricas revisados (2.2)
- [ ] Volume e período de cada fato
- [ ] Distinct de cada coluna categórica confirmada
- [ ] Amostra de cada tabela
- [ ] As 5 perguntas acima respondidas por escrito

---

<a id="secao-3-etl"></a>
## Seção 3 — Documentação do ETL (recomendado)

Anexe o que existir (documento, wiki, comentários no código). Se não houver
nada formal, responda por escrito:

1. **Tipo de carga**: full reload ou incremental? Frequência?
2. **De-paras**: há mapeamentos manuais entre fontes? (ex.: nomes de
   produtos diferentes em sistemas diferentes)
3. **Valores tratados**: nulos substituídos? Datas estimadas?
   Registros "Não informado"?
4. **Chaves substitutas**: como as `SK_*` são geradas? São estáveis
   entre cargas?
5. **Problemas conhecidos**: encoding, divergências entre fontes,
   duplicidades históricas?
6. **Linhas de agregação**: o ETL insere linhas de total? Em quais
   tabelas e com que identificador?

---

<a id="secao-4-regras"></a>
## Seção 4 — Regras de negócio (obrigatório)

Preencha com o cliente/PO. Formato: uma afirmação por linha.

### 4.1 Aditividade das medidas

Para **cada medida** de cada fato, marque:

| Medida | Pode somar livremente? | Só com restrição? Qual? | Nunca somar? |
|---|---|---|---|
| `<medida_1>` | ☐ | ☐ | ☐ |
| `<medida_2>` | ☐ | ☐ | ☐ |

### 4.2 Regras de totalização

- [ ] O valor oficial de totais vem de **linha agregada** ou da **soma do detalhe**?
- [ ] Há filtros obrigatórios para algum relatório oficial?
  (ex.: "o relatório oficial exclui o setor X")

### 4.3 Unidades e convenções

- Unidade monetária e escala (ex.: R$ **milhões**)
- Valores nominais ou deflacionados? Se deflacionados, ano-base?
- Convenção de datas (ano-calendário? ano fiscal? data de competência
  ou de pagamento?)
- Percentuais: sobre qual denominador?

### 4.4 Restrições de acesso (RLS — Row Level Security)

**CRÍTICO:** Se múltiplos projetos/segmentos compartilham o mesmo DW, é
essencial definir quem pode ver o quê. Isso vira filtro automático nas
views via RLS (Virtual Private Database).

#### 4.4.1 Visão geral do acesso

- [ ] **Acesso total:** Usuários veem TODOS os dados do projeto
- [ ] **Acesso restrito:** Usuários veem APENAS parte dos dados

Se marcou **acesso restrito**, responda:

#### 4.4.2 Filtros por usuário/segmento

| Grupo de Usuários | Filtro Aplicado | Coluna da Tabela | Exemplo |
|---|---|---|---|
| `<grupo_1>` | Só vê `<segmento_1>` | `<coluna_filtro>` | `WHERE cidade = 'SAO_PAULO'` |
| `<grupo_2>` | Só vê `<segmento_2>` | `<coluna_filtro>` | `WHERE cidade IN ('BH', 'RJ')` |
| `<grupo_3>` | Acesso total | — | (sem filtro) |

#### 4.4.3 Níveis de restrição

Para **cada tabela fato/dimensão** que precisa de filtro:

| Tabela | Coluna de filtro | Tipos de restrição |
|---|---|---|
| `<tabela_1>` | `<coluna>` | ☐ Por cidade ☐ Por secretaria ☐ Por órgão ☐ Outro |
| `<tabela_2>` | `<coluna>` | ☐ Por cidade ☐ Por secretaria ☐ Por órgão ☐ Outro |

#### 4.4.4 Regras de sobreposição

- [ ] Um usuário pode ver **múltiplos segmentos**? (ex.: secretaria A + B)
- [ ] Um usuário pode ver **todos os segmentos**? (acesso total)
- [ ] Segmentos são **exclusivos**? (usuário vê APENAS um)
- [ ] Há **hierarquia de acesso**? (ex.: gestor vê tudo, analista vê só uma área)

#### 4.4.5 Implementação

Como o RLS será implementado?

- [ ] **Função PL/SQL** (VPD — Virtual Private Database)
- [ ] **Contexto de sessão** (DBMS_SESSION.SET_CONTEXT)
- [ ] **View com filtro** (WHERE usuario = SYSDATE)
- [ ] **Outro:** <descreva>

> **Importante:** A IA precisa saber os filtros para incluí-los nas views
> analíticas automaticamente. Exemplo:
> ```sql
> CREATE VIEW vw_projeto_evento AS
> SELECT * FROM FATO_X
> WHERE <coluna_filtro> IN (
>   SELECT segmento FROM usuario_segmentos WHERE usuario = SYS_CONTEXT('USERENV', 'SESSION_USER')
> );
> ```

---

<a id="secao-5-perguntas"></a>
## Seção 5 — Perguntas dos usuários (recomendado)

Liste **10 a 20 perguntas reais** que os usuários fazem/farão, na linguagem
deles (sem traduzir para técnico — isso é trabalho nosso).

**Boas perguntas** (específicas, respondíveis com o DW):
- "Qual foi a receita total por ano?"
- "Qual produto mais vendeu em 2023?"
- "Como evoluiu a participação da região Sul?"

**Evite** (fora de escopo ou subjetivas):
- "Por que vendeu menos?" (o DW mostra o QUANTO, não o porquê)
- "Qual a previsão para o próximo ano?" (projeção não é consulta ao DW)

```
1. <pergunta>
2. <pergunta>
...
```

---

<a id="empacotamento-e-entrega"></a>
## Empacotamento e entrega

```
entrega/
├── ddl/
│   └── ddl_completo.sql          <- Seção 1 (select único)
├── amostras/
│   ├── inventario_tabelas.txt    <- Seção 2.1 (select único)
│   ├── colunas_categoricas.txt   <- Seção 2.2 (select único, heurística)
│   └── amostras_dados.txt        <- Seções 2.3-2.5 + respostas às perguntas
├── 03_etl.md                     <- Seção 3 (doc existente + 6 respostas)
├── 04_regras_negocio.md          <- Seção 4 (questionário preenchido)
└── 05_perguntas_usuarios.md      <- Seção 5
```

<a id="checklist-final-entrega"></a>
## Checklist final antes de entregar

- [ ] Pasta `entrega/` criada com subpastas `ddl/` e `amostras/`
- [ ] DDL completo com constraints e comentários
- [ ] Perfil dos dados com as 5 perguntas-armadilha respondidas
- [ ] ETL: documento ou as 6 respostas
- [ ] Regras de negócio: aditividade de TODAS as medidas marcada
- [ ] 10–20 perguntas de usuários
- [ ] Nada de credenciais ou dados sensíveis nos arquivos

<a id="depois-da-entrega"></a>
## O que acontece depois da entrega

1. Devolvemos um **documento de entendimento** (grão, aditividade,
   hierarquias, relacionamentos, armadilhas) para sua validação
2. Com o OK, geramos os scripts prontos para executar no Oracle:
   views analíticas + tabelas `META_` preenchidas
3. A camada semântica entra no ar — BI e IA passam a consultar o DW
   através dela

---

<a id="visao-completa-projeto"></a>
## Visão completa do projeto

### Como o projeto funciona

```
Você (engenheiro)                          IA (agente)
─────────────────                          ─────────────
1. Entrega insumos (DDL, amostras, regras)
2. Valida documento de entendimento
3. Executa scripts no Oracle
4. Mantém PROJETO_RESUMO.md atualizado
                                              │
5. Recebe scripts SQL prontos ◄──────────────┘
6. Recebe atualizações do PROJETO_RESUMO.md
```

### O ciclo de vida do projeto

```
Fase 1 — Geração inicial (1h30 de trabalho)
  ├─ Você entrega insumos (DDL, amostras, regras, perguntas)
  ├─ IA gera 10 scripts SQL (views + CREATE + 8 inserts)
  ├─ Você executa no Oracle
  └─ IA preenche PROJETO_RESUMO.md com tudo

Fase 2 — Manutenção incremental (20-30 min por mudança)
  ├─ DW muda (nova tabela, coluna, regra)
  ├─ Você entrega a mudança para IA
  ├─ IA gera scripts de UPDATE/INSERT
  ├─ Você executa no Oracle
  └─ IA atualiza PROJETO_RESUMO.md

Fase 3 — Retomada (5 min)
  ├─ Abre PROJETO_RESUMO.md
  ├─ IA lê e entende o estado atual
  └─ Gera SQL correto baseado no projeto
```

---

<a id="projeto-resumo-fonte-verdade"></a>
## PROJETO_RESUMO.md — A fonte única da verdade

### O que é

Arquivo central que contém **todo o estado do projeto** em um único lugar:
- DDLs completos de todas as tabelas
- Amostras de dados
- Regras de aditividade
- Views analíticas com SQL
- Regras de negócio
- Perguntas dos usuários
- Histórico de mudanças

### Por que é importante

Com o PROJETO_RESUMO.md atualizado, você consegue:
- **Retomar o projeto** após meses sem perder contexto
- **Transferir responsabilidade** para outro engenheiro
- **Usar qualquer IA** (minha, Gemini, Claude) — basta entregar o arquivo
- **Auditar mudanças** através do histórico de versões

### Quando atualizar

**SEMPRE** que houver mudança no projeto:
- Nova tabela adicionada
- Coluna nova em tabela existente
- Regra de negócio alterada
- View criada ou removida
- Pergunta de usuário adicionada

A IA **sempre** atualiza o arquivo após validar as mudanças com você.

### Como funciona na prática

```
Muda no DW
  ↓
Você informa a IA (ex.: "adicionar coluna vl_desconto em FATO_X")
  ↓
IA gera scripts de UPDATE
  ↓
Você executa no Oracle
  ↓
IA atualiza PROJETO_RESUMO.md automaticamente
  ↓
Pronto. Tudo documentado.
```

---

<a id="manutencao-do-projeto"></a>
## Manutenção do projeto

### Cenário 1 — Nova tabela no DW

1. Extraia o DDL da nova tabela (`DBMS_METADATA.GET_DDL`)
2. Forneça 10 linhas de amostra
3. Informe aditividade das medidas
4. Entregue para a IA
5. IA gera scripts de UPDATE + atualiza PROJETO_RESUMO.md

### Cenário 2 — Coluna nova em tabela existente

1. Extraia o DDL atualizado da tabela
2. Forneça amostras da nova coluna
3. Informe aditividade da nova medida
4. Entregue para a IA
5. IA gera scripts de UPDATE + atualiza PROJETO_RESUMO.md

### Cenário 3 — Regra de negócio muda

1. Informe a nova regra (ex.: "não incluir cancelados")
2. IA gera scripts de UPDATE nas views
3. IA atualiza META_REGRA_NEGOCIO
4. IA atualiza PROJETO_RESUMO.md

### Cenário 4 — Pergunta nova dos usuários

1. Liste a nova pergunta em linguagem natural
2. IA gera INSERT para META_CONSULTA_NEGOCIO
3. IA gera SQL base para a pergunta
4. IA atualiza PROJETO_RESUMO.md

---

<a id="transferencia-responsabilidade"></a>
## Transferência de responsabilidade

### De engenheiro A para engenheiro B

1. **Entregue:** PROJETO_RESUMO.md + PROJETO_VERSION.md
2. **Engenheiro B lê:** PROJETO_RESUMO.md e entende tudo
3. **Engenheiro B executa:** scripts SQL no Oracle
4. **Engenheiro B mantém:** PROJETO_RESUMO.md atualizado

### De IA para IA

1. **Entregue:** PROJETO_RESUMO.md
2. **Nova IA lê:** arquivo e entende o estado atual
3. **Nova IA gera:** SQL correto baseado no projeto
4. **Nova IA atualiza:** PROJETO_RESUMO.md após mudanças

---

<a id="checklist-final-projeto"></a>
## Checklist final antes de entregar

- [ ] Pasta `entrega/` criada com subpastas `ddl/` e `amostras/`
- [ ] DDL completo com constraints e comentários
- [ ] Perfil dos dados com as 5 perguntas-armadilha respondidas
- [ ] ETL: documento ou as 6 respostas
- [ ] Regras de negócio: aditividade de TODAS as medidas marcada
- [ ] 10–20 perguntas de usuários
- [ ] Nada de credenciais ou dados sensíveis nos arquivos

<a id="checklist-manutencao"></a>
## Checklist de manutenção

- [ ] DDL atualizado (se houve mudança nas tabelas)
- [ ] Amostras atualizadas (se houve mudança nos dados)
- [ ] Regras de negócio atualizadas (se houve mudança)
- [ ] PROJETO_RESUMO.md atualizado (sempre!)
- [ ] PROJETO_VERSION.md atualizado (sempre!)

<a id="o-que-nao-fazer"></a>
## O que NÃO fazer

- ❌ Nunca execute scripts sem validar com a IA primeiro
- ❌ Nunca altere tabelas META_ diretamente no Oracle
- ❌ Nunca atualize o projeto sem atualizar o PROJETO_RESUMO.md
- ❌ Nunca entregue insumos incompletos (risco de SQL incorreto)

---

# 📋 Apêndice — Prompts Prontos para a IA

Este apêndice contém **prompts prontos** que você pode copiar e colar ao conversar com a IA (agente). Cada prompt é otimizado para uma situação específica.

> **Dica:** Substitua os valores entre `<colchetes>` pelas informações do seu projeto.

---

<a id="prompt-1-geracao-inicial"></a>
## 1. Geração Inicial do Projeto

### Prompt 1.1 — Iniciar projeto do zero

```
Iniciar projeto de camada semântica.

Schema Oracle: <SCHEMA_ALVO>
Projeto: <NOME_DO_PROJETO>

Insumos:
1. DDL das tabelas:
<cole aqui o DDL completo>

2. Amostras dos dados:
<cole aqui 10-20 linhas de cada tabela>

3. Regras de aditividade:
- <medida_1>: ADITIVA (pode somar livremente)
- <medida_2>: SEMI-ADITIVA (somar apenas se status = 'ATIVO')
- <medida_3>: NÃO-ADITIVA (não somar)

4. Perguntas dos usuários:
- <pergunta_1>
- <pergunta_2>
- ...

5. Regras de negócio específicas:
- <regra_1>
- <regra_2>
- ...

Gere os 4 scripts SQL (01 a 04) e preencha o PROJETO_RESUMO.md.
```

### Prompt 1.2 — Projeto com modelo complexo

```
Iniciar projeto de camada semântica com modelo complexo.

Schema Oracle: <SCHEMA_ALVO>
Projeto: <NOME_DO_PROJETO>

Características do modelo:
- Modelo estrela com <N> fatos e <N> dimensões
- Hierarquias: <descreva hierarquias>
- Valores sintéticos: <sim/não, descreva>
- Linhas de total: <sim/não, descreva>

Insumos:
1. DDL: <cole aqui>
2. Amostras: <cole aqui>
3. Aditividade: <descreva>
4. Perguntas: <liste>
5. Regras: <liste>

Gere os 4 scripts SQL e preencha o PROJETO_RESUMO.md.
```

---

<a id="prompt-2-nova-tabela"></a>
## 2. Manutenção — Nova Tabela

### Prompt 2.1 — Adicionar nova tabela FATO

```
Adicionar nova tabela FATO ao projeto existente.

Schema: <SCHEMA_ALVO>
Projeto: <NOME_DO_PROJETO>
Versão atual: <versão>

Nova tabela:
- Nome: FATO_<NOVO_FATO>
- DDL: <cole aqui o DDL completo>
- Amostras (10 linhas): <cole aqui>
- Grão: Uma linha representa <descreva>
- Medidas e aditividade:
  - <medida_1>: ADITIVA
  - <medida_2>: SEMI-ADITIVA
- Dimensões relacionadas:
  - DIM_<X> (via FK id_dim_x)
  - DIM_<Y> (via FK id_dim_y)

Perguntas relacionadas:
- <pergunta_1>
- <pergunta_2>

Gere scripts de UPDATE e atualize o PROJETO_RESUMO.md.
```

### Prompt 2.2 — Adicionar nova tabela DIM

```
Adicionar nova tabela DIM ao projeto existente.

Schema: <SCHEMA_ALVO>
Projeto: <NOME_DO_PROJETO>
Versão atual: <versão>

Nova dimensão:
- Nome: DIM_<NOVA_DIM>
- DDL: <cole aqui o DDL completo>
- Amostras (10 linhas): <cole aqui>
- Grão: Uma linha representa <descreva>
- Hierarquia:
  - Nível 1: <coluna>
  - Nível 2: <coluna>
  - Nível 3: <coluna>

Fatos relacionados:
- FATO_<X> (via FK id_dim)

Gere scripts de UPDATE e atualize o PROJETO_RESUMO.md.
```

---

<a id="prompt-3-coluna-nova"></a>
## 3. Manutenção — Coluna Nova

### Prompt 3.1 — Adicionar coluna em tabela FATO

```
Adicionar nova coluna em tabela FATO existente.

Schema: <SCHEMA_ALVO>
Projeto: <NOME_DO_PROJETO>
Versão atual: <versão>

Tabela alterada: FATO_<NOME>
Nova coluna:
- Nome: <coluna_nova>
- Tipo: <NUMBER/VARCHAR2/etc>
- Descrição: <descreva>
- Aditividade: <ADITIVA/SEMI-ADITIVA/NÃO-ADITIVA>

DDL atualizado:
<cole aqui o DDL completo atualizado>

Amostras da nova coluna:
<cole aqui 10 linhas>

Gere scripts de UPDATE nas views e atualize o PROJETO_RESUMO.md.
```

### Prompt 3.2 — Adicionar coluna em tabela DIM

```
Adicionar nova coluna em tabela DIM existente.

Schema: <SCHEMA_ALVO>
Projeto: <NOME_DO_PROJETO>
Versão atual: <versão>

Tabela alterada: DIM_<NOME>
Nova coluna:
- Nome: <coluna_nova>
- Tipo: <NUMBER/VARCHAR2/etc>
- Descrição: <descreva>

DDL atualizado:
<cole aqui o DDL completo atualizado>

Amostras da nova coluna:
<cole aqui 10 linhas>

Gere scripts de UPDATE nas views e atualize o PROJETO_RESUMO.md.
```

---

<a id="prompt-4-regras-negocio"></a>
## 4. Manutenção — Regras de Negócio

### Prompt 4.1 — Nova regra de negócio

```
Adicionar nova regra de negócio ao projeto existente.

Schema: <SCHEMA_ALVO>
Projeto: <NOME_DO_PROJETO>
Versão atual: <versão>

Nova regra:
- Regra: <descreva a regra em linguagem natural>
- Severidade: <CRITICA/ALERTA/INFORMATIVA>
- Contexto: <qual tabela/view a regra se aplica>
- Restrição: <qual filtro deve ser aplicado>

Exemplo:
- Regra: Não incluir processos cancelados no total anual
- Severidade: CRITICA
- Contexto: FATO_SEI_PROCESSO
- Restrição: WHERE status != 'CANCELADO'

Gere scripts de UPDATE nas views e atualize o PROJETO_RESUMO.md.
```

### Prompt 4.2 — Alterar regra existente

```
Alterar regra de negócio existente.

Schema: <SCHEMA_ALVO>
Projeto: <NOME_DO_PROJETO>
Versão atual: <versão>

Regra atual:
- Regra antiga: <descreva a regra antiga>
- Regra nova: <descreva a regra nova>
- Severidade: <CRITICA/ALERTA/INFORMATIVA>
- Contexto: <qual tabela/view>

Exemplo:
- Regra antiga: Incluir todos os processos no total
- Regra nova: Não incluir processos cancelados no total
- Severidade: CRITICA
- Contexto: FATO_SEI_PROCESSO

Gere scripts de UPDATE nas views e atualize o PROJETO_RESUMO.md.
```

---

<a id="prompt-5-perguntas-negocio"></a>
## 5. Manutenção — Perguntas de Negócio

### Prompt 5.1 — Adicionar perguntas novas

```
Adicionar novas perguntas de negócio ao projeto existente.

Schema: <SCHEMA_ALVO>
Projeto: <NOME_DO_PROJETO>
Versão atual: <versão>

Novas perguntas:
1. <pergunta_1>
2. <pergunta_2>
3. <pergunta_3>

Painéis relacionados (se houver):
- <pergunta_1> → <painel_1>
- <pergunta_2> → <painel_2>

Gere INSERTs para META_CONSULTA_NEGOCIO e atualize o PROJETO_RESUMO.md.
```

### Prompt 5.2 — Remover perguntas

```
Remover perguntas de negócio do projeto existente.

Schema: <SCHEMA_ALVO>
Projeto: <NOME_DO_PROJETO>
Versão atual: <versão>

Perguntas a remover:
- <id_consulta_1> (<pergunta_1>)
- <id_consulta_2> (<pergunta_2>)

Gere scripts de DELETE e atualize o PROJETO_RESUMO.md.
```

---

<a id="prompt-6-views"></a>
## 6. Manutenção — Views

### Prompt 6.1 — Criar nova view

```
Criar nova view analítica no projeto existente.

Schema: <SCHEMA_ALVO>
Projeto: <NOME_DO_PROJETO>
Versão atual: <versão>

Nova view:
- Nome: vw_<projeto>_<nome>
- Tipo: <DETALHE/RESUMO_TEMPO/RESUMO_DIMENSAO/EVOLUCAO/COMPOSICAO>
- Fato base: FATO_<NOME>
- Dimensões envolvidas: DIM_<X>, DIM_<Y>
- Grão: Uma linha representa <descreva>
- Aditividade: <ADITIVA/SEMI-ADITIVA/NÃO-ADITIVA>
- SQL base: <cole aqui o SQL desejado>

Gere a view com COMMENTs e atualize o PROJETO_RESUMO.md.
```

### Prompt 6.2 — Remover view

```
Remover view analítica do projeto existente.

Schema: <SCHEMA_ALVO>
Projeto: <NOME_DO_PROJETO>
Versão atual: <versão>

View a remover:
- Nome: vw_<projeto>_<nome>
- Motivo: <descreva por que está removendo>

Gere script de DROP VIEW e atualize o PROJETO_RESUMO.md.
```

---

<a id="prompt-7-validacao-auditoria"></a>
## 7. Validação e Auditoria

### Prompt 7.1 — Validar projeto completo

```
Validar projeto de camada semântica existente.

Schema: <SCHEMA_ALVO>
Projeto: <NOME_DO_PROJETO>
Versão atual: <versão>

Critérios de validação:
1. Views retornam linhas?
2. Aditividade está correta? (soma do detalhe = total)
3. Valores de domínio estão completos?
4. Relacionamentos funcionam?
5. Regras de negócio estão documentadas?

Gere queries de validação e relatório de inconsistências.
```

### Prompt 7.2 — Auditoria de mudanças

```
Gerar relatório de auditoria do projeto.

Schema: <SCHEMA_ALVO>
Projeto: <NOME_DO_PROJETO>
Versão atual: <versão>

Relatório deve conter:
1. Histórico completo de mudanças (versões)
2. Contagem de registros por META_
3. Contagem de views analíticas
4. Contagem de regras de negócio
5. Contagem de perguntas de negócio
6. Últimas atualizações

Gere o relatório em formato Markdown.
```

---

<a id="prompt-8-transferencia"></a>
## 8. Transferência de Responsabilidade

### Prompt 8.1 — Transferir para outro engenheiro

```
Transferir responsabilidade do projeto.

Schema: <SCHEMA_ALVO>
Projeto: <NOME_DO_PROJETO>
Versão atual: <versão>

Contexto para o novo engenheiro:
1. Leia o PROJETO_RESUMO.md para entender o estado atual
2. Leia o PROJETO_VERSION.md para entender o histórico
3. Os scripts SQL estão em inserts/ (vw_analiticas/, meta_projeto/)
4. Ordens de execução:
   - inserts/vw_analiticas/vw_<projeto>_dim_<nome>.sql → cria views DIM
   - inserts/vw_analiticas/vw_<projeto>_evento.sql → cria views EVENTO
   - inserts/vw_analiticas/vw_<projeto>_kpi_<nome>.sql → cria views KPI
   - inserts/meta_projeto/01_create_meta_tables.sql → cria tabelas META_
   - inserts/meta_projeto/01_meta_glossario.sql … 08_meta_valor_dominio.sql → insere dados semânticos (nesta ordem)
   - inserts/meta_projeto/02_rls.sql → RLS (só se houver acesso restrito)
   - inserts/meta_projeto/09_validacoes.sql → checagens de integridade e execução

Gere um resumo executivo para o novo engenheiro.
```

### Prompt 8.2 — Transferir para outra IA

```
Transferir projeto para outra IA.

Schema: <SCHEMA_ALVO>
Projeto: <NOME_DO_PROJETO>
Versão atual: <versão>

Contexto para a nova IA:
1. Leia o PROJETO_RESUMO.md para entender o estado atual
2. Leia o PROJETO_VERSION.md para entender o histórico
3. Os scripts SQL estão em inserts/ (vw_analiticas/, meta_projeto/)
4. Regras críticas:
   - Sempre atualizar PROJETO_RESUMO.md após mudanças
   - Nunca alterar META_ diretamente no Oracle
   - Validar scripts antes de executar
   - Gerar documentação em exemplo_tabelas/ antes de copiar para raiz

Gere um resumo técnico para a nova IA.
```

---

<a id="prompt-9-situacoes-especiais"></a>
## 9. Situações Especiais

### Prompt 9.1 — Dados foram atualizados (nova carga)

```
Dados foram atualizados no DW. Verificar impacto na camada semântica.

Schema: <SCHEMA_ALVO>
Projeto: <NOME_DO_PROJETO>
Versão atual: <versão>

Atualização:
- Data da carga: <data>
- Tabelas afetadas: <listar>
- Volume antes: <N> linhas
- Volume depois: <N> linhas
- Mudanças nos dados: <descreva>

Verificar se:
1. Novos valores de domínio aparecem
2. Novas categorias foram adicionadas
3. Regras de aditividade ainda se aplicam

Gere relatório de impacto.
```

### Prompt 9.2 — Erro em view analítica

```
View analítica está com erro.

Schema: <SCHEMA_ALVO>
Projeto: <NOME_DO_PROJETO>
Versão atual: <versão>

View com erro: vw_<projeto>_<nome>
Erro: <cole aqui a mensagem de erro>

SQL da view:
<cole aqui o SQL da view>

Tabelas envolvidas:
- FATO_<NOME>
- DIM_<NOME>

Debugue o erro e gere correção.
```

### Prompt 9.3 — Performance de view lenta

```
View analítica está lenta.

Schema: <SCHEMA_ALVO>
Projeto: <NOME_DO_PROJETO>
Versão atual: <versão>

View lenta: vw_<projeto>_<nome>
Tempo atual: <N> segundos
Tempo esperado: <N> segundos

SQL da view:
<cole aqui o SQL>

Sugira otimizações (índices, views materializadas, partições).
```

### Prompt 9.4 — Divergência de dados

```
Dados da view não batem com a fonte.

Schema: <SCHEMA_ALVO>
Projeto: <NOME_DO_PROJETO>
Versão atual: <versão>

View: vw_<projeto>_<nome>
Medida: <medida>
Valor esperado: <N>
Valor obtido: <N>
Diferença: <N>

SQL da view:
<cole aqui o SQL>

Debugue a divergência e sugira correção.
```

### Prompt 9.5 — Novo tipo de relatório

```
Novo tipo de relatório solicitado.

Schema: <SCHEMA_ALVO>
Projeto: <NOME_DO_PROJETO>
Versão atual: <versão>

Relatório solicitado:
- Descrição: <descreva o relatório>
- Pergunta: <pergunta do usuário>
- Fato base: FATO_<NOME>
- Dimensões: DIM_<X>, DIM_<Y>
- Filtros: <descreva filtros>
- Agrupamento: <descreva agrupamento>

Gere view analítica + INSERT para META_CONSULTA_NEGOCIO.
```

---

<a id="prompt-10-comandos-rapidos"></a>
## 10. Comandos Rápidos

### Prompt 10.1 — Status do projeto

```
Qual o status atual do projeto <NOME_DO_PROJETO>?
Gere resumo com:
- Versão atual
- Tabelas FATO/DIM
- Views analíticas
- Regras de negócio
- Perguntas de negócio
- Últimas mudanças
```

### Prompt 10.2 — Gerar script de backup

```
Gere script de backup das META_ do projeto <NOME_DO_PROJETO>.
Inclua:
- CREATE TABLE para backup de cada META_
- INSERT INTO para popular backups
- Instruções de restauração
```

### Prompt 10.3 — Gerar documentação

```
Gere documentação técnica do projeto <NOME_DO_PROJETO>.
Inclua:
- Diagrama do modelo
- DDLs das views
- DDLs das META_
- Regras de negócio
- Perguntas de negócio
```

---

<a id="prompt-11-rls"></a>
## 11. Regras de RLS (Row Level Security)

### Prompt 11.1 — Ativar RLS simples (filtro na view)

```
Ativar RLS simples no projeto existente.

Schema: <SCHEMA_ALVO>
Projeto: <NOME_DO_PROJETO>
Versão atual: <versão>

Configuração de RLS:
- Tipo: Acesso restrito por segmento
- Coluna de filtro: <coluna_na_tabela> (ex: nm_cidade)
- Tabela de mapeamento: usuario_segmentos

Mapeamento de usuários:
| Grupo de Usuários | Segmentos Permitidos | Coluna |
|---|---|---|
| analista_sp | SAO_PAULO | nm_cidade |
| analista_bh | BH | nm_cidade |
| analista_rj | RIO_JANEIRO | nm_cidade |
| gestor_geral | (acesso total) | — |

Views que precisam de filtro:
- vw_<projeto>_evento
- vw_<projeto>_resumo_tempo
- vw_<projeto>_resumo_<dimensao>

Gere:
1. CREATE TABLE usuario_segmentos
2. INSERTs com o mapeamento
3. UPDATE em todas as views (adiciona WHERE filtro)
4. INSERT para META_REGRA_NEGOCIO
5. Atualize o PROJETO_RESUMO.md
```

### Prompt 11.2 — Ativar RLS avançado (VPD + Função PL/SQL)

```
Ativar RLS avançado (VPD) no projeto existente.

Schema: <SCHEMA_ALVO>
Projeto: <NOME_DO_PROJETO>
Versão atual: <versão>

Configuração de RLS:
- Tipo: Acesso restrito com hierarquia
- Coluna de filtro: <coluna_na_tabela>
- Tabela de mapeamento: usuario_segmentos
- Implementação: Função PL/SQL (VPD)

Mapeamento de usuários:
| Grupo de Usuários | Segmentos Permitidos | Hierarquia |
|---|---|---|
| analista_sp | SAO_PAULO | Analista (só SP) |
| analista_bh | BH | Analista (só BH) |
| gestor_regional | SAO_PAULO, BH, RJ | Gestor (região Sudeste) |
| gestor_geral | (acesso total) | Diretor (tudo) |

Regras de sobreposição:
- [ ] Um usuário pode ver múltiplos segmentos
- [ ] Há hierarquia de acesso (gestor vê mais que analista)

Gere:
1. CREATE TABLE usuario_segmentos
2. INSERTs com o mapeamento
3. Função PL/SQL fn_rls_filtro_usuario
4. DBMS_RLS.ADD_POLICY para cada view
5. INSERT para META_REGRA_NEGOCIO
6. Atualize o PROJETO_RESUMO.md
```

### Prompt 11.3 — Alterar regra de RLS existente

```
Alterar regra de RLS no projeto existente.

Schema: <SCHEMA_ALVO>
Projeto: <NOME_DO_PROJETO>
Versão atual: <versão>

Alteração:
- Usuário/grupo: <nome_do_usuario>
- Segmentos antigos: <segmentos_antigos>
- Segmentos novos: <segmentos_novos>
- Coluna de filtro: <coluna>

Exemplo:
- Usuário: analista_sp
- Segmentos antigos: SAO_PAULO
- Segmentos novos: SAO_PAULO, CAMPINAS
- Coluna: nm_cidade

Gere:
1. UPDATE no usuario_segmentos
2. Atualize o PROJETO_RESUMO.md
```

### Prompt 11.4 — Remover RLS (voltar para acesso total)

```
Remover RLS do projeto existente (voltar para acesso total).

Schema: <SCHEMA_ALVO>
Projeto: <NOME_DO_PROJETO>
Versão atual: <versão>

Ação:
- Remover filtros de todas as views
- Manter tabela usuario_segmentos (para uso futuro)
- Remover política RLS das views

Views que precisam de UPDATE:
- vw_<projeto>_evento
- vw_<projeto>_resumo_tempo
- vw_<projeto>_resumo_<dimensao>

Gere:
1. UPDATE em todas as views (remove WHERE filtro)
2. DROP POLICY em todas as views
3. INSERT para META_REGRA_NEGOCIO (status REMOVIDA)
4. Atualize o PROJETO_RESUMO.md
```

### Prompt 11.5 — Consultar permissões de RLS

```
Consultar permissões de RLS do projeto existente.

Schema: <SCHEMA_ALVO>
Projeto: <NOME_DO_PROJETO>

Gere:
1. Relatório de todos os usuários e seus segmentos
2. Relatório de todas as views com filtros RLS
3. Relatório de políticas RLS ativas
4. Verificação de inconsistências (usuários sem segmentos, views sem filtro)
```

---

<a id="prompt-12-validacao-perguntas"></a>
## 12. Validação de Perguntas de Negócio (META_CONSULTA_NEGOCIO)

### Prompt 12.1 — Gerar perguntas para validação do engenheiro

```
Gerar perguntas de negócio para validação do engenheiro.

Schema: <SCHEMA_ALVO>
Projeto: <NOME_DO_PROJETO>
Versão atual: <versão>

Gere as perguntas de negócio a partir do modelo:
- Para cada fato + medida + dimensão: "Qual foi [medida] por [dimensão] em [período]?"
- Inclua SQL base para cada pergunta
- Agrupe por painel

IMPORTANTE: Não execute INSERTs ainda. Apenas gere o catálogo para validação.
```

### Prompt 12.2 — Validar SQL de cada pergunta

```
Validar SQL de cada pergunta de negócio.

Schema: <SCHEMA_ALVO>
Projeto: <NOME_DO_PROJETO>
Versão atual: <versão>

Perguntas para validar:
| ID | Pergunta | SQL Base | Status |
|----|----------|----------|--------|
| Q001 | Qual foi o total? | SELECT SUM(...) | ☐ OK ☐ Corrigir |
| Q002 | Por cidade? | SELECT ... GROUP BY | ☐ OK ☐ Corrigir |

Para cada pergunta marcada "Corrigir", informe:
- ID da pergunta
- SQL corrigido
- Motivo da correção

Após validação, gere INSERTs apenas para as perguntas aprovadas.
```

### Prompt 12.3 — Inserir perguntas validadas

```
Inserir perguntas de negócio validadas no projeto.

Schema: <SCHEMA_ALVO>
Projeto: <NOME_DO_PROJETO>
Versão atual: <versão>

Perguntas validadas (apenas estas):
| ID | Pergunta | SQL Validado | Painel |
|----|----------|--------------|--------|
| Q001 | Qual foi o total? | SELECT SUM(...) | visao_geral |
| Q002 | Por cidade? | SELECT ... GROUP BY | analise_cidade |

Gere INSERTs para META_CONSULTA_NEGOCIO apenas das perguntas aprovadas.
Atualize o PROJETO_RESUMO.md.
```

### Prompt 12.4 — Adicionar pergunta específica do domínio

```
Adicionar pergunta específica do domínio ao projeto.

Schema: <SCHEMA_ALVO>
Projeto: <NOME_DO_PROJETO>
Versão atual: <versão>

Pergunta específica:
- Pergunta: <pergunta em linguagem natural>
- SQL base: <SQL validado pelo engenheiro>
- Painel: <painel relacionado>
- Objetos chave: <tabelas/views envolvidas>

Gere INSERT para META_CONSULTA_NEGOCIO.
Atualize o PROJETO_RESUMO.md.
```

### Prompt 12.5 — Gerar relatório de perguntas pendentes

```
Gerar relatório de perguntas pendentes de validação.

Schema: <SCHEMA_ALVO>
Projeto: <NOME_DO_PROJETO>

Relatório deve conter:
1. Perguntas geradas automaticamente (não validadas)
2. Perguntas específicas do domínio (não inseridas)
3. Perguntas com SQL incorreto (requerem correção)
4. Resumo por painel

Gere checklist de validação para o engenheiro.
```

---

# Arquitetura em 3 Camadas

O projeto segue uma arquitetura em 3 camadas, inspirada no projeto SEI Municipal:

<a id="camada-1-dim"></a>
## Camada 1 — VIEWS DIM (versão vigente)

- Filtram apenas a versão vigente de cada dimensão SCD Type 2 (`dtc_expiracao IS NULL`)
- Grao: um registro por objeto vigente
- São usadas como base para as views EVENTO
- Exemplo: `vw_<projeto>_dim_<dimensao>_atual`

<a id="camada-2-evento"></a>
## Camada 2 — VIEWS EVENTO (camada intermediária)

- Normalizam os dados brutos em registros analíticos
- FATO + JOINs com DIMs (incluindo dimensões temporais)
- Incluem: SKs, datas calculadas, medidas, indicadores (ind_concluido, ind_em_aberto)
- São a BASE para gerar views KPI
- Exemplo: `vw_<projeto>_evento`

<a id="camada-3-kpi"></a>
## Camada 3 — VIEWS KPI (consolidadas)

- Consolidadas para responder perguntas específicas dos usuários
- Geradas a partir das views EVENTO e DIM
- Usam CTEs para cálculos (COUNT DISTINCT, SUM, AVG)
- Grao: depende do projeto (ex: por mês, por dia, por dimensão, etc.)
- Exemplo: `vw_<projeto>_kpi_<medida>_por_<dimensao>`

<a id="views-materializadas"></a>
## Views Materializadas (opcional)

- Para consultas pesadas com performance
- BUILD IMMEDIATE, REFRESH COMPLETE ON DEMAND
- Exemplo: `mv_<projeto>_kpi_<medida>_por_<dimensao>`

<a id="fluxo-dependencia"></a>
## Fluxo de Dependência

```
DIM (vw_<projeto>_dim_*_atual)
  ↓
EVENTO (vw_<projeto>_evento)
  ↓
KPI (vw_<projeto>_kpi_*)
  ↓
MV (mv_<projeto>_kpi_*) — opcional
```

<a id="como-ia-gera-views"></a>
## Como a IA gera as views

1. **Gera VIEWS DIM** — Filtra dimensões SCD Type 2 (dtc_expiracao IS NULL)
2. **Gera VIEWS EVENTO** — Join FATO + DIMs, inclui medidas e indicadores
3. **Gera VIEWS KPI** — CTEs com cálculos a partir de views EVENTO
4. **Gera VIEWS MATERIALIZADAS** — Opcional, para performance

<a id="quando-atualizar-resumo"></a>
## Quando atualizar o PROJETO_RESUMO.md

O engenheiro deve informar à IA quando terminar todas as alterações. A IA só atualiza o PROJETO_RESUMO.md após confirmação do engenheiro.

Exemplo de prompt:
```
Todas as alterações foram concluídas. Atualize o PROJETO_RESUMO.md com:
- DDLs atualizados
- Amostras atualizadas
- Regras atualizadas
- Views atualizadas
- Versão: <nova_versao>
```

---

<a id="dicas-uso-prompts"></a>
## Dicas de Uso dos Prompts

### ✅ Faça

- **Copie e cole** o prompt completo
- **Substitua** todos os `<colchetes>` pelas informações reais
- **Anexe** DDLs, amostras e regras no corpo do prompt
- **Valide** o resultado antes de executar no Oracle

### ❌ Não faça

- **Não omita** informações obrigatórias (DDL, amostras, aditividade)
- **Não execute** scripts sem validar com a IA primeiro
- **Não altere** META_ diretamente no Oracle
- **Não esqueça** de atualizar o PROJETO_RESUMO.md após mudanças

---

<a id="fluxo-trabalho-prompts"></a>
## Fluxo de Trabalho com Prompts

```
1. Identifique a situação (nova tabela, regra, view, etc.)
2. Encontre o prompt correspondente neste guia
3. Copie e cole o prompt
4. Substitua os <colchetes> pelas informações
5. Envie para a IA
6. Valide o resultado
7. Execute no Oracle (se aplicável)
8. Confirme que a IA atualizou o PROJETO_RESUMO.md
```
