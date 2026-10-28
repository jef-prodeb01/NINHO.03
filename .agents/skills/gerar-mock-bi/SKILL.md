---
name: gerar-mock-bi
description: Gera massa CSV sintética relacionalmente íntegra (~3% de chaves -1) para homologação de dashboards no Power BI.
---

# /gerar-mock-bi

Gera massa CSV sintética relacionalmente íntegra (~3% de chaves -1) para homologação de dashboards no Power BI.

## Execução Determinística

Ao receber o comando /gerar-mock-bi (ou pedido equivalente), execute imediatamente na raiz do projeto, usando a ferramenta de terminal da sua IDE (Bash, PowerShell ou `run_command`):

```bash
python ninho.py gerar-mock-bi
```

Se o usuário informar argumentos adicionais (ex.: tópico, tema, caminho de arquivo ou flag), repasse-os ao final do comando python ninho.py gerar-mock-bi <argumentos> e apresente o resultado de forma clara no chat.
