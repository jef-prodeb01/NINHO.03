# Convenções Técnicas da Camada Semântica (Oracle)

> **Fonte Única da Verdade:** Este arquivo é sincronizado com [`core/convencoes/CONVENCOES_SEMANTICA.md`](../../../../core/convencoes/CONVENCOES_SEMANTICA.md).

## 1. Nomenclatura Padronizada das Views Analíticas

Todas as views devem ser criadas com nomes em **MAIÚSCULAS** seguindo os prefixos corporativos (nunca use `SEM_VW_`, `SEC_` ou `TST_`):

1. **Views de Dimensão Vigente (Camada 1):**
   - Padrão: `VW_<PROJETO>_DIM_<ENTIDADE>_ATUAL`
   - Regra: Filtram automaticamente `WHERE DTC_EXPIRACAO IS NULL` para expor apenas o registro atualmente vigente da dimensão SCD Tipo 2.
   - Exemplo: `CREATE VIEW VW_SEI_DIM_UNIDADE_ATUAL AS ...`

2. **Views de Evento Intermediárias (Camada 2):**
   - Padrão: `VW_<PROJETO>_EVENTO` ou `VW_<PROJETO>_FATO_<NOME>`
   - Regra: Normalizam os dados da Fato com os joins para as dimensões vigentes, trazendo SKs, datas calculadas, flags e métricas prontas para agregação.
   - Exemplo: `CREATE VIEW VW_SEI_EVENTO AS ...`

3. **Views de KPI Consolidadas (Camada 3):**
   - Padrão: `VW_<PROJETO>_KPI_<MEDIDA>_POR_<DIMENSAO>`
   - Regra: Agregações pré-computadas para responder diretamente às perguntas de negócio prioritárias dos gestores.
   - Exemplo: `CREATE VIEW VW_SEI_KPI_TEMPO_MEDIO_TRAMITACAO AS ...`

---

## 2. Padrões de Qualidade de Código SQL

1. **Identificadores em Maiúsculas:**
   - Palavras-chave: `SELECT`, `FROM`, `WHERE`, `GROUP BY`, `JOIN`, `ON`.
   - Colunas e tabelas: `SK_CHAMADO`, `VAL_TOTAL`, `DTC_ABERTURA`.
   - Aliases: `F` (fato), `D` (dimensão).
2. **Documentação Integrada e Grão Canônico Obrigatório (`COMMENT ON`):**
   - Toda view deve conter comentário descritivo iniciando **obrigatoriamente** pela declaração do grão:
     ```sql
     COMMENT ON TABLE VW_SEI_EVENTO IS 'Uma linha representa um ciclo de tramitação de processo administrativo no órgão.';
     ```
   - O padrão `"Uma linha representa..."` é essencial para orientar copilotos de IA e analistas, evitando agregações indevidas.
   - Toda coluna calculada ou métrica deve conter comentário explicativo da fórmula.

3. **Decodificação de Domínios com Fallback Seguro:**
   - Nas views analíticas, evite expor códigos numéricos ou siglas transacionais obscuras. Decodifique utilizando `CASE WHEN` com cláusula `ELSE` explícita:
     ```sql
     CASE ORIGEM.STA_TIPO
       WHEN '0' THEN 'INTERNO'
       WHEN '1' THEN 'SISTEMAS'
       WHEN '2' THEN 'EXTERNO - PENDENTE DE LIBERAÇÃO'
       WHEN '3' THEN 'EXTERNO'
       ELSE 'TIPO NÃO IDENTIFICADO'
     END AS TIPO_USUARIO
     ```

4. **Abstração e Correção Semântica de Colunas Físicas Legadas:**
   - Se a base transacional ou tabela física contiver erros ortográficos ou nomenclaturas antigas (ex: `STA_DOCUMETO`, `DS_PROCEDIMETO`, `FLG_SN`), a View Semântica DEVE expor o alias correto e claro em português:
     ```sql
     SELECT 
       STA_DOCUMETO   AS SITUACAO_DOCUMENTO,
       DS_PROCEDIMETO AS DS_PROCEDIMENTO,
       ...
     ```
   - A IA e as ferramentas de BI devem interagir exclusivamente com os nomes corretos certificados pela Camada Semântica.

5. **Escrita de SQL nas Tabelas META_:**
   - Ao gravar consultas SQL na tabela `META_CONSULTA_NEGOCIO`, utilize a notação de quote do Oracle `q'[SELECT ... FROM ...]'` para preservar a formatação, indentação e evitar escape manual de aspas simples.

---

## 3. Padrão Enriquecido da Biblioteca Pergunta-SQL (`META_CONSULTA_NEGOCIO`)

A tabela `META_CONSULTA_NEGOCIO` funciona como biblioteca de treinamento few-shot para soluções Text-to-SQL e BI Copilot. Toda consulta catalogada deve seguir o padrão:

1. **Parâmetros Tipados via Bind Variables (`:P_*`):**
   - Use `:P_DT_INICIO`, `:P_DT_FIM`, `:P_COD_ORGAO`, `:P_MES_REFERENCIA`.
   - Realize `CAST` explícito nas CTEs de entrada para evitar erro `ORA-00932` caso o driver cliente infira tipo inconsistente para valores nulos:
     ```sql
     WITH ENTRADA AS (
       SELECT CAST(:P_DT_INICIO AS DATE) AS DT_INICIO,
              CAST(:P_DT_FIM AS DATE)    AS DT_FIM
       FROM DUAL
     )
     ```
2. **Fallbacks Temporais Inteligentes:**
   - Se o usuário não informar data de término, utilize o último mês disponível ou `TRUNC(SYSDATE)`.
3. **Metadados de Apoio:**
   - Preencher sempre `PAINEL_RELACIONADO` (ex: "Visão Executiva", "Andamento e Eficiência") e `OBJETOS_CHAVE` (lista de views envolvidas, ex: `VW_SEI_KPI_PROCESSO_MES, VW_SEI_DIM_ORGAO`).

---

## 4. As 5 Dimensões de Validação para IA (Quality Gates Text-to-SQL)

Toda consulta analítica sugerida por IA ou gerada pela Camada Semântica deve ser auditada sob 5 dimensões antes da homologação:

| Dimensão | O que Avaliar | Critério de Aceite |
| :--- | :--- | :--- |
| **1. Sintaxe** | Compatibilidade Oracle 12c+ | Uso de `FETCH FIRST n ROWS ONLY` (sem `LIMIT`), maiúsculas, binds tipados e sem erros de parse. |
| **2. Semântica** | Consistência com o Negócio | Uso de fórmulas exatas de `META_METRICA`, respeito a aditividade (nunca somar taxa ou média) e joins de `META_RELACIONAMENTO`. |
| **3. Resultado** | Fidedignidade Numérica | Tratamento de nulos com `NVL`, sem divisões por zero (`NULLIF`), sem duplicações por joins em leque. |
| **4. Segurança** | Isolamento e Permissões | Isolamento estrito por tenant/órgão (RLS), proibição categórica de DDL/DML destrutivos (deny-by-default). |
| **5. Explicação** | Clareza para o Usuário | Justificativa em português claro explicando quais métricas, filtros e recortes foram aplicados. |


