---
name: comparar-modelo
description: Compara o DW em produção (entrega/planejador_dw/ddl) com o modelo novo (saida/) e gera ALTERs incrementais seguros (remoções e estreitamentos comentados).
---

# /comparar-modelo

Compara o DW em produção (entrega/planejador_dw/ddl) com o modelo novo (saida/) e gera ALTERs incrementais seguros (remoções e estreitamentos comentados).

## Execução Determinística

Ao receber o comando /comparar-modelo (ou pedido equivalente), execute imediatamente na raiz do projeto, usando a ferramenta de terminal da sua IDE (Bash, PowerShell ou `run_command`):

```bash
python ninho.py comparar-modelo
```

Se o usuário informar argumentos adicionais (ex.: tópico, tema, caminho de arquivo ou flag), repasse-os ao final do comando python ninho.py comparar-modelo <argumentos> e apresente o resultado de forma clara no chat.
