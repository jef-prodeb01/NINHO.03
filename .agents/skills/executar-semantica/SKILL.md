---
name: executar-semantica
description: Executa diretamente a geração completa da Camada Semântica (Views em 3 camadas, 8 tabelas META_* e RLS) em saida/camada_semantica/ sem exigir simulação.
---

# /executar-semantica

Executa diretamente a geração completa da Camada Semântica (Views em 3 camadas, 8 tabelas META_* e RLS) em saida/camada_semantica/ sem exigir simulação.

## Execução Determinística

Ao receber o comando /executar-semantica (ou pedido equivalente), execute imediatamente na raiz do projeto, usando a ferramenta de terminal da sua IDE (Bash, PowerShell ou `run_command`):

```bash
python ninho.py executar-semantica
```

Se o usuário informar argumentos adicionais (ex.: tópico, tema, caminho de arquivo ou flag), repasse-os ao final do comando python ninho.py executar-semantica <argumentos> e apresente o resultado de forma clara no chat.
