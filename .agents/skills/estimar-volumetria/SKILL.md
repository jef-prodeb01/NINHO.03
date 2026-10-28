---
name: estimar-volumetria
description: Calculadora DBA: tamanho de tabelas e índices, crescimento em 5 anos, recomendação de particionamento e dimensionamento de tablespaces.
---

# /estimar-volumetria

Calculadora DBA: tamanho de tabelas e índices, crescimento em 5 anos, recomendação de particionamento e dimensionamento de tablespaces.

## Execução Determinística

Ao receber o comando /estimar-volumetria (ou pedido equivalente), execute imediatamente na raiz do projeto, usando a ferramenta de terminal da sua IDE (Bash, PowerShell ou `run_command`):

```bash
python ninho.py estimar-volumetria
```

Se o usuário informar argumentos adicionais (ex.: tópico, tema, caminho de arquivo ou flag), repasse-os ao final do comando python ninho.py estimar-volumetria <argumentos> e apresente o resultado de forma clara no chat.
