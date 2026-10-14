# Convenções Técnicas e Nomenclaturas de DW (Oracle)

> **Fonte Única da Verdade:** Este arquivo é sincronizado com [`core/convencoes/CONVENCOES_DW.md`](../../../../core/convencoes/CONVENCOES_DW.md).

## 1. Padrões de Nomes de Objetos e Fidelidade à Origem

1. **Fidelidade 100% às Colunas de Origem:**
   - Preserve ipsis litteris (em MAIÚSCULAS) os nomes das colunas vindas do DDL de origem. NUNCA invente ou abrevie colunas existentes.
   - Apresente a Matriz De/Para completa no Blueprint (`/gerar-blueprint`) antes de gerar os scripts físicos.

2. **Staging:**
   - Tabelas: `STG_<SISTEMA>_<DOMINIO>_<ENTIDADE>` ou `STG_<FONTE>_<ENTIDADE>`.
   - Colunas: idênticas à origem + metadados `DTC_EXTRACAO` e `ID_LOTE`.
   - **PK na Staging:** Sempre declarar `PRIMARY KEY` ou índice único nas colunas da chave de negócio da `STG_*` quando usada em cargas incrementais/MERGE no ODI.

3. **Dimensões:**
   - Tabelas: `DIM_<SISTEMA>_<DOMINIO>_<ENTIDADE>` ou `DIM_<ENTIDADE>`.
   - Surrogate Key: `DIMENSION_KEY NUMBER(38,0) NOT NULL` (ou `<NOME_DIM>_KEY`).
   - Sequence: `SEQ_DIM_<ENTIDADE> START WITH 1 INCREMENT BY 1 CACHE 50 NOCYCLE NOORDER`.
   - Chave Natural: `ID_<ENTIDADE>` (preservando o nome e tipo original).
   - Colunas SCD2: `SIN_ATIVO`, `DTC_EFETIVACAO`, `DTC_EXPIRACAO`, `DES_ATUALIZAR`.
   - **Linha `-1` Obrigatória:** Registro inicial `-1` (`NAO INFORMADO`) em todas as dimensões.
   - **Índices:** Exclusivamente **B-Tree** (proibido `BITMAP INDEX` em dimensões para evitar deadlock `ORA-00060`).
   - Tabela auxiliar ODI (se `[x] ODI` habilitado): `ODI_DIM_<ENTIDADE>` com `DES_STATUS_REGISTRO`.

4. **Fatos:**
   - Tabelas: `FATO_<SISTEMA>_<DOMINIO>_<PROCESSO>` ou `FATO_<PROCESSO_NEGOCIO>`.
   - Chaves Estrangeiras (FKs): `NOT NULL` com fallback `NVL(LOOKUP.DIMENSION_KEY, -1)`.
   - Estratégia A (Truncate & Load): `BITMAP INDEX` nas FKs da Fato + `PRC_POS_CARGA_FATO`.
   - Estratégia B (Incremental MERGE): `B-TREE INDEX` nas chaves de merge.
   - Estratégia Híbrida: Janela móvel diária (ex: últimos 5-15 dias) combinada com recarga de consolidação no fim de semana/mês.

5. **Identificadores e Destino de Saída:**
   - **TUDO EM MAIÚSCULAS:** NUNCA gere identificadores com aspas e letras minúsculas (ex: `"id_processo"`).
   - **Saída Canônica:** Grave diretamente nas 11 pastas numeradas de `saida/planejador_dw/` (`01_controle_carga` a `11_dicionario_dados`), sem criar subpasta com o nome do projeto.

---

## 2. Padrões de Tipos de Dados no Oracle

| Conceito | Tipo Oracle Recomendado | Observações |
| :--- | :--- | :--- |
| Chave Surrogate (SK) | `NUMBER(38,0)` | Gerada via Sequence |
| Quantidades e Contadores | `NUMBER(18,0)` ou `NUMBER(10,0)` | Inteiros |
| Valores Monetários / Decimais | `NUMBER(18,2)` ou `NUMBER(18,4)` | Precisão fixa |
| Textos Curtos e Códigos | `VARCHAR2(50 CHAR)` a `VARCHAR2(255 CHAR)` | Usar semântica `CHAR` |
| Textos Longos e Descrições | `VARCHAR2(4000 CHAR)` | Se exceder 4000, avaliar `CLOB` |
| Datas | `DATE` | Inclui ano, mês, dia, hora, minuto e segundo |
| Timestamps com Fração | `TIMESTAMP(6)` | Usar se frações de segundo forem cruciais |
| Flags / Indicadores | `CHAR(1 CHAR)` ou `VARCHAR2(1 CHAR)` | 'S' / 'N' ou 'A' / 'I' |

---

## 3. Arquitetura Multi-Tenant e Prevenção de Violação de Chave Única (`ORA-00001`)

Em ambientes analíticos consolidados onde múltiplos órgãos, secretarias ou prefeituras (tenants) compartilham o mesmo schema físico de DW:

### 3.1 Colisão de Chaves Naturais
- Identificadores numéricos transacionais (`ID_USUARIO`, `ID_PROCEDIMENTO`, `ID_UNIDADE`) colidem frequentemente entre diferentes tenants (ex: o usuário `10` existe em múltiplos órgãos com identidades e pessoas completamente distintas).
- **🛑 Regra Anti-Falha (`ORA-00001`):** NUNCA crie constraints de unicidade (`UNIQUE`) considerando apenas a coluna do ID natural. Toda constraint física de unicidade em dimensões multi-tenant DEVE ser composta com a coluna identificadora do tenant:
  ```sql
  -- CORRETO:
  ALTER TABLE "SCHEMA_OLAP"."DIM_USUARIO" 
    ADD CONSTRAINT "UK_DIM_USUARIO" UNIQUE ("ID_USUARIO", "COD_TENANT", "DTC_EXPIRACAO");

  -- INCORRETO (Causa ORA-00001 na carga concorrente do 2º tenant):
  -- ALTER TABLE "SCHEMA_OLAP"."DIM_USUARIO" ADD CONSTRAINT "UK_DIM_USUARIO" UNIQUE ("ID_USUARIO");
  ```

### 3.2 Resolução Numérica de Chaves Naturais no ETL/ELT
- Para evitar colisões de dados antes da alocação da Surrogate Key definitiva, aplique nos mapeamentos de Staging/DW a composição numérica com base no código do tenant:
  ```sql
  to_number(to_char(V_TENANT) || '000' || to_char(ORIGEM.ID_NATURAL))
  ```
- Isso garante chaves unívocas na esteira de integração, preservando a rastreabilidade original.



