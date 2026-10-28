---
name: empacotar-projeto
description: Verifica o status do projeto, exporta a entrega completa em .zip ou limpa o workspace para um novo projeto.
---

# /empacotar-projeto

Verifica o status do projeto, exporta a entrega completa em .zip ou limpa o workspace para um novo projeto.

## Execução Determinística

Ao receber o comando /empacotar-projeto (ou pedido equivalente), execute imediatamente na raiz do projeto, usando a ferramenta de terminal da sua IDE (Bash, PowerShell ou `run_command`):

```bash
python ninho.py empacotar-projeto
```

Se o usuário informar argumentos adicionais (ex.: tópico, tema, caminho de arquivo ou flag), repasse-os ao final do comando python ninho.py empacotar-projeto <argumentos> e apresente o resultado de forma clara no chat.
