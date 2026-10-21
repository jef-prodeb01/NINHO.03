---
name: gerar-indices
description: Gera apenas índices de tuning (Bitmap/B-Tree) + procedures PRC_PRE_CARGA_FATO e PRC_POS_CARGA_FATO.
---

# /gerar-indices

Gera apenas índices de tuning (Bitmap/B-Tree) + procedures PRC_PRE_CARGA_FATO e PRC_POS_CARGA_FATO.

## Execução Determinística

Ao receber o comando /gerar-indices (ou pedido equivalente), execute imediatamente no terminal via `run_command`:

```bash
python ninho.py gerar-indices
```

Se o usuário informar argumentos adicionais (ex.: tópico, tema, caminho de arquivo ou flag), repasse-os ao final do comando python ninho.py gerar-indices <argumentos> e apresente o resultado de forma clara no chat.
