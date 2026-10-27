---
name: gerar-dw
description: Alias para /executar-dw: executa diretamente a construção completa do Data Warehouse em saida/planejador_dw/.
---

# /gerar-dw

Alias para /executar-dw: executa diretamente a construção completa do Data Warehouse em saida/planejador_dw/.

## Execução Determinística

Ao receber o comando /gerar-dw (ou pedido equivalente), execute imediatamente no terminal via `run_command`:

```bash
python ninho.py gerar-dw
```

Se o usuário informar argumentos adicionais (ex.: tópico, tema, caminho de arquivo ou flag), repasse-os ao final do comando python ninho.py gerar-dw <argumentos> e apresente o resultado de forma clara no chat.
