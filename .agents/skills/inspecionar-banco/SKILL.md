---
name: inspecionar-banco
description: Extrai o DDL real de um schema Oracle (DBMS_METADATA) para entrega/planejador_dw/ddl/; sem conexão, gera o script de extração para o DBA.
---

# /inspecionar-banco

Extrai o DDL real de um schema Oracle (DBMS_METADATA) para entrega/planejador_dw/ddl/; sem conexão, gera o script de extração para o DBA.

## Execução Determinística

Ao receber o comando /inspecionar-banco (ou pedido equivalente), execute imediatamente na raiz do projeto, usando a ferramenta de terminal da sua IDE (Bash, PowerShell ou `run_command`):

```bash
python ninho.py inspecionar-banco
```

Se o usuário informar argumentos adicionais (ex.: tópico, tema, caminho de arquivo ou flag), repasse-os ao final do comando python ninho.py inspecionar-banco <argumentos> e apresente o resultado de forma clara no chat.
