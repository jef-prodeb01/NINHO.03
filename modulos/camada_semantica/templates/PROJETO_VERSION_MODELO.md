# PROJETO_VERSION.md — Histórico de Mudanças

> **Schema Oracle:** `<SCHEMA_ALVO>`
> **Projeto:** `<NOME_DO_PROJETO>`
> **Última atualização:** 2026-09-01

---

## Versão Atual: 1.0

**Data:** `<DATA>`
**Responsável:** `<NOME>`

### Resumo
- `<descreva o resumo da versão>`

### Tabelas FATO
| Tabela | Linhas (aprox.) | Última carga |
|--------|-----------------|--------------|
| `<FATO_1>` | `<qtde>` | `<data>` |
| `<FATO_2>` | `<qtde>` | `<data>` |

### Tabelas DIM
| Tabela | Linhas (aprox.) | Última carga |
|--------|-----------------|--------------|
| `<DIM_1>` | `<qtde>` | `<data>` |
| `<DIM_2>` | `<qtde>` | `<data>` |

### Views Analíticas
| View | Tipo | Regra de Aditividade |
|------|------|---------------------|
| `<VW_1>` | `<DETALHE/RESUMO>` | `<ADITIVA/SEMIADITIVA/NAO_ADITIVA>` |

### Views Materializadas
| View | Refresh | Regra |
|------|---------|-------|
| `<MV_1>` | `<ON_DEMAND/DAILY>` | `<regra>` |

### Regras de Negócio
| Regra | Severidade | Status |
|-------|------------|--------|
| `<regra_1>` | `<CRITICA/ALERTA/INFORMATIVA>` | `<HOMOLOGADA/PROVISORIA/PENDENTE>` |

### Perguntas de Negócio
| Total | Automáticas | Específicas |
|-------|-------------|-------------|
| `<total>` | `<auto>` | `<especificas>` |

### META_ — Contagem de Registros
| Tabela | Registros |
|--------|-----------|
| META_GLOSSARIO | `<qtde>` |
| META_METRICA | `<qtde>` |
| META_OBJETO | `<qtde>` |
| META_RELACIONAMENTO | `<qtde>` |
| META_REGRA_NEGOCIO | `<qtde>` |
| META_CONSULTA_NEGOCIO | `<qtde>` |
| META_ORIENTACAO_IA | `<qtde>` |
| META_VALOR_DOMINIO | `<qtde>` |

---

## Histórico de Mudanças

### Versão 1.0 — `<DATA>`
**Tipo:** CRIAÇÃO
**Responsável:** `<NOME>`

**Mudanças:**
- Criação do projeto
- Tabelas FATO: `<lista>`
- Tabelas DIM: `<lista>`
- Views: `<quantidade>` views analíticas
- Regras: `<quantidade>` regras cadastradas
- Perguntas: `<quantidade>` perguntas

**Scripts gerados:**
- `inserts/vw_analiticas/VW_<PROJETO>_DIM_<NOME>.sql`
- `inserts/vw_analiticas/VW_<PROJETO>_EVENTO.sql`
- `inserts/vw_analiticas/VW_<PROJETO>_KPI_<NOME>.sql`
- `inserts/meta_projeto/01_create_meta_tables.sql`
- `inserts/meta_projeto/01-08.sql`

**Arquivo PROJETO_RESUMO.md:** Versão inicial preenchida

---

### Versão 1.1 — 2026-09-15
**Tipo:** ADIÇÃO
**Responsável:** `<NOME>`

**Mudanças:**
- **ADICIONADO:** FATO_VENDA_EXTRA (nova tabela fato)
- **ATUALIZADO:** FATO_X (coluna VL_DESCONTO NUMBER)
- **REMOVIDO:** VW_<PROJETO>_ANTIGO (substituída por nova)
- **REGRA ALTERADA:** "Não incluir cancelados" → status HOMOLOGADA
- **PERGUNTA ADICIONADA:** "Média de processos por dia?"

**Impacto:**
- Views atualizadas: 2
- Regras atualizadas: 1
- Perguntas adicionadas: 1

**Scripts gerados:**
- `inserts/vw_analiticas/VW_<PROJETO>_DIM_<NOME>.sql` (UPDATE)
- `inserts/meta_projeto/05_meta_regra_negocio.sql` (UPDATE)
- `inserts/meta_projeto/06_meta_consulta_negocio.sql` (INSERT)

**Arquivo PROJETO_RESUMO.md:** Atualizado com DDLs e amostras

---

### Versão 1.2 — 2026-10-01
**Tipo:** ALTERAÇÃO
**Responsável:** `<NOME>`

**Mudanças:**
- ...

**Impacto:**
- ...

**Scripts gerados:**
- ...

**Arquivo PROJETO_RESUMO.md:** Atualizado

---


## Como Usar

### Para novos projetos
1. Copie este arquivo para o novo projeto
2. Preencha as informações da "Versão Atual"
3. Adicione entradas no "Histórico de Mudanças" a cada alteração

### Para atualizações incrementais
1. Atualize a "Versão Atual" com os dados mais recentes
2. Adicione uma nova entrada no "Histórico de Mudanças"
3. Atualize o PROJETO_RESUMO.md com DDLs, amostras e regras

### Para retomada de projeto
1. Leia o "Histórico de Mudanças" para entender a evolução
2. Consulte a "Versão Atual" para o estado atual
3. Abra o PROJETO_RESUMO.md para detalhes completos

---

## Notas de Versão

### Versão 1.0
- Projeto piloto
- Modelo estrela simples
- Sem views materializadas

### Versão 1.1
- Adição de nova fonte de dados
- Necessidade de views materializadas para performance

### Versão 1.2
- ...