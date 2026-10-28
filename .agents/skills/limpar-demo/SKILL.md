---
name: limpar-demo
description: Remove todos os artefatos de demonstração gerados pelo comando /demo, deixando entrega/ e saida/ limpos.
---

# /limpar-demo

Remove todos os artefatos de demonstração gerados pelo comando /demo, deixando entrega/ e saida/ limpos.

## Execução Determinística

Ao receber o comando /limpar-demo (ou pedido equivalente), execute imediatamente na raiz do projeto, usando a ferramenta de terminal da sua IDE (Bash, PowerShell ou `run_command`):

```bash
python ninho.py limpar-demo
```

Se o usuário informar argumentos adicionais (ex.: tópico, tema, caminho de arquivo ou flag), repasse-os ao final do comando python ninho.py limpar-demo <argumentos> e apresente o resultado de forma clara no chat.
