# PROJETO_RESUMO.md — Documentação Central do Projeto

> **Schema Oracle:** `<SCHEMA_ALVO>`
> **Projeto:** `<NOME_DO_PROJETO>`
> **Data de criação:** 2026-09-01
> **Última atualização:** 2026-09-01
> **Versão:** 1.0

> **Regra:** Este arquivo deve ser atualizado SEMPRE que houver mudança no projeto.
> É a "fonte única da verdade" para a IA gerar SQL correto.

---

## 0. Estrutura de Arquivos do Projeto

### 0.1 Scripts SQL

| Arquivo | Finalidade |
|---------|------------|
| `inserts/vw_analiticas/VW_<PROJETO>_DIM_<NOME>.sql` | Views DIM (uma por dimensão) |
| `inserts/vw_analiticas/VW_<PROJETO>_EVENTO.sql` | Views EVENTO (uma por fato) |
| `inserts/vw_analiticas/VW_<PROJETO>_KPI_<NOME>.sql` | Views KPI (uma por pergunta) |
| `inserts/meta_projeto/01_create_meta_tables.sql` | CREATE TABLE das 8 META_ |
| `inserts/meta_projeto/01_meta_glossario.sql` | INSERTs META_GLOSSARIO |
| `inserts/meta_projeto/02_meta_metrica.sql` | INSERTs META_METRICA |
| `inserts/meta_projeto/03_meta_objeto.sql` | INSERTs META_OBJETO |
| `inserts/meta_projeto/04_meta_relacionamento.sql` | INSERTs META_RELACIONAMENTO |
| `inserts/meta_projeto/05_meta_regra_negocio.sql` | INSERTs META_REGRA_NEGOCIO |
| `inserts/meta_projeto/06_meta_consulta_negocio.sql` | INSERTs META_CONSULTA_NEGOCIO |
| `inserts/meta_projeto/07_meta_orientacao_ia.sql` | INSERTs META_ORIENTACAO_IA |
| `inserts/meta_projeto/08_meta_valor_dominio.sql` | INSERTs META_VALOR_DOMINIO |
| `inserts/meta_projeto/02_rls.sql` | RLS opcional (só se houver acesso restrito) |
| `inserts/meta_projeto/09_validacoes.sql` | Checagens de integridade entre META_ e teste de execução das views/consultas |

### 0.2 Arquitetura em 3 Camadas

O projeto segue uma arquitetura em 3 camadas:

#### Camada 1 — VIEWS DIM (versão vigente)
- Filtram apenas a versão vigente de cada dimensão SCD Type 2 (`DTC_EXPIRACAO IS NULL`)
- Grao: um registro por objeto vigente
- São usadas como base para as views EVENTO
- Exemplo: `VW_<PROJETO>_DIM_<DIMENSAO>_ATUAL`

#### Camada 2 — VIEWS EVENTO (camada intermediária)
- Normalizam os dados brutos em registros analíticos
- FATO + JOINs com DIMs (incluindo dimensões temporais)
- Incluem: SKs, datas calculadas, medidas, indicadores (IND_CONCLUIDO, IND_EM_ABERTO)
- São a BASE para gerar views KPI
- Exemplo: `VW_<PROJETO>_EVENTO`

#### Camada 3 — VIEWS KPI (consolidadas)
- Consolidadas para responder perguntas específicas dos usuários
- Geradas a partir das views EVENTO e DIM
- Usam CTEs para cálculos (COUNT DISTINCT, SUM, AVG)
- Grao: depende do projeto (ex: por mês, por dia, por dimensão, etc.)
- Exemplo: `VW_<PROJETO>_KPI_<MEDIDA>_POR_<DIMENSAO>`

#### Views Materializadas (opcional)
- Para consultas pesadas com performance
- BUILD IMMEDIATE, REFRESH COMPLETE ON DEMAND
- Exemplo: `MV_<PROJETO>_KPI_<MEDIDA>_POR_<DIMENSAO>`

**Fluxo de dependência:**
```
DIM (VW_<PROJETO>_DIM_*_ATUAL)
  ↓
EVENTO (VW_<PROJETO>_EVENTO)
  ↓
KPI (VW_<PROJETO>_KPI_*)
  ↓
MV (MV_<PROJETO>_KPI_*) — opcional
```

### 0.3 Ordem de Execução

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

### 0.4 Regras de Manutenção

- ❌ Nunca execute INSERTs sem validar primeiro
- ❌ Nunca altere INSERTs diretamente no Oracle
- ✅ Sempre valide SQL das perguntas antes de executar 06_meta_consulta_negocio.sql
- ✅ Sempre atualize PROJETO_RESUMO.md após execução
- ✅ INSERTs ficam em arquivos separados — nunca misture CREATE com INSERT
- ✅ **O projeto só atualiza versão quando o engenheiro termina TODAS as alterações**
  - A IA só atualiza o PROJETO_RESUMO.md após confirmação explícita do engenheiro
  - Exemplo de prompt: "Todas as alterações foram concluídas. Atualize o PROJETO_RESUMO.md."

---

## 1. Visão Geral

### 1.1 Objetivo
Descrever o objetivo do projeto e o que a camada semântica responde.

### 1.2 Escopo
- **O que responde:** Lista de perguntas que o DW responde
- **O que NÃO responde:** Limites do modelo

### 1.3 Glossário de Negócio
| Termo | Definição |
|-------|-----------|
| Processo | Um pedido administrativo |
| Secretaria | Órgão responsável |

---

## 2. Tabelas FATO

### 2.1 FATO_<NOME>

**Grão:** Uma linha representa ___

**DDL:**
```sql
-- Cole aqui o DDL completo (CREATE TABLE + CONSTRAINTS + COMMENTS)
```

**Colunas:**
| Coluna | Tipo | PK/FK | Descrição | Aditividade |
|--------|------|-------|-----------|-------------|
| ID_FATO | NUMBER | PK | Chave primária | — |
| ID_DIMENSAO | NUMBER | FK | Chave estrangeira | — |
| VL_VALOR | NUMBER | — | Valor da medida | ADITIVA |
| QT_REGISTROS | NUMBER | — | Contagem | ADITIVA |

**Amostra (10 linhas):**
```sql
-- Cole aqui 10 linhas de exemplo
```

**Views geradas:**
- `VW_<PROJETO>_<FATO>_EVENTO` — Detalhe por evento
- `VW_<PROJETO>_<FATO>_RESUMO_TEMPO` — Evolução temporal
- `VW_<PROJETO>_<FATO>_RESUMO_<DIMENSAO>` — Agrupamento por dimensão

---

### 2.2 FATO_<NOME> (repetir para cada fato)

...

---

## 3. Tabelas DIM

### 3.1 DIM_<NOME>

**Grão:** Uma linha representa ___

**DDL:**
```sql
-- Cole aqui o DDL completo
```

**Colunas:**
| Coluna | Tipo | PK | Descrição |
|--------|------|----|-----------|
| ID_DIM | NUMBER | PK | Chave primária |
| NM_DIM | VARCHAR2 | — | Nome da dimensão |

**Hierarquia:**
```
Nível 1: NM_NIVEL1
  └─ Nível 2: NM_NIVEL2
      └─ Nível 3: NM_NIVEL3
```

**Amostra (10 linhas):**
```sql
-- Cole aqui 10 linhas de exemplo
```

---

### 3.2 DIM_<NOME> (repetir para cada dimensão)

...

---

## 4. Relacionamentos

### 4.1 Mapa de Joins

| Tabela Origem | Coluna Origem | Tabela Destino | Coluna Destino | Tipo Join | Cardinalidade |
|---------------|---------------|----------------|----------------|-----------|---------------|
| FATO_X | ID_DIM | DIM_Y | ID_DIM | LEFT | N:1 |

### 4.2 Diagrama de Relacionamentos

```
FATO_X ──(ID_DIM)──> DIM_Y
FATO_X ──(ID_ORGAO)──> DIM_ORGAO
FATO_X ──(ID_TEMPO)──> DIM_TEMPO
```

---

## 5. Views Analíticas

### 5.1 Views Detalhe

#### VW_<PROJETO>_EVENTO

**Grão:** Uma linha representa ___

**Aditividade:** ADITIVA / SEMI-ADITIVA / NÃO-ADITIVA

**SQL:**
```sql
-- Cole aqui o SQL da view
```

**Comentários:**
```sql
COMMENT ON TABLE VW_<PROJETO>_EVENTO IS '...';
COMMENT ON COLUMN VW_<PROJETO>_EVENTO.ID_FATO IS '...';
```

---

### 5.2 Views Resumo

#### VW_<PROJETO>_RESUMO_TEMPO

**Grão:** Uma linha representa ___ por período

**Aditividade:** ADITIVA

**SQL:**
```sql
-- Cole aqui o SQL da view
```

---

#### VW_<PROJETO>_RESUMO_<DIMENSAO>

**Grão:** Uma linha representa ___ por dimensão

**Aditividade:** ADITIVA

**SQL:**
```sql
-- Cole aqui o SQL da view
```

---

### 5.3 Views Materializadas (se houver)

#### MV_<PROJETO>_RESUMO

**Finalidade:** Performance para consultas pesadas

**Refresh:** DAILY / ON DEMAND

**SQL:**
```sql
-- Cole aqui o SQL da view materializada
```

---

## 6. Regras de Acesso (RLS — Row Level Security)

### 6.1 Visão Geral

- [ ] **Acesso total:** Usuários veem TODOS os dados
- [ ] **Acesso restrito:** Usuários veem APENAS parte dos dados

### 6.2 Filtros por Grupo de Usuários

| Grupo de Usuários | O que pode ver | Coluna da Tabela | Exemplo |
|---|---|---|---|
| `<grupo_1>` | Só `<segmento_1>` | `<coluna>` | `WHERE cidade = 'SAO_PAULO'` |
| `<grupo_2>` | Só `<segmento_2>` | `<coluna>` | `WHERE cidade IN ('BH', 'RJ')` |
| `<grupo_3>` | Acesso total | — | (sem filtro) |

### 6.3 Tabela por Tabela

| Tabela | Coluna de Filtro | Restrição |
|---|---|---|
| `<tabela>` | `<coluna>` | ☐ Por cidade ☐ Por secretaria ☐ Por órgão ☐ Outro |

### 6.4 Regras de Sobreposição

- [ ] Um usuário pode ver **múltiplos segmentos**?
- [ ] Segmentos são **exclusivos**?
- [ ] Há **hierarquia de acesso**? (gestor vê tudo, analista vê só uma área)

### 6.5 Implementação

- [ ] Função PL/SQL (VPD)
- [ ] Contexto de sessão (DBMS_SESSION)
- [ ] View com filtro
- [ ] Outro: <descreva>

---

## 7. Regras de Negócio

### 7.1 Regras de Aditividade

| Medida | Aditividade | Restrição |
|--------|-------------|-----------|
| VL_VALOR | ADITIVA | — |
| VL_DESCONTO | SEMI-ADITIVA | Somar apenas se CD_STATUS = 'APROVADO' |
| NM_STATUS | NÃO-ADITIVA | — |

### 7.2 Regras de Negócio Específicas

1. **Regra 1:** Não incluir processos cancelados no total anual
2. **Regra 2:** Valores sintéticos não devem ser somados
3. **Regra 3:** ...

---

## 8. Perguntas dos Usuários

### 8.1 Perguntas Geradas Automaticamente

| ID | Pergunta | Painel | SQL Base |
|----|----------|--------|----------|
| Q001 | Qual foi o total? | VISAO_GERAL | SELECT SUM(...) |

### 8.2 Perguntas Específicas do Domínio

| ID | Pergunta | Painel | SQL Base |
|----|----------|--------|----------|
| Q999 | Pergunta específica | PAINEL_ESPECIFICO | SELECT ... |

---

## 9. Histórico de Mudanças

### Versão 1.0 — 2026-09-01
- Criação do projeto
- Tabelas: FATO_X, DIM_Y
- Views: 5 views analíticas
- Regras: 3 regras cadastradas
- Perguntas: 15 perguntas

### Versão 1.1 — 2026-09-15
- **ADICIONADO:** FATO_VENDA_EXTRA
- **ATUALIZADO:** FATO_X (coluna VL_DESCONTO)
- **REMOVIDO:** VW_<PROJETO>_ANTIGO
- **REGRA ALTERADA:** "Não incluir cancelados"
- **PERGUNTA ADICIONADA:** "Média de processos por dia?"

### Versão 1.2 — 2026-10-01
...

---

## 10. Instruções de Execução

### 10.1 Ordem de Execução

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

### 10.2 Queries de Validação

```sql
-- Contagem das META_
SELECT COUNT(*) FROM META_GLOSSARIO;
SELECT COUNT(*) FROM META_METRICA;
SELECT COUNT(*) FROM META_OBJETO;
SELECT COUNT(*) FROM META_RELACIONAMENTO;
SELECT COUNT(*) FROM META_REGRA_NEGOCIO;
SELECT COUNT(*) FROM META_CONSULTA_NEGOCIO;
SELECT COUNT(*) FROM META_ORIENTACAO_IA;
SELECT COUNT(*) FROM META_VALOR_DOMINIO;

-- Teste de view
SELECT COUNT(*) FROM VW_<PROJETO>_EVENTO;

-- Teste de consulta
SELECT * FROM META_CONSULTA_NEGOCIO WHERE ID_CONSULTA = 'Q001';
```

---

## 11. Contatos e Responsáveis

| Papel | Nome | Contato |
|-------|------|---------|
| Engenheiro de Dados | ... | ... |
| Analista de Negócio | ... | ... |
| Proprietário do Dado | ... | ... |

---

## 12. Notas Adicionais

### 12.1 Armadilhas Conhecidas
- Dupla contagem em FATO_X quando JOIN com DIM_Y sem filtro de data
- Valores sintéticos em DIM_Y.CD_STATUS = '0'

### 12.2 Limitações do Modelo
- Não responde perguntas sobre períodos anteriores a 2020
- Não inclui dados de filiais desativadas

### 12.3 Próximos Passos
- [ ] Adicionar dimensão de produto
- [ ] Implementar view de composição
- [ ] Homologar regras de negócio
