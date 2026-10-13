# Catálogo Completo das 36 Orientações para IA (Camada Semântica)

Este catálogo define as 36 diretrizes universais (`GLOBAL`) inseridas na tabela `META_ORIENTACAO_IA`, que guiam qualquer agente de IA ou LLM a consultar o DW corporativo sem cometer erros semânticos.

---

## 1. Categoria: WORKFLOW (Ordens 1 a 9)

| Ordem | Tipo | Diretriz Técnica |
| :---: | :---: | :--- |
| 1 | `CONSULTA_CATALOGO` | Antes de escrever qualquer SQL, consulte `META_CONSULTA_NEGOCIO` buscando similaridade com a pergunta do usuário. |
| 2 | `VERIFICACAO_METRICA` | Se a pergunta envolve métricas, consulte `META_METRICA` para obter a fórmula SQL homologada, aditividade e filtros obrigatórios. |
| 3 | `INSPECAO_OBJETOS` | Verifique em `META_OBJETO` quais views ou tabelas contêm os atributos solicitados (priorize sempre as views `VW_*`). |
| 4 | `VALIDACAO_JOINS` | Se a consulta exigir múltiplos objetos, consulte `META_RELACIONAMENTO` para identificar os joins válidos e caminhos homologados. |
| 5 | `CHECA_REGRAS_NEGOCIO` | Consulte `META_REGRA_NEGOCIO` para aplicar restrições obrigatórias (ex: desconsiderar registros inativos ou testes). |
| 6 | `CONSULTA_DOMINIOS` | Para filtros categóricos ou códigos de status, valide os valores permitidos em `META_VALOR_DOMINIO`. |
| 7 | `APLICACAO_RLS` | Se o usuário pertencer a um grupo/órgão específico, aplique os filtros de isolamento declarados nas regras de segurança. |
| 8 | `ESCRITA_SQL` | Escreva o SQL final utilizando estritamente a sintaxe do Oracle (12c+), com palavras-chave e identificadores em MAIÚSCULAS. |
| 9 | `AUTO_EXPLICACAO` | Ao apresentar o resultado, explique em linguagem natural quais métricas, filtros e recortes foram considerados. |

---

## 2. Categoria: PRINCIPIO (Ordens 1 a 11)

| Ordem | Tipo | Diretriz Técnica |
| :---: | :---: | :--- |
| 1 | `FIDELIDADE_SEMANTICA` | Nunca altere o significado de uma métrica homologada. Use a fórmula exata cadastrada em `META_METRICA`. |
| 2 | `NAO_INVENTAR_COLUNAS` | É expressamente proibido referenciar colunas ou tabelas inexistentes no DW. Consulte `META_OBJETO`. |
| 3 | `PREFERENCIA_VIEWS` | Prefira sempre consultar views da camada semântica (`VW_*`) em vez de tabelas físicas brutas da staging. |
| 4 | `DIMENSOES_VIGENTES` | Em dimensões SCD Tipo 2, filtre sempre os registros vigentes (`DTC_EXPIRACAO IS NULL`) a menos que uma análise temporal histórica seja explicitamente pedida. |
| 5 | `TRATAMENTO_NULOS` | Utilize `NVL` ou `COALESCE` para tratamento de valores nulos em métricas aditivas. |
| 6 | `DIVISAO_POR_ZERO` | Proteja operações de divisão contra divisão por zero utilizando `NULLIF(divisor, 0)`. |
| 7 | `PADRAO_DATAS` | Sempre utilize conversão de datas explícita com `TO_DATE('YYYY-MM-DD', ...)` ou formato ANSI `DATE 'YYYY-MM-DD'`. |
| 8 | `HERANCA_MULTI_PROJETO` | Ao filtrar metadados, garanta herança global consultando `WHERE PROJETO IN ('GLOBAL', '<PROJETO>')`. |
| 9 | `ISOLAMENTO_TENANT` | Nunca execute queries sem o predicado de restrição do cliente quando operando em bases multi-órgão. |
| 10 | `PRECISAO_DECIMAL` | Valores monetários devem ser formatados e arredondados com `ROUND(valor, 2)`. |
| 11 | `LEITURA_DOCUMENTACAO` | Sempre forneça contexto adicional com base nos comentários (`COMMENT ON`) das tabelas e colunas. |

---

## 3. Categoria: VALIDACAO (Ordens 1 a 8)

| Ordem | Tipo | Diretriz Técnica |
| :---: | :---: | :--- |
| 1 | `CHECA_ADITIVIDADE` | Nunca aplique `SUM()` em métricas marcadas como `NAO_ADITIVA` (ex: taxas, médias, saldos pontuais). |
| 2 | `FILTRO_SEMI_ADITIVA` | Métricas `SEMI_ADITIVA` só podem ser somadas dentro da restrição de dimensão homologada (ex: dentro do mesmo mês). |
| 3 | `VERIFICA_SINTAXE` | Garanta compatibilidade com Oracle 12c+ (usar `FETCH FIRST n ROWS ONLY` em vez de `LIMIT`). |
| 4 | `CONFERE_CARDS` | Evite produtos cartesianos validando que todo join possui condição explícita em `ON`. |
| 5 | `EXCLUSAO_SINTETICOS` | Exclua registros técnicos como a linha `-1` (Não Informado) quando calcular médias ou percentuais. |
| 6 | `CONSISTENCIA_TIPOS` | Nunca compare tipos incompatíveis sem `CAST` ou conversão explícita (evite coerção implícita). |
| 7 | `RESPEITO_GRÃO` | Não realize agregações em níveis mais detalhados do que o grão físico da Fato sem avisar o usuário. |
| 8 | `AUDITORIA_METADADOS` | Cheque se as chaves referenciadas nos joins possuem correspondência em `META_RELACIONAMENTO`. |

---

## 4. Categoria: DESVIO (Ordens 1 a 3)

| Ordem | Tipo | Diretriz Técnica |
| :---: | :---: | :--- |
| 1 | `TERMO_AMBIGUO` | Se o termo do usuário possuir múltiplos significados no glossário, pare e solicite esclarecimento. |
| 2 | `METRICA_INEXISTENTE` | Se a métrica solicitada não constar em `META_METRICA`, informe que o cálculo não está homologado. |
| 3 | `DIVERGENCIA_FILTROS` | Se o usuário solicitar filtros conflitantes (ex: status cancelado + ativo), aponte a inconsistência antes de rodar. |

---

## 5. Categoria: RESPOSTA (Ordens 1 a 5)

| Ordem | Tipo | Diretriz Técnica |
| :---: | :---: | :--- |
| 1 | `APRESENTACAO_TABULAR` | Apresente resultados numéricos sempre em tabelas Markdown legíveis e ordenadas. |
| 2 | `FONTE_E_DATA` | Informe sempre a data/hora do corte dos dados ou última carga do DW. |
| 3 | `JUSTIFICATIVA_FORMULA` | Mostre a query SQL gerada para que o analista de negócio possa auditar os resultados. |
| 4 | `LIMITES_DE_EXIBICAO` | Se a consulta retornar mais de 50 linhas, resuma os principais registros e ofereça agregação. |
| 5 | `SUGESTAO_DESDOBRAMENTO`| Sugira 1 ou 2 perguntas de negócio correlacionadas para aprofundar a análise (*drill-down*). |
