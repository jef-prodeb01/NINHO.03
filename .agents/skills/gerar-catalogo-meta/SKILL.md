---
name: gerar-catalogo-meta
description: Gera o DDL e scripts MERGE INTO idempotentes das 8 tabelas META_* da Camada Semântica.
---

# /gerar-catalogo-meta

Gera o DDL e scripts MERGE INTO idempotentes das 8 tabelas META_* da Camada Semântica.

## Execução Determinística

Ao receber o comando /gerar-catalogo-meta (ou pedido equivalente), execute imediatamente na raiz do projeto, usando a ferramenta de terminal da sua IDE (Bash, PowerShell ou `run_command`):

```bash
python ninho.py gerar-catalogo-meta
```

Se o usuário informar argumentos adicionais (ex.: tópico, tema, caminho de arquivo ou flag), repasse-os ao final do comando python ninho.py gerar-catalogo-meta <argumentos> e apresente o resultado de forma clara no chat.
