---
name: executar-governanca
description: Executa diretamente a esteira de Governança Corporativa (Gate 0.5 + 5 coleções MongoDB padrão PRODEB + AWS SageMaker Catalog) em saida/governanca_dados/.
---

# /executar-governanca

Executa diretamente a esteira de Governança Corporativa (Gate 0.5 + 5 coleções MongoDB padrão PRODEB + AWS SageMaker Catalog) em saida/governanca_dados/.

## Execução Determinística

Ao receber o comando /executar-governanca (ou pedido equivalente), execute imediatamente no terminal via `run_command`:

```bash
python ninho.py executar-governanca
```

Se o usuário informar argumentos adicionais (ex.: tópico, tema, caminho de arquivo ou flag), repasse-os ao final do comando python ninho.py executar-governanca <argumentos> e apresente o resultado de forma clara no chat.
