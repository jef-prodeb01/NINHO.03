---
name: inspecionar-governanca
description: Audita (sem gerar nada) planilhas e amostras de governança: Gate 0.5, cruzamento dicionário x amostra e classificação LGPD. Aceita --json.
---

# /inspecionar-governanca

Audita (sem gerar nada) planilhas e amostras de governança: Gate 0.5, cruzamento dicionário x amostra e classificação LGPD. Aceita --json.

## Execução Determinística

Ao receber o comando /inspecionar-governanca (ou pedido equivalente), execute imediatamente na raiz do projeto, usando a ferramenta de terminal da sua IDE (Bash, PowerShell ou `run_command`):

```bash
python ninho.py inspecionar-governanca
```

Se o usuário informar argumentos adicionais (ex.: tópico, tema, caminho de arquivo ou flag), repasse-os ao final do comando python ninho.py inspecionar-governanca <argumentos> e apresente o resultado de forma clara no chat.
