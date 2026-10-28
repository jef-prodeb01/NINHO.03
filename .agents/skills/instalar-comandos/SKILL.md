---
name: instalar-comandos
description: Registra e sincroniza todos os comandos /<comando> do NINHO como Skills nativas (.agents/skills/) na IDE.
---

# /instalar-comandos

Registra e sincroniza todos os comandos /<comando> do NINHO como Skills nativas (.agents/skills/) na IDE.

## Execução Determinística

Ao receber o comando /instalar-comandos (ou pedido equivalente), execute imediatamente na raiz do projeto, usando a ferramenta de terminal da sua IDE (Bash, PowerShell ou `run_command`):

```bash
python ninho.py instalar-comandos
```

Se o usuário informar argumentos adicionais (ex.: tópico, tema, caminho de arquivo ou flag), repasse-os ao final do comando python ninho.py instalar-comandos <argumentos> e apresente o resultado de forma clara no chat.
