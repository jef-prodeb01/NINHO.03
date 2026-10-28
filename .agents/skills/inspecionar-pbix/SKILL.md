---
name: inspecionar-pbix
description: Descompacta e audita arquivos .pbix do Power BI, extraindo filtros AST/DAX e executando as heurísticas PBIX-H1 a PBIX-H5.
---

# /inspecionar-pbix

Descompacta e audita arquivos .pbix do Power BI, extraindo filtros AST/DAX e executando as heurísticas PBIX-H1 a PBIX-H5.

## Execução Determinística

Ao receber o comando /inspecionar-pbix (ou pedido equivalente), execute imediatamente na raiz do projeto, usando a ferramenta de terminal da sua IDE (Bash, PowerShell ou `run_command`):

```bash
python ninho.py inspecionar-pbix
```

Se o usuário informar argumentos adicionais (ex.: tópico, tema, caminho de arquivo ou flag), repasse-os ao final do comando python ninho.py inspecionar-pbix <argumentos> e apresente o resultado de forma clara no chat.
