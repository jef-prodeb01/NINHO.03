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
    USUARIO_ORACLE    VARCHAR2(128) NOT NULL,
    SEGMENTO          VARCHAR2(128) NOT NULL,
    IND_ACESSO_TOTAL  CHAR(1) DEFAULT 'N' NOT NULL,  -- 'S' ignora o filtro (ex: Gestor Geral / Auditoria)
    DT_CRIACAO        DATE DEFAULT SYSDATE NOT NULL,
    CONSTRAINT PK_USUARIO_SEGMENTOS PRIMARY KEY (USUARIO_ORACLE, SEGMENTO)
);
```

---

## 📂 Destino Canônico de Saída

Quando acionada, os artefatos de segurança devem ser gerados em:
- `saida/camada_semantica/seguranca/02_rls_politicas.sql` (Criação de contextos, funções de predicado e políticas VPD).
- `saida/camada_semantica/seguranca/01_usuario_segmentos.sql` (DDL da tabela de permissões e inserts de carga inicial).

Consulte o template completo em [template_rls_vpd.sql](./templates/template_rls_vpd.sql).

