---
name: ajuda
description: Exibe o catálogo completo de comandos da plataforma NINHO organizado por tópico (use /ajuda para não colidir com o /help nativo da IDE).
---

# /ajuda

Exibe o catálogo completo de comandos da plataforma NINHO organizado por tópico (use /ajuda para não colidir com o /help nativo da IDE).

## Execução Determinística

Ao receber o comando /ajuda (ou pedido equivalente), execute imediatamente no terminal via `run_command`:

```bash
python ninho.py ajuda
```

Se o usuário informar argumentos adicionais (ex.: tópico, tema, caminho de arquivo ou flag), repasse-os ao final do comando python ninho.py ajuda <argumentos> e apresente o resultado de forma clara no chat.
