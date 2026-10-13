# Convenções Técnicas da Camada Semântica (Oracle)

## 1. Nomenclatura Padronizada das Views Analíticas

Todas as views devem ser criadas com nomes em **MAIÚSCULAS** seguindo os prefixos corporativos:

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
2. **Documentação Integrada (`COMMENT ON`):**
   - Toda view deve conter comentário descritivo:
     `COMMENT ON TABLE VW_SEI_EVENTO IS 'Camada intermediária unificada de eventos de tramitação do SEI';`
   - Toda coluna calculada deve conter comentário explicativo da fórmula.
3. **Escrita de SQL nas Tabelas META_:**
   - Ao gravar consultas SQL na tabela `META_CONSULTA_NEGOCIO`, utilize a notação de quote do Oracle `q'[SELECT ... FROM ...]'` para preservar a indentação e evitar escape de aspas simples.
