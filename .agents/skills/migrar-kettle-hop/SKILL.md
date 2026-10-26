---
name: migrar-kettle-hop
description: Migra projetos legados do Pentaho Kettle (.ktr, .kjb, shared.xml) para Apache Hop 2.x (.hpl, .hwf, metadata/rdbms/*.json e diagrama SVG).
---

# /migrar-kettle-hop

Migra projetos legados do Pentaho Kettle (.ktr, .kjb, shared.xml) para Apache Hop 2.x (.hpl, .hwf, metadata/rdbms/*.json e diagrama SVG).

## Execução Determinística

Ao receber o comando /migrar-kettle-hop (ou pedido equivalente), execute imediatamente no terminal via `run_command`:

```bash
python ninho.py migrar-kettle-hop
```

Se o usuário informar argumentos adicionais (ex.: tópico, tema, caminho de arquivo ou flag), repasse-os ao final do comando python ninho.py migrar-kettle-hop <argumentos> e apresente o resultado de forma clara no chat.
