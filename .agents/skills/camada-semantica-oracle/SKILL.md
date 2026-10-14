---
name: camada-semantica-oracle
description: >-
  Modela e implementa a camada semântica sobre DW Oracle em 3 camadas
  (Views DIM vigentes, Views EVENTO e Views KPI), além de gerar os scripts DDL e INSERT
  das 8 tabelas META_* com suporte a multi-projeto e catálogo de 36 orientações de IA.
---

# Skill: Camada Semântica sobre DW Oracle

Esta skill guia o desenvolvimento da camada semântica corporativa sobre um Data Warehouse existente no Oracle Database.

## 1. Arquitetura em 3 Camadas

A modelagem de views analíticas segue rigorosamente a separação em 3 níveis:

```text
Camada 1: Views DIM Vigentes (VW_<PROJETO>_DIM_<NOME>_ATUAL)
    ↓ (Filtram WHERE DTC_EXPIRACAO IS NULL)
Camada 2: Views EVENTO Intermediárias (VW_<PROJETO>_EVENTO)
    ↓ (Unem Fato + Dimensões + Flags + Indicadores)
Camada 3: Views KPI de Alto Nível (VW_<PROJETO>_KPI_<MEDIDA>_POR_<DIM>)
      (Agregações diretas para dashboards e perguntas de negócio)
```

- **Documentação Mandatória de Grão:** Toda view deve ter comentário iniciando por `"Uma linha representa..."` para orientar LLMs e analistas.
- **Abstração de Legados:** Decodifique códigos com `CASE WHEN ... ELSE 'NÃO IDENTIFICADO'` e renomeie colunas legadas com erro ortográfico para nomes limpos e padronizados.
- **Validação em 5 Dimensões:** Toda consulta para IA deve atender aos gates de *Sintaxe*, *Semântica*, *Resultado*, *Segurança* e *Explicação*.

Consulte as convenções completas em [convencoes_semantica.md](./references/convencoes_semantica.md).

---

## 2. Catálogo de Metadados: As 8 Tabelas `META_*`

O schema semântico padronizado baseia-se em 8 tabelas centrais:
1. `META_GLOSSARIO`: Termos de negócio, sinônimos e definições em linguagem comum.
2. `META_METRICA`: Fórmulas homologadas, tipo de aditividade (`ADITIVA`, `SEMI_ADITIVA`, `NAO_ADITIVA`) e filtros obrigatórios.
3. `META_OBJETO`: Inventário de views e tabelas do DW com nível de sensibilidade e regras de uso.
4. `META_RELACIONAMENTO`: Caminhos homologados de join (chave origem -> chave destino, cardinalidade).
5. `META_REGRA_NEGOCIO`: Restrições e filtros de integridade (ex: exclusão de cancelados, status vigente).
6. `META_CONSULTA_NEGOCIO`: Catálogo de perguntas executivas com o SQL homologado correspondente.
7. `META_ORIENTACAO_IA`: Guia comportamental para LLMs e IAs consultarem o DW.
   - Consulte o catálogo completo das 36 diretrizes em [catalogo_orientacoes_ia.md](./references/catalogo_orientacoes_ia.md).
8. `META_VALOR_DOMINIO`: Domínio de valores válidos e códigos com descrição humana e flag de ativo.

---

## 3. Gestão de Carga: Schema Novo vs Schema Existente

Antes de gerar os scripts, verifique o estado do schema (Seção 0.2 do `INTAKE_SEMANTICA.md`):

### Cenário 1: Primeira Execução no Schema (Tabelas META_* Inexistentes)
- Gere o DDL das 8 tabelas: `saida/camada_semantica/meta_projeto/01_create_meta_tables.sql`.
- Gere os INSERTs completos (incluindo as 36 orientações `GLOBAL` de IA).

### Cenário 2: Tabelas META_* Já Existem no Schema (Reexecução ou Compartilhamento)
- 🛑 **NÃO gere nem tente executar CREATE TABLE.** Pule o script `01_create_meta_tables.sql`.
- Nos scripts `01_meta_glossario.sql` a `08_meta_valor_dominio.sql`:
  - Gere **APENAS ACRESCENTAR** utilizando `MERGE INTO` ou `WHERE NOT EXISTS`.
  - Vincule todas as novidades do projeto à coluna `PROJETO = '<NOME_PROJETO>'`.

---

## 4. Destino dos Artefatos Canônicos

Gere os arquivos diretamente nas pastas canônicas:
- Views SQL: `saida/camada_semantica/vw_analiticas/`
- Scripts de Metadados: `saida/camada_semantica/meta_projeto/`
- Script de Validação e Testes: `saida/camada_semantica/meta_projeto/09_validacoes.sql`
- Catálogo Corporativo: `documentacao/catalogo_projetos/PROJETO_RESUMO.md` e `PROJETO_VERSION.md`

