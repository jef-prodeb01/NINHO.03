# Arquitetura Física das Coleções de Governança no MongoDB (`tb_dataset`, `tb_auditoria_eventos` e `tb_quarentena`)

Este documento contém os templates oficiais de validação `$jsonSchema`, exemplos de documentos canônicos e scripts de indexação (`mongosh`) para o repositório de Governança no MongoDB Enterprise.

---

## 1. Alerta Técnico Crítico sobre `$jsonSchema` (`patternProperties` + `additionalProperties: false`)

> ⚠️ **ARMADILHA DE VALIDAÇÃO BSON A EVITAR:**
> Nunca utilize `"patternProperties": { "^[a-z]{3}_[a-z0-9_]*$": {} }` combinado com `"additionalProperties": false` sem declarar explicitamente os nomes dos subdocumentos de primeiro nível (`orgao_responsavel`, `sistema_origem`, `governanca`, `metadados_campos`, `regras_qualidade`, `linhagem_origem`, `consumo_autorizado`, `historico_versionamento`, `detalhes_execucao`, etc.) dentro de `"properties"`.
> Caso contrário, o MongoDB rejeitará qualquer documento que contenha esses objetos aninhados por não começarem com prefixo de 3 letras + underscore!

---

## 2. Coleção Central de Catálogo Técnico: `tb_dataset`

Armazena a definição lógica e física de cada conjunto de dados, consolidando num único documento (`Embedding`) o órgão responsável, o sistema de origem, os papéis de governança (vinculados ao cargo/setor e titular atual), o dicionário de campos com classificação LGPD, as regras da barreira de qualidade, a linhagem de transporte e os termos de consumo autorizado.

### 2.1 Script de Criação e Validação (`schemas_mongo/01_schema_tb_dataset.js`)

```javascript
// ============================================================================
// Script: 01_schema_tb_dataset.js
// Objetivo: Criação da coleção tb_dataset com validação $jsonSchema e índices
// ============================================================================

db.createCollection("tb_dataset", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: [
        "cod_dataset",
        "nom_dataset",
        "des_finalidade",
        "sts_dataset",
        "dth_cadastro",
        "orgao_responsavel",
        "sistema_origem",
        "governanca",
        "metadados_campos",
        "regras_qualidade",
        "linhagem_origem"
      ],
      properties: {
        _id: { bsonType: ["objectId", "string"] },
        cod_dataset: {
          bsonType: "string",
          pattern: "^[A-Z0-9]+_[A-Z0-9]+_[A-Z0-9_]+_V[0-9]+$",
          description: "Código padronizado: SIGLA_ORGAO_UNIDADE_TEMA_VERSAO"
        },
        nom_dataset: { bsonType: "string" },
        des_finalidade: { bsonType: "string" },
        sts_dataset: {
          enum: ["ATIVO", "EM_HOMOLOGACAO", "DEVOLVIDO_AO_CLIENTE", "INATIVO"]
        },
        dth_cadastro: { bsonType: "date" },
        dth_atualizacao: { bsonType: "date" },
        num_versao_schema: { bsonType: "string" },

        orgao_responsavel: {
          bsonType: "object",
          required: ["cod_orgao", "sig_orgao", "nom_orgao", "nom_unidade_responsavel"],
          properties: {
            cod_orgao: { bsonType: "string" },
            sig_orgao: { bsonType: "string" },
            nom_orgao: { bsonType: "string" },
            nom_unidade_responsavel: { bsonType: "string" },
            num_cnpj: { bsonType: "string" },
            des_email_institucional: { bsonType: "string" }
          }
        },

        sistema_origem: {
          bsonType: "object",
          required: ["cod_sistema", "nom_sistema", "tip_fonte", "des_ambiente"],
          properties: {
            cod_sistema: { bsonType: "string" },
            nom_sistema: { bsonType: "string" },
            des_tecnologia_origem: { bsonType: "string" },
            des_versao_origem: { bsonType: "string" },
            tip_fonte: { enum: ["BANCO_DADOS", "API_REST", "ARQUIVO_FTP", "NOSQL", "SAP_ERP"] },
            des_ambiente: { enum: ["ON_PREMISE", "NUVEM_AWS", "NUVEM_PRODEB", "HIBRIDO"] },
            des_metodo_autenticacao: { bsonType: "string" }
          }
        },

        governanca: {
          bsonType: "object",
          required: [
            "des_cargo_data_owner",
            "nom_titular_data_owner",
            "des_area_data_steward",
            "nom_titular_data_steward",
            "des_criticidade",
            "des_nivel_acesso_padrao",
            "des_frequencia_atualizacao"
          ],
          properties: {
            des_cargo_data_owner: { bsonType: "string", description: "Cargo/Unidade institucional proprietária do dado" },
            nom_titular_data_owner: { bsonType: "string", description: "Nome do gestor titular responsável na origem" },
            des_area_data_steward: { bsonType: "string" },
            nom_titular_data_steward: { bsonType: "string" },
            des_equipe_engenharia_transporte: { bsonType: "string" },
            des_criticidade: { enum: ["ALTA", "MEDIA", "BAIXA", "CRITICA"] },
            des_nivel_acesso_padrao: { enum: ["PUBLICO", "INTERNO", "CONFIDENCIAL", "RESTRITO"] },
            des_grau_sigilo_lai: { enum: ["OSTENSIVO", "RESERVADO_5_ANOS", "SECRETO_15_ANOS", "ULTRASSECRETO_25_ANOS"] },
            des_politica_retencao: { bsonType: "string" },
            des_frequencia_atualizacao: { bsonType: "string" },
            des_janela_sla: { bsonType: "string" },
            val_volume_estimado_gb: { bsonType: ["double", "decimal", "int"] },
            val_crescimento_mensal_gb: { bsonType: ["double", "decimal", "int"] }
          }
        },

        metadados_campos: {
          bsonType: "array",
          minItems: 1,
          items: {
            bsonType: "object",
            required: [
              "cod_campo",
              "nom_campo_origem",
              "nom_campo_mongo",
              "des_campo",
              "tip_dado_origem",
              "tip_bson_mongo",
              "ind_obrigatorio",
              "classificacao_lgpd"
            ],
            properties: {
              cod_campo: { bsonType: "string" },
              nom_campo_origem: { bsonType: "string" },
              nom_campo_mongo: {
                bsonType: "string",
                pattern: "^[a-z]{3}_[a-z0-9_]+$",
                description: "Atributo físico no padrão snake_case com prefixo oficial PRODEB"
              },
              des_campo: { bsonType: "string" },
              tip_dado_origem: { bsonType: "string" },
              tip_bson_mongo: {
                enum: ["string", "int", "long", "decimal", "double", "date", "bool", "object", "array", "binData"]
              },
              num_tamanho_maximo: { bsonType: ["int", "null"] },
              ind_obrigatorio: { bsonType: "bool" },
              ind_chave_negocio: { bsonType: "bool" },
              cod_conceito_canonico: { bsonType: ["string", "null"] },
              classificacao_lgpd: {
                bsonType: "object",
                required: [
                  "des_nivel_sensibilidade",
                  "ind_dado_pessoal",
                  "ind_dado_sensivel",
                  "ind_anonimizar",
                  "des_base_legal"
                ],
                properties: {
                  des_nivel_sensibilidade: { enum: ["PUBLICO", "INTERNO", "CONFIDENCIAL", "RESTRITO"] },
                  ind_dado_pessoal: { bsonType: "bool" },
                  ind_dado_sensivel: { bsonType: "bool" },
                  ind_anonimizar: { bsonType: "bool" },
                  des_tecnica_anonimizacao: { bsonType: "string" },
                  des_base_legal: { bsonType: "string" }
                }
              }
            }
          }
        },

        regras_qualidade: {
          bsonType: "array",
          minItems: 1,
          items: {
            bsonType: "object",
            required: ["cod_regra", "nom_regra", "tip_dimensao_dama", "des_severidade", "prc_meta_conformidade", "des_acao_falha"],
            properties: {
              cod_regra: { bsonType: "string" },
              nom_regra: { bsonType: "string" },
              tip_dimensao_dama: { enum: ["COMPLETUDE", "CONFORMIDADE", "UNICIDADE", "VALIDADE", "INTEGRIDADE", "TEMPESTIVIDADE"] },
              nom_campo_alvo: { bsonType: "string" },
              des_expressao_validacao: { bsonType: "string" },
              des_severidade: { enum: ["CRITICA", "ALTA", "MEDIA", "BAIXA"] },
              prc_meta_conformidade: { bsonType: ["double", "decimal"] },
              des_acao_falha: { enum: ["ENVIAR_QUARENTENA_E_NOTIFICAR_CLIENTE", "BLOQUEAR_LOTE_E_DEVOLVER_AO_CLIENTE"] }
            }
          }
        },

        linhagem_origem: {
          bsonType: "array",
          items: {
            bsonType: "object",
            required: ["cod_linhagem", "nom_objeto_origem", "des_ferramenta_transporte", "nom_job_transporte", "nom_colecao_raw", "nom_colecao_trusted"],
            properties: {
              cod_linhagem: { bsonType: "string" },
              nom_objeto_origem: { bsonType: "string" },
              des_ferramenta_transporte: { enum: ["ODI_12C", "APACHE_HOP", "PYTHON_EXTRACTOR", "AWS_GLUE"] },
              nom_job_transporte: { bsonType: "string" },
              nom_colecao_raw: { bsonType: "string" },
              nom_colecao_trusted: { bsonType: "string" },
              nom_ativo_aws_sagemaker_catalog: { bsonType: "string" }
            }
          }
        },

        consumo_autorizado: {
          bsonType: "array",
          items: {
            bsonType: "object",
            required: ["cod_consumo", "sig_orgao_consumidor", "des_finalidade_uso", "cod_termo_compartilhamento", "ind_exige_mascaramento"],
            properties: {
              cod_consumo: { bsonType: "string" },
              sig_orgao_consumidor: { bsonType: "string" },
              nom_sistema_consumidor: { bsonType: "string" },
              des_finalidade_uso: { bsonType: "string" },
              cod_termo_compartilhamento: { bsonType: "string" },
              tip_acesso: { enum: ["SAGEMAKER_LAKEHOUSE_VIEW", "API_REST", "MONGO_READ_ONLY", "POWER_BI_DIRECT"] },
              ind_exige_mascaramento: { bsonType: "bool" },
              sts_consumo: { enum: ["ATIVO", "SUSPENSO", "EXPIRADO"] }
            }
          }
        }
      }
    }
  }
});

// Índices recomendados para tb_dataset
db.tb_dataset.createIndex({ "cod_dataset": 1 }, { unique: true, name: "uk_tb_dataset_cod" });
db.tb_dataset.createIndex({ "orgao_responsavel.sig_orgao": 1, "sts_dataset": 1 }, { name: "idx_tb_dataset_orgao_sts" });
db.tb_dataset.createIndex({ "metadados_campos.classificacao_lgpd.ind_dado_sensivel": 1 }, { name: "idx_tb_dataset_lgpd_sensivel" });
db.tb_dataset.createIndex({ "metadados_campos.cod_conceito_canonico": 1 }, { name: "idx_tb_dataset_conceito" });
```

---

## 3. Coleção de Observabilidade e Auditoria Operacional: `tb_auditoria_eventos`

Isolada fisicamente de `tb_dataset` (*Write-Heavy Collection*) para registrar todas as execuções de transporte (ODI/Hop/Python), rejeições enviadas à quarentena, mudanças de metadados/LGPD e acessos, evitando que o documento de catálogo atinja o limite de 16MB do BSON.

### 3.1 As 4 Categorias de Eventos Auditados
1. **`EXECUCAO_CARGA`**: Log de cada lote transportado (registros lidos, inseridos na TRUSTED, rejeitados para Quarentena, tempo de execução e status).
2. **`ALTERACAO_METADADOS`**: Evolução de schema (*Schema Drift* homologado, adição de campos).
3. **`ALTERACAO_CLASSIFICACAO_LGPD`**: Mudança de nível de sigilo, anonimização ou base legal (exige identificação do autor e justificativa).
4. **`ACESSO_CONSUMO`**: Registro de compartilhamento ou consulta a dados restritos/confidenciais.

### 3.2 Script de Criação e Índice TTL de 5 Anos (`schemas_mongo/04_schema_tb_auditoria_eventos.js`)

```javascript
// ============================================================================
// Script: 04_schema_tb_auditoria_eventos.js
// Objetivo: Coleção de auditoria operacional com retenção TTL de 5 anos
// ============================================================================

db.createCollection("tb_auditoria_eventos", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: [
        "cod_evento",
        "cod_dataset",
        "dth_evento",
        "tip_categoria_evento",
        "des_evento",
        "des_usuario_ou_job"
      ],
      properties: {
        _id: { bsonType: ["objectId", "string"] },
        cod_evento: { bsonType: "string" },
        cod_dataset: { bsonType: "string" },
        dth_evento: { bsonType: "date", description: "Timestamp UTC obrigatório (base para o índice TTL)" },
        tip_categoria_evento: {
          enum: [
            "EXECUCAO_CARGA",
            "ALTERACAO_METADADOS",
            "ALTERACAO_CLASSIFICACAO_LGPD",
            "ACESSO_CONSUMO",
            "DEVOLUCAO_DADOS_CLIENTE"
          ]
        },
        des_evento: { bsonType: "string" },
        des_usuario_ou_job: { bsonType: "string" },
        detalhes_execucao: {
          bsonType: "object",
          properties: {
            sts_final: { enum: ["SUCESSO", "SUCESSO_PARCIAL_COM_QUARENTENA", "FALHA_DEVOLVIDO_AO_CLIENTE", "ERRO_TECNICO"] },
            val_tempo_segundos: { bsonType: ["double", "decimal", "int"] },
            qtd_registros_lidos: { bsonType: ["int", "long"] },
            qtd_registros_trusted: { bsonType: ["int", "long"] },
            qtd_registros_quarentena: { bsonType: ["int", "long"] },
            nom_colecao_quarentena_gerada: { bsonType: ["string", "null"] },
            des_mensagem_erro: { bsonType: ["string", "null"] }
          }
        },
        detalhes_alteracao: {
          bsonType: "object",
          properties: {
            nom_campo_afetado: { bsonType: "string" },
            des_valor_anterior: { bsonType: "string" },
            des_valor_novo: { bsonType: "string" },
            des_justificativa: { bsonType: "string" }
          }
        }
      }
    }
  }
});

// 1. Índice Composto para consultas de histórico por Dataset e Tempo Decrescente
db.tb_auditoria_eventos.createIndex(
  { "cod_dataset": 1, "dth_evento": -1 },
  { name: "idx_auditoria_dataset_dth" }
);

// 2. Índice por Categoria de Evento e Status de Execução
db.tb_auditoria_eventos.createIndex(
  { "tip_categoria_evento": 1, "detalhes_execucao.sts_final": 1, "dth_evento": -1 },
  { name: "idx_auditoria_categoria_status" }
);

// 3. Índice TTL de Expurgo Automático após 5 Anos (157.680.000 segundos) conforme Marco Civil / LGPD
db.tb_auditoria_eventos.createIndex(
  { "dth_evento": 1 },
  { expireAfterSeconds: 157680000, name: "idx_ttl_auditoria_5_anos" }
);
```

---

## 4. Mecanismo de Quarentena (`tb_quarentena_<dataset>_<YYYYMMDD>`)

Quando o lote passa pelo transporte (RAW ➔ TRUSTED) e a **Barreira de Qualidade de 4 Etapas** detecta registros com campos obrigatórios vazios, CPFs inválidos ou datas corrompidas enviados pelo cliente:
1. Os registros defeituosos **NUNCA entram na coleção `trusted_*`**.
2. São gravados em `tb_quarentena_<tema>_<yyyymmdd>` com o motivo exato da reprovação para **devolução ao Data Owner do cliente**:

```json
{
  "cod_dataset": "SAEB_SGI_IDENTIDADE_CIDADAO_V1",
  "dth_rejeicao": "2026-10-14T03:15:00Z",
  "cod_job_transporte": "PL_CARGA_IDENTIDADE_ODI",
  "cod_regra_violada": "DQ_01_COMPLETUDE_CPF_OBRIGATORIO",
  "des_motivo_devolucao_cliente": "Registro enviado pelo órgão com campo obrigatório 'identificador' (CPF) vazio/nulo. Responsabilidade de saneamento na origem: SAEB.",
  "jsn_registro_original_bruto": {
    "nome": "JOAO DA SILVA",
    "identificador": "",
    "dataNascimento": "1985-04-12"
  }
}
```

