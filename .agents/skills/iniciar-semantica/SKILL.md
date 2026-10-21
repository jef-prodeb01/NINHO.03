---
name: iniciar-semantica
description: Executa a geração completa da Camada Semântica (Views + Catálogo META_* + RLS + Validações).
---

# /iniciar-semantica

Executa a geração completa da Camada Semântica (Views + Catálogo META_* + RLS + Validações).

## Execução Determinística

Ao receber o comando /iniciar-semantica (ou pedido equivalente), execute imediatamente no terminal via `run_command`:

```bash
python ninho.py iniciar-semantica
```

Se o usuário informar argumentos adicionais (ex.: tópico, tema, caminho de arquivo ou flag), repasse-os ao final do comando python ninho.py iniciar-semantica <argumentos> e apresente o resultado de forma clara no chat.
