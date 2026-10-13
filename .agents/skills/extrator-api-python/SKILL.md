---
name: extrator-api-python
description: >-
  Gera extratores em Python para ingestão de APIs REST (paginação, autenticação token/OAuth,
  retentativas) aterrissando em tabelas Staging no Oracle. Use APENAS quando a opção
  Python API estiver explicitamente marcada no INTAKE_DW.md.
---

# Skill: Extrator de APIs Web em Python

Esta skill orienta a geração de scripts Python robustos para consumo e ingestão de APIs RESTful públicas ou corporativas, gravando os dados diretamente nas tabelas de Staging (`STG_*`) do Oracle DW.

> 🛑 **REGRA DE ATIVAÇÃO CONDICIONAL:**  
> Esta skill **NUNCA** deve gerar arquivos se o Engenheiro de Dados não tiver marcado `[x] Extratores Python / Ingestão de APIs` na Seção 1 do `INTAKE_DW.md`.  
> Se desmarcado, a pasta `saida/planejador_dw/07_extratores_python/` DEVE permanecer intacta contendo apenas seu `.gitkeep`.

---

## 1. Padrões de Engenharia do Extrator

Ao ser acionada, os scripts gerados devem ser salvos diretamente em:
`saida/planejador_dw/07_extratores_python/`

### Requisitos Técnicos Mandatórios:
1. **Biblioteca de Banco:** Utilizar `oracledb` (driver oficial moderno do Oracle, modo Thin padrão, sem necessidade de Oracle Client instalado).
2. **Resiliência e Retentativas:** Usar `urllib3.util.Retry` com `requests.adapters.HTTPAdapter` para tratar erros transitórios de rede (429, 500, 502, 503, 504).
3. **Paginação Eficiente:** Tratar cursores, offsets (`limit`/`offset`) ou números de página (`page`/`size`) sem carregar milhões de registros em memória de uma só vez.
4. **Inserção em Lote (*Bulk Insert*):** Usar `cursor.executemany()` em lotes de 1.000 a 5.000 registros para máxima performance de aterrissagem na Staging.
5. **Configurações por Variáveis de Ambiente:** NUNCA deixar credenciais ou tokens hardcoded no código. Utilizar `os.getenv()`.

---

## 2. Template do Extrator Python

Consulte o modelo em [template_extrator_api.py](./templates/template_extrator_api.py).
