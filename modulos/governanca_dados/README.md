# Módulo de Planejamento de Governança de Dados

Este diretório centraliza as propostas de arquitetura, padrões corporativos e planejamentos conceituais para a plataforma de governança.

---

## 📂 Documentos Disponíveis

### 1. [ARQUITETURA_MONGO_AWS.md](ARQUITETURA_MONGO_AWS.md) ⭐ *(Novo / Atual)*
> **Arquitetura de Governança para Setor Público: MongoDB Lakehouse + AWS Glue + Amazon DataZone**
- Estratégia sem Amazon S3 e com desvinculação do DW Oracle.
- Organização em MongoDB para múltiplos Órgãos (Databases), Diretorias e Unidades (`_org`).
- Envelope Canônico de Metadados (`_governance`, LAI, LGPD).
- Papel das ferramentas: Apache Hop, Python, ODI.
- Integração e catálogo com AWS Glue Data Catalog e Amazon DataZone.

### 2. [ARQUITETURA_FRAMEWORK_GOVERNANCA.md](ARQUITETURA_FRAMEWORK_GOVERNANCA.md)
> **Proposta de Arquitetura em 4 Pilares DAMA-DMBOK**
- Visão macro dos módulos: Semântica, Data Quality, Governança/LGPD e Observabilidade.
- Conceito de Metadados Ativos (*Active Metadata*).

### 3. [PROPOSTAS_DE_NOMES.md](PROPOSTAS_DE_NOMES.md)
> **Brainstorming e Nomenclaturas Corporativas**
- Sugestões de nomes para a plataforma e submódulos.
