# Plano de Melhorias do NINHO — Arquivo de Continuidade

> Revisão iniciada em 27/10/2026 sobre a versão `0.11.1`.
> Relatório completo (com tabelas e roadmap desenhado): https://claude.ai/artifact/FpJS2qukgDVufkRtg93qjD
>
> **Como usar este arquivo:** ele é a memória do trabalho de melhoria. Se a sessão for interrompida, peça ao agente:
> *"Leia o PLANO_MELHORIAS.md e continue do primeiro item não marcado."*
> Itens `[x]` já foram aplicados no código; itens `[ ]` ainda estão pendentes.

---

## 1. Diagnóstico resumido

| Item | Valor na revisão |
| --- | --- |
| Scripts Python em `core/scripts_comuns/` | 15 + `ninho.py` (~24.000 linhas) |
| Maior arquivo | `gerador_artefatos_visuais.py` (4.777 linhas) |
| Funções com mais de 150 linhas | 35 de 266 |
| Maior função | `construir_guia_bi_rapido` (881 linhas) |
| Rotas no `ninho.py` | ~90 (muitos aliases) |
| Skills em `.agents/skills/` | 49 |
| Baterias E2E | 17 (T01..T17) |
| `pyproject.toml` / CI / testes unitários | inexistentes na revisão |

**Pontos fortes:** domínio Kimball/ODI/Hop/Semântica muito bem codificado; simulação editável (Blueprint); só biblioteca padrão (exceto `openpyxl`); suíte E2E própria.

**Riscos principais:** (1) `/testar-ninho` apagava os arquivos reais de `entrega/` e `saida/`; (2) funções e arquivos gigantes; (3) fonte da verdade duplicada (convenções, templates, contagem de testes); (4) sem empacotamento/CI; (5) superfície de comandos grande.

---

## 2. Pontos de melhoria por área (códigos usados no relatório)

### Arquitetura (A)
- A1 `core/scripts_comuns` não é pacote; 7 arquivos fazem `sys.path.insert`.
- A2 Cadeia de dependência longa `simular_projeto → modular_semantica → melhorar_dw_existente → gerador_artefatos_visuais`.
- A3 `gerador_artefatos_visuais.py` mistura leitores de insumo e geradores de saída.
- A4 `melhorar_dw_existente.py` concentra 15+ comandos via `--modo`.
- A5 `ninho.py` chama tudo por `subprocess`.
- A6 Dois catálogos de comandos (`DESCRICOES_SKILLS_SLASH` e `ROTAS_COMANDOS`) com descrições divergentes.
- A7 Quatro `AGENTS.md` com regras sobrepostas.
- A8 Convenções/templates duplicados com conteúdo diferente.
- A9 Templates SQL em três lugares (skills, módulos e código).
- A10 `.gitignore` ignorava `documentacao/REVISAO_TECNICA_NINHO.md`.

### Qualidade de código (Q)
- Q1 Funções gigantes (35 acima de 150 linhas).
- Q2 39 blocos `except ...: pass`.
- Q3 Nenhum uso de `logging`.
- Q4 `print_ok/print_warn/print_err` e `get_base_dir` copiados em 4 arquivos.
- Q5 SQL/HTML em f-strings no Python.
- Q6 OOXML/PDF escritos à mão.
- Q7 Parser DDL só com regex.
- Q8 Tipagem parcial, sem `mypy`.
- Q9 Modelos de tabela/coluna como `dict` soltos.
- Q10 28 chamadas a `datetime.now()` espalhadas.
- Q11 Sem linter/formatador.

### Testes (T)
- T1 **Perda de dados**: suíte apagava `entrega/` e `saida/` reais.
- T2 Suíte parava no primeiro erro.
- T3 Só testes E2E, sem unitários.
- T4 Testes nomeados por lote de correção.
- T5 Contagem de testes divergente na documentação.
- T6 Sem CI.
- T7 Sem golden files dos SQL gerados.
- T8 SQL gerado nunca executado em banco.
- T9 Sem cobertura.

### Documentação e UX (D)
- D1 Documentação duplicada/divergente.
- D2 README longo e decorado.
- D3 Guias muito grandes.
- D4 Links absolutos `file:///c:/Users/...`.
- D5 Skills presas ao `run_command` (Antigravity).
- D6 Excesso de comandos/aliases.
- D7 `AGENTS.md` muito prescritivo.
- D8 Sem `CONTRIBUTING.md`.
- D9 Sem saída `--json`.

### Segurança (S)
- S1 `.gitignore` não protegia `entrega/` e `saida/` (dados de cliente).
- S2 Senha padrão `"DW_PASS"` no template do extrator.
- S3 Senha FTPS na linha de comando do `curl`.
- S4 Dois templates de extrator API diferentes.
- S5 XML de terceiros sem `defusedxml`.
- S6 Mascaramento de PII opcional.
- S7 Sem manifesto/trilha de execução.

### Novas funcionalidades sugeridas (F)
F1 `/inspecionar-banco` · F2 `/comparar-modelo` · F3 modelo Power BI PBIP/TMDL · F4 servidor MCP · F5 `/deploy-sandbox` (Oracle Free) · F6 linhagem OpenLineage · F7 avaliação text-to-SQL com `META_CONSULTA_NEGOCIO` · F8 painel de observabilidade de carga · F9 editor visual da Blueprint · F10 regras de qualidade por coluna · F11 recomendação de particionamento · F12 dialeto PostgreSQL via `sqlglot` · F13 manifesto de execução + empacotamento versionado.

---

## 3. Estratégia (ordem obrigatória)

1. **Fase 0 — Estancar riscos** (T1, S1, S2, S3). Gate: `testar-ninho` não apaga nada do engenheiro.
2. **Fase 1 — Fundação** (`pyproject.toml`, `ruff`, `pytest`, CI, pacote `ninho_core`, golden files). Gate: CI verde.
3. **Fase 2 — Modularização guiada por testes** (quebrar arquivos gigantes, templates únicos, fonte única de comandos). Gate: golden files inalterados.
4. **Fase 3 — Novas funcionalidades** (F1, F5, F2, F4, F3).
5. **Governança** — reforço final do módulo de Governança de Dados (pedido explícito do usuário).

Técnicas: testes de caracterização antes de refatorar; refatoração incremental ("strangler fig"); uma fonte de verdade com o resto gerado; modelo de domínio com `dataclasses`; ADRs em `documentacao/adr/`; commits convencionais.

---

## 4. Checklist de execução (atualizado a cada etapa)

### Fase 0 — Riscos
- [x] T1 `testar_ninho.py` roda em cópia temporária isolada do projeto (`--sem-sandbox` para o modo antigo) — validado 17/17
- [x] S1 `.gitignore` protege `entrega/` e `saida/` (mantém `README.md`, `.gitkeep` e templates)
- [x] A10 `REVISAO_TECNICA_NINHO.md` volta a ser versionado
- [x] S2 template do extrator exige variáveis de ambiente (sem senha padrão)
- [x] S3 script FTPS usa `--netrc-file` em vez de `-u usuario:senha`

### Fase 1 — Fundação
- [x] `pyproject.toml` com `ruff` e `pytest`; `requirements.txt` e `requirements-dev.txt`
- [x] Pacote `core/scripts_comuns/ninho_core/` (console, paths) e remoção das cópias (Q4); cores ANSI desligadas fora de terminal / `NO_COLOR`
- [x] `ruff --fix` seguro: 96 f-strings sem placeholder e 11 imports não usados (Q11)
- [x] Testes unitários `pytest` em `tests/` (parser DDL, modelagem DW, nomes ODI, PII, CLI/skills)
- [x] CI (`.github/workflows/ci.yml` + `.gitlab-ci.yml`) — confirmar qual plataforma será usada e apagar a outra

### UX e documentação
- [x] `ninho.py`: sugestão de comando parecido quando o nome está errado
- [x] T5 contagens de testes removidas/corrigidas (README, AGENTS, core/README, GUIA_INICIAL, ninho.py)
- [x] D4 links `file:///` convertidos para relativos (21 em `REVISAO_TECNICA_NINHO.md`)
- [x] D5 skills com texto neutro de IDE (48 skills regeneradas + `AGENTS.md`)
- [x] A6 descrições de `testar-ninho` e governança alinhadas
- [x] D8 `CONTRIBUTING.md`
- [x] `/doctor` checa Python, pacotes opcionais, skills e proteção LGPD do `.gitignore`
- [x] S5 `ninho_core/xml_seguro.py` (usa `defusedxml` se instalado; bloqueia `<!ENTITY`) em todos os parsers de XML
- [x] A8 avaliado: `modulos/planejador_dw/CONVENCOES_DW.md` é resumo que aponta para o normativo — mantido

### Governança (foco final)
- [x] Revisão do motor `inspecionar_insumos_governanca.py`
- [x] Melhorias de governança aplicadas (detalhadas na seção 5)

### Fechamento
- [x] `PATCH_NOTES.md`, `README.md` e `pyproject.toml` na versão `0.12.0`
- [x] Suíte `testar-ninho` 17/17 + `pytest` 54/54 + `ruff` limpo (após a segunda rodada)

### Segunda rodada (27/10/2026) — inclui triagem da análise externa colada pelo usuário
- [x] T7 golden files (`tests/golden/`, 22 scripts) — regenerar com `NINHO_ATUALIZAR_GOLDEN=1`
- [x] T2 suíte E2E roda todas as baterias e mostra o placar (`--parar-no-erro` mantém o modo antigo)
- [x] S4 extrator API unificado (contrato `.tmp` + `_REJEITADOS.csv` + `STATUS:SUCCESS`), stdlib only
- [x] Templates duplicados unificados (RLS, extrator, `09_validacoes`) + `tests/test_templates_sincronizados.py`
- [x] RLS seguro (identidade efetiva com `RLS_CONTAS_SERVICO`, sem autoconcessão, sem `LISTAGG`, `DYNAMIC`, fail-closed)
- [x] `VW_EVENTO` sem `CASE WHEN 1 = 1`; `VW_KPI` com eixo temporal; aliases seguros em 30 caracteres
- [x] Pergunta-gabarito do Radar coerente com a situação real da Fato
- [x] Fatos do DW com todas as FKs (`ENABLE NOVALIDATE`), inclusive `DIM_TEMPO`
- [x] Recomendação comentada de particionamento/compressão no DDL de Fato
- [x] Parser da Blueprint tolerante + aviso de linha ignorada
- [x] `--resetar` e `/limpar-demo` restauram as fichas do projeto (modelos em `documentacao/catalogo_projetos/modelos/`)
- [x] Zip bomb: `ninho_core/zip_seguro.py` em todos os leitores de ZIP
- [x] Fase 2 iniciada: `ninho_core/leitores.py` e `ninho_core/lgpd.py` extraídos do `gerador_artefatos_visuais.py` (fachada mantida)
- [x] Referência fantasma `orquestrador_governanca_bagov.py` corrigida no `PATCH_NOTES.md`
- [x] Radar da Governança sugere `CNC_*`/`DOM_*` para `tb_sem_conceitos`

**Triagem da análise externa:** já resolvidos antes dela: esteira física de governança (2.1), isolamento dos testes (3.6), `pyproject`/CI, XML seguro, utilitários comuns (início). Uma sugestão foi **ajustada por segurança**: `COALESCE(CLIENT_IDENTIFIER, SESSION_USER)` puro permitiria a qualquer usuário se passar por outro; foi implementada a versão com contas de serviço confiáveis.

### Fase 2 — terceira rodada (27/10/2026)
- [x] `gerador_artefatos_visuais.py` 4.777 → ~290 linhas (`visual_comum`, `pdf`, `prova_dax`, `mockup_bi`, `diagramas`, `office`, `leitores`, `lgpd`)
- [x] `melhorar_dw_existente.py` 3.871 → ~600 linhas (`dw_modelo`, `dw_patches`, `odi`, `guia_bi`); imports diretos de `ninho_core` em vez do gerador inteiro
- [x] `auditar_esteira_hop.py` 1.867 → ~1.050 linhas (`hop_gerador`)
- [x] Q2/Q3: 35 `except: pass` → `_LOG.debug` (`NINHO_LOG_LEVEL=DEBUG`)
- [x] `tests/test_arquitetura.py`: `ninho_core` sem dependência dos scripts, fachadas com nomes antigos, limite de tamanho dos arquivos desmembrados
- Ferramenta usada: script "mover" (fechamento de dependências via AST + fachada). Para repetir: mover grupo → `ruff --fix` F401 no destino → golden + pytest + E2E.

### Fase 3 + Governança + pedido extra (27/10/2026 — versão 0.13.0)
- [x] Pedido do usuário: catálogo `META_CONSULTA_NEGOCIO` com **mínimo de 30 perguntas da IA** (3 horizontes, SQL nas views) + perguntas do cliente (Intake 5.1 / `perguntas_cliente.md`) — `ninho_core/perguntas_semanticas.py`, Blueprint 6.2/6.3, E2E T03 exige >= 30
- [x] Governança: `/simular-governanca` + bateria E2E T18 (simulação, MongoDB, AWS, pendências, devolução)
- [x] F4 servidor MCP (`ninho_mcp_server.py`, `.mcp.json`)
- [x] F2 `/comparar-modelo` (ALTERs incrementais seguros)
- [x] F5 `/estimar-volumetria` (tamanho, crescimento 5 anos, particionamento, tablespaces)
- [x] F1 `/inspecionar-banco` (DBMS_METADATA via `oracledb` ou script para o DBA)

### Pendente para os próximos ciclos (em ordem sugerida)
- [ ] Confirmar plataforma de CI (GitHub ou GitLab da PRODEB) e apagar o arquivo da outra
- [ ] Testar `/inspecionar-banco` com conexão real ao Oracle do ambiente PRODEB (só o modo script foi validado aqui)
- [ ] F3 exportador Power BI `.pbip`/TMDL; gerador Groovy para ODI 12c; grafo de linhagem no dicionário HTML
- [ ] Perguntas de negócio: validar os SQL gerados contra um Oracle real (Oracle Free em container no CI)
- [ ] Testes unitários das heurísticas HOP-H1..H9 e ODI H1..H9 (pré-requisito do Rule Registry)
- [ ] Rule Registry nos auditores (`audit_hop_directory` com 696 linhas, ODI `_run_predictive_heuristics`, PBIX) com `--json`/SARIF
- [ ] Quebrar `validar_saida_gerada` (539 linhas) em verificações independentes; `simular_projeto.py` (geração de Blueprints x execução) e `modular_semantica.construir_catalogo_meta` (383 linhas)
- [ ] Modelo de domínio com `dataclasses` (`TableSpec`, `ColumnSpec`, `ForeignKeySpec`, `Finding`) (Q9)
- [ ] A1 transformar `core/scripts_comuns` em pacote e remover os `sys.path.insert`
- [ ] Q5 geradores lendo os templates de `modulos/*/templates/` (`string.Template`) em vez de SQL em f-strings
- [ ] D2/D3/D7 README de 1 tela, guias quebrados por tarefa, `AGENTS.md` enxuto (decisão do usuário)
- [ ] D6 reduzir aliases expostos como skills
- [ ] S6 mascarar PII por padrão em mockups/guias
- [ ] Domínio: sugerir Junk Dimensions e Bridge Tables (N:N) no classificador; leitura de `.pbip`/TMDL no `/inspecionar-pbix`
- [ ] Governança: bateria E2E da esteira no `testar_ninho.py`; `/simular-governanca`
- [ ] Fase 3 — F1 `/inspecionar-banco`, F5 `/deploy-sandbox` e calculadora de volumetria, F2 `/comparar-modelo`, F4 servidor MCP, F3 PBIP/TMDL, gerador Groovy para ODI, grafo de linhagem

---

## 5. Registro do que foi feito (27/10/2026)

### Fase 0 — Riscos
- `core/scripts_comuns/testar_ninho.py`: `executar_em_sandbox()` copia o projeto (sem `.git`, `.venv` e sem os arquivos de `entrega/`/`saida/`) para uma pasta temporária e roda lá via `NINHO_TESTE_SANDBOX=1`. `--manter-arquivos` preserva a sandbox; `--sem-sandbox` mantém o modo antigo.
- `.gitignore`: `/entrega/**` e `/saida/**` ignorados, exceto pastas, `README.md`, `.gitkeep` e `saida/camada_semantica/meta_projeto/01_create_meta_tables.sql`. `REVISAO_TECNICA_NINHO.md` voltou a ser versionado.
- `template_extrator_api.py`: `variavel_obrigatoria()` para `ORACLE_USER/PASS/DSN`.
- `extrair_metadados_ftps.sh`: credenciais em `.netrc` temporário (chmod 600, removido no `trap EXIT`).

### Fase 1 — Fundação
- `pyproject.toml` (versão, extras opcionais, pytest, ruff), `requirements.txt`, `requirements-dev.txt`, `.github/workflows/ci.yml`, `.gitlab-ci.yml`, `CONTRIBUTING.md`.
- `core/scripts_comuns/ninho_core/`: `console.py` (cores só em TTY; `NO_COLOR`/`FORCE_COLOR`), `paths.py`, `xml_seguro.py`. Seis motores passaram a importar daqui.
- `tests/`: `test_parser_ddl.py`, `test_modelagem_dw.py`, `test_cli_e_skills.py`, `test_lgpd_pii.py`, `test_ninho_core.py`, `test_governanca.py`.
- Ambiente local de desenvolvimento: `.venv/` com pytest, ruff, openpyxl e defusedxml (ignorado no Git).

### Governança
- **Nova esteira `gerar_artefatos_governanca.py`** ligada a `/executar-governanca`, `/gerar-governanca` e `/iniciar-governanca` (antes só imprimiam a auditoria). Detalhes em `saida/governanca_dados/README.md`.
- `inspecionar_insumos_governanca.py`:
  - leitor `.xlsx` sem `openpyxl` (`_carregar_xlsx_sem_openpyxl`), preservando a posição das células;
  - `classificar_campo_lgpd()` em 4 níveis com base legal e técnica de anonimização;
  - `cruzar_dicionario_com_amostras()`: coluna não catalogada e PII em coluna declarada não sensível bloqueiam;
  - colunas opcionais `Obrigatório?` e `Chave?` no dicionário (alimentam regras de qualidade e índice único);
  - nomenclatura PRODEB corrigida (`num_` para documentos, `ide_`, `long`, remoção de prefixos legados por extenso);
  - `executar_inspecao()` reutilizável e `--json`.
- `validar_entrega.py saida`: reprova artefatos de governança com `<INFORMAR: ...>`.
- Documentação alinhada: `SKILL.md` da governança (Fase 3), `modulos/governanca_dados/AGENTS.md`, `saida/governanca_dados/README.md`.

### Como validar tudo de novo
```bash
.venv\Scripts\python -m ruff check .
.venv\Scripts\python -m pytest
python ninho.py testar-ninho
```
