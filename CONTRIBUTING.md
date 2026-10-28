# Como manter e evoluir o NINHO

Guia curto para quem mexe no código da plataforma (não para quem só usa os comandos).

## Ambiente

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate   |   Linux/macOS: source .venv/bin/activate
pip install -r requirements-dev.txt
```

Os motores rodam só com a biblioteca padrão (Python 3.10+). `openpyxl` e `defusedxml` são opcionais; `/doctor` mostra o que está faltando.

## Antes de cada commit

```bash
ruff check .                  # lint (regras em pyproject.toml)
pytest                        # testes unitários rápidos (tests/)
python ninho.py testar-ninho  # suíte E2E completa, numa sandbox temporária
```

O CI (`.github/workflows/ci.yml` ou `.gitlab-ci.yml`) roda os três passos em Python 3.10 e 3.12.

> `testar-ninho` copia o projeto para uma pasta temporária e roda lá, por isso nunca apaga seus arquivos de `entrega/` e `saida/`. Use `--manter-arquivos` para inspecionar o que foi gerado e `--parar-no-erro` para interromper na primeira falha (o padrão roda todas e mostra o placar).

### Golden files (SQL gerado congelado)

`tests/test_golden.py` gera DW, ODI, Camada Semântica, RLS e `META_*` para um DDL de referência e compara com `tests/golden/`. Se você mudou um gerador de propósito, regenere e **revise o diff** antes do commit:

```bash
NINHO_ATUALIZAR_GOLDEN=1 pytest tests/test_golden.py          # Linux/macOS
$env:NINHO_ATUALIZAR_GOLDEN=1; pytest tests/test_golden.py    # PowerShell
```

Se o diff mostrar mudança que você não pretendia, é regressão: corrija o código, não o golden.

### Templates com cópia na skill

`tests/test_templates_sincronizados.py` exige que as cópias em `.agents/skills/*/templates/` sejam idênticas à fonte única em `modulos/*/templates/` (RLS, extrator API e `09_validacoes`). Edite sempre o arquivo de `modulos/` e copie para a skill.

## Onde fica cada coisa

| Pasta | Conteúdo |
| --- | --- |
| `ninho.py` | Dispatcher: mapa `ROTAS_COMANDOS` (comando → script + argumentos) e `DESCRICOES_SKILLS_SLASH` (o que aparece no menu `/` da IDE) |
| `core/scripts_comuns/` | Motores (um script por área) |
| `core/scripts_comuns/ninho_core/` | Base e motores reutilizáveis (nunca importa os scripts de cima; `tests/test_arquitetura.py` verifica). Utilitários: `console`, `paths`, `catalogo`, `xml_seguro`, `zip_seguro`, `leitores`, `lgpd`. DW: `dw_modelo`, `dw_patches`, `odi`, `guia_bi`. Visual/documentos: `visual_comum`, `diagramas`, `mockup_bi`, `prova_dax`, `office`, `pdf`. Hop: `hop_gerador` |
| `gerador_artefatos_visuais.py`, `melhorar_dw_existente.py`, `auditar_esteira_hop.py` | Orquestradores/CLIs finos + fachadas de reimportação (código novo vai para `ninho_core/`) |
| `.agents/skills/<skill>/` | Skills arquiteturais (procedimentos de domínio) e skills de comando (geradas) |
| `modulos/<modulo>/` | Intakes, templates SQL/Hop e regras de cada módulo |
| `core/convencoes/` | Convenções normativas (fonte única); os resumos em `modulos/` apontam para elas |
| `tests/` | Testes unitários `pytest` |

## Adicionar um comando novo

1. Implemente a função no motor certo em `core/scripts_comuns/` (ou crie um script com `argparse`).
2. Registre em `ROTAS_COMANDOS` no `ninho.py`; se ele deve aparecer no menu `/`, também em `DESCRICOES_SKILLS_SLASH`.
3. Rode `python ninho.py instalar-comandos` para gerar a skill. Não edite as skills de comando à mão: elas são sobrescritas.
4. Os testes em `tests/test_cli_e_skills.py` acusam rota sem script ou skill sem rota.

## Servidor MCP

`ninho_mcp_server.py` expõe os comandos de `DESCRICOES_SKILLS_SLASH` como ferramentas MCP (stdio, só biblioteca padrão). O `.mcp.json` da raiz já o registra para agentes compatíveis. Comando novo com descrição em `DESCRICOES_SKILLS_SLASH` vira ferramenta automaticamente; marque-o em `SOMENTE_LEITURA` se não gravar arquivos.

## Regras de código

- Mensagens de console via `ninho_core.console` (`print_ok`, `print_warn`, `print_err`). Não copie as funções para dentro do script.
- XML vindo de cliente sempre via `ninho_core.xml_seguro`, nunca `ET.fromstring`/`ET.parse` direto.
- Membros de ZIP de cliente sempre via `ninho_core.zip_seguro.ler_membro`, nunca `zf.read()` direto.
- Ao desmembrar um arquivo grande, mova as funções para `ninho_core/` e deixe no arquivo antigo uma fachada de reimportação (`from ninho_core.x import f  # noqa: F401`); os golden files dizem se algo mudou.
- Limpezas de workspace restauram `documentacao/catalogo_projetos/PROJETO_*.md` com `ninho_core.catalogo.restaurar_fichas_projeto()`; nunca apague esses arquivos.
- Nada de `except: pass` novo: registre o aviso no relatório do motor ou use `_LOG.debug(...)`. Para diagnosticar um arquivo de cliente problemático, rode com `NINHO_LOG_LEVEL=DEBUG`.
- Funções novas com no máximo ~60 linhas; ao tocar numa função gigante existente, extraia o trecho alterado.
- Credenciais só por variável de ambiente, sem valor padrão.
- Dados de cliente nunca entram no Git (`entrega/` e `saida/` estão no `.gitignore`).

## Versionamento

`X.Y.Z` no `PATCH_NOTES.md`, `README.md` e `pyproject.toml`: X = marco da plataforma, Y = novo recurso/comando, Z = correção.
