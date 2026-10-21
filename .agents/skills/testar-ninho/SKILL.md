---
name: testar-ninho
description: Executa a suíte automatizada de testes End-to-End (E2E) em todos os motores do NINHO e limpa o workspace ao final.
---

# /testar-ninho

Executa a suíte automatizada de testes End-to-End (E2E) em todos os motores do NINHO e limpa o workspace ao final.

## Execução Determinística

Ao receber o comando /testar-ninho (ou pedido equivalente), execute imediatamente no terminal via `run_command`:

```bash
python ninho.py testar-ninho
```

Se o usuário informar argumentos adicionais (ex.: tópico, tema, caminho de arquivo ou flag), repasse-os ao final do comando python ninho.py testar-ninho <argumentos> e apresente o resultado de forma clara no chat.
