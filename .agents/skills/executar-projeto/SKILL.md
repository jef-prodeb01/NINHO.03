---
name: executar-projeto
description: Executa diretamente a geração completa do Data Warehouse e da Camada Semântica de ponta a ponta em saida/ sem exigir simulação prévia.
---

# /executar-projeto

Executa diretamente a geração completa do Data Warehouse e da Camada Semântica de ponta a ponta em saida/ sem exigir simulação prévia.

## Execução Determinística

Ao receber o comando /executar-projeto (ou pedido equivalente), execute imediatamente na raiz do projeto, usando a ferramenta de terminal da sua IDE (Bash, PowerShell ou `run_command`):

```bash
python ninho.py executar-projeto
```

Se o usuário informar argumentos adicionais (ex.: tópico, tema, caminho de arquivo ou flag), repasse-os ao final do comando python ninho.py executar-projeto <argumentos> e apresente o resultado de forma clara no chat.
