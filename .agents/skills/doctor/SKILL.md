---
name: doctor
description: Diagnostica a saúde das pastas de entrega/, detecta arquivos soltos fora da subpasta canônica e os organiza automaticamente.
---

# /doctor

Diagnostica a saúde das pastas de entrega/, detecta arquivos soltos fora da subpasta canônica e os organiza automaticamente.

## Execução Determinística

Ao receber o comando /doctor (ou pedido equivalente), execute imediatamente no terminal via `run_command`:

```bash
python ninho.py doctor
```

Se o usuário informar argumentos adicionais (ex.: tópico, tema, caminho de arquivo ou flag), repasse-os ao final do comando python ninho.py doctor <argumentos> e apresente o resultado de forma clara no chat.
