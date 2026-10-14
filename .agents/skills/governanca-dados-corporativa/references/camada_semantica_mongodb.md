# Camada Semântica Governamental e Interoperabilidade no MongoDB (`tb_sem_dominios` e `tb_sem_conceitos`)

Este documento especifica a **Camada Semântica Corporativa em MongoDB**, projetada para conectar conceitos de negócio transversais entre diferentes secretarias e órgãos (ex: `SAEB/BA.GOV.BR`, `DETRAN`, `PLANSERV`, `RH BAHIA`, `SUPREV`, `SESAB`, `SEFAZ`) usando o **Modelo Híbrido Centrado no Conceito (Cenário C)**.

---

## 1. Por que a Camada Semântica no MongoDB?

No ecossistema governamental, o mesmo conceito real aparece com nomes físicos completamente distintos em cada órgão:
- No **BA.GOV.BR (SAEB)**: tabela `identidade`, campo `identificador` (CPF) e `nome`.
- No **DETRAN (RENACH/RENAVAM)**: tabela `Cadastro de Condutores`, campo `v100t_nrcpfcgc` e `v100t_nmpropriet`.
- No **PLANSERV**: tabela `BENEFICIARIOS`, campo `NR_CPF` e `NOME_COMPLETO`.
- Na **SUPREV / RH BAHIA (SAP)**: infotipo `PA0465`/`PA0002`, campo `CPF_NR`, `VORNA` e `NACHN`.

A Camada Semântica resolve essa fragmentação por meio de **2 coleções complementares**:
1. **`tb_sem_dominios`**: Cadastro leve dos macrodomínios de negócio do Estado (ex: `DOM_CIDADANIA_IDENTIFICACAO`, `DOM_MOBILIDADE_TRANSITO`, `DOM_GESTAO_PESSOAS_PREVIDENCIA`, `DOM_SAUDE_ASSISTENCIA`).
2. **`tb_sem_conceitos`**: Documento autocontido para cada **Conceito Canônico (`CNC_*`)**, contendo internamente:
   - `lst_termos`: Glossário de negócio (`PREFERENCIAL`, `SINONIMO`, `TECNICO_JURIDICO`).
   - `lst_atributos`: Atributos canônicos do conceito + classificação LGPD corporativa.
   - `lst_relacionamentos`: Grafo ontológico (`ESPECIALIZACAO_DE` / *"é um"*, `VINCULADO_A`, `COMPONENTE_DE`).
   - `lst_dataset_conceitos`: Mapeamento físico DE/PARA ligando os atributos canônicos aos campos físicos (`nom_campo_mongo` e `nom_campo_origem`) de cada dataset em `tb_dataset`.

---

## 2. Script de Criação: `tb_sem_dominios` (`schemas_mongo/02_schema_tb_sem_dominios.js`)

```javascript
// ============================================================================
// Script: 02_schema_tb_sem_dominios.js
// Objetivo: Criação da coleção de Domínios Semânticos Governamentais
// ============================================================================

db.createCollection("tb_sem_dominios", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["cod_dominio", "nom_dominio", "des_dominio", "sts_dominio", "dth_criacao"],
      properties: {
        _id: { bsonType: ["objectId", "string"] },
        cod_dominio: {
          bsonType: "string",
          pattern: "^DOM_[A-Z0-9_]+$",
          description: "Código canônico do domínio (ex: DOM_CIDADANIA_IDENTIFICACAO)"
        },
        nom_dominio: { bsonType: "string" },
        des_dominio: { bsonType: "string" },
        sig_orgaos_participantes: {
          bsonType: "array",
          items: { bsonType: "string" }
        },
        nom_comite_curadoria: { bsonType: "string" },
        sts_dominio: { enum: ["ATIVO", "EM_REVISAO", "INATIVO"] },
        dth_criacao: { bsonType: "date" }
      }
    }
  }
});

db.tb_sem_dominios.createIndex({ "cod_dominio": 1 }, { unique: true, name: "uk_sem_dominios_cod" });
```

---

## 3. Script de Criação: `tb_sem_conceitos` (`schemas_mongo/03_schema_tb_sem_conceitos.js`)

```javascript
// ============================================================================
// Script: 03_schema_tb_sem_conceitos.js
// Objetivo: Coleção Core da Camada Semântica (Modelo Híbrido Centrado no Conceito)
// ============================================================================

db.createCollection("tb_sem_conceitos", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: [
        "cod_conceito",
        "nom_conceito",
        "des_conceito",
        "cod_dominio",
        "sts_conceito",
        "lst_termos",
        "lst_atributos",
        "lst_dataset_conceitos"
      ],
      properties: {
        _id: { bsonType: ["objectId", "string"] },
        cod_conceito: {
          bsonType: "string",
          pattern: "^CNC_[A-Z0-9_]+$",
          description: "Código canônico do conceito (ex: CNC_CIDADAO, CNC_SERVIDOR_PUBLICO)"
        },
        nom_conceito: { bsonType: "string" },
        des_conceito: { bsonType: "string" },
        cod_dominio: { bsonType: "string" },
        sts_conceito: { enum: ["ATIVO", "EM_HOMOLOGACAO", "INATIVO"] },
        num_versao: { bsonType: "string" },
        dth_atualizacao: { bsonType: "date" },

        lst_termos: {
          bsonType: "array",
          minItems: 1,
          items: {
            bsonType: "object",
            required: ["des_termo", "tip_termo"],
            properties: {
              des_termo: { bsonType: "string" },
              tip_termo: { enum: ["PREFERENCIAL", "SINONIMO", "SIGLA", "TECNICO_JURIDICO"] },
              des_contexto_uso: { bsonType: "string" }
            }
          }
        },

        lst_atributos: {
          bsonType: "array",
          minItems: 1,
          items: {
            bsonType: "object",
            required: ["cod_atributo_canonico", "nom_atributo_canonico", "tip_bson_padrao", "ind_chave_identificadora", "classificacao_lgpd_padrao"],
            properties: {
              cod_atributo_canonico: { bsonType: "string" },
              nom_atributo_canonico: { bsonType: "string" },
              des_atributo: { bsonType: "string" },
              tip_bson_padrao: { bsonType: "string" },
              ind_chave_identificadora: { bsonType: "bool" },
              classificacao_lgpd_padrao: {
                bsonType: "object",
                required: ["des_nivel_sensibilidade", "ind_dado_pessoal", "ind_dado_sensivel"],
                properties: {
                  des_nivel_sensibilidade: { enum: ["PUBLICO", "INTERNO", "CONFIDENCIAL", "RESTRITO"] },
                  ind_dado_pessoal: { bsonType: "bool" },
                  ind_dado_sensivel: { bsonType: "bool" }
                }
              }
            }
          }
        },

        lst_relacionamentos: {
          bsonType: "array",
          items: {
            bsonType: "object",
            required: ["cod_conceito_destino", "tip_relacionamento", "des_regra_vinculo"],
            properties: {
              cod_conceito_destino: { bsonType: "string" },
              tip_relacionamento: { enum: ["ESPECIALIZACAO_DE", "GENERALIZACAO_DE", "VINCULADO_A", "COMPONENTE_DE"] },
              des_regra_vinculo: { bsonType: "string" }
            }
          }
        },

        lst_dataset_conceitos: {
          bsonType: "array",
          minItems: 1,
          items: {
            bsonType: "object",
            required: ["cod_dataset", "sig_orgao", "tip_papel_dataset", "lst_campos"],
            properties: {
              cod_dataset: { bsonType: "string" },
              sig_orgao: { bsonType: "string" },
              tip_papel_dataset: { enum: ["FONTE_AUTORITATIVA_MASTER", "FONTE_ESPECIALIZADA_SETORIAL", "FONTE_CONSUMIDORA"] },
              lst_campos: {
                bsonType: "array",
                minItems: 1,
                items: {
                  bsonType: "object",
                  required: ["cod_atributo_canonico", "nom_campo_origem", "nom_campo_mongo"],
                  properties: {
                    cod_atributo_canonico: { bsonType: "string" },
                    nom_campo_origem: { bsonType: "string" },
                    nom_campo_mongo: { bsonType: "string" },
                    txt_regra_transformacao: { bsonType: "string" }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
});

db.tb_sem_conceitos.createIndex({ "cod_conceito": 1 }, { unique: true, name: "uk_sem_conceitos_cod" });
db.tb_sem_conceitos.createIndex({ "cod_dominio": 1 }, { name: "idx_sem_conceitos_dominio" });
db.tb_sem_conceitos.createIndex({ "lst_termos.des_termo": 1 }, { name: "idx_sem_conceitos_termo" });
db.tb_sem_conceitos.createIndex({ "lst_dataset_conceitos.cod_dataset": 1 }, { name: "idx_sem_conceitos_dataset" });
```

---

## 4. Ponte de Interoperabilidade com a Camada Semântica Oracle (`META_*`) e Amazon SageMaker Catalog

| Elemento em `tb_sem_conceitos` (MongoDB) | Equivalente no DW Oracle (`META_*`) | Equivalente no Amazon SageMaker Catalog (AWS) |
| :--- | :--- | :--- |
| `tb_sem_dominios` (`cod_dominio`) | `META_OBJETO.DOMINIO` | **SageMaker Domain / Project** |
| `lst_termos` (`PREFERENCIAL`, `SINONIMO`) | `META_GLOSSARIO` | **Business Glossary Term** |
| `lst_atributos` + `classificacao_lgpd` | `META_OBJETO` + `GOV_CLASSIFICACAO` | **Asset Schema + Metadata Form (LGPD/LAI)** |
| `lst_relacionamentos` | `META_RELACIONAMENTO` | **Asset Lineage & Semantic Links** |

