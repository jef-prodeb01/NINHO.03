---
name: validar-medidas-bi
description: Executa a Prova Real Pós-Carga das medidas DAX do Guia do Analista de BI contra amostras de DIM_* e FATO_*, corrige medidas parcialmente corretas e popula o Mockup Visual com os valores reais.
---

# /validar-medidas-bi

Executa a Prova Real Pós-Carga das medidas DAX do Guia do Analista de BI contra amostras de DIM_* e FATO_*, corrige medidas parcialmente corretas e popula o Mockup Visual com os valores reais.

## Execução Determinística

Ao receber o comando /validar-medidas-bi (ou pedido equivalente), execute imediatamente na raiz do projeto, usando a ferramenta de terminal da sua IDE (Bash, PowerShell ou `run_command`):

```bash
python ninho.py validar-medidas-bi
```

Se o usuário informar argumentos adicionais (ex.: tópico, tema, caminho de arquivo ou flag), repasse-os ao final do comando python ninho.py validar-medidas-bi <argumentos> e apresente o resultado de forma clara no chat.
