# Convenções Técnicas e Nomenclaturas de DW (Oracle)

## 1. Padrões de Nomes de Objetos

1. **Staging:**
   - Tabelas: `STG_<FONTE>_<ENTIDADE>` (ex: `STG_ORACLE_PROCESSO`, `STG_API_DOCUMENTO`).
   - Colunas: idênticas à origem, preferencialmente `VARCHAR2` amplo para evitar truncamentos na aterrissagem.

2. **Dimensões:**
   - Tabelas: `DIM_<ENTIDADE>` (ex: `DIM_UNIDADE`, `DIM_TIPO_PROCESSO`).
   - Surrogate Key: `<NOME_DIM>_KEY NUMBER(38,0) NOT NULL`.
   - Sequence: `SEQ_DIM_<ENTIDADE> START WITH 1 INCREMENT BY 1 NOCACHE NOCYCLE`.
   - Chave Natural: `ID_<ENTIDADE>` (preservando o nome e tipo original).
   - Tabela auxiliar ODI (se habilitado): `ODI_DIM_<ENTIDADE>`.

3. **Fatos:**
   - Tabelas: `FATO_<PROCESSO_NEGOCIO>` ou `FAT_<PROCESSO_NEGOCIO>` (ex: `FATO_TRAMITACAO`, `FATO_FATURAMENTO`).
   - Chaves Estrangeiras (FKs): `<NOME_DIM>_KEY NUMBER(38,0) NOT NULL` com valor padrão `-1` para ausentes.
   - Chaves Primárias Compostas: `PK_FAT_<PROCESSO>` composta pela data do fato + SKs das dimensões.

4. **Identificadores e Sintaxe:**
   - **TUDO EM MAIÚSCULAS:** NUNCA gere identificadores com aspas e letras minúsculas (ex: `"id_processo"`). O Oracle trata como case-sensitive e gera problemas de consulta.
   - Use sempre nomes em maiúsculas sem aspas: `ID_PROCESSO`, `DIM_UNIDADE`.

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
| Flags / Indicadores | `VARCHAR2(1 CHAR)` | 'S' / 'N' ou 'A' / 'I' |

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


