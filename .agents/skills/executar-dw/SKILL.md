---
name: executar-dw
description: Executa diretamente a geração completa do Data Warehouse (pastas 01 a 11 em saida/planejador_dw/) a partir dos insumos em entrega/planejador_dw/ sem exigir etapa de simulação.
---

# /executar-dw

Executa diretamente a geração completa do Data Warehouse (pastas 01 a 11 em saida/planejador_dw/) a partir dos insumos em entrega/planejador_dw/ sem exigir etapa de simulação.

## Execução Determinística

Ao receber o comando /executar-dw (ou pedido equivalente), execute imediatamente no terminal via `run_command`:

```bash
python ninho.py executar-dw
```

Se o usuário informar argumentos adicionais (ex.: tópico, tema, caminho de arquivo ou flag), repasse-os ao final do comando python ninho.py executar-dw <argumentos> e apresente o resultado de forma clara no chat.
