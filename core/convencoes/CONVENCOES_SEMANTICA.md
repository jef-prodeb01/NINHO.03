# CONVENCOES_SEMANTICA.md — Dicionário de Convenções da Camada Semântica

> Objetivo: qualquer engenheiro ou IA que assuma o projeto deve
> conseguir prever o nome/tipo de uma coluna ou objeto sem precisar
> perguntar. Convenções novas devem ser adicionadas aqui, nunca
> deduzidas caso a caso.

## Prefixos de coluna

| Prefixo | Significado | Tipo Oracle típico |
|---|---|---|
| `sk_` | Chave substituta (surrogate key) de dimensão | `NUMBER` |
| `id_` | Identificador de negócio (natural key) | `NUMBER` ou `VARCHAR2` |
| `cd_` | Código curto de referência/domínio | `VARCHAR2` |
| `nm_` | Nome | `VARCHAR2` |
| `descricao_` | Descrição funcional (mais longa que `nm_`) | `VARCHAR2` |
| `dt_` | Data ou data+hora de negócio | `DATE` |
| `dtc_` | Data de controle/técnica (ex.: `dtc_expiracao` do SCD2) | `DATE` |
| `vl_` | Valor monetário ou numérico livre | `NUMBER` |
| `qt_` | Quantidade/contagem | `NUMBER` |
| `pct_` | Percentual | `NUMBER` |
| `ind_` | Indicador binário de negócio (S/N) | `CHAR(1)` |
| `categoria_` | Classificação/categoria de uma dimensão | `VARCHAR2` |

## Booleanos

Nunca usar `NUMBER(1)`/`BOOLEAN`. Sempre `CHAR(1) DEFAULT 'S' NOT NULL`
com domínio `'S'` / `'N'` (ver Seção "Armadilhas Oracle vs. Postgres"
do [README.md](../../modulos/camada_semantica/README.md)). Colunas booleanas começam com `ind_`.

## Nomenclatura de views (arquitetura em 3 camadas)

> ⚠️ **TUDO EM MAIÚSCULAS** — todos os identificadores de banco são gerados em MAIÚSCULAS.

| Camada | Padrão | Exemplo |
|---|---|---|
| DIM | `VW_<PROJETO>_DIM_<DIMENSAO>_ATUAL` | `VW_SEI_DIM_ORGAO_ATUAL` |
| EVENTO | `VW_<PROJETO>_EVENTO` (ou `VW_<PROJETO>_<FATO>_EVENTO` se houver mais de um fato) | `VW_SEI_EVENTO` |
| KPI | `VW_<PROJETO>_KPI_<MEDIDA>_POR_<DIMENSAO>` | `VW_SEI_KPI_PROCESSOS_POR_ORGAO_POR_MES` |
| Materializada | `MV_<PROJETO>_KPI_<MEDIDA>_POR_<DIMENSAO>` | `MV_SEI_KPI_PROCESSOS_POR_ORGAO_POR_MES` |

`<PROJETO>` é sempre o mesmo identificador curto (maiúsculo, sem acentos) em todas as views do projeto — nunca varie a sigla.

## Tabelas META_ e objetos semânticos

- `META_OBJETO.NOME_OBJETO` deve ser **idêntico** ao nome físico da view/tabela em maiúsculas (ex.: objeto físico `VW_SEI_EVENTO` → `NOME_OBJETO = 'VW_SEI_EVENTO'`). Isso é o que permite validar integridade entre META_ e o schema real (ver `saida/camada_semantica/meta_projeto/09_validacoes.sql`).
- `META_RELACIONAMENTO.OBJETO_ORIGEM`/`OBJETO_DESTINO` também devem bater exatamente com `META_OBJETO.NOME_OBJETO` — não são FKs de banco (o design é intencionalmente livre para não travar a ordem de carga), mas devem ser validadas com o script de validações.

## Coluna PROJETO nas Tabelas META_ (Multi-Projeto e RLS)

Todas as 8 tabelas `META_*` possuem a coluna:
`PROJETO VARCHAR2(50) DEFAULT 'GLOBAL' NOT NULL`

- **Metadados e Diretrizes Globais (`PROJETO = 'GLOBAL'`):**
  Utilizado para regras de modelagem universais, princípios gerais de IA e métricas/conceitos compartilhados entre todos os projetos do schema.
- **Metadados Específicos do Projeto (`PROJETO = '<PROJETO>'`):**
  Identifica objetos, métricas, consultas e regras que pertencem exclusivamente àquele projeto (ex.: `'SEI'`, `'SIPAR'`).
- **Comportamento com RLS por Projeto:**
  Quando a separação por projeto for solicitada, as views e políticas de acesso às tabelas `META_*` devem sempre carregar tanto as regras globais quanto as do projeto autorizado:
  `WHERE PROJETO IN ('GLOBAL', '<PROJETO>')` (ou via subquery contra `USUARIO_SEGMENTOS`).

## Idioma e formatação

- Todo conteúdo de negócio (comentários, glossário, regras, perguntas)
  em **português**.
- **Identificadores de banco em MAIÚSCULAS** — views, tabelas, colunas, aliases.
- SQL de consultas armazenado em `META_CONSULTA_NEGOCIO` sempre em
  `q'[...]'` (quoting alternativo Oracle), indentado para leitura no
  DBeaver/SQL Developer.

## Placeholders do template

| Placeholder | Substituir por |
|---|---|
| `<PROJETO>` | Sigla curta do projeto (MAIÚSCULA, sem acentos) |
| `<SCHEMA_ALVO>` | Nome do schema Oracle de destino |
| `<DIMENSAO>`, `<FATO>`, `<MEDIDA>` | Nome real do objeto/coluna do domínio (MAIÚSCULO) |

Nunca deixe um placeholder `<...>` sem substituir em scripts entregues
— é o primeiro item do checklist final em
[CHECKLIST_VALIDACAO.md](../../documentacao/checklists/CHECKLIST_VALIDACAO.md).

---

## Padrões de Qualidade de Código SQL nas Views e Catálogo

1. **Grão Canônico Obrigatório em `COMMENT ON TABLE`:**
   - Toda view analítica deve iniciar seu comentário com a declaração explícita do grão:
     `COMMENT ON TABLE VW_<PROJETO>_EVENTO IS 'Uma linha representa...';`
2. **Decodificação de Domínios com Fallback Seguro:**
   - Substituir siglas ou códigos obscuros da origem por `CASE WHEN ... ELSE 'NÃO IDENTIFICADO' END`, registrando também o mapeamento em `META_VALOR_DOMINIO`.
3. **Correção Semântica de Nomes Físicos Legados:**
   - Quando a tabela física contiver abreviações truncadas ou erros de grafia herdados da fonte (ex: `STA_DOCUMETO`, `DS_PROCEDIMETO`), a view deve expor o alias corporativo corrigido (`SITUACAO_DOCUMENTO`, `DS_PROCEDIMENTO`).
4. **Biblioteca Pergunta-SQL (`META_CONSULTA_NEGOCIO`):**
   - Utilizar bind variables tipadas (`:P_DT_INICIO`, `:P_DT_FIM`, `:P_COD_ORGAO`) com `CAST` explícito em CTE de entrada (`SELECT CAST(:P_DT_INICIO AS DATE) FROM DUAL`) para prevenir `ORA-00932`.
   - Preencher sempre `PAINEL_RELACIONADO` e `OBJETOS_CHAVE`.
5. **Proibição de Prefixos Banidos:**
   - Nunca utilizar prefixos `SEM_VW_`, `SEC_` ou `TST_` nos objetos entregues. As views seguem estritamente `VW_<PROJETO>_*` e `MV_<PROJETO>_*`.

---

## As 5 Dimensões de Validação para IA (Quality Gates Text-to-SQL)

| Dimensão | O que Avaliar | Critério de Aceite |
| :--- | :--- | :--- |
| **1. Sintaxe** | Compatibilidade Oracle 12c+ | Uso de `FETCH FIRST n ROWS ONLY` (sem `LIMIT`), maiúsculas, binds tipados e sem erros de parse. |
| **2. Semântica** | Consistência com o Negócio | Uso de fórmulas exatas de `META_METRICA`, respeito à aditividade (nunca somar taxa ou média) e joins de `META_RELACIONAMENTO`. |
| **3. Resultado** | Fidedignidade Numérica | Tratamento de nulos com `NVL`, sem divisões por zero (`NULLIF`), sem duplicações por joins em leque. |
| **4. Segurança** | Isolamento e Permissões | Isolamento estrito por tenant/órgão (RLS), proibição categórica de DDL/DML destrutivos (deny-by-default). |
| **5. Explicação** | Clareza para o Usuário | Justificativa em português claro explicando quais métricas, filtros e recortes foram aplicados. |

