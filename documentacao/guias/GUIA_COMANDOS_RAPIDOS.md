# Guia Central de Comandos Rápidos & Referência Operacional (Cheat Sheet)

> **Documento Oficial de Referência Operacional** — Plataforma NINHO  
> Este guia centraliza comandos, scripts, queries, rotinas e prompts para o **Planejador de DW**, a **Camada Semântica & Metadados Ativos**, **Apache Hop**, **Shell/ODI**, **Oracle Database**, **DAX/Power BI** e **Interações com IA**.

---

## 📑 Sumário Interativo de Comandos

Clique em qualquer tópico ou comando abaixo para navegar diretamente para a instrução correspondente:

- [1. Utilitários & Scripts Python da Plataforma](#1-utilitarios-python)
  - [1.1 Validador Pré-Voo de Insumos (Auditoria de Arquivos)](#11-validador-pre-voo)
  - [1.2 Gerador de Dados Sintéticos / Mock para Teste de BI](#12-gerador-mock-dados)
  - [1.3 Execução e Teste de Extratores de APIs REST](#13-extratores-python-api)
  - [1.4 Transicionador Automatizado (Planejador DW -> Camada Semântica)](#14-transicionador-dw-semantica)
- [2. Comandos Operacionais do Planejador de DW (Oracle)](#2-comandos-planejador-dw)
  - [2.1 Ordem Canônica de Execução dos DDLs Físicos](#21-ordem-execucao-ddls)
  - [2.2 Gerenciamento de Sequences e Surrogate Keys](#22-sequences-surrogate-keys)
  - [2.3 Carga e Validação da Linha Técnica -1 (Sentinela)](#23-registro-tecnico-menos-um)
  - [2.4 Manutenção e Expiração de Histórico SCD Tipo 2](#24-manutencao-scd2)
  - [2.5 Execução da Procedure de Pós-Carga (PRC_POS_CARGA_FATO)](#25-execucao-prc-pos-carga)
  - [2.6 Consultas de Auditoria e Métricas na TB_CONTROLE_CARGA](#26-auditoria-tb-controle-carga)
  - [2.7 Identificação e Correção de Registros Órfãos (Integridade)](#27-registros-orfaos)
  - [2.8 Manutenção e Reparticionamento de Fatos (Partições Range)](#28-manutencao-particoes-fato)
- [3. Comandos Operacionais da Camada Semântica & Metadados Ativos](#3-comandos-camada-semantica)
  - [3.1 Compilação e Consulta das Views Analíticas (DIM, EVENTO, KPI)](#31-views-analiticas)
  - [3.2 Criação e Estrutura das 8 Tabelas META_* de Catálogo](#32-criacao-tabelas-meta)
  - [3.3 Ordem de Execução dos DMLs nas Tabelas META_*](#33-carga-dml-tabelas-meta)
  - [3.4 Consultas no Catálogo Semântico para IA e Text-to-SQL](#34-consultas-catalogo-ia)
  - [3.5 Configuração e Testes de Segurança por Linha (RLS / VPD)](#35-seguranca-rls-vpd)
  - [3.6 Bateria Automatizada de Validações Semânticas (09_validacoes.sql)](#36-validacoes-semanticas)
- [4. Comandos de Servidor Linux, Shell, Apache Hop e ODI](#4-comandos-servidor-hop-odi)
  - [4.1 Execução de Pipelines (.hpl) via Apache Hop CLI](#41-execucao-pipeline-hop)
  - [4.2 Execução de Workflows (.hwf) com Captura de Erro](#42-execucao-workflow-hop)
  - [4.3 Sintaxe para Chamadas Remotas via OdiOSCommand (ODI)](#43-odioscommand-ssh)
  - [4.4 Monitoramento de Processos Hop e Memória JVM no Linux](#44-monitoramento-linux-hop)
  - [4.5 Exemplo de Crontab para Agendamento Noturno](#45-agendamento-cron-linux)
- [5. Diagnóstico, Tuning & Resolução de Problemas no Oracle (DBA / Data Engineer)](#5-diagnostico-tuning-oracle)
  - [5.1 Identificar e Matar Sessões Bloqueadoras (Locks e Deadlocks)](#51-locks-sessoes-bloqueadoras)
  - [5.2 Identificar e Reconstruir Índices UNUSABLE (NOLOGGING)](#52-rebuild-indices-unusable)
  - [5.3 Coleta de Estatísticas em Cascata com Paralelismo](#53-coleta-estatisticas-dbms-stats)
  - [5.4 Consultar Tamanho Físico e Espaço Ocupado por Tabelas/Índices](#54-tamanho-fisico-tablespace)
  - [5.5 Consultar Consultas Ofensoras e Consumo de Temp/PGA](#55-consultas-ofensoras-temp)
- [6. Fórmulas Canônicas DAX para o Analista de BI (Power BI)](#6-formulas-dax-powerbi)
  - [6.1 Divisão Segura contra Erros de Divisão por Zero](#61-dax-divisao-segura)
  - [6.2 Acumulado no Ano (Year-to-Date - YTD)](#62-dax-acumulado-ytd)
  - [6.3 Variações Periódicas (Month-over-Month & Year-over-Year %)](#63-dax-variacoes-mom-yoy)
  - [6.4 Médias Móveis e Janelas Deslizantes (Rolling 12M)](#64-dax-rolling-12m)
  - [6.5 Médias Ponderadas Seguras](#65-dax-media-ponderada)
  - [6.6 Filtros Seguros Preservando Contexto (KEEPFILTERS)](#66-dax-keepfilters)
- [7. Comandos Chaves de Interação & Portões de Decisão por Etapa (Engenheiro + IA)](#7-comandos-interacao-etapas)
  - [7.1 Etapa 1: Ingestão de Insumos & Profiling de Fontes (/inspecionar-fontes)](#71-etapa-insumos-profiling)
  - [7.2 Etapa 2: Definição do Grão e Processo de Negócio (/desafiar-grao)](#72-etapa-definicao-grao)
  - [7.3 Etapa 3: Classificação e Modelagem de Dimensões (/classificar-scd)](#73-etapa-modelagem-scd)
  - [7.4 Etapa 4: Arquitetura de Ingestão & Estratégia de Carga (/definir-estrategia-carga)](#74-etapa-estrategia-carga)
  - [7.5 Etapa 5: Revisão do Blueprint Técnico & Gate de Aprovação Formal (/gerar-blueprint)](#75-etapa-aprovacao-blueprint)
  - [7.6 Etapa 6: Geração Física & Testes de Integridade Referencial (/auditar-ddl)](#76-etapa-geracao-testes)
  - [7.7 Etapa 7: Handoff & Documentação Central Contínua (/concluir-dw ou /transicionar-semantica)](#77-etapa-handoff-transicao)
  - [7.8 Etapa 8: Modelagem da Camada Semântica & Catálogo Ativo (/iniciar-semantica)](#78-etapa-camada-semantica)
  - [7.9 Etapa 9: Diagnóstico Operacional & Manutenção em Produção (/diagnosticar-erro-carga)](#79-etapa-diagnostico-producao)
- [8. Biblioteca Master de Prompts Prontos para a IA no Chat](#8-prompts-ia-chat)
  - [8.1 Iniciar Planejamento de um Novo DW (Passo 1: Entendimento & Blueprint)](#81-prompt-planejar-dw)
  - [8.2 Aprovar Blueprint e Gerar Artefatos Físicos do DW (Passo 2)](#82-prompt-aprovar-gerar-dw)
  - [8.3 Criar a Camada Semântica & Catálogo Ativo (Views + 8 META_*)](#83-prompt-gerar-semantica)
  - [8.4 Gerar Guia Customizado de BI e Dicionário de Dados HTML](#84-prompt-guia-bi-dicionario)
  - [8.5 Diagnosticar Falhas em Cargas e Corrigir Pipelines](#85-prompt-diagnostico-erro-carga)
  - [8.6 Migrar Dimensão Normal para Histórico SCD Tipo 2](#86-prompt-migracao-scd2)

---

<a id="1-utilitarios-python"></a>
## 1. Utilitários & Scripts Python da Plataforma

<a id="11-validador-pre-voo"></a>
### 1.1 Validador Pré-Voo de Insumos (Auditoria de Arquivos)
> **Cenário:** Execute sempre antes de solicitar à IA a geração de um DW ou Camada Semântica. O validador checa integridade de pastas, formulários de intake preenchidos, encoding e presença de schemas fonte.

```bash
# Validar apenas os insumos do Planejador de DW
python core/scripts_comuns/validar_entrega.py dw

# Validar apenas os insumos da Camada Semântica
python core/scripts_comuns/validar_entrega.py semantica

# Validar TODOS os módulos da plataforma simultaneamente
python core/scripts_comuns/validar_entrega.py all
```
*Saída esperada:* `[SUCESSO] Auditoria concluida com 0 erros.`  
*Se houver erro:* O script aponta a linha e o arquivo exato que precisa de correção antes de rodar os modelos de IA.

---

<a id="12-gerador-mock-dados"></a>
### 1.2 Gerador de Dados Sintéticos / Mock para Teste de BI
> **Cenário:** O analista de BI precisa homologar o painel Power BI antes do término da implementação do ETL no banco. Gere dados aderentes ao Star Schema com distribuição de datas e chaves válidas.

```bash
# Gerar 100 linhas padrão com colunas canônicas
python core/scripts_comuns/gerar_mock_dados.py --linhas 100 --saida saida/mock_teste_bi.csv

# Gerar 5.000 linhas diretamente no diretório do projeto
python core/scripts_comuns/gerar_mock_dados.py --linhas 5000 --saida saida/planejador_dw/MEU_PROJETO/mock_fato_grande.csv

# Exibir ajuda e parâmetros disponíveis
python core/scripts_comuns/gerar_mock_dados.py --help
```

---

<a id="13-extratores-python-api"></a>
### 1.3 Execução e Teste de Extratores de APIs REST
> **Cenário:** O projeto possui fontes externas (APIs JSON/REST). Execute o extrator modular que busca os dados paginados e carrega na tabela de staging `STG_*` do Oracle.

```bash
# 1. Ativar o ambiente virtual Python
# No Linux / macOS:
source .venv/bin/activate
# No Windows (PowerShell):
.venv\Scripts\Activate.ps1
# No Windows (CMD):
.venv\Scripts\activate.bat

# 2. Executar o extrator de teste com dry-run (sem gravar no banco)
python saida/planejador_dw/<PROJETO>/07_extratores_python/extract_api_<entidade>.py --dry-run

# 3. Executar a extração real carregando na Staging
python saida/planejador_dw/<PROJETO>/07_extratores_python/extract_api_<entidade>.py --lote 20261001 --limite 10000
```

---

<a id="14-transicionador-dw-semantica"></a>
### 1.4 Transicionador Automatizado (Planejador DW -> Camada Semântica)
> **Cenário:** O Planejador de DW concluiu a modelagem dimensional. O pipeline contínuo da NINHO não permite retrabalho manual ou silos entre módulos. Execute o transicionador para copiar os DDLs, gerar o DDL consolidado `DDL_COMPLETO_DW_<PROJETO>.sql`, transferir amostras e relatórios para `entrega/camada_semantica/`, preencher o `INTAKE_SEMANTICA.md` e catalogar o projeto em `documentacao/catalogo_projetos/PROJETO_RESUMO.md` e `PROJETO_VERSION.md`.

```bash
# 1. Execução padrão (detecta projeto e schema automaticamente a partir do DW)
python core/scripts_comuns/transicionar_dw_para_semantica.py

# 2. Especificando o projeto e forçando sobrescrita limpa na entrega
python core/scripts_comuns/transicionar_dw_para_semantica.py --projeto SEI_BAHIA --forcar

# 3. Especificando projeto, schema e responsável explicitamente
python core/scripts_comuns/transicionar_dw_para_semantica.py --projeto COAPS_FINOPS --schema COAPS_OLAP --engenheiro "Carlos Silva"
```
*Saída esperada:* DDLs consolidados em `entrega/camada_semantica/ddl/`, amostras de dados em `amostras/`, relatórios em `relatorios_etl/`, `INTAKE_SEMANTICA.md` preenchido e auditoria pré-voo semântica aprovada.

---

<a id="2-comandos-planejador-dw"></a>
## 2. Comandos Operacionais do Planejador de DW (Oracle)

<a id="21-ordem-execucao-ddls"></a>
### 2.1 Ordem Canônica de Execução dos DDLs Físicos
> **Cenário:** Deploy inicial ou reconstrução do ambiente de Data Warehouse no schema de destino. **Respeite estritamente a ordem de dependência**:

```text
Ordem Obrigatória:
1. TABELA DE CONTROLE: 00_tb_controle_carga.sql
2. TABELAS DE STAGING: 01_stg_<tabelas>.sql
3. SEQUENCES E TRIGGERS: 02_seq_<tabelas>.sql
4. DIMENSÃO TEMPO:     03_dim_tempo.sql
5. DEMAIS DIMENSÕES:   03_dim_<entidades>.sql
6. REGISTROS -1:       04_insert_menos_um.sql
7. TABELAS FATOS:      05_fato_<processos>.sql
8. PROCEDURES PÓS-ETL: 08_procedures/prc_pos_carga_fato.sql
```

No **Oracle SQL*Plus** ou **SQLcl**, execute em lote:
```sql
-- Conectar no schema do DW
CONNECT usuario_dw/senha@ORCL_PROD;

-- Executar os scripts gerados
@saida/planejador_dw/<PROJETO>/00_tb_controle_carga.sql;
@saida/planejador_dw/<PROJETO>/01_stg_tabelas.sql;
@saida/planejador_dw/<PROJETO>/02_sequences.sql;
@saida/planejador_dw/<PROJETO>/03_dimensoes.sql;
@saida/planejador_dw/<PROJETO>/04_insert_menos_um.sql;
@saida/planejador_dw/<PROJETO>/05_fatos.sql;
@saida/planejador_dw/<PROJETO>/08_procedures/prc_pos_carga_fato.sql;
```

---

<a id="22-sequences-surrogate-keys"></a>
### 2.2 Gerenciamento de Sequences e Surrogate Keys
> **Cenário:** Criação de sequences para Surrogate Keys das dimensões com `NOORDER`, `CACHE 50` e verificação do próximo valor livre.

```sql
-- Criar sequence padrão para dimensão (iniciando em 1, pois -1 é inserido manualmente)
CREATE SEQUENCE "<SCHEMA>"."SEQ_DIM_<ENTIDADE>"
    START WITH 1
    INCREMENT BY 1
    NOCYCLE
    CACHE 50
    NOORDER;

-- Consultar próximo valor da sequence
SELECT "<SCHEMA>"."SEQ_DIM_<ENTIDADE>".NEXTVAL FROM DUAL;

-- Consultar último valor emitido
SELECT "<SCHEMA>"."SEQ_DIM_<ENTIDADE>".CURRVAL FROM DUAL;

-- Reiniciar a sequence após carga inicial de legado (ex: após maior SK existente)
ALTER SEQUENCE "<SCHEMA>"."SEQ_DIM_<ENTIDADE>" RESTART WITH 105420;
```

---

<a id="23-registro-tecnico-menos-um"></a>
### 2.3 Carga e Validação da Linha Técnica -1 (Sentinela)
> **Cenário:** O Star Schema **proíbe FKs nulas**. Quando um registro da Fato não encontra correspondente na dimensão, deve apontar para `-1` (*Não Informado / Não Aplicável*).

```sql
-- Inserir o registro técnico na dimensão (caso ainda não exista)
INSERT INTO "<SCHEMA>"."DIM_<ENTIDADE>" (
    SK_<ENTIDADE>,
    ID_<ENTIDADE>,
    DES_<CAMPO_TEXTO>,
    DTC_INICIO_VIGENCIA,
    DTC_EXPIRACAO,
    FLG_VERSAO_ATUAL
) 
SELECT 
    -1, 
    -1, 
    'NAO INFORMADO', 
    TO_DATE('1900-01-01', 'YYYY-MM-DD'), 
    NULL, 
    'S' 
FROM DUAL
WHERE NOT EXISTS (
    SELECT 1 FROM "<SCHEMA>"."DIM_<ENTIDADE>" WHERE SK_<ENTIDADE> = -1
);
COMMIT;

-- Query de Auditoria: Verificar se TODAS as dimensões possuem a linha -1
SELECT TABLE_NAME, 'PRESENTE' AS STATUS
FROM USER_TABLES
WHERE TABLE_NAME LIKE 'DIM_%'
  AND TABLE_NAME IN (
      SELECT SUBSTR(TABLE_NAME, 1, 30) FROM USER_TAB_COLUMNS WHERE COLUMN_NAME LIKE 'SK_%'
  );
```

---

<a id="24-manutencao-scd2"></a>
### 2.4 Manutenção e Expiração de Histórico SCD Tipo 2
> **Cenário:** Expiração da versão antiga e inserção da nova versão quando atributos rastreados de uma dimensão sofrem alteração no sistema de origem.

```sql
-- 1. Expirar a versão anterior definindo a DTC_EXPIRACAO e desativando a flag
UPDATE "<SCHEMA>"."DIM_<ENTIDADE>"
SET 
    DTC_EXPIRACAO = SYSDATE - (1/86400),
    FLG_VERSAO_ATUAL = 'N'
WHERE ID_<ENTIDADE> = :ID_ORIGEM
  AND FLG_VERSAO_ATUAL = 'S';

-- 2. Inserir a nova versão vigente com nova SK
INSERT INTO "<SCHEMA>"."DIM_<ENTIDADE>" (
    SK_<ENTIDADE>,
    ID_<ENTIDADE>,
    DES_NOME,
    DES_CATEGORIA,
    DTC_INICIO_VIGENCIA,
    DTC_EXPIRACAO,
    FLG_VERSAO_ATUAL
) VALUES (
    "<SCHEMA>"."SEQ_DIM_<ENTIDADE>".NEXTVAL,
    :ID_ORIGEM,
    :NOVO_NOME,
    :NOVA_CATEGORIA,
    SYSDATE,
    NULL,
    'S'
);
COMMIT;
```

---

<a id="25-execucao-prc-pos-carga"></a>
### 2.5 Execução da Procedure de Pós-Carga (PRC_POS_CARGA_FATO)
> **Cenário:** Após a carga da Fato, a procedure rebuilda índices locais, recalcula as estatísticas do CBO e expurga registros temporários da Staging.

```sql
-- Executar no SQL*Plus / DBeaver com exibição dos logs DBMS_OUTPUT:
SET SERVEROUTPUT ON SIZE UNLIMITED;

BEGIN
    "<SCHEMA>"."PRC_POS_CARGA_FATO"(
        p_ano_mes => '202610'  -- Parâmetro opcional para partição específica
    );
END;
/
```

---

<a id="26-auditoria-tb-controle-carga"></a>
### 2.6 Consultas de Auditoria e Métricas na TB_CONTROLE_CARGA
> **Cenário:** Consultar status das cargas diárias, identificar falhas, duração em segundos e taxa de registros por segundo.

```sql
-- Top 15 últimas execuções de ETL com throughput
SELECT 
    ID_CONTROLE,
    NOM_ROTINA,
    ID_LOTE,
    DTC_INICIO,
    DTC_FIM,
    ROUND((DTC_FIM - DTC_INICIO) * 86400, 1) AS DURACAO_SEG,
    QTD_REGISTROS_LIDOS,
    QTD_REGISTROS_INSERIDOS,
    QTD_REGISTROS_ERRO,
    CASE 
        WHEN (DTC_FIM - DTC_INICIO) * 86400 > 0 
        THEN ROUND(QTD_REGISTROS_INSERIDOS / ((DTC_FIM - DTC_INICIO) * 86400), 0)
        ELSE 0 
    END AS LINHAS_POR_SEG,
    DES_STATUS_EXECUCAO,
    DES_MENSAGEM_ERRO
FROM "<SCHEMA>"."TB_CONTROLE_CARGA"
ORDER BY DTC_INICIO DESC
FETCH FIRST 15 ROWS ONLY;

-- Buscar rotinas que falharam nas últimas 24 horas
SELECT NOM_ROTINA, ID_LOTE, DTC_INICIO, DES_MENSAGEM_ERRO
FROM "<SCHEMA>"."TB_CONTROLE_CARGA"
WHERE DES_STATUS_EXECUCAO = 'ERRO'
  AND DTC_INICIO >= SYSDATE - 1
ORDER BY DTC_INICIO DESC;
```

---

<a id="27-registros-orfaos"></a>
### 2.7 Identificação e Correção de Registros Órfãos (Integridade)
> **Cenário:** Verificar se existem chaves na tabela Fato apontando para Surrogate Keys inexistentes na Dimensão.

```sql
-- 1. Diagnóstico: Contar linhas da Fato sem pai na dimensão
SELECT COUNT(*) AS QTD_ORFAOS
FROM "<SCHEMA>"."FATO_<PROCESSO>" F
WHERE NOT EXISTS (
    SELECT 1 FROM "<SCHEMA>"."DIM_<ENTIDADE>" D
    WHERE D.SK_<ENTIDADE> = F.SK_<ENTIDADE>
);

-- 2. Remediação: Atualizar órfãos para a linha técnica sentinela -1
UPDATE "<SCHEMA>"."FATO_<PROCESSO>" F
SET F.SK_<ENTIDADE> = -1
WHERE NOT EXISTS (
    SELECT 1 FROM "<SCHEMA>"."DIM_<ENTIDADE>" D
    WHERE D.SK_<ENTIDADE> = F.SK_<ENTIDADE>
);
COMMIT;
```

---

<a id="28-manutencao-particoes-fato"></a>
### 2.8 Manutenção e Reparticionamento de Fatos (Partições Range)
> **Cenário:** Operações em Fatos particionadas por mês (`P_YYYYMM`) no Oracle.

```sql
-- 1. Consultar as partições existentes e volume de linhas
SELECT 
    PARTITION_NAME, 
    HIGH_VALUE, 
    NUM_ROWS, 
    LAST_ANALYZED
FROM USER_TAB_PARTITIONS
WHERE TABLE_NAME = 'FATO_<PROCESSO>'
ORDER BY PARTITION_POSITION;

-- 2. Adicionar partição para um novo mês
ALTER TABLE "<SCHEMA>"."FATO_<PROCESSO>"
    ADD PARTITION P_202611 VALUES LESS THAN (20261201);

-- 3. Truncar uma partição específica para recarga limpa (Direct-path)
ALTER TABLE "<SCHEMA>"."FATO_<PROCESSO>"
    TRUNCATE PARTITION P_202610 UPDATE INDEXES;

-- 4. Excluir (Drop) partição antiga após expiração de política de retenção
ALTER TABLE "<SCHEMA>"."FATO_<PROCESSO>"
    DROP PARTITION P_202112 UPDATE INDEXES;
```

---

<a id="3-comandos-camada-semantica"></a>
## 3. Comandos Operacionais da Camada Semântica & Metadados Ativos

<a id="31-views-analiticas"></a>
### 3.1 Compilação e Consulta das Views Analíticas (DIM, EVENTO, KPI)
> **Cenário:** As views semânticas padronizam as regras de negócio em 3 níveis (Views Dimensão Vigente, Views Evento e Views KPI consolidadas).

```sql
-- 1. Consultar a visão vigente de uma dimensão (sem histórico expirado)
SELECT * 
FROM "<SCHEMA>"."VW_<PROJETO>_DIM_<ENTIDADE>_ATUAL"
FETCH FIRST 10 ROWS ONLY;

-- 2. Consultar a visão analítica de evento (Fato com nomes amigáveis em português)
SELECT 
    NUM_ANO_MES,
    DES_ENTIDADE,
    DES_CANAL,
    VLR_TOTAL_RECEITA,
    QTD_EVENTOS
FROM "<SCHEMA>"."VW_<PROJETO>_EVENTO"
WHERE DTC_EVENTO >= TRUNC(SYSDATE, 'MM')
FETCH FIRST 20 ROWS ONLY;

-- 3. Consultar a visão de KPI corporativo homologado
SELECT * 
FROM "<SCHEMA>"."VW_<PROJETO>_KPI_DESEMPENHO"
ORDER BY ANO_MES DESC;
```

---

<a id="32-criacao-tabelas-meta"></a>
### 3.2 Criação e Estrutura das 8 Tabelas META_* de Catálogo
> **Cenário:** O catálogo ativo armazena regras, métricas e orientações de IA dentro do Oracle. Execute o script mestre uma única vez no início do projeto.

```sql
-- Executar o DDL das 8 tabelas e triggers de auditoria
@modulos/camada_semantica/templates/01_create_meta_tables.sql;

-- Verificar se as 8 tabelas foram criadas com sucesso no schema
SELECT TABLE_NAME, STATUS, NUM_ROWS 
FROM USER_TABLES
WHERE TABLE_NAME LIKE 'META_%'
ORDER BY TABLE_NAME;
```
*Tabelas geradas:*
1. `META_GLOSSARIO` (Conceitos, sinônimos, termos de negócio)
2. `META_METRICA` (Fórmulas, regras de aditividade, filtros mandatórios)
3. `META_CONSULTA_NEGOCIO` (Perguntas em linguagem natural e SQL validado)
4. `META_OBJETO` (Tabelas e views governadas com grão e vigência)
5. `META_RELACIONAMENTO` (Mapeamento de PK/FK e cardinalidade de joins)
6. `META_REGRA_NEGOCIO` (Regras de validação, severidade e status)
7. `META_VALOR_DOMINIO` (Domínios aceitos por coluna: ex: 'A'=Ativo, 'I'=Inativo)
8. `META_ORIENTACAO_IA` (Roteiro, princípios e restrições para assistentes de IA)

---

<a id="33-carga-dml-tabelas-meta"></a>
### 3.3 Ordem de Execução dos DMLs nas Tabelas META_*
> **Cenário:** Carga dos metadados gerados pela IA a partir do `INTAKE_SEMANTICA.md`. Execute rigorosamente nesta ordem:

```sql
-- Conectar na pasta do projeto: saida/camada_semantica/meta_projeto/
@01_meta_glossario.sql;
@02_meta_metrica.sql;
@03_meta_objeto.sql;
@04_meta_relacionamento.sql;
@05_meta_regra_negocio.sql;
@06_meta_consulta_negocio.sql;
@07_meta_orientacao_ia.sql;
@08_meta_valor_dominio.sql;
COMMIT;
```

---

<a id="34-consultas-catalogo-ia"></a>
### 3.4 Consultas no Catálogo Semântico para IA e Text-to-SQL
> **Cenário:** Um assistente de IA ou engenheiro precisa descobrir como calcular uma métrica oficial ou quais relacionamentos usar sem abrir o código fonte.

```sql
-- 1. Localizar métricas e suas fórmulas SQL oficiais por palavra-chave
SELECT NOME_METRICA, TIPO_ADITIVIDADE, FORMULA_SQL, FILTROS_OBRIGATORIOS
FROM META_METRICA
WHERE PROJETO IN ('GLOBAL', '<NOME_PROJETO>')
  AND UPPER(NOME_METRICA) LIKE '%RECEITA%';

-- 2. Extrair relacionamentos para montar Joins automáticos
SELECT OBJETO_ORIGEM, COLUNA_ORIGEM, TIPO_JOIN, OBJETO_DESTINO, COLUNA_DESTINO, CARDINALIDADE
FROM META_RELACIONAMENTO
WHERE PROJETO IN ('GLOBAL', '<NOME_PROJETO>');

-- 3. Obter orientações de prompt e workflow para o modelo de IA
SELECT SECAO, ORDEM, TITULO, CONTEUDO
FROM META_ORIENTACAO_IA
WHERE PROJETO IN ('GLOBAL', '<NOME_PROJETO>')
ORDER BY SECAO, ORDEM;
```

---

<a id="35-seguranca-rls-vpd"></a>
### 3.5 Configuração e Testes de Segurança por Linha (RLS / VPD)
> **Cenário:** Usuários só podem enxergar os dados do seu próprio órgão/segmento. O filtro é aplicado dinamicamente via `SYS_CONTEXT`.

```sql
-- 1. Cadastrar permissão de um usuário para visualização restrita
INSERT INTO USUARIO_SEGMENTOS (USUARIO_ORACLE, SEGMENTO, IND_ACESSO_TOTAL)
VALUES ('ANALISTA_FINANCAS', 'DIRETORIA_FINANCEIRA', 'N');
COMMIT;

-- 2. Cadastrar usuário gestor com acesso irrestrito
INSERT INTO USUARIO_SEGMENTOS (USUARIO_ORACLE, SEGMENTO, IND_ACESSO_TOTAL)
VALUES ('DIRETOR_GERAL', 'TODOS', 'S');
COMMIT;

-- 3. Testar a view de segurança simulando a sessão do usuário
EXEC PKG_<PROJETO>_SEGURANCA.DEFINIR_CONTEXTO;

-- 4. Testar a consulta com RLS ativo
SELECT DISTINCT DES_SEGMENTO, COUNT(*) AS TOTAL_LINHAS
FROM "<SCHEMA>"."VW_<PROJETO>_EVENTO"
GROUP BY DES_SEGMENTO;
```

---

<a id="36-validacoes-semanticas"></a>
### 3.6 Bateria Automatizada de Validações Semânticas (09_validacoes.sql)
> **Cenário:** Auditoria completa antes de entregar o catálogo semântico para produção. Detecta objetos inexistentes, métricas sem fórmula e regras pendentes.

```sql
-- Executar no SQL Developer / DBeaver
SET SERVEROUTPUT ON SIZE UNLIMITED;
@modulos/camada_semantica/templates/09_validacoes.sql;
```
*Itens checados automaticamente:*
- Órfãos em `META_RELACIONAMENTO` (tabelas referenciadas que não existem em `META_OBJETO`).
- Órfãos em `META_VALOR_DOMINIO`.
- `META_OBJETO` marcado como ativo cujo objeto físico não existe no schema do Oracle.
- Métricas sem `FORMULA_SQL` preenchida.
- Regras de negócio com status ainda `PENDENTE`.
- Execução de `SELECT COUNT(*)` dinâmico em todos os SQLs cadastrados em `META_CONSULTA_NEGOCIO`.

---

<a id="4-comandos-servidor-hop-odi"></a>
## 4. Comandos de Servidor Linux, Shell, Apache Hop e ODI

<a id="41-execucao-pipeline-hop"></a>
### 4.1 Execução de Pipelines (.hpl) via Apache Hop CLI
> **Cenário:** Disparo de pipeline de ingestão ou transformação direto na linha de comando do servidor de ETL.

```bash
# Execução simples com log básico
sh /opt/hop/hop-run.sh \
  -r local \
  -p /opt/etl/saida/planejador_dw/<PROJETO>/06_pipelines_hop/pipe_stg_<entidade>.hpl \
  -l Basic

# Execução com passagem de parâmetros dinâmicos e log detalhado
sh /opt/hop/hop-run.sh \
  -r local \
  -p /opt/etl/saida/planejador_dw/<PROJETO>/06_pipelines_hop/pipe_stg_<entidade>.hpl \
  -l Detailed \
  -o "PARAM_DATA_CORTE=2026-10-01,PARAM_LOTE_ID=554"
```

---

<a id="42-execucao-workflow-hop"></a>
### 4.2 Execução de Workflows (.hwf) com Captura de Erro
> **Cenário:** Disparar o workflow mestre que orquestra staging, dimensões e fatos, garantindo captura do código de saída (`exit code`).

```bash
#!/bin/bash
# Script de execução com checagem de status
WORKFLOW="/opt/etl/saida/planejador_dw/<PROJETO>/06_pipelines_hop/wf_carga_mestre.hwf"

sh /opt/hop/hop-run.sh -r local -p "$WORKFLOW" -l Basic
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo "[ERRO] Carga do Workflow Hop falhou com status: $EXIT_CODE" >&2
    exit $EXIT_CODE
else
    echo "[SUCESSO] Workflow executado com exito."
    exit 0
fi
```

---

<a id="43-odioscommand-ssh"></a>
### 4.3 Sintaxe para Chamadas Remotas via OdiOSCommand (ODI)
> **Cenário:** O Oracle Data Integrator orquestra a carga chamando o Apache Hop em um servidor Linux dedicado via chave SSH sem senha.

```bash
# Colar este comando dentro do passo OdiOSCommand do Pacote do ODI:
ssh -i /home/oracle/.ssh/id_rsa -o StrictHostKeyChecking=no oracle@servidor-hop.rede.local \
  "sh /opt/hop/hop-run.sh -r local -p /dados/hop/<PROJETO>/wf_carga_<dominio>.hwf -l Basic"
```

---

<a id="44-monitoramento-linux-hop"></a>
### 4.4 Monitoramento de Processos Hop e Memória JVM no Linux
> **Cenário:** Checar se há instâncias do Apache Hop em execução, travadas ou consumindo memória excessiva.

```bash
# 1. Localizar processos do Apache Hop rodando na máquina
ps aux | grep -i "hop-run" | grep -v grep

# 2. Monitorar consumo de CPU e memória JVM em tempo real
top -p $(pgrep -f "org.apache.hop")

# 3. Encerrar forçadamente um pipeline travado (Kill)
pkill -9 -f "org.apache.hop"
```

---

<a id="45-agendamento-cron-linux"></a>
### 4.5 Exemplo de Crontab para Agendamento Noturno
> **Cenário:** Configuração de agendamento automático diário às 02h00 da manhã com redirecionamento de logs de auditoria.

```bash
# Editar o crontab do usuário de serviço
crontab -e

# Inserir a linha de agendamento diário às 02:00 AM:
0 2 * * * /opt/etl/scripts/run_carga_diaria.sh >> /var/log/etl/carga_$(date +\%Y\%m\%d).log 2>&1
```

---

<a id="5-diagnostico-tuning-oracle"></a>
## 5. Diagnóstico, Tuning & Resolução de Problemas no Oracle (DBA / Data Engineer)

<a id="51-locks-sessoes-bloqueadoras"></a>
### 5.1 Identificar e Matar Sessões Bloqueadoras (Locks e Deadlocks)
> **Cenário:** A carga do ETL travou aguardando liberação de lock exclusivo em tabela ou partição.

```sql
-- 1. Identificar quem está bloqueando e quem está esperando
SELECT 
    b.session_id AS SID_BLOQUEADOR,
    sb.serial#   AS SERIAL_BLOQUEADOR,
    sb.username  AS USUARIO_BLOQUEADOR,
    sb.program   AS PROGRAMA_BLOQUEADOR,
    w.session_id AS SID_AGUARDANDO,
    sw.username  AS USUARIO_AGUARDANDO,
    ROUND(w.ctime / 60, 1) AS MINUTOS_TRAVADO
FROM v$lock b
JOIN v$session sb ON b.session_id = sb.sid
JOIN v$lock w     ON b.id1 = w.id1 AND b.id2 = w.id2 AND w.request > 0
JOIN v$session sw ON w.session_id = sw.sid
WHERE b.block = 1;

-- 2. Encerrar imediatamente a sessão bloqueadora (requer privilégio de DBA)
-- Sintaxe: ALTER SYSTEM KILL SESSION '<SID>,<SERIAL#>' IMMEDIATE;
ALTER SYSTEM KILL SESSION '142,50421' IMMEDIATE;
```

---

<a id="52-rebuild-indices-unusable"></a>
### 5.2 Identificar e Reconstruir Índices UNUSABLE (NOLOGGING)
> **Cenário:** Após uma carga massiva via *direct-path insert* (`/*+ APPEND */`) ou truncate de partição, índices locais podem entrar em estado inválido.

```sql
-- 1. Listar todos os índices em estado UNUSABLE no schema
SELECT TABLE_NAME, INDEX_NAME, PARTITION_NAME, STATUS
FROM USER_IND_PARTITIONS
WHERE STATUS = 'UNUSABLE'
UNION ALL
SELECT TABLE_NAME, INDEX_NAME, 'N/A' AS PARTITION_NAME, STATUS
FROM USER_INDEXES
WHERE STATUS = 'UNUSABLE';

-- 2. Rebuild rápido de índice convencional com NOLOGGING
ALTER INDEX "<SCHEMA>"."IX_<NOME_DO_INDICE>" REBUILD NOLOGGING PARALLEL 4;
ALTER INDEX "<SCHEMA>"."IX_<NOME_DO_INDICE>" NOPARALLEL;

-- 3. Rebuild de partição de índice local específica
ALTER INDEX "<SCHEMA>"."IX_<NOME_DO_INDICE>" REBUILD PARTITION P_202610 NOLOGGING;
```

---

<a id="53-coleta-estatisticas-dbms-stats"></a>
### 5.3 Coleta de Estatísticas em Cascata com Paralelismo
> **Cenário:** O otimizador de consultas (CBO) está gerando planos ruins (Full Table Scan) por falta de histogramas atualizados pós-carga.

```sql
-- Executar coleta completa com paralelismo 4 e cascata nos índices
BEGIN
    DBMS_STATS.GATHER_TABLE_STATS(
        ownname          => '<SCHEMA>',
        tabname          => '<TABELA_FATO>',
        estimate_percent => DBMS_STATS.AUTO_SAMPLE_SIZE,
        method_opt       => 'FOR ALL COLUMNS SIZE AUTO',
        degree           => 4,
        cascade          => TRUE,
        no_invalidate    => FALSE
    );
END;
/
```

---

<a id="54-tamanho-fisico-tablespace"></a>
### 5.4 Consultar Tamanho Físico e Espaço Ocupado por Tabelas/Índices
> **Cenário:** Análise de capacidade e crescimento de volumetria em Megabytes/Gigabytes.

```sql
SELECT 
    SEGMENT_NAME,
    SEGMENT_TYPE,
    ROUND(SUM(BYTES) / 1024 / 1024, 2) AS TAMANHO_MB,
    ROUND(SUM(BYTES) / 1024 / 1024 / 1024, 2) AS TAMANHO_GB
FROM USER_SEGMENTS
WHERE SEGMENT_NAME IN ('<TABELA_FATO>', '<TABELA_DIM>')
   OR SEGMENT_NAME IN (SELECT INDEX_NAME FROM USER_INDEXES WHERE TABLE_NAME = '<TABELA_FATO>')
GROUP BY SEGMENT_NAME, SEGMENT_TYPE
ORDER BY TAMANHO_MB DESC;
```

---

<a id="55-consultas-ofensoras-temp"></a>
### 5.5 Consultar Consultas Ofensoras e Consumo de Temp/PGA
> **Cenário:** Identificar queries em execução no momento que estão consumindo muito espaço temporário no disco (Tablespace TEMP).

```sql
SELECT 
    s.sid,
    s.serial#,
    s.username,
    s.program,
    u.tablespace,
    ROUND((u.blocks * 8192) / 1024 / 1024, 2) AS CONSUMO_TEMP_MB,
    q.sql_text
FROM v$sort_usage u
JOIN v$session s ON u.session_addr = s.saddr
JOIN v$sql q     ON s.sql_id = q.sql_id
ORDER BY CONSUMO_TEMP_MB DESC;
```

---

<a id="6-formulas-dax-powerbi"></a>
## 6. Fórmulas Canônicas DAX para o Analista de BI (Power BI)

> **Regra de Arquitetura:** Todas as métricas devem ser centralizadas na tabela técnica vazia **`_Medidas`**. Nunca referencie colunas da Fato diretamente sem agregação.

<a id="61-dax-divisao-segura"></a>
### 6.1 Divisão Segura contra Erros de Divisão por Zero
```dax
Percentual Seguro = 
DIVIDE(
    [Total Numerador], 
    [Total Denominador], 
    0  -- Retorno padrão seguro quando o denominador for zero ou nulo
)
```

---

<a id="62-dax-acumulado-ytd"></a>
### 6.2 Acumulado no Ano (Year-to-Date - YTD)
```dax
Receita YTD = 
TOTALYTD(
    [Receita Total],
    'dTempo'[DTC_COMPLETA]
)
```

---

<a id="63-dax-variacoes-mom-yoy"></a>
### 6.3 Variações Periódicas (Month-over-Month & Year-over-Year %)
```dax
-- Mês Anterior
Receita Mes Anterior = 
CALCULATE(
    [Receita Total],
    DATEADD('dTempo'[DTC_COMPLETA], -1, MONTH)
)

-- Variação Percentual Mês contra Mês (MoM %)
Variacao MoM % = 
DIVIDE(
    [Receita Total] - [Receita Mes Anterior], 
    [Receita Mes Anterior], 
    0
)

-- Mesmo Período do Ano Anterior (SPLY)
Receita Ano Anterior = 
CALCULATE(
    [Receita Total],
    SAMEPERIODLASTYEAR('dTempo'[DTC_COMPLETA])
)

-- Variação Percentual Ano contra Ano (YoY %)
Variacao YoY % = 
DIVIDE(
    [Receita Total] - [Receita Ano Anterior], 
    [Receita Ano Anterior], 
    0
)
```

---

<a id="64-dax-rolling-12m"></a>
### 6.4 Médias Móveis e Janelas Deslizantes (Rolling 12M)
```dax
Total Ultimos 12 Meses = 
CALCULATE(
    [Receita Total],
    DATESINPERIOD(
        'dTempo'[DTC_COMPLETA],
        MAX('dTempo'[DTC_COMPLETA]),
        -12,
        MONTH
    )
)
```

---

<a id="65-dax-media-ponderada"></a>
### 6.5 Médias Ponderadas Seguras
```dax
Ticket Medio Ponderado = 
DIVIDE(
    SUMX('fVendas', 'fVendas'[VLR_FATURAMENTO]),
    SUMX('fVendas', 'fVendas'[QTD_VENDIDA]),
    0
)
```

---

<a id="66-dax-keepfilters"></a>
### 6.6 Filtros Seguros Preservando Contexto (KEEPFILTERS)
```dax
Receita Clientes VIP = 
CALCULATE(
    [Receita Total],
    KEEPFILTERS('dCliente'[DES_SEGMENTO] = "VIP")
)
```

---

<a id="7-comandos-interacao-etapas"></a>
## 7. Comandos Chaves de Interação & Portões de Decisão por Etapa (Engenheiro + IA)

> **Princípio Fundamental:** A modelagem dimensional e a governança semântica **não são uma caixa-preta executada às cegas**. Em cada etapa do ciclo de vida, existem trade-offs técnicos, regras de negócio ocultas e decisões irreversíveis (como grão da fato e tipo de SCD) que **exigem alinhamento entre o Engenheiro de Dados e a IA**.  
> Use os comandos de chat abaixo (Slash Commands conceituais) para forçar a IA a debater, desafiar hipóteses e consolidar checkpoints antes de avançar.

---

<a id="71-etapa-insumos-profiling"></a>
### 7.1 Etapa 1: Ingestão de Insumos & Profiling de Fontes (/inspecionar-fontes)
* **Por que discutir nesta etapa?** Para evitar modelar sobre premissas falsas (ex: achar que uma coluna é PK quando ela tem valores nulos ou duplicados, ou ignorar tabelas de apoio do sistema legado).
* **Comando do Chat:**
  ```text
  /inspecionar-fontes
  ```
* **O que a IA analisa e devolve:** Lista completa das tabelas detectadas, tipos de fontes (OLTP, SFTP, API), integridade dos relacionamentos e uma lista de inconsistências ou ausências identificadas.
* **Query Técnica de Apoio (Engenheiro executa no banco de origem):**
  ```sql
  -- Validar se a PK da tabela de origem realmente é única e não nula
  SELECT 
      '<COLUNA_CHAVE>' AS COLUNA,
      COUNT(*) AS TOTAL_LINHAS,
      COUNT(DISTINCT <COLUNA_CHAVE>) AS VALORES_DISTINTOS,
      SUM(CASE WHEN <COLUNA_CHAVE> IS NULL THEN 1 ELSE 0 END) AS QTD_NULOS
  FROM <SCHEMA_ORIGEM>.<TABELA_ORIGEM>;
  ```
* 🚪 **Quality Gate 1:** Insumos validados pelo script `validar_entrega.py` e confirmação pelo engenheiro de que as amostras representam a totalidade dos dados.

---

<a id="72-etapa-definicao-grao"></a>
### 7.2 Etapa 2: Definição do Grão e Processo de Negócio (/desafiar-grao)
* **Por que discutir nesta etapa?** O grão da Fato é a decisão mais crítica de um Data Warehouse. Se o grão for definido errado (ex: item de processo vs processo inteiro), todas as agregações futuras gerarão erro de contagem dupla (*fan-out*) ou perda irrecuperável de métricas.
* **Comando do Chat:**
  ```text
  /desafiar-grao
  ```
* **O que a IA analisa e devolve:** A IA propõe de 2 a 3 alternativas de grão (ex: Transacional atômico no item vs Snapshot periódico consolidado por mês) e avalia cada uma contra as 10 perguntas de negócio listadas no Intake.
* **Query Técnica de Apoio (Engenheiro executa no banco de origem):**
  ```sql
  -- Testar se a combinação proposta como grão é 100% única (sem duplicidade)
  SELECT 
      <COL_DIM1>, 
      <COL_DIM2>, 
      <COL_DATA>, 
      COUNT(*) AS QTD_OCORRENCIAS
  FROM <SCHEMA_ORIGEM>.<TABELA_ORIGEM>
  GROUP BY <COL_DIM1>, <COL_DIM2>, <COL_DATA>
  HAVING COUNT(*) > 1;
  ```
* 🚪 **Quality Gate 2:** Declaração explícita no Blueprint: *"Uma linha nesta tabela fato representa..."* aprovada sem ressalvas pelo engenheiro.

---

<a id="73-etapa-modelagem-scd"></a>
### 7.3 Etapa 3: Classificação e Modelagem de Dimensões (/classificar-scd)
* **Por que discutir nesta etapa?** Nem todo atributo deve ser SCD Tipo 2 (histórico versionado). Se você colocar SCD2 em campos muito voláteis (ex: telefone, saldo), o volume de linhas da dimensão explode. Se colocar SCD1 onde o negócio precisa ver "como estava na época", o histórico de relatórios passados é corrompido.
* **Comando do Chat:**
  ```text
  /classificar-scd
  ```
* **O que a IA analisa e devolve:** A IA lista todas as dimensões identificadas e questiona atributo por atributo: *"Se o atributo X mudar na origem, você deseja sobrescrever (SCD1) ou preservar o valor histórico criando uma nova versão com vigência (SCD2)?"*.
* **Query Técnica de Apoio (Engenheiro executa no banco de origem):**
  ```sql
  -- Checar a frequência de atualização (churn) dos registros nos últimos 6 meses
  SELECT 
      TRUNC(DTC_ATUALIZACAO, 'MM') AS MES,
      COUNT(*) AS TOTAL_REGISTROS_ALTERADOS
  FROM <SCHEMA_ORIGEM>.<TABELA_DIM_ORIGEM>
  WHERE DTC_ATUALIZACAO >= ADD_MONTHS(SYSDATE, -6)
  GROUP BY TRUNC(DTC_ATUALIZACAO, 'MM')
  ORDER BY 1 DESC;
  ```
* 🚪 **Quality Gate 3:** Matriz de atributos aprovada definindo colunas SCD1, colunas SCD2, chaves de negócio (`ID_*`) e flags de vigência (`DTC_INICIO`, `DTC_EXPIRACAO`, `FLG_VERSAO_ATUAL`).

---

<a id="74-etapa-estrategia-carga"></a>
### 7.4 Etapa 4: Arquitetura de Ingestão & Estratégia de Carga (/definir-estrategia-carga)
* **Por que discutir nesta etapa?** Escolher entre **Estratégia A (Truncate & Load Massivo)** e **Estratégia B (Incremental via MERGE)** afeta diretamente o tempo de janela noturna, o tipo de índice Oracle (Bitmap vs B-Tree) e os riscos de deadlocks (`ORA-00060`).
* **Comando do Chat:**
  ```text
  /definir-estrategia-carga
  ```
* **O que a IA analisa e devolve:** Matriz comparativa entre Estratégia A e B ponderando volume esperado de linhas, frequência de carga (intra-dia vs noturna em lote) e necessidade da procedure `PRC_POS_CARGA_FATO`.
* **Query Técnica de Apoio (Engenheiro executa no banco de origem):**
  ```sql
  -- Avaliar taxa diária de novas inserções versus modificações
  SELECT 
      TRUNC(DTC_CRIACAO) AS DIA,
      COUNT(*) AS TOTAL_NOVOS,
      SUM(CASE WHEN DTC_MODIFICACAO > DTC_CRIACAO THEN 1 ELSE 0 END) AS TOTAL_MODIFICADOS
  FROM <SCHEMA_ORIGEM>.<TABELA_ORIGEM>
  WHERE DTC_CRIACAO >= SYSDATE - 14
  GROUP BY TRUNC(DTC_CRIACAO)
  ORDER BY 1 DESC;
  ```
* 🚪 **Quality Gate 4:** Definição formal: Estratégia A (com Bitmaps + Procedure) ou Estratégia B (B-Trees exclusivos + Merge) e chave de particionamento da Fato (`P_YYYYMM`).

---

<a id="75-etapa-aprovacao-blueprint"></a>
### 7.5 Etapa 5: Revisão do Blueprint Técnico & Gate de Aprovação Formal (/gerar-blueprint)
* **Por que discutir nesta etapa?** É o **ponto sem retorno**. A partir deste momento, a IA começará a escrever centenas de linhas de código físico. Ajustar um grão ou chave depois da geração física pronta custa até 10x mais tempo.
* **Comando do Chat:**
  ```text
  /gerar-blueprint
  ```
* **O que a IA analisa e devolve:** O documento consolidado de Blueprint contendo o diagrama Mermaid Star Schema, dicionário de campos com tipagem Oracle precisa, estimativa de sizing e checklist de confirmação.
* **Comando de Confirmação pelo Engenheiro:**
  ```text
  /aprovar-blueprint
  ```
  *(Ou: "Blueprint 100% aprovado! Pode iniciar a geração dos artefatos físicos.")*
* 🚪 **Quality Gate 5:** Aceite explícito do Blueprint registrado no chat.

---

<a id="76-etapa-geracao-testes"></a>
### 7.6 Etapa 6: Geração Física & Testes de Integridade Referencial (/auditar-ddl)
* **Por que discutir nesta etapa?** Garantir que o código gerado segue 100% das convenções do projeto antes de rodar no banco Oracle do cliente (proibição de Bitmaps em dimensões, sequences iniciando em 1 com `CACHE 50`, e inserção mandatória da linha técnica `-1`).
* **Comando do Chat:**
  ```text
  /auditar-ddl
  ```
* **O que a IA analisa e devolve:** Relatório de auditoria de conformidade sintática, verificação de índices e conferência de todos os nomes em MAIÚSCULAS.
* **Comando Técnico de Apoio (Engenheiro executa no Oracle):**
  ```sql
  -- Executar a bateria de smoke tests pré-voo gerada pela plataforma
  @saida/planejador_dw/<PROJETO>/10_testes_integridade/13_testes_integridade.sql;
  ```
* 🚪 **Quality Gate 6:** Bateria de testes de integridade executada com zero erros reportados no terminal.

---

<a id="77-etapa-handoff-transicao"></a>
### 7.7 Etapa 7: Handoff & Documentação Central Contínua (/concluir-dw ou /transicionar-semantica)
* **Por que discutir nesta etapa?** O trabalho de engenharia de dados corporativo **não deve parar em um único módulo**. Uma vez que os scripts DDL, rotinas Hop/Python e dicionários foram aprovados e gerados, o modelo dimensional precisa ser imediatamente catalogado e transferido para a Camada Semântica. Isso evita retrabalho de copiar e colar DDLs, impede divergência de versões e conecta ponta a ponta o DW com o Power BI e assistentes de IA.
* **Comando do Chat:**
  ```text
  /concluir-dw
  ```
  *(Ou: `/transicionar-semantica`, ou "Concluí o DW, documente o projeto e transfira os insumos para a camada semântica")*
* **O que a IA analisa e executa automaticamente:**
  1. Executa o transicionador `python core/scripts_comuns/transicionar_dw_para_semantica.py --projeto <PROJETO>`.
  2. Coleta os DDLs de Fatos e Dimensões e gera o arquivo consolidado `entrega/camada_semantica/ddl/DDL_COMPLETO_DW_<PROJETO>.sql`.
  3. Prepara a pasta de amostras (`entrega/camada_semantica/amostras/`) e relatórios de estratégias ETL.
  4. Preenche o formulário `modulos/camada_semantica/INTAKE_SEMANTICA.md` com schema, projeto, regras e perguntas de negócio.
  5. Atualiza o catálogo central em `documentacao/catalogo_projetos/PROJETO_RESUMO.md` e lança a versão `v1.0.0` no histórico `PROJETO_VERSION.md`.
  6. Dispara a auditoria de pré-voo semântica e convida o engenheiro para iniciar a Camada Semântica.
* **Comando Técnico de Apoio (Engenheiro executa no terminal):**
  ```bash
  python core/scripts_comuns/transicionar_dw_para_semantica.py --projeto <NOME_PROJETO>
  ```
* 🚪 **Quality Gate 7:** Insumos auditados em `entrega/camada_semantica/` e `INTAKE_SEMANTICA.md` preenchido sem nenhum marcador pendente.

---

<a id="78-etapa-camada-semantica"></a>
### 7.8 Etapa 8: Modelagem da Camada Semântica & Catálogo Ativo (/iniciar-semantica)
* **Por que discutir nesta etapa?** Traduzir a modelagem técnica do DW em termos acessíveis ao negócio e padronizar as regras de negócio em um catálogo que alimente tanto o BI quanto assistentes de IA (Text-to-SQL).
* **Comando do Chat:**
  ```text
  /iniciar-semantica
  ```
* **O que a IA analisa e devolve:** Proposta das views analíticas em 3 níveis (`VW_DIM_*_ATUAL`, `VW_EVENTO`, `VW_KPI_*`), mapeamento de sinônimos para o glossário e definição da aditividade das métricas.
* **Comando Técnico de Apoio (Engenheiro executa no Oracle):**
  ```sql
  -- Validar a integridade do catálogo e sintaxe de todas as views criadas
  @modulos/camada_semantica/templates/09_validacoes.sql;
  ```
* 🚪 **Quality Gate 8:** Catálogo semântico com 8 tabelas `META_*` povoadas e nenhuma métrica com fórmula SQL nula ou regra pendente.

---

<a id="79-etapa-diagnostico-producao"></a>
### 7.9 Etapa 9: Diagnóstico Operacional & Manutenção em Produção (/diagnosticar-erro-carga)
* **Por que discutir nesta etapa?** Cargas diárias podem falhar por motivos externos (queda de link de rede, estouro de tablespace, chave primária duplicada na origem ou índices em `UNUSABLE`).
* **Comando do Chat:**
  ```text
  /diagnosticar-erro-carga [COLE_O_LOG_DA_TB_CONTROLE_CARGA]
  ```
* **O que a IA analisa e devolve:** Diagnóstico de causa raiz, identificação do código do erro Oracle (`ORA-xxxxx`), script de remediação e comando para reprocessar a carga mantendo a idempotência.
* **Query Técnica de Apoio (Engenheiro executa no Oracle):**
  ```sql
  -- Consultar mensagem detalhada da última rotina com falha
  SELECT NOM_ROTINA, ID_LOTE, DTC_INICIO, DES_MENSAGEM_ERRO
  FROM "<SCHEMA>"."TB_CONTROLE_CARGA"
  WHERE DES_STATUS_EXECUCAO = 'ERRO'
  ORDER BY DTC_INICIO DESC
  FETCH FIRST 1 ROWS ONLY;
  ```
* 🚪 **Quality Gate 9:** Resolução e registro da causa raiz no arquivo `documentacao/catalogo_projetos/PROJETO_VERSION.md`.

---

<a id="8-prompts-ia-chat"></a>
## 8. Biblioteca Master de Prompts Prontos para a IA no Chat

Copie e cole os textos abaixo diretamente no prompt do seu assistente de IA para disparar os fluxos automatizados da plataforma NINHO:

<a id="81-prompt-planejar-dw"></a>
### 💬 8.1 Iniciar Planejamento de um Novo DW (Passo 1: Entendimento & Blueprint)
```text
Olá! Depositei os insumos brutos do meu projeto na pasta `entrega/planejador_dw/` e preenchi o arquivo `INTAKE_DW.md`. 
Por favor, analise as fontes, identifique os processos de negócio, determine o grão exato da tabela fato, selecione as dimensões com histórico SCD Tipo 2 e me apresente:
1. O Documento de Entendimento Dimensional e Grão.
2. O Blueprint Técnico Completo para aprovação antes de gerar o código físico.
```

---

<a id="82-prompt-aprovar-gerar-dw"></a>
### 💬 8.2 Aprovar Blueprint e Gerar Artefatos Físicos do DW (Passo 2)
```text
O Blueprint técnico apresentado está 100% aprovado! 
Pode prosseguir com a geração de todos os artefatos físicos do projeto na pasta `saida/planejador_dw/<NOME_DO_PROJETO>/`:
- DDLs completos (Staging, Dimensões com Sequence e linha -1, Fatos particionadas);
- Procedure de pós-carga e manutenção (PRC_POS_CARGA_FATO);
- Pipelines Hop (.hpl/.hwf) ou Extratores Python;
- Datasets de teste e o Relatório Executivo de Entrega.
```

---

<a id="83-prompt-gerar-semantica"></a>
### 💬 8.3 Criar a Camada Semântica & Catálogo Ativo (Views + 8 META_*)
```text
As tabelas do DW foram implementadas e desejo estruturar a Camada Semântica corporativa e o Catálogo Ativo de Metadados. 
Preenchi o formulário `INTAKE_SEMANTICA.md`. 
Por favor, gere:
1. Os scripts das views analíticas em 3 camadas (`VW_DIM_*_ATUAL`, `VW_EVENTO`, `VW_KPI_*`);
2. Os DMLs das 8 tabelas de catálogo semântico (`META_GLOSSARIO`, `META_METRICA`, `META_OBJETO`, `META_RELACIONAMENTO`, `META_REGRA_NEGOCIO`, `META_CONSULTA_NEGOCIO`, `META_ORIENTACAO_IA`, `META_VALOR_DOMINIO`);
3. O script de segurança RLS (`02_rls.sql`) e os testes de validação (`09_validacoes.sql`).
```

---

<a id="84-prompt-guia-bi-dicionario"></a>
### 💬 8.4 Gerar Guia Customizado de BI e Dicionário de Dados HTML
```text
Com base no modelo dimensional homologado em `saida/planejador_dw/<NOME_DO_PROJETO>/`, por favor gere:
1. O Guia de Modelagem do Analista de BI (`GUIA_ANALISTA_BI_<NOME_DO_PROJETO>.md`), detalhando relacionamentos 1:N, tabela técnica `_Medidas`, métricas canônicas DAX e regras para evitar bi-direcionalidade;
2. O Dicionário de Dados Interativo em HTML (`dicionario_dados.html`), contendo barra de busca instantânea, tipagem, indicação de chaves (PK/FK/SK) e grão de cada tabela.
```

---

<a id="85-prompt-diagnostico-erro-carga"></a>
### 💬 8.5 Diagnosticar Falhas em Cargas e Corrigir Pipelines
```text
A carga da Fato falhou no ambiente de produção. Segue o log de erro retornado pela TB_CONTROLE_CARGA:
[COLE O LOG DE ERRO AQUI]

Por favor, analise a causa raiz (ex: erro de chave estrangeira, estouro de tablespace, índice em UNUSABLE ou falha de conversão de tipos) e me forneça o script SQL de correção e os passos para reprocessar o lote com segurança.
```

---

<a id="86-prompt-migracao-scd2"></a>
### 💬 8.6 Migrar Dimensão Normal para Histórico SCD Tipo 2
```text
Preciso alterar a dimensão `DIM_<ENTIDADE>` de SCD Tipo 1 (sobrescrita) para SCD Tipo 2 (histórico com versionamento).
Por favor, forneça o script de migração contendo:
1. Adição das colunas `DTC_INICIO_VIGENCIA`, `DTC_EXPIRACAO` e `FLG_VERSAO_ATUAL`;
2. Carga inicial retroativa dos registros vigentes;
3. Atualização do pipeline de ETL / Merge para expirar a versão antiga e inserir a nova versão.
```
