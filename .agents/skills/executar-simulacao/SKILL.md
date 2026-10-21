---
name: executar-simulacao
description: Lê as edições feitas nas Blueprints aprovadas e executa a geração física dos scripts em saida/planejador_dw/ e saida/camada_semantica/.
---

# /executar-simulacao

Lê as edições feitas nas Blueprints aprovadas e executa a geração física dos scripts em saida/planejador_dw/ e saida/camada_semantica/.

## Execução Determinística

Ao receber o comando /executar-simulacao (ou pedido equivalente), execute imediatamente no terminal via `run_command`:

```bash
python ninho.py executar-simulacao
```

Se o usuário informar argumentos adicionais (ex.: tópico, tema, caminho de arquivo ou flag), repasse-os ao final do comando python ninho.py executar-simulacao <argumentos> e apresente o resultado de forma clara no chat.
