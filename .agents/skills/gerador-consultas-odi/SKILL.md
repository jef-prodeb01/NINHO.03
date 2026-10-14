---
name: gerador-consultas-odi
description: Gera consultas analíticas SQL, procedures, mappings e pacotes para o Oracle Data Integrator (ODI 12c), além do Guia Completo de Implementação no Canvas (Procedures, Mapas, Pacotes e Cenários) e Diagnóstico de Tuning de Performance para projetos novos e legados. Use APENAS quando a opção Oracle Data Integrator (ODI 12c) estiver explicitamente marcada no INTAKE_DW.md ou ao solicitar análise de objetos ODI.
---

# Skill: Gerador de Consultas, Arquitetura e Tuning de Performance para Oracle Data Integrator (ODI 12c)

Esta skill orienta o agente em duas grandes frentes técnicas especializadas no **Oracle Data Integrator (ODI 12c)**:
1. **Frente 1 (Projetos Novos / Greenfield):** Geração de scripts SQL de extração, transformação dimensional (SCD Tipo 2, lookups com fallback `-1`, surrogate keys) e elaboração do **Guia Completo de Implementação no ODI 12c** cobrindo os 4 componentes: Procedures (`TRT_*`), Mapeamentos (`MAP_*`), Pacotes com Loop Multi-Tenant (`PACK_*`) e Cenários de Produção (`SCEN_*`).
2. **Frente 2 (Consultoria de Tuning em Projetos Existentes / Brownfield):** Auditoria estática de objetos ODI exportados (arquivos XML de Mapas, Pacotes, Procedures ou Session Logs de execução) para identificar anti-padrões e gargalos de performance, entregando o **Relatório de Diagnóstico & Plano de Tuning de Performance** para acelerar esteiras lentas.

> 🛑 **REGRA CONDICIONAL INVIOLÁVEL:**  
> Para geração em esteiras de novo DW, esta skill **SÓ PODE SER ACIONADA** se a opção `[x] Oracle Data Integrator (ODI 12c)` estiver assinalada na Seção 1 do [`INTAKE_DW.md`](../../../modulos/planejador_dw/INTAKE_DW.md).  
> Para consultoria de tuning em projetos existentes, pode ser acionada diretamente sob demanda do engenheiro mediante fornecimento do XML ou SQL do objeto.

---

## 🎯 Arquitetura de 2 Fases no ODI 12c

O processo de carga do Data Warehouse com ODI 12c é dividido em duas fases canônicas de alta performance:

### FASE 1: Extração de Origem para Staging (`STG_*`)
- **SQL de Origem:** CTEs com `WITH (NOLOCK)` (se SQL Server), filtros temporais (janelas ativas de N meses), eliminação de duplicidades via `DISTINCT` e tipagem estrita (`NUMBER` para dias/durações, **nunca** `TIMESTAMP`).
- **LKM:** `LKM SQL to Oracle (Built-In)` ou `LKM Oracle to Oracle Pull (DB Link)`.
- **IKM:** `IKM Oracle Insert` com opções físicas:
  - `TRUNCATE = False` (quando o truncate é gerenciado na Procedure de início do lote) ou `True` (em cargas isoladas)
  - `INSERT_HINT = /*+ APPEND */`
  - `FLOW_CONTROL = False` (elimina o overhead de CKM)

### FASE 2: Carga Dimensional da Staging para a Fato DW (`FATO_*`)
- **Ambiente:** Execução **100% interna Oracle para Oracle** no mesmo schema (`{SCHEMA_ALVO}`).
- **Zero LKM:** Nenhum LKM necessário (sem overhead de rede ou DBLink).
- **Resolução Dimensional:** Lookups dimensionais em dimensões SCD Tipo 2 (`DTC_EXPIRACAO IS NULL`) e dimensões conformadas (`DIM_TEMPO`).
- **Role-Playing Dimensions:** Uso de instâncias e aliases separados para dimensões reutilizadas (ex: `DIM_USR` executor e `DIM_USR_ATRIB` atribuído; `DIM_TEMPO_INI` e `DIM_TEMPO_FIM`).
- **Regra Inegociável do `-1`:** Aplicação de `NVL(dim.DIMENSION_KEY, -1)` para **TODAS** as FKs dimensionais, garantindo integridade referencial para registros nulos ou não encontrados.
- **IKM:** `IKM Oracle Insert` com Direct-Path Parallel (`/*+ APPEND PARALLEL(4) */`), atingindo milhões de linhas em minutos.

---

## 🧭 As 3 Estratégias de Implementação no ODI 12c

Ao documentar e gerar as esteiras de ODI, considere sempre as 3 estratégias de implementação:
1. **Estratégia 1 (View na Origem):** Quando a equipe tem permissão DDL no banco transacional. Mapeamento 1 para 1 direto no ODI.
2. **Estratégia 2 (100% Visual no Canvas Lógico):** **O padrão corporativo recomendado quando o acesso à origem é estritamente LEITURA (SELECT).** Modela todo o fluxo usando componentes nativos do ODI (`Datastore`, `Filtro`, `Distinto`, `Junção`, `Lookup`).
3. **Estratégia 3 (ODI Procedure Direta):** Script SQL/PL/SQL direto em uma procedure ODI para casos específicos de contingência.

---

## ⚡ As 7 Alavancas de Performance & Tuning no ODI 12c

Consulte o documento de referência completo: [Guia Avançado de Arquitetura e Tuning de Performance no ODI 12c](./references/guia_tuning_performance_odi.md).

1. **Eliminação do CKM (`FLOW_CONTROL = False`):** Desativar checagem de erros linha a linha via tabelas `$E_`.
2. **Direct-Path Insert (`/*+ APPEND PARALLEL(4) */`):** Gravação de blocos inteiros acima da High-Water Mark sem contenção de freelists.
3. **Desativação de Índices Secundários na Carga:** Procedure de Pré-Carga torna índices `UNUSABLE`. Pós-Carga reconstrói com `REBUILD PARALLEL 4 NOLOGGING`.
4. **Otimização de Loops Multi-Tenant:** Uso de loop controlado por variáveis (`V_CNT`, `V_MAX`) ou chamadas assíncronas paralelas via `OdiStartScen -ASYNC=YES`.
5. **Staging Area no Target:** Configuração física da Staging no schema do DW, eliminando tráfego de rede cruzado.
6. **Lookups Otimizados no Canvas:** Garantir `Lookup com Nulo Retornado = True` e índices na Staging para evitar `TABLE ACCESS FULL` repetidos.
7. **Coleta de Estatísticas Pós-Carga:** Execução única de `DBMS_STATS.GATHER_TABLE_STATS` pós-rebuild de índices.

---

---

## 🧠 Motor de Inteligência Preditiva de Tuning e CDC

A skill `gerador-consultas-odi` não atua apenas como geradora passiva de SQL, mas como um **Motor Preditivo Ativo**. Ao inspecionar qualquer mapeamento (XML, DDL, dicionário ou descrição de esteira), a skill executa automaticamente uma **Varredura Preditiva de 5 Heurísticas**:

### 1. Taxonomia Ampla de Datas e Detecção de Ciclo de Vida (Workflow)
- **Gatilho de Inspeção:** A origem pode conter:
  - **A. Auditoria Clássica:** `UPDATED_AT`, `DT_ALTERACAO`, `MODIFIED_DATE`.
  - **B. Ciclo de Vida de Workflow (Sem updated_at):** Pares de datas como `dth_abertura` (criação) e `dth_conclusao` (encerramento/atualização de estado), como na tabela `atividade` do SEI.
  - **C. Append-Only / Imutável:** Apenas data de criação (`dth_abertura`, `dth_registro`) com chave sequencial (`id_atividade`).
  - **D. Tabela sem Datas:** Cadastros estáticos (`unidade`, `tarefa`).
- **Anti-Padrão Previsto:** Carga Total (`TRUNCATE` + `INSERT` ou `Control Append`) trazendo 100% da base todos os dias. Em bases transacionais com dezenas de milhões de linhas, reprocessar tudo diariamente causa saturação de I/O, esgotamento de REDO/UNDO (`ORA-01555`) e cargas de 2 a 4 horas.
- **Prescrição Preditiva Especializada:**
  1. **Para Ciclo de Vida (Workflow):** Injetar filtro inteligente de 3 vias:
     ```sql
     (ORIGEM.dth_abertura >= TRUNC(SYSDATE) - 3 OR ORIGEM.dth_conclusao >= TRUNC(SYSDATE) - 3 OR ORIGEM.dth_conclusao IS NULL)
     ```
     *(Descarta o histórico estático concluído e traz apenas itens recentes + itens em aberto, reduzindo em >99% as linhas lidas).*
  2. **Para Auditoria Clássica:** Filtro direto com buffer deslizante: `UPDATED_AT >= TRUNC(SYSDATE) - 2`.
  3. **Para Append-Only:** Filtro por data de criação ou High-Water Mark de ID: `ID > #V_MAX_ID`.
  4. **Pré-requisito Obrigatório de Primary Key na Staging:** O ODI exige uma chave de correspondência para sincronizar linhas. A skill prescreve automaticamente o DDL de criação da PK na Staging (`ALTER TABLE STG_... ADD CONSTRAINT PK_... PRIMARY KEY (ID)`) e a configuração de `Target Key = PK` no ODI Canvas.
  5. **Seleção do IKM Ótimo (`IKM Oracle Merge`):** Prescrever `IKM Oracle Merge` em vez de `IKM Oracle Incremental Update`. O Merge resolve a carga em um único comando SQL atômico nativo no kernel do Oracle, evitando o duplo passo (Update correlacionado + Insert) do Incremental Update tradicional.

### 2. Detecção de Monolitos Multi-Fluxo
- **Gatilho de Inspeção:** Mais de 3 fluxos independentes de tabelas no mesmo canvas sem relacionamentos entre si.
- **Anti-Padrão Previsto:** Bloqueio serializado na JVM do ODI Agent — cadastros leves de 500 linhas ficam travados esperando tabelas pesadas de milhões de linhas terminarem.
- **Prescrição Preditiva:** Desacoplamento em mapeamentos atômicos e orquestração via Pacote com chamadas assíncronas paralelas (`OdiStartScen -ASYNC=YES`).

### 3. Detecção de Funil de I/O no Driver JDBC e Loops Multi-Tenant Intra-Oracle (H5 / H9)
- **Gatilho de Inspeção:** Transferência Oracle-para-Oracle configurada com `LKM SQL to Oracle (Built-In)` ou loop de schemas (`#V_SCHEMA` / `ODI_SCHEMA_CTRL` descobertos na mesma instância via `all_users`) recriando tabelas `C$_` a cada iteração.
- **Anti-Padrão Previsto:** Trafegar milhões de registros como objetos Java na memória heap do ODI Agent, executando `CREATE TABLE C$_` + bind row-by-row + `DROP TABLE C$_` para cada município/órgão.
- **Prescrição Preditiva:** Eliminar o `LKM SQL to Oracle` quando os schemas residirem no mesmo Oracle, realizando `INSERT /*+ APPEND */ INTO STG_... SELECT ... FROM #V_SCHEMA.TABELA` direto no banco (ou via `LKM Oracle to Oracle Pull (DB Link)` entre instâncias distintas).

### 4. Qualidade Dimensional em Cargas de Dimensões SCD2 e Tabelas Fato (H6 / H7 / H8)
- **H6 — Prevenção de Fan Trap em Lookups de Fato:** Todo join/lookup de Fato (`FATO_*` / `FAT_*`) contra dimensões SCD Tipo 2 (`DIM_*`) deve filtrar obrigatoriamente o registro ativo (`AND DIM.DTC_EXPIRACAO IS NULL`), evitando multiplicação de linhas quando houver histórico.
- **H7 — Integridade do Hash de Mudança SCD Tipo 2 (`DES_ATUALIZAR`):** Proibido fixar literal constante (`'X'`) na coluna `DES_ATUALIZAR` das tabelas `ODI_DIM_*`, pois isso torna a condição `STG.DES_ATUALIZAR <> DIM.DES_ATUALIZAR` sempre falsa e desativa o histórico SCD2. Utilizar sempre `STANDARD_HASH(col1 || '|' || col2, 'MD5')`.
- **H8 — Joins Temporais com `TRUNC()` e Agregação Estrita no `GROUP BY`:** Todo join de coluna `DATE`/`TIMESTAMP` com `DIM_TEMPO.DTC_COMPLETA` deve aplicar `TRUNC(coluna_data)`, e fórmulas de tempo/duração (`(DT_FIM - DT_INI) * 86400`) devem estar envolvidas em `SUM(...)` ou `AVG(...)`, nunca soltas na cláusula `GROUP BY`.

---

## 🤝 Protocolo de Alinhamento e Copiloto com o Engenheiro (Anti-Caixa-Preta)

Nenhum projeto de dados é idêntico a outro. Decisões arquiteturais críticas no ODI (estratégia de CDC, injeção de filtros de ciclo de vida, truncamento de staging, escolha de IKMs e particionamento) **não devem ser tomadas isoladamente pelo agente**.

O agente atua como um **Copiloto Consultivo**:
1. **Inspeção & Hipóteses:** O agente analisa os metadados, aciona as heurísticas e formula o diagnóstico preliminar.
2. **Pausa para Alinhamento:** Se houver volumetria massiva (>1M linhas), ausência de colunas óbvias de auditoria, ou regras de negócio implícitas, o agente **NÃO gera scripts físicos imediatamente**.
3. **Mesa de Discussão com o Engenheiro:** O agente apresenta:
   - O que foi detectado nos objetos/DDL;
   - As dúvidas e lacunas identificadas (ex: se o sistema transacional atualiza registros antigos, se há expurgo, se o DBA permite DDL na Staging);
   - As opções arquiteturais com seus prós, contras e riscos.
4. **Consenso & Construção a Quatro Mãos:** A experiência prática do engenheiro no ecossistema corporativo define o caminho ótimo.
5. **Geração Física Definitiva:** Somente após a validação explícita do engenheiro os scripts finais são gravados.

---

## 🛠️ Frente de Consultoria e Tuning de Projetos ODI Existentes

Quando o engenheiro fornecer um objeto ou diretório completo de um projeto legado para análise (XML de Mapa `MAP_*`, Cenário compilado `SCEN_*`, Pacote `PACK_*`, Procedure `TRT_*` ou Variável `VAR_*`):
1. **Auditoria Estática Automatizada via CLI (Arquivo Único ou Diretório Completo):**
   - Execute o script oficial v2.0 do NINHO:
     ```bash
     python core/scripts_comuns/auditar_mapa_odi.py <caminho_xml_ou_pasta_odi> --output <relatorio.md>
     ```
   - O auditor varre mapas, cenários compilados (`SnpScenTask`), pacotes, procedures e variáveis, aplicando as **9 Heurísticas Preditivas (`H1` a `H9`)**.
2. **Auditar o Objeto Manualmente (se fornecido via texto/SQL):**
   - Inspecione KMs e opções (`FLOW_CONTROL`, `INSERT_HINT`, `COMMIT`, `TRUNCATE`).
   - Avalie se há joins cartesianos ou falta de predicados sargáveis.
   - Verifique a estratégia de indexação e volume trafegado.
3. **Gerar Relatório de Diagnóstico Preditivo:**
   - Salvar em: `saida/planejador_dw/09_relatorio_estrategias/DIAGNOSTICO_TUNING_ODI_<OBJETO>.md`.
   - Incluir:
     - Resumo executivo dos gargalos de I/O e CPU.
     - As heurísticas acionadas com semáforo de gravidade.
     - Tabela De/Para de opções dos KMs a serem corrigidas no ODI Studio.
     - DDLs de Primary Key para a Staging.
     - Scripts PL/SQL de apoio (procedimentos de pré/pós carga, criação de índices na Staging).
     - Projeção de redução de tempo de execução.

---

## 📂 Destino Canônico de Saída

Ao ser acionada, os arquivos gerados devem ser salvos diretamente em:
- `saida/planejador_dw/03_dimensoes/03_selects_odi_dimensoes.sql` (Consultas de surrogate keys e SCD2 para dimensões).
- `saida/planejador_dw/04_fatos/04_select_odi_fato.sql` (Consulta consolidada com Lookups da Fato).
- `saida/planejador_dw/09_relatorio_estrategias/GUIA_IMPLEMENTACAO_ODI_<FATO>.md` (Roteiro passo a passo cobrindo Procedures, Mapeamentos, Pacotes e Cenários de Produção).
- `saida/planejador_dw/09_relatorio_estrategias/DIAGNOSTICO_TUNING_ODI_<OBJETO>.md` (Relatório de consultoria de tuning para objetos legados).

---

## 📐 Padrões Obrigatórios do ODI

1. **Uso de Sequences:** Sempre referenciar a sequence qualificada com aspas e schema:
   ```sql
   "SCHEMA_ALVO"."SEQ_DIM_NOME".NEXTVAL AS DIMENSION_KEY
   ```
2. **Tratamento de Nulos na Fato:** Proibido deixar FK nula:
   ```sql
   NVL(dp.DIMENSION_KEY, -1) AS DIM_PROJETO,
   NVL(dt.DIMENSION_KEY, -1) AS DIM_TEMPO
   ```
3. **Limpeza e Normalização com REGEXP:**
   ```sql
   UPPER(NVL(REGEXP_SUBSTR(CAMPO_TEXTO, '^([^-]+)', 1, 1, 'i', 1), CAMPO_TEXTO)) AS DES_SIGLA
   ```
4. **Função Analítica no Canvas para Fatos Snapshot (`ROW_NUMBER()`):**
   * Empregar o par `Componente Expressão (EXP_ANALITICA)` com `RN = ROW_NUMBER() OVER(PARTITION BY ... ORDER BY ... DESC)` + `Componente Filtro (RN = 1)` para extrair o estado mais recente no Canvas Lógico sem subqueries manuais.
5. **Lookups em Cadeia e "Lookup com Nulo Retornado":**
   * Quando uma chave depender de dimensão intermediária (ex: `STG -> DIM_USUARIO -> DIM_ORGAO`), encadear lookups.
   * Marcar **obrigatoriamente** `Lookup com Nulo Retornado = True` (Left Outer Join) para evitar o descarte silencioso de linhas.
6. **Tratamento de Vigências Abertas / Datas Nulas (`DIM_TEMPO_FIM = -1`):**
   * Mapear registros com data fim aberta (`DTH_FIM IS NULL`) com fallback para a linha `-1` da `DIM_TEMPO` (`DTC_COMPLETA = NULL`, `DES_MES = 'Não Informado / Vigente'`).
7. **Arquitetura de Fatos Híbridas para Tabelas Transacionais Massivas:**
   * Quando a fonte tiver dezenas/centenas de milhões de linhas, separar em Fato Histórica Agregada e Fato Snapshot Recente conforme [Arquitetura de Fatos Híbridas](../planejador-dw-oracle/references/arquitetura_fatos_hibridas.md).
8. **Decodificação de Domínios com Fallback Seguro:**
   * No componente Expressão do Canvas ODI, decodifique códigos de status transacionais para termos de negócio humanos com cláusula `ELSE` protetora:
     ```sql
     CASE ORIGEM.STA_TIPO
       WHEN '0' THEN 'INTERNO'
       WHEN '1' THEN 'SISTEMAS'
       WHEN '2' THEN 'EXTERNO - PENDENTE DE LIBERAÇÃO'
       WHEN '3' THEN 'EXTERNO'
       ELSE 'TIPO NÃO IDENTIFICADO'
     END
     ```
9. **Chaves Naturais Multi-Tenant via Variáveis ODI:**
   * Ao carregar múltiplos schemas/tenants para uma base consolidada compartilhada, evite colisões concatenando a variável de projeto/tenant:
     ```sql
     to_number(to_char(#PROJETO.V_TENANT) || '000' || to_char(ORIGEM.ID_CAMPO))
     ```
10. **Orquestração de Pacotes com Pré e Pós-Carga (`TRT_PRE_CARGA` e `TRT_POS_CARGA`):**
    * No ODI Package, posicione uma Procedure (`Technology: Oracle`) antes do Mapeamento executando `PRC_PRE_CARGA_FATOS` (desativa índices secundários para carga rápida com `INSERT /*+ APPEND */`), e outra Procedure pós-mapeamento executando `PRC_POS_CARGA_FATOS` (reconstrói índices com `REBUILD PARALLEL 4 NOLOGGING`, reverte para `NOPARALLEL LOGGING` e dispara `DBMS_STATS`).

Consulte os modelos estruturais em:
- [guia_tuning_performance_odi.md](./references/guia_tuning_performance_odi.md)
- [template_guia_implementacao_odi.md](./templates/template_guia_implementacao_odi.md)
- [template_selects_odi.sql](./templates/template_selects_odi.sql)
- [arquitetura_fatos_hibridas.md](../planejador-dw-oracle/references/arquitetura_fatos_hibridas.md)
