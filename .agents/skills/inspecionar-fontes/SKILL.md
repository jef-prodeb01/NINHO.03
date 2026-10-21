---
name: inspecionar-fontes
description: Inspeciona DDLs SQL/CSV depositados em entrega/planejador_dw/ddl/, extrai metadados e gera sugestões analíticas.
---

# /inspecionar-fontes

Inspeciona DDLs SQL/CSV depositados em entrega/planejador_dw/ddl/, extrai metadados e gera sugestões analíticas.

## Execução Determinística

Ao receber o comando /inspecionar-fontes (ou pedido equivalente), execute imediatamente no terminal via `run_command`:

```bash
python ninho.py inspecionar-fontes
```

Se o usuário informar argumentos adicionais (ex.: tópico, tema, caminho de arquivo ou flag), repasse-os ao final do comando python ninho.py inspecionar-fontes <argumentos> e apresente o resultado de forma clara no chat.
