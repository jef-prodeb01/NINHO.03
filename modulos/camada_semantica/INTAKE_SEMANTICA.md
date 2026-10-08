# INTAKE — Formulário de coleta para construção da camada semântica

Preencha (ou anexe) o máximo que tiver. Com os itens obrigatórios já é
possível começar; os demais refinam o resultado.

---

## 0. Identificação do Projeto ☐ (obrigatório)

| Campo | Valor |
|---|---|
| **Nome do Projeto** (sigla curta em maiúsculas, ex: SEI, SIPAR) | `<informe o nome/sigla>` |
| **Engenheiro de Dados Responsável** | `<informe seu nome>` |
| **Schema Alvo no Oracle** | `<informe o schema de destino>` |
| **Primeira execução neste schema?** | `[ ] Sim  [ ] Não` |
| **Tabelas META_* já existem no schema?** | `[ ] Sim  [ ] Não` |
| **Se já existem, projetos já cadastrados:** | `<listar ou informar nenhum>` |
| **Data de Início** | `<AAAA-MM-DD>` |

---

## 1. DDL das fatos e dimensões ☐ (obrigatório)

Não cole o DDL aqui — gere com o **select único** da Seção 1 do
[GUIA_ENGENHEIRO_DADOS.md](GUIA_ENGENHEIRO_DADOS.md) (DDL + comentários
de todas as tabelas em uma consulta) e informe o caminho do arquivo:

```
<cole aqui>
```

## 2. Amostras dos dados ☐ (obrigatório)

Não cole os dados aqui — gere com as queries da Seção 2 do
[GUIA_ENGENHEIRO_DADOS.md](GUIA_ENGENHEIRO_DADOS.md) (inventário de
tabelas, candidatos a colunas categóricas, volume/período, distinct e
amostra de linhas) e informe o caminho da pasta:

```
<cole aqui>
```

Perguntas que as amostras ajudam a responder:
- Existem **linhas de total/subtotal** misturadas ao detalhe? (ex.: "Total Geral")
- Há **hierarquia** em códigos? (ex.: código `2110.01` filho de `2110`)
- Quais os **valores exatos** das colunas categóricas?

## 3. Relatório / documentação do ETL ☐ (recomendado)

```
<cole ou anexe>
```

O que procuro nele:
- Regras de carga (full reload? incremental?)
- De-paras e tratamentos (valores sintéticos criados no processo?)
- Problemas conhecidos (encoding, divergências entre fontes)
- Frequência de atualização e cobertura temporal

## 4. Regras de negócio do cliente ☐ (obrigatório)

```
<cole aqui>
```

Exemplos do formato ideal:
- "Medida X só pode ser somada dentro do mesmo nível da hierarquia Y"
- "O valor oficial do total é a linha Z, não a soma do detalhe"
- "Usuários da área A não podem ver dados da área B"
- "Valores estão em milhões / nominais / moeda de referência"

## 4.1 Regras de RLS (Row Level Security) ☐ (se aplicável)

**CRÍTICO:** Se múltiplos projetos/segmentos compartilham o mesmo DW, defina
quem pode ver o quê. Isso vira filtro automático nas views.

### 4.1.1 Visão geral

- [ ] **Acesso total:** Usuários veem TODOS os dados
- [ ] **Acesso restrito:** Usuários veem APENAS parte dos dados

### 4.1.2 Filtros por grupo de usuários

| Grupo de Usuários | O que pode ver | Coluna da tabela | Exemplo |
|---|---|---|---|
| `<grupo_1>` | Só `<segmento_1>` | `<coluna>` | `WHERE cidade = 'SAO_PAULO'` |
| `<grupo_2>` | Só `<segmento_2>` | `<coluna>` | `WHERE cidade IN ('BH', 'RJ')` |
| `<grupo_3>` | Acesso total | — | (sem filtro) |

### 4.1.3 Tabela por tabela

Para **cada tabela fato/dimensão** que precisa de filtro:

| Tabela | Coluna de filtro | Restrição |
|---|---|---|
| `<tabela>` | `<coluna>` | ☐ Por cidade ☐ Por secretaria ☐ Por órgão ☐ Outro |

### 4.1.4 Regras de sobreposição

- [ ] Um usuário pode ver **múltiplos segmentos**?
- [ ] Segmentos são **exclusivos**? (usuário vê APENAS um)
- [ ] Há **hierarquia de acesso**? (gestor vê tudo, analista vê só uma área)

### 4.1.5 Implementação

Como o RLS será feito?
- [ ] Função PL/SQL (VPD)
- [ ] Contexto de sessão (DBMS_SESSION)
- [ ] View com filtro
- [ ] Outro: <descreva>

---

## 5. Perguntas que os usuários querem responder ☐ (recomendado)

Liste as perguntas de negócio reais (linguagem do usuário, sem técnica):

```
1. <pergunta>
2. <pergunta>
...
```

Elas viram o conteúdo da `META_CONSULTA_NEGOCIO` (com SQL pronto + variantes).

---

## O que eu devolvo após receber os insumos

1. **Documento de entendimento** — grão, aditividade, hierarquias,
   relacionamentos e armadilhas identificadas (para sua validação)
2. **inserts/vw_analiticas/** — views `VW_*` prontas para o seu modelo
   (arquitetura em 3 camadas: DIM → EVENTO → KPI → MV)
3. **inserts/meta_projeto/01_create_meta_tables.sql** — CREATE TABLE das 8 META_
4. **inserts/meta_projeto/01_meta_glossario.sql** a **08_meta_valor_dominio.sql** — INSERTs das META_ (arquivos separados)
