---
name: seguranca-rls-oracle
description: Implementa segurança a nível de linha (Row Level Security - RLS) e Virtual Private Database (VPD via DBMS_RLS / DBMS_SESSION) em Data Warehouses e Camadas Semânticas no Oracle. Use quando houver requisitos de acesso restrito, segregação de órgãos, secretarias, unidades ou isolamento multi-tenant.
---

# Skill: Segurança a Nível de Linha no Oracle (RLS & VPD)

Esta skill guia o agente na implementação de **segurança de acesso a nível de linha (Row Level Security - RLS)** em tabelas e views analíticas do Oracle 12c+. 

Ela garante que usuários de diferentes órgãos, secretarias, unidades administrativas ou clientes acessem estritamente os dados que lhes são autorizados, mesmo consultando as mesmas views corporativas (`VW_EVENTO`, `VW_KPI_*`).

---

## 🎯 As 3 Estratégias de RLS no Oracle

O agente deve selecionar ou sugerir ao engenheiro **uma** das três estratégias (nunca misturar):

| Estratégia | Mecanismo | Complexidade | Recomendação de Uso |
| :--- | :--- | :--- | :--- |
| **Estratégia A: Filtro na View Semântica** | `WHERE ... IN (SELECT SEGMENTO FROM USUARIO_SEGMENTOS WHERE ...)` | Baixa | Relatórios simples de BI e consultas via SQL direto. Fácil de auditar. |
| **Estratégia B: Contexto de Sessão** | `SYS_CONTEXT('CTX_SEGURANCA', 'SEGMENTO')` + `DBMS_SESSION` | Média | Dashboards com conexão compartilhada onde a aplicação seta o contexto da sessão. |
| **Estratégia C: Oracle VPD Nativo** | `DBMS_RLS.ADD_POLICY` em tabelas/views | Avançada | Segurança mandatória transparente em banco: impede vazamento mesmo em consultas ad-hoc ou Text-to-SQL. |

---

## 🏛️ Tabela Canônica de Controle: `USUARIO_SEGMENTOS`

Em qualquer estratégia, cria-se a tabela de apoio para mapear usuário ➔ segmentos permitidos:

```sql
CREATE TABLE USUARIO_SEGMENTOS (
    PROJETO           VARCHAR2(50) DEFAULT 'GLOBAL' NOT NULL,
    USUARIO_ORACLE    VARCHAR2(128) NOT NULL,
    SEGMENTO          VARCHAR2(128) NOT NULL,
    IND_ACESSO_TOTAL  CHAR(1) DEFAULT 'N' NOT NULL,  -- 'S' ignora o filtro (ex: Gestor Geral / Auditoria)
    DT_CRIACAO        DATE DEFAULT SYSDATE NOT NULL,
    CONSTRAINT PK_USUARIO_SEGMENTOS PRIMARY KEY (PROJETO, USUARIO_ORACLE, SEGMENTO),
    CONSTRAINT CHK_USR_SEG_TOTAL CHECK (IND_ACESSO_TOTAL IN ('S', 'N'))
);
```

---

## 📂 Destino Canônico de Saída

Quando acionada, os artefatos de segurança devem ser gerados no arquivo canônico da Camada Semântica:
- `saida/camada_semantica/meta_projeto/02_rls.sql` (DDL da tabela `USUARIO_SEGMENTOS`, inserts de carga inicial, criação de contextos, funções de predicado e políticas VPD).

Consulte o template completo em [template_rls_vpd.sql](./templates/template_rls_vpd.sql).


