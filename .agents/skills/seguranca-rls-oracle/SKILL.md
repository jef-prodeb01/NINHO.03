---
name: seguranca-rls-oracle
description: Implementa segurança a nível de linha (Row Level Security - RLS) e Virtual Private Database (VPD via DBMS_RLS) em Data Warehouses e Camadas Semânticas no Oracle, com identidade efetiva segura para pools de conexão de BI/IA. Use quando houver requisitos de acesso restrito, segregação de órgãos, secretarias, unidades ou isolamento multi-tenant.
---

# Skill: Segurança a Nível de Linha no Oracle (RLS & VPD)

Esta skill guia o agente na implementação de **segurança de acesso a nível de linha (RLS)** em tabelas e views analíticas do Oracle 12c+, garantindo que usuários de diferentes órgãos, secretarias ou unidades acessem apenas os dados autorizados, mesmo consultando as mesmas views (`VW_EVENTO`, `VW_KPI_*`).

Para gerar o script do projeto, execute `/gerar-rls` (`python ninho.py gerar-rls`). Ele produz `saida/camada_semantica/meta_projeto/02_rls.sql` já parametrizado. Não escreva o PL/SQL à mão.

---

## 🔑 Regra inegociável: identidade efetiva segura

Power BI, gateways e agentes de IA conectam com **uma conta de serviço** (pool). Filtrar só por `SESSION_USER` daria a todos a visão da conta de serviço.

- A aplicação informa o usuário final com `DBMS_SESSION.SET_IDENTIFIER('<login>')` e limpa com `CLEAR_IDENTIFIER` ao devolver a conexão.
- O banco só aceita o `CLIENT_IDENTIFIER` se `SESSION_USER` estiver em **`RLS_CONTAS_SERVICO`**. Qualquer outra sessão usa `SESSION_USER`.
- **Nunca** use `COALESCE(CLIENT_IDENTIFIER, SESSION_USER)` puro: qualquer usuário pode definir o próprio `CLIENT_IDENTIFIER` e se passar por outro.
- **Nunca** aceite segmentos ou "acesso total" como parâmetro de procedure: quem tem `EXECUTE` no pacote se autoconcederia acesso.
- **Nunca** concatene listas de segmentos (`LISTAGG`): estoura 4000 bytes (ORA-01489) com centenas de unidades. Use subconsulta/`EXISTS` e `DBMS_ASSERT.ENQUOTE_LITERAL`.
- Funções de predicado são **fail-closed** (`EXCEPTION WHEN OTHERS THEN RETURN '1 = 0'`) e as políticas usam `POLICY_TYPE => DBMS_RLS.DYNAMIC`.

---

## 🎯 Estratégias (escolha uma)

| Estratégia | Mecanismo | Recomendação de Uso |
| :--- | :--- | :--- |
| **A: Filtro na View** | `WHERE EXISTS (SELECT 1 FROM USUARIO_SEGMENTOS ... = FN_<PROJETO>_USUARIO_EFETIVO ...)` | Relatórios simples; fácil de auditar. |
| **C: Oracle VPD** | `DBMS_RLS.ADD_POLICY` com predicado dinâmico | Segurança mandatória, inclusive em consultas ad-hoc e Text-to-SQL. Padrão do `/gerar-rls`. |
| **D: META por projeto** | VPD nas tabelas `META_*` | Vários projetos no mesmo schema; regras `GLOBAL` sempre visíveis. |

A antiga estratégia B (contexto preenchido no logon com `LISTAGG`) foi descontinuada: estourava 4000 bytes e não funciona com pool, porque o logon acontece antes do `SET_IDENTIFIER`.

---

## 🏛️ Tabelas de apoio

- `USUARIO_SEGMENTOS (PROJETO, USUARIO_ORACLE, SEGMENTO, IND_ACESSO_TOTAL, DT_CRIACAO)`: usuário efetivo x segmento permitido.
- `RLS_CONTAS_SERVICO (USUARIO_ORACLE, DES_FINALIDADE, DT_CRIACAO)`: contas de pool autorizadas a repassar identidade.

---

## 📂 Destino Canônico de Saída

- `saida/camada_semantica/meta_projeto/02_rls.sql` (gerado por `/gerar-rls`).

Template de referência (fonte única em `modulos/camada_semantica/templates/02_rls_template.sql`, cópia sincronizada aqui): [template_rls_vpd.sql](./templates/template_rls_vpd.sql).
