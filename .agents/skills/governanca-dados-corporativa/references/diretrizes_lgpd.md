# Diretrizes Corporativas de Conformidade LGPD e LAI

## 1. Classificação de Dados em 4 Níveis

| Nível | Categoria | Descrição | Exemplos | Tratamento Técnico |
| :---: | :---: | :--- | :--- | :--- |
| **1** | `PÚBLICO` | Dados de transparência ativa que não identificam pessoas físicas. | Nomes de órgãos, tabela de feriados, orçamentos consolidados. | Livre acesso |
| **2** | `INTERNO` | Dados operacionais corporativos de circulação restrita à organização. | Códigos de fila, métricas de produtividade interna, logs de sistema. | Acesso autenticado |
| **3** | `PESSOAL` | Dado relativo a pessoa física identificada ou identificável (Art. 5º, I, LGPD). | Nome, CPF, e-mail, telefone, cargo, matrícula funcional. | Mascaramento / Pseudo-anonimização |
| **4** | `SENSÍVEL` | Dados sobre origem racial, convicção religiosa, saúde, biometria (Art. 5º, II, LGPD). | Prontuários, laudos médicos, dados biométricos, processos disciplinares sigilosos. | Criptografia + RLS estrito |

---

## 2. Padrões de Mascaramento no Oracle

Para colunas classificadas como `PESSOAL` ou `SENSÍVEL`, aplique máscaras ou regras de desidentificação nas views analíticas expostas a consumidores amplos:

- **CPF:** `SUBSTR(CPF, 1, 3) || '.***.***-' || SUBSTR(CPF, 10, 2)`
- **E-mail:** `SUBSTR(EMAIL, 1, 2) || '****@' || SUBSTR(EMAIL, INSTR(EMAIL, '@') + 1)`
- **Nomes de Partes em Processos Sigilosos:** Mascarar com a expressão `'RESERVADO - LEI 13.709/2018'`.

