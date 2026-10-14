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

## 2.1 💡 Radar Consultivo da IA: Expansão de KPIs, Regras de Negócio e Perguntas

Muitas vezes o cliente solicita um escopo inicial fechado ou enxuto sem perceber todo o potencial analítico das tabelas Fato e Dimensão do DW. Antes de gerar os scripts SQL finais, apresente no `DOCUMENTO_ENTENDIMENTO_<PROJETO>.md` dois blocos claramente separados:

1. **🎯 Escopo Solicitado pelo Cliente (Mandatório):**
   - Views `KPI`, métricas (`META_METRICA`), regras (`META_REGRA_NEGOCIO`) e perguntas (`META_CONSULTA_NEGOCIO`) explicitamente pedidas no `INTAKE_SEMANTICA.md` ou nos documentos da pasta `entrega/camada_semantica/`.
2. **💡 Radar Consultivo da IA (Sugestões Proativas para Aprovação):**
   - Inspecione todas as colunas de datas, prazos, status, unidades de origem/destino, responsáveis e valores das Fatos/Dimensões (utilizando `python core/scripts_comuns/inspecionar_ddl_origem.py --caminho entrega/camada_semantica/ddl/` quando houver DDLs) e proponha ao Engenheiro/Analista:
     - **Novos KPIs e Views `VW_<PROJETO>_KPI_*`:** Ex: *Lead Time / Tempo Médio de Ciclo*, *Estoque/Backlog em Aberto (`DTC_CONCLUSAO IS NULL`)*, *Faixas de Envelhecimento de Fila (Aging 0-15, 16-30, 31-60, >60 dias)*, *Taxa de Vazão (Throughput)*, *Cumprimento de SLA (%)*, *Taxa de Auto-Tramitação/Retrabalho* e *Variação Mensal (MoM) / Curva ABC (Pareto)*.
     - **Regras de Negócio e Qualidade Implícitas (`META_REGRA_NEGOCIO` / `META_ORIENTACAO_IA`):** Ex: *Sanitização de datas invertidas (`DTC_CONCLUSAO < DTC_ABERTURA`)*, *Segregação estrita entre consultas de fluxo concluído (`IS NOT NULL`) e passivo aberto (`IS NULL`)*, *Preservação de demandas sem responsável (`DIMENSION_KEY = -1`)* e *Proteção contra divisão por zero (`NULLIF`)*.
     - **Novas Perguntas de Negócio (`META_CONSULTA_NEGOCIO`) em 3 Horizontes:**
       1. *Horizonte Executivo/Estratégico:* Tendências mensais, cumprimento de metas/SLA e concentração de Pareto (80/20).
       2. *Horizonte Tático/Operacional:* Gestão de fila ativa, envelhecimento de passivo (Aging), demandas em risco de vencer e produtividade por equipe/colaborador.
       3. *Horizonte de Auditoria/Qualidade:* Detecção de anomalias cronológicas, gargalos de rota (Origem -> Destino) e demandas órfãs.
   - **Alinhamento antes do Código:** Pergunte ao Engenheiro quais itens do Radar Consultivo ele deseja aprovar para serem incluídos nas views `VW_*_KPI_*` e nos scripts `02_meta_metrica.sql`, `05_meta_regra_negocio.sql` e `06_meta_consulta_negocio.sql`.

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

