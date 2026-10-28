# Core — Núcleo Compartilhado

Este diretório contém os padrões, convenções corporativas e componentes reutilizáveis compartilhados por todos os módulos do framework.

---

## 📁 Estrutura do Diretório

- **`convencoes/`**
  - **`CONVENCOES_DW.md`**: Padrões de modelagem dimensional para DW Oracle (prefixos `DIM_`, `FATO_`, chave artificial `DIMENSION_KEY`, SCD Tipo 2, linha `-1`, particionamento e índices).
  - **`CONVENCOES_SEMANTICA.md`**: Padrões da camada semântica e catálogo de metadados (prefixos `VW_*`, medidas aditivas/semi-aditivas, 8 tabelas `META_*`).
- **`scripts_comuns/`**: Scripts utilitários de UX conversacional, simulação, banco, auditoria, engenharia reversa e automação transversal:
  - `ajuda_ninho.py`: Motor de UX Conversacional do Chat (`/help`, `/comecar` com 5 trilhas de onboarding, `/onde-estou` Bússola de Progresso, `/duvida <tema>` Oráculo Arquitetural, `/doctor` de pastas e `/demo` Playground em 5s).
  - `simular_projeto.py`: Gerador de Simulações Ponta a Ponta e Blueprints 100% Editáveis (`SIMULACAO_BLUEPRINT_DW.md` e `SIMULACAO_BLUEPRINT_SEMANTICA.md`) com execução real pós-aprovação (`/simular-projeto` e `/executar-simulacao`).
  - `melhorar_dw_existente.py`: Motor Fast-Track e Micro-Processos Independentes para DWs e ODI (`--modo {tudo,comentarios,dicionario,indices,linha-default,constraints,testes,guia-bi,selects-odi,guia-odi,patch}`).
  - `modular_semantica.py`: Motor de Micro-Processos Independentes da Camada Semântica e Segurança (`--modo {tudo,views-semantica,views-dim,views-evento,views-kpi,catalogo-meta,rls}`).
  - `inspecionar_ddl_origem.py`: Extrator determinístico de DDLs de origem e Radar Consultivo de KPIs.
  - `validar_entrega.py`: Auditor pré-voo e pós-geração das Regras de Ouro (suporta `dw`, `fast-track`, `semantica`, `governanca`, `saida`, `all`).
  - `auditar_mapa_odi.py`: Auditor preditivo de tuning e anti-padrões (`H1` a `H9`) para projetos ODI 12c.
  - `auditar_esteira_hop.py`: Auditor de segurança e qualidade (`HOP-H1` a `HOP-H8`) para Apache Hop 2.x, FTPS e Python.
  - `inspecionar_pbix.py`: Engenharia reversa de arquivos `.pbix` do Power BI (`PBIX-H1` a `PBIX-H5`).
  - `inspecionar_insumos_governanca.py`: Auditoria Gate 0.5 de planilhas/CSVs do cliente e geração da Matriz DE/PARA MongoDB PRODEB.
  - `transicionar_dw_para_semantica.py`: Handoff automatizado do Planejador DW para a Camada Semântica.
  - `gerar_mock_dados.py`: Gerador dinâmico de dados sintéticos CSV para testes no Power BI (lê DDLs/Blueprints reais e injeta ~3% de chaves `-1`).
  - `gerenciar_projeto.py`: Exportação de pacotes `.zip` e limpeza segura do workspace (`--status`, `--exportar`, `--resetar`).
  - `testar_ninho.py`: Suíte automatizada de testes End-to-End (E2E) que valida todos os motores do NINHO numa cópia temporária do projeto, sem tocar nos seus arquivos de `entrega/` e `saida/` (`/testar-ninho`).

