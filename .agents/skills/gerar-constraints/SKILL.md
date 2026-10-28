---
name: gerar-constraints
description: Gera apenas constraints PK/FK não-destrutivas (ENABLE/RELY NOVALIDATE) sobre DW existente.
---

# /gerar-constraints

Gera apenas constraints PK/FK não-destrutivas (ENABLE/RELY NOVALIDATE) sobre DW existente.

## Execução Determinística

Ao receber o comando /gerar-constraints (ou pedido equivalente), execute imediatamente na raiz do projeto, usando a ferramenta de terminal da sua IDE (Bash, PowerShell ou `run_command`):

```bash
python ninho.py gerar-constraints
```

Se o usuário informar argumentos adicionais (ex.: tópico, tema, caminho de arquivo ou flag), repasse-os ao final do comando python ninho.py gerar-constraints <argumentos> e apresente o resultado de forma clara no chat.
