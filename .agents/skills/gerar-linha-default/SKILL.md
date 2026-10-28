---
name: gerar-linha-default
description: Gera apenas o script idempotente MERGE INTO do registro sentinela -1 ('Não Informado') nas dimensões.
---

# /gerar-linha-default

Gera apenas o script idempotente MERGE INTO do registro sentinela -1 ('Não Informado') nas dimensões.

## Execução Determinística

Ao receber o comando /gerar-linha-default (ou pedido equivalente), execute imediatamente na raiz do projeto, usando a ferramenta de terminal da sua IDE (Bash, PowerShell ou `run_command`):

```bash
python ninho.py gerar-linha-default
```

Se o usuário informar argumentos adicionais (ex.: tópico, tema, caminho de arquivo ou flag), repasse-os ao final do comando python ninho.py gerar-linha-default <argumentos> e apresente o resultado de forma clara no chat.
