---
name: testar-ninho
description: Executa a suíte E2E de todos os motores do NINHO numa sandbox temporária (seus arquivos de entrega/ e saida/ não são tocados).
---

# /testar-ninho

Executa a suíte E2E de todos os motores do NINHO numa sandbox temporária (seus arquivos de entrega/ e saida/ não são tocados).

## Execução Determinística

Ao receber o comando /testar-ninho (ou pedido equivalente), execute imediatamente na raiz do projeto, usando a ferramenta de terminal da sua IDE (Bash, PowerShell ou `run_command`):

```bash
python ninho.py testar-ninho
```

Se o usuário informar argumentos adicionais (ex.: tópico, tema, caminho de arquivo ou flag), repasse-os ao final do comando python ninho.py testar-ninho <argumentos> e apresente o resultado de forma clara no chat.
