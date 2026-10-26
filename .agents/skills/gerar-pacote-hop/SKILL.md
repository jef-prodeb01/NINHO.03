---
name: gerar-pacote-hop
description: Gera um pacote completo Apache Hop 2.x (wf_*.hwf, ppl_*.hpl com TableOutput ou OraBulkLoader, hop-lint.yml, hop-pwd.json, diagrama_esteira_hop.svg e DOCUMENTACAO_HOP.md).
---

# /gerar-pacote-hop

Gera um pacote completo Apache Hop 2.x (wf_*.hwf, ppl_*.hpl com TableOutput ou OraBulkLoader, hop-lint.yml, hop-pwd.json, diagrama_esteira_hop.svg e DOCUMENTACAO_HOP.md).

## Execução Determinística

Ao receber o comando /gerar-pacote-hop (ou pedido equivalente), execute imediatamente no terminal via `run_command`:

```bash
python ninho.py gerar-pacote-hop
```

Se o usuário informar argumentos adicionais (ex.: tópico, tema, caminho de arquivo ou flag), repasse-os ao final do comando python ninho.py gerar-pacote-hop <argumentos> e apresente o resultado de forma clara no chat.
