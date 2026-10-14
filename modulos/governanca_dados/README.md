# Módulo de Governança de Dados (Padrão PRODEB MongoDB & AWS SageMaker Catalog)

Este diretório centraliza a arquitetura oficial, o formulário de intake, os padrões de nomenclatura/tipagem BSON e a camada semântica documental para governança corporativa de dados no **MongoDB Enterprise** com publicação ativa no **AWS Glue Data Catalog** e **Amazon SageMaker Unified Studio / SageMaker Catalog (ex-DataZone)**.

---

## 🛑 Regra de Ouro — Fronteira de Responsabilidade (Gate 0.5)

- **Qualidade na Origem é Responsabilidade do Cliente:** Nossa atuação cobre **exclusivamente o transporte dos dados saneados para o MongoDB e sua catalogação final na AWS**.
- **Devolução Obrigatória ao Cliente:** Planilhas com abas `Dados - Insumos` ou `Dicionário de Dados` incompletas, textos evasivos (*"ver com sap"*, *"a definir"*), campos sem classificação LGPD (`Anonimizar?`, `Sensibilidade`, `Sensível?`) ou amostras `.csv` com registros vazios/colunas fantasmas (`;;;`) são automaticamente reprovadas por `python core/scripts_comuns/inspecionar_insumos_governanca.py` e devolvidas ao órgão de origem via Relatório Formal de Devolução.

---

## 📂 Documentos e Templates do Módulo

1. **[INTAKE_GOVERNANCA.md](INTAKE_GOVERNANCA.md)** ⭐ *(Ponto de Partida Obrigatório — Gate 0)*
   - Formulário de entrada para identificação do dataset (`SIGLA_ORGAO_UNIDADE_TEMA_VERSAO`), seleção de tecnologias (MongoDB, AWS SageMaker Catalog / Glue, ODI, Hop, Python) e diretrizes LGPD/LAI.
2. **[AGENTS.md](AGENTS.md)**
   - Protocolo de atuação do Agente de Governança (Gate 0, Gate 0.5 de Devolução ao Cliente, Padrão PRODEB e Radar Consultivo da IA).
3. **[ARQUITETURA_MONGO_AWS.md](ARQUITETURA_MONGO_AWS.md)** ⭐ *(Arquitetura Ponta a Ponta)*
   - Topologia completa: Origem Saneada pelo Cliente ➔ Gate 0.5 ➔ Transporte (ODI/Hop/Python) ➔ MongoDB Enterprise (`tb_dataset`, `tb_sem_dominios`, `tb_sem_conceitos`, `tb_auditoria_eventos`) ➔ AWS Glue & Amazon SageMaker Unified Studio / SageMaker Catalog.
4. **[DOCUMENTO_CONSOLIDADO_GOVERNANCA_DADOS.md](DOCUMENTO_CONSOLIDADO_GOVERNANCA_DADOS.md)**
   - Especificação técnica consolidada do padrão PRODEB no MongoDB Enterprise (nomenclatura de datasets e atributos, tipagem BSON estrita, `$jsonSchema`, quarentena e auditoria).
5. **[CAMADA_SEMANTICA_GOVERNANCA_DADOS_MONGODB.md](CAMADA_SEMANTICA_GOVERNANCA_DADOS_MONGODB.md)**
   - Especificação da Camada Semântica de Governança (`tb_sem_dominios` e `tb_sem_conceitos`), casos reais (SAEB, DETRAN, PLANSERV, SUPREV, BA.GOV.BR) e queries de descoberta (`$lookup`).
6. **[templates/Template_Insumos_Governanca_Dados.xlsx](templates/Template_Insumos_Governanca_Dados.xlsx)**
   - Planilha oficial em branco (`Dados - Insumos` e `Dicionário de Dados`) para envio aos órgãos clientes.
7. **[ARQUITETURA_FRAMEWORK_GOVERNANCA.md](ARQUITETURA_FRAMEWORK_GOVERNANCA.md)** & **[PROPOSTAS_DE_NOMES.md](PROPOSTAS_DE_NOMES.md)**
   - Referências conceituais DAMA-DMBOK e histórico de nomenclatura.
