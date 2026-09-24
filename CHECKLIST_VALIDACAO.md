# Checklist de Validação Final

> **Atenção:** Este checklist deve ser executado ANTES de executar os scripts no Oracle.
> Cada item deve ser validado pelo engenheiro de dados.

---

## 1. Validação de Insumos e Estado do Schema

- [ ] Nome do projeto e Engenheiro responsável identificados
- [ ] Estado do schema verificado:
  - [ ] É a primeira execução no schema?
  - [ ] Tabelas `META_*` já existem no schema alvo?
- [ ] Se tabelas `META_*` já existem:
  - [ ] Execução de `01_create_meta_tables.sql` foi pulada (para não recriar tabelas)
  - [ ] Carga foi configurada para APENAS ACRESCENTAR (`MERGE INTO` / `WHERE NOT EXISTS`)
- [ ] DDL completo de todas as tabelas FATO e DIM
- [ ] Constraints de PK/FK presentes
- [ ] Comentários existentes incluídos
- [ ] Amostras de dados (10-20 linhas) de cada tabela
- [ ] Valores distintos das colunas categóricas
- [ ] Regras de aditividade de TODAS as medidas marcadas
- [ ] Perguntas dos usuários (10-20 perguntas)
- [ ] Regras de negócio específicas documentadas
- [ ] Regras de RLS definidas (se aplicável)

---

## 2. Validação de Views Analíticas

- [ ] `inserts/vw_analiticas/` gerado (views DIM, EVENTO, KPI)
- [ ] Todas as views têm COMMENT ON na tabela
- [ ] Todas as views têm COMMENT ON nas colunas
- [ ] Grão de cada view documentado
- [ ] Aditividade de cada view documentada
- [ ] Filtros de RLS incluídos (se aplicável)
- [ ] SQL testado e funcionando (SELECT COUNT(*))

---

## 3. Validação de CREATE TABLE (Apenas para Schemas Novos)

> **Atenção:** Se as tabelas `META_*` já existem no schema, pule esta seção.

- [ ] `inserts/meta_projeto/01_create_meta_tables.sql` gerado
- [ ] Todas as 8 META_ estão presentes com coluna `PROJETO DEFAULT 'GLOBAL' NOT NULL`
- [ ] Constraints de PK presentes (`PK_META_OBJETO` composta por `PROJETO, NOME_OBJETO`)
- [ ] Unique constraints presentes (`UK_META_ORIENTACAO_IA` por `PROJETO, SECAO, ORDEM`)
- [ ] DEFAULTs configurados (IND_ATIVO, IND_GOVERNADO, etc.)
- [ ] IDENTITY configurado (META_RELACIONAMENTO, META_REGRA_NEGOCIO, META_ORIENTACAO_IA, META_VALOR_DOMINIO)
- [ ] Comentários em todas as tabelas
- [ ] Comentários em todas as colunas

---

## 4. Validação de INSERTs

- [ ] `inserts/meta_projeto/01_meta_glossario.sql` gerado
- [ ] `inserts/meta_projeto/02_meta_metrica.sql` gerado
- [ ] `inserts/meta_projeto/03_meta_objeto.sql` gerado
- [ ] `inserts/meta_projeto/04_meta_relacionamento.sql` gerado
- [ ] `inserts/meta_projeto/05_meta_regra_negocio.sql` gerado
- [ ] `inserts/meta_projeto/06_meta_consulta_negocio.sql` gerado
- [ ] `inserts/meta_projeto/07_meta_orientacao_ia.sql` gerado
- [ ] `inserts/meta_projeto/08_meta_valor_dominio.sql` gerado

### Validação Específica por Arquivo

#### 01_meta_glossario.sql
- [ ] Sinônimos incluídos
- [ ] Exemplos de valores incluídos
- [ ] Regras de uso documentadas

#### 02_meta_metrica
- [ ] SQL das fórmulas testado
- [ ] Aditividade correta (ADITIVA, SEMI_ADITIVA, NAO_ADITIVA)
- [ ] Unidades de medida incluídas

#### 03_meta_objeto
- [ ] Governança documentada
- [ ] Vigência configurada
- [ ] Grao de cada objeto documentado

#### 04_meta_relacionamento
- [ ] Joins corretos (FKs do DDL)
- [ ] Cardinalidade correta (N:1, 1:1, 1:N)
- [ ] Tipo de join configurado (LEFT, INNER, RIGHT)

#### 05_meta_regra_negocio
- [ ] Severidade configurada (CRITICA, ALERTA, INFORMATIVA)
- [ ] Status configurado (HOMOLOGADA, PROVISORIA, PENDENTE)
- [ ] Contexto documentado

#### 06_meta_consulta_negocio
- [ ] SQL de CADA pergunta testado e validado
- [ ] Perguntas em linguagem natural claras
- [ ] Painéis organizados
- [ ] Objetos chave listados

#### 07_meta_orientacao_ia
- [ ] Catálogo completo com as **36 orientações de IA** incluído
- [ ] WORKFLOW documentado (ordens 1 a 9)
- [ ] PRINCIPIO configurado (ordens 1 a 11)
- [ ] VALIDACAO documentada (ordens 1 a 8)
- [ ] DESVIO configurado (ordens 1 a 3)
- [ ] RESPOSTA formatada (ordens 1 a 5)
- [ ] Execução idempotente com `MERGE INTO` (insere ou apenas acrescenta sem duplicar)

#### 08_meta_valor_dominio
- [ ] Valores de domínio completos
- [ ] Descrição de cada valor incluída
- [ ] IND_ATIVO configurado (S/N)

---

## 5. Validação de PROJETO_RESUMO.md

- [ ] DDLs completos de todas as tabelas
- [ ] Amostras de dados incluídas
- [ ] Regras de aditividade documentadas
- [ ] Mapa de relacionamentos incluído
- [ ] Views analíticas com SQL
- [ ] Regras de negócio documentadas
- [ ] Perguntas dos usuários listadas
- [ ] Regras de RLS documentadas (se aplicável)
- [ ] Histórico de mudanças preenchido

---

## 6. Validação de PROJETO_VERSION.md

- [ ] Versão atual preenchida
- [ ] Data preenchida
- [ ] Responsável preenchido
- [ ] Tabelas FATO/DIM listadas
- [ ] Views analíticas listadas
- [ ] Regras de negócio listadas
- [ ] Perguntas de negócio listadas
- [ ] Contagem de META_ preenchida
- [ ] Histórico de mudanças preenchido

---

## 7. Validação Final

- [ ] Nenhum placeholder `<...>` nos scripts
- [ ] Sintaxe Oracle 12c+ verificada
- [ ] VARCHAR2/CLOB/NUMBER corretos
- [ ] USER_* em vez de pg_catalog
- [ ] IDENTITY configurado
- [ ] COMMIT no final de cada arquivo
- [ ] Arquivos sem erros de sintaxe
- [ ] PROJETO_RESUMO.md atualizado
- [ ] PROJETO_VERSION.md atualizado

---

## 8. Execução no Oracle

### Ordem de Execução

```sql
-- 1. Criar views analíticas
@inserts/vw_analiticas/VW_<PROJETO>_DIM_<NOME>.sql
@inserts/vw_analiticas/VW_<PROJETO>_EVENTO.sql
@inserts/vw_analiticas/VW_<PROJETO>_KPI_<NOME>.sql

-- 2. Criar tabelas META_ (executar uma vez)
@inserts/meta_projeto/01_create_meta_tables.sql

-- 3. Inserir dados META_ (executar nesta ordem)
@inserts/meta_projeto/01_meta_glossario.sql
@inserts/meta_projeto/02_meta_metrica.sql
@inserts/meta_projeto/03_meta_objeto.sql
@inserts/meta_projeto/04_meta_relacionamento.sql
@inserts/meta_projeto/05_meta_regra_negocio.sql
@inserts/meta_projeto/06_meta_consulta_negocio.sql
@inserts/meta_projeto/07_meta_orientacao_ia.sql
@inserts/meta_projeto/08_meta_valor_dominio.sql

-- 4. RLS (opcional, somente se houver acesso restrito)
@inserts/meta_projeto/02_rls.sql

-- 5. Validações (sempre, após tudo acima)
@inserts/meta_projeto/09_validacoes.sql
```

- [ ] Views analíticas executadas com sucesso
- [ ] Tabelas META_ criadas com sucesso
- [ ] INSERTs executados com sucesso
- [ ] RLS aplicado com sucesso (se houver acesso restrito)
- [ ] Nenhum erro de constraint
- [ ] Nenhum erro de sintaxe

---

## 9. Validação Pós-Execução

- [ ] `inserts/meta_projeto/09_validacoes.sql` executado sem órfãos nem falhas de execução
- [ ] Contagem de registros por META_
- [ ] Teste de view (SELECT COUNT(*))
- [ ] Teste de consulta (SELECT * FROM META_CONSULTA_NEGOCIO)
- [ ] Teste de aditividade (soma do detalhe = total)
- [ ] Teste de RLS (usuários veem apenas segmentos autorizados)

---

## Checklist de Validação — Assinatura

| Papel | Nome | Data | Assinatura |
|-------|------|------|------------|
| Engenheiro de Dados | | | |
| Analista de Negócio | | | |
| Proprietário do Dado | | | |

---

## Observações

```
<cole aqui observações, pendências ou riscos>
```
