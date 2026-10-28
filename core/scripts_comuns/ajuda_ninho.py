#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
🧭 CENTRAL DE EXPERIÊNCIA DO USUÁRIO (UX), AJUDA, BÚSSOLA & ORÁCULO — NINHO
================================================================================
Concentra os recursos de UX conversacional da plataforma NINHO:
  1. `/help` (`/ajuda`, `/comandos`)    : Catálogo de comandos por tópico ou busca.
  2. `/onde-estou` (`/status`)          : Bússola contextual com barra de progresso e próximo passo.
  3. `/comecar` (`/onboarding`)         : Trilhas guiadas de 3 passos para os 5 cenários reais.
  4. `/duvida <tema>` (`/explicar`)     : Oráculo interativo de arquitetura e FAQ técnico.
  5. `/doctor` (`--corrigir`)           : Diagnóstico de saúde e corretor de arquivos na pasta errada.
  6. `/demo` e `/limpar-demo`           : Modo Playground em 1 comando para demonstração prática.

Exemplos de uso:
  python core/scripts_comuns/ajuda_ninho.py
  python core/scripts_comuns/ajuda_ninho.py --topico simulacao
  python core/scripts_comuns/ajuda_ninho.py --onde-estou
  python core/scripts_comuns/ajuda_ninho.py --onboarding
  python core/scripts_comuns/ajuda_ninho.py --explicar estrategia-carga
  python core/scripts_comuns/ajuda_ninho.py --doctor --corrigir
  python core/scripts_comuns/ajuda_ninho.py --demo
  python core/scripts_comuns/ajuda_ninho.py --limpar-demo
================================================================================
"""

import logging as _logging_ninho

_LOG = _logging_ninho.getLogger("ninho.ajuda_ninho")

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parents[2]
ENTREGA_DIR = ROOT_DIR / "entrega"
SAIDA_DIR = ROOT_DIR / "saida"


# ==============================================================================
# 1. CATÁLOGO DE COMANDOS (/help)
# ==============================================================================

CATALOGO_TOPICOS: Dict[str, Dict] = {
    "ajuda": {
        "titulo": "🧭 0. Experiência Guiada, Bússola Contextual, Oráculo & Playground",
        "descricao": "Comandos de UX para descobrir por onde começar, saber em que etapa o projeto está, tirar dúvidas técnicas ou rodar uma demonstração.",
        "comandos": [
            {
                "chat": "`/help` (ou `/ajuda`, `/comandos`)",
                "objetivo": "Exibe no chat este catálogo completo de comandos organizado por tópico.",
                "cli": "`python core/scripts_comuns/ajuda_ninho.py`",
            },
            {
                "chat": "`/help <topico>`",
                "objetivo": "Filtra os comandos de um tópico específico (`ajuda`, `simulacao`, `micro`, `auditoria`, `dw`, `semantica`, `governanca`, `qualidade`).",
                "cli": "`python core/scripts_comuns/ajuda_ninho.py --topico <topico>`",
            },
            {
                "chat": "`/onde-estou` (ou `/status`)",
                "objetivo": "Mostra a Bússola Contextual do projeto com barra de progresso (`[███░░]`), arquivos detectados e o próximo comando recomendado.",
                "cli": "`python core/scripts_comuns/ajuda_ninho.py --onde-estou`",
            },
            {
                "chat": "`/comecar` (ou `/onboarding`)",
                "objetivo": "Exibe as 5 Trilhas Guiadas de Bolso (3 passos: onde soltar o arquivo -> qual comando rodar -> o que é gerado).",
                "cli": "`python core/scripts_comuns/ajuda_ninho.py --onboarding`",
            },
            {
                "chat": "`/duvida <tema>` (ou `/explicar <conceito>`)",
                "objetivo": "Aciona o Oráculo Interativo do NINHO para explicar conceitos (`estrategia-carga`, `scd`, `linha-default`, `camadas-views`, `arquitetura-etl`, `gate-governanca`, `simulacao`, `fast-track`, `rls`).",
                "cli": "`python core/scripts_comuns/ajuda_ninho.py --explicar <tema>`",
            },
            {
                "chat": "`/doctor`",
                "objetivo": "Diagnostica a saúde do workspace, detecta arquivos soltos na pasta errada e corrige automaticamente (`--corrigir`).",
                "cli": "`python core/scripts_comuns/ajuda_ninho.py --doctor --corrigir`",
            },
            {
                "chat": "`/demo` e `/limpar-demo`",
                "objetivo": "Cria e executa um projeto corporativo completo de demonstração em 1 comando (ou limpa tudo ao final).",
                "cli": "`python core/scripts_comuns/ajuda_ninho.py --demo` | `--limpar-demo`",
            },
        ],
    },
    "simulacao": {
        "titulo": "🧪 1. Simulador Ponta a Ponta & Blueprint 100% Editável (Dry-Run)",
        "descricao": "Simula como o projeto vai começar, transformar e terminar em uma Blueprint editável antes da geração física em `saida/`.",
        "comandos": [
            {
                "chat": "`/simular-dw`",
                "objetivo": "Gera a Blueprint 100% editável do DW (`entrega/planejador_dw/SIMULACAO_BLUEPRINT_DW.md`) com tabelas, colunas (`[x]`/`[ ]`), tipos, SCD, prévia de 3 linhas + linha `-1` e Radar Consultivo.",
                "cli": "`python core/scripts_comuns/simular_projeto.py --modulo dw --acao simular`",
            },
            {
                "chat": "`/simular-semantica`",
                "objetivo": "Gera a Blueprint 100% editável da Camada Semântica (`entrega/camada_semantica/SIMULACAO_BLUEPRINT_SEMANTICA.md`) com Views em 3 camadas (`VW_DIM`, `VW_EVENTO`, `VW_KPI`), 8 `META_*` e RLS.",
                "cli": "`python core/scripts_comuns/simular_projeto.py --modulo semantica --acao simular`",
            },
            {
                "chat": "`/simular-projeto`",
                "objetivo": "Gera simultaneamente as Blueprints editáveis do Planejador DW e da Camada Semântica.",
                "cli": "`python core/scripts_comuns/simular_projeto.py --modulo ambos --acao simular`",
            },
            {
                "chat": "`/executar-simulacao` (ou `/executar-simulacao-dw`, `/executar-simulacao-semantica`)",
                "objetivo": "Lê todas as edições feitas pelo engenheiro na Blueprint aprovada e dispara a geração real em `saida/`.",
                "cli": "`python core/scripts_comuns/simular_projeto.py --modulo {dw,semantica,ambos} --acao executar`",
            },
        ],
    },
    "micro": {
        "titulo": "⚡ 2. Micro-Processos Independentes & Fast-Track (DW, ODI e Semântica)",
        "descricao": "Executa apenas um recorte cirúrgico para melhorar um DW já existente ou gerar um artefato específico sem mexer no restante do projeto.",
        "comandos": [
            {
                "chat": "`/gerar-comentarios`",
                "objetivo": "Gera apenas `COMMENT ON TABLE` / `COMMENT ON COLUMN` (`90_patch_comentarios_*.sql`).",
                "cli": "`python core/scripts_comuns/melhorar_dw_existente.py --modo comentarios`",
            },
            {
                "chat": "`/gerar-dicionario`",
                "objetivo": "Gera exclusivamente o Dicionário de Dados HTML interativo (`11_dicionario_dados/dicionario_dados.html`).",
                "cli": "`python core/scripts_comuns/melhorar_dw_existente.py --modo dicionario`",
            },
            {
                "chat": "`/gerar-indices`",
                "objetivo": "Gera apenas os índices de performance (`BITMAP` ou `B-TREE COMPRESS 1` nas FKs da Fato, B-Tree SCD2 nas Dimensões, `DBMS_STATS`) + `07_prc_pos_carga_fato.sql`.",
                "cli": "`python core/scripts_comuns/melhorar_dw_existente.py --modo indices`",
            },
            {
                "chat": "`/gerar-linha-default`",
                "objetivo": "Gera apenas o script idempotente (`MERGE INTO`) do registro sentinela `-1` (`Não Informado`).",
                "cli": "`python core/scripts_comuns/melhorar_dw_existente.py --modo linha-default`",
            },
            {
                "chat": "`/gerar-constraints`",
                "objetivo": "Gera apenas as constraints `PK`/`FK` não-destrutivas (`ENABLE NOVALIDATE` / `RELY DISABLE NOVALIDATE`).",
                "cli": "`python core/scripts_comuns/melhorar_dw_existente.py --modo constraints`",
            },
            {
                "chat": "`/gerar-testes-dw`",
                "objetivo": "Gera apenas a suíte SQL de 6 testes de integridade pós-carga (`10_testes_integridade/`).",
                "cli": "`python core/scripts_comuns/melhorar_dw_existente.py --modo testes`",
            },
            {
                "chat": "`/gerar-guia-bi`",
                "objetivo": "Gera o Guia Completo do Analista de BI (`GUIA_ANALISTA_BI_<PROJETO>.md/.docx`), Mockup Visual (`mockup_painel_bi.svg` + `preview_painel_bi.html`), Planilha `.xlsx` 3 abas e Deck `.pptx`.",
                "cli": "`python core/scripts_comuns/melhorar_dw_existente.py --modo guia-bi`",
            },
            {
                "chat": "`/gerar-mockup-bi`",
                "objetivo": "Gera o Mockup Vetorial Full HD do Painel Power BI (`mockup_painel_bi.svg`, `mockup_painel_bi_devmode.svg` com Redlines DAX `①..⑦` e `preview_painel_bi.html` com exportação PNG 2x).",
                "cli": "`python core/scripts_comuns/melhorar_dw_existente.py --modo mockup-bi`",
            },
            {
                "chat": "`/validar-medidas-bi`",
                "objetivo": "Executa a Prova Real Pós-Carga das medidas DAX sobre amostras de `DIM_*` e `FATO_*` (`entrega/planejador_dw/amostras/`), detecta/corrige medidas parcialmente corretas (`MED-01..06`) e popula o Mockup Visual com os números reais da carga.",
                "cli": "`python core/scripts_comuns/melhorar_dw_existente.py --modo validar-medidas-bi`",
            },
            {
                "chat": "`/gerar-apresentacao`",
                "objetivo": "Gera a Apresentação Executiva `16:9` de Kickoff/Entrega do projeto (`apresentacao_executiva_<projeto>.pptx` + `apresentacao_slides.html`).",
                "cli": "`python core/scripts_comuns/melhorar_dw_existente.py --modo apresentacao`",
            },
            {
                "chat": "`/exportar-docx`",
                "objetivo": "Exporta os guias técnicos (`.md`) para documentos Microsoft Word corporativos estilizados (`.docx`).",
                "cli": "`python core/scripts_comuns/melhorar_dw_existente.py --modo exportar-docx`",
            },
            {
                "chat": "`/exportar-pdf`",
                "objetivo": "Exporta os guias técnicos (`.md`) para documentos PDF 1.4 corporativos multi-página (`.pdf`) prontos para anexação em SEI/Ofícios.",
                "cli": "`python core/scripts_comuns/melhorar_dw_existente.py --modo exportar-pdf`",
            },
            {
                "chat": "`/gerar-mock-bi`",
                "objetivo": "Gera dados sintéticos CSV 100% dinâmicos a partir dos DDLs/Blueprints reais do projeto (com ~3% de chaves `-1` Kimball).",
                "cli": "`python core/scripts_comuns/gerar_mock_dados.py --linhas 150`",
            },
            {
                "chat": "`/gerar-selects-odi`",
                "objetivo": "Gera apenas as consultas SQL de carga do ODI (`03_selects_odi_dimensoes.sql` e `04_select_odi_fato.sql`).",
                "cli": "`python core/scripts_comuns/melhorar_dw_existente.py --modo selects-odi`",
            },
            {
                "chat": "`/gerar-guia-odi`",
                "objetivo": "Gera apenas o Guia passo a passo de construção no Canvas do ODI 12c (`MAP_*`, `TRT_*`, `PACK_*`, `SCEN_*`).",
                "cli": "`python core/scripts_comuns/melhorar_dw_existente.py --modo guia-odi`",
            },
            {
                "chat": "`/melhorar-dw-existente`",
                "objetivo": "Executa o Raio-X não-destrutivo completo de um DW já construído e gera todos os patches sem mexer no ETL.",
                "cli": "`python core/scripts_comuns/melhorar_dw_existente.py --modo tudo`",
            },
            {
                "chat": "`/gerar-views-dim` | `/gerar-views-evento` | `/gerar-views-kpi`",
                "objetivo": "Gera isoladamente a Camada 1 (`VW_DIM_*_ATUAL`), Camada 2 (`VW_EVENTO_*`) ou Camada 3 (`VW_KPI_*`) da Camada Semântica.",
                "cli": "`python core/scripts_comuns/modular_semantica.py --modo {views-dim,views-evento,views-kpi}`",
            },
            {
                "chat": "`/gerar-views-semantica`",
                "objetivo": "Gera apenas os scripts das 3 camadas de Views semânticas (`01`, `02` e `03`).",
                "cli": "`python core/scripts_comuns/modular_semantica.py --modo views-semantica`",
            },
            {
                "chat": "`/gerar-catalogo-meta`",
                "objetivo": "Gera apenas o DDL e os `MERGE INTO` idempotentes das 8 tabelas `META_*` da Camada Semântica.",
                "cli": "`python core/scripts_comuns/modular_semantica.py --modo catalogo-meta`",
            },
            {
                "chat": "`/gerar-rls` (ou `/gerar-rls-semantica`)",
                "objetivo": "Gera apenas o script de segurança Row-Level Security / VPD (`DBMS_SESSION` + `DBMS_RLS.ADD_POLICY`).",
                "cli": "`python core/scripts_comuns/modular_semantica.py --modo rls`",
            },
        ],
    },
    "auditoria": {
        "titulo": "🔍 3. Inspeção de Fontes, Engenharia Reversa & Auditoria Técnica",
        "descricao": "Motores determinísticos para inspecionar DDLs, desconstruir relatórios Power BI (`.pbix`) e auditar esteiras ODI 12c, Apache Hop e Governança.",
        "comandos": [
            {
                "chat": "`/inspecionar-fontes`",
                "objetivo": "Audita DDLs/CSVs depositados em `entrega/planejador_dw/`, extrai colunas/PKs e gera o Radar Consultivo de KPIs.",
                "cli": "`python core/scripts_comuns/inspecionar_ddl_origem.py`",
            },
            {
                "chat": "`/inspecionar-pbix`",
                "objetivo": "Descompacta arquivos `.pbix` do Power BI, extrai filtros AST/DAX e executa as heurísticas `PBIX-H1` a `PBIX-H5`.",
                "cli": "`python core/scripts_comuns/inspecionar_pbix.py <arquivo.pbix>`",
            },
            {
                "chat": "`/auditar-mapa-odi`",
                "objetivo": "Executa o diagnóstico preditivo de tuning (`H1` a `H9`) em XMLs ou pastas do ODI 12c (`Mapas`, `Cenas`, `Pacotes`, `Procedures`).",
                "cli": "`python core/scripts_comuns/auditar_mapa_odi.py <pasta_ou_xml>`",
            },
            {
                "chat": "`/auditar-hop`",
                "objetivo": "Audita projetos Apache Hop 2.x (`.hpl`, `.hwf`, `.json`) e extratores Python/FTPS com `HOP-H1`..`H8`, catálogo oficial `hop-lint` (`TRANS-002`, `SQL-002`, `META-001`) e `THREAT_MODEL.md` (`HOP-SEC-01/02`).",
                "cli": "`python core/scripts_comuns/auditar_esteira_hop.py <pasta_hop> --svg-doc --gerar-lint-yml`",
            },
            {
                "chat": "`/migrar-kettle-hop`",
                "objetivo": "Migra projetos legados do Pentaho Data Integration / Kettle (`.ktr`, `.kjb`, `shared.xml`) para Apache Hop 2.x (`.hpl`, `.hwf`, `metadata/rdbms/*.json` e diagramas SVG).",
                "cli": "`python core/scripts_comuns/auditar_esteira_hop.py <pasta_kettle> --migrar-kettle saida/planejador_dw/06_pipelines_hop`",
            },
            {
                "chat": "`/gerar-pacote-hop`",
                "objetivo": "Gera um pacote completo Apache Hop 2.x (`wf_*.hwf`, `ppl_*.hpl` JDBC ou `OraBulkLoader`, `hop-lint.yml`, `hop-pwd.json`, `diagrama_esteira_hop.svg` e `DOCUMENTACAO_HOP.md`).",
                "cli": "`python core/scripts_comuns/auditar_esteira_hop.py --gerar-pacote-hop [--orabulkloader]`",
            },
            {
                "chat": "`/inspecionar-governanca`",
                "objetivo": "Executa o Gate 0.5 sobre planilhas `.xlsx` e `.csv` do cliente (emite Relatório de Devolução na Origem ou Matriz DE/PARA MongoDB).",
                "cli": "`python core/scripts_comuns/inspecionar_insumos_governanca.py`",
            },
        ],
    },
    "dw": {
        "titulo": "🏛️ 4. Modelagem Dimensional & Construção Completa do DW",
        "descricao": "Comandos do fluxo arquitetural completo para desenhar e gerar um Data Warehouse Star Schema do zero.",
        "comandos": [
            {
                "chat": "`/executar-dw` (ou `/gerar-dw`, `/construir-dw`)",
                "objetivo": "Executa **diretamente** a construção completa do DW (pastas `01` a `11` em `saida/planejador_dw/`) a partir de `entrega/planejador_dw/`, sem precisar passar pela etapa de simulação.",
                "cli": "`python core/scripts_comuns/simular_projeto.py --modulo dw --acao direto`",
            },
            {
                "chat": "`/executar-projeto` (ou `/gerar-projeto`, `/construir-projeto`)",
                "objetivo": "Executa **diretamente** a construção ponta a ponta do DW + Camada Semântica em `saida/` sem exigir simulação prévia.",
                "cli": "`python core/scripts_comuns/simular_projeto.py --modulo ambos --acao direto`",
            },
            {
                "chat": "`/desafiar-grao`",
                "objetivo": "Propõe e compara alternativas de granularidade para a tabela Fato contra as perguntas de negócio.",
                "cli": "Interativo via Agente Arquiteto (`planejador-dw-oracle`)",
            },
            {
                "chat": "`/classificar-scd`",
                "objetivo": "Classifica cada atributo das dimensões entre Chave Natural (`ID_*`), SCD Tipo 1 (sobrescrita) e SCD Tipo 2 (histórico).",
                "cli": "Interativo via Agente Arquiteto (`planejador-dw-oracle`)",
            },
            {
                "chat": "`/definir-estrategia-carga`",
                "objetivo": "Compara e recomenda entre Estratégia A (`Truncate & Load` + `BITMAP`) e Estratégia B (`MERGE Incremental` + `B-Tree`).",
                "cli": "Interativo via Agente Arquiteto (`planejador-dw-oracle`)",
            },
            {
                "chat": "`/gerar-blueprint`",
                "objetivo": "Compila o Blueprint técnico com a Matriz De/Para fiel à origem e o 💡 Radar Consultivo da IA antes da codificação.",
                "cli": "`python core/scripts_comuns/simular_projeto.py --modulo dw --acao simular`",
            },
            {
                "chat": "`/aprovar-blueprint`",
                "objetivo": "Libera o Gate de aprovação e gera todos os scripts DDL, procedures, esteiras ETL e Guia de BI nas 11 pastas de `saida/planejador_dw/`.",
                "cli": "`python core/scripts_comuns/simular_projeto.py --modulo dw --acao executar`",
            },
            {
                "chat": "`/auditar-ddl`",
                "objetivo": "Audita a sintaxe Oracle, registro sentinela `-1`, sequences e índices dos scripts gerados.",
                "cli": "`python core/scripts_comuns/validar_entrega.py saida`",
            },
        ],
    },
    "semantica": {
        "titulo": "🧠 5. Handoff & Camada Semântica Completa (Oracle)",
        "descricao": "Transição contínua do DW para a Camada Semântica em 3 níveis (`VW_DIM`, `VW_EVENTO`, `VW_KPI`), RLS e catálogo ativo (`META_*`).",
        "comandos": [
            {
                "chat": "`/concluir-dw` (ou `/transicionar-semantica`)",
                "objetivo": "Transfere automaticamente os DDLs/amostras de `saida/planejador_dw/` para `entrega/camada_semantica/` e preenche o `INTAKE_SEMANTICA.md`.",
                "cli": "`python core/scripts_comuns/transicionar_dw_para_semantica.py`",
            },
            {
                "chat": "`/executar-semantica` (ou `/iniciar-semantica`, `/gerar-semantica`)",
                "objetivo": "Gera diretamente o pacote completo da Camada Semântica (Views em 3 camadas, RLS/VPD, 8 tabelas `META_*`, validações e documento) em `saida/camada_semantica/`.",
                "cli": "`python core/scripts_comuns/simular_projeto.py --modulo semantica --acao direto`",
            },
        ],
    },
    "governanca": {
        "titulo": "🛡️ 6. Governança Corporativa, MongoDB PRODEB & AWS SageMaker Catalog",
        "descricao": "Transporte de metadados aprovados no Gate 0.5 para as 5 coleções MongoDB Enterprise e publicação no AWS Glue / SageMaker Catalog.",
        "comandos": [
            {
                "chat": "`/inspecionar-governanca`",
                "objetivo": "Valida planilhas `.xlsx` e amostras `.csv` do cliente no Gate 0.5 (bloqueia campos LGPD vazios ou CSVs corrompidos).",
                "cli": "`python core/scripts_comuns/inspecionar_insumos_governanca.py`",
            },
            {
                "chat": "`/executar-governanca` (ou `/gerar-governanca`, `/iniciar-governanca`)",
                "objetivo": "Gera diretamente os schemas/scripts das 5 coleções MongoDB padrão PRODEB (`tb_dataset`, `tb_sem_dominios`, `tb_sem_conceitos`, `tb_auditoria_eventos`, `tb_quarentena`), matriz LGPD/LAI e AWS SageMaker Catalog.",
                "cli": "`python core/scripts_comuns/gerar_governanca_corporativa.py`",
            },
        ],
    },
    "qualidade": {
        "titulo": "✅ 7. Qualidade, Testes E2E, Diagnóstico & Empacotamento",
        "descricao": "Validação automatizada de entregas, suíte de regressão E2E, troubleshooting de erros de banco/ETL e exportação/limpeza do workspace.",
        "comandos": [
            {
                "chat": "`/validar-entrega`",
                "objetivo": "Executa a bateria de auditoria pré-voo (`all`, `dw`, `fast-track`, `semantica`, `governanca`) e pós-geração (`saida`).",
                "cli": "`python core/scripts_comuns/validar_entrega.py {all,fast-track,saida}`",
            },
            {
                "chat": "`/testar-ninho`",
                "objetivo": "Executa a suíte automatizada de testes End-to-End (E2E) em todos os motores do NINHO e limpa o workspace ao final.",
                "cli": "`python core/scripts_comuns/testar_ninho.py`",
            },
            {
                "chat": "`/diagnosticar-erro-carga`",
                "objetivo": "Diagnostica falhas de execução no Oracle (`ORA-*`), ODI 12c ou Apache Hop e gera script de correção idempotente.",
                "cli": "Interativo via Agente Arquiteto",
            },
            {
                "chat": "`/empacotar-projeto`",
                "objetivo": "Verifica status, exporta a entrega final em `.zip` para `pacotes_exportados/` ou reseta o workspace para um novo projeto.",
                "cli": "`python core/scripts_comuns/gerenciar_projeto.py --status`",
            },
        ],
    },
}


# ==============================================================================
# 2. ORÁCULO INTERATIVO DE ARQUITETURA & FAQ (/duvida ou /explicar)
# ==============================================================================

BASE_CONHECIMENTO_ORACULO: Dict[str, Dict] = {
    "estrategia-carga": {
        "titulo": "⚡ Estratégia A (Truncate & Load + BITMAP) vs Estratégia B (MERGE Incremental + B-Tree)",
        "aliases": ["bitmap", "btree", "b-tree", "truncate", "merge", "carga", "indices", "indice", "estrategia"],
        "resumo": "No Oracle Data Warehouse, o tipo de índice da tabela Fato depende diretamente de como ela é carregada no ETL.",
        "conteudo": [
            "| Critério | Estratégia A (`Truncate & Load`) | Estratégia B (`MERGE Incremental`) |",
            "| :--- | :--- | :--- |",
            "| **Volume recomendado** | Fatos pequenas/médias (até ~5–10 milhões de linhas) ou recarga total rápida | Fatos grandes (>10 milhões de linhas) ou janela curta com carga contínua/CDC |",
            "| **Índice nas FKs da Fato** | **`BITMAP INDEX`** (altíssima compressão e `BITMAP AND/OR` ultrarrápido no Star Schema) | **`B-TREE INDEX COMPRESS 1`** (evita *deadlocks* `ORA-00060` e degradação de Bitmap em `MERGE`) |",
            "| **Rito de Carga (ODI)** | 1) Desabilita/Dropa Bitmaps (`PRC_POS_CARGA_FATO`) -> 2) `TRUNCATE` + `INSERT /*+ APPEND */` -> 3) Recria Bitmaps + `DBMS_STATS` | 1) `MERGE INTO FATO_*` filtrando janela incremental -> 2) Atualiza `DBMS_STATS` sem precisar dropar os índices B-Tree |",
            "",
            "💡 **Dica de Ouro do NINHO:** Nunca mantenha índices `BITMAP` ativos durante um `MERGE` ou `INSERT` concorrente sem antes marcá-los como `UNUSABLE`.",
        ],
        "proximos": [
            ("`/gerar-indices`", "Gera automaticamente os scripts de índices e a `07_prc_pos_carga_fato.sql`."),
            ("`/definir-estrategia-carga`", "Pede ao Agente para avaliar qual estratégia é melhor para a sua Fato."),
        ],
    },
    "scd": {
        "titulo": "🕰️ Dimensões SCD Tipo 1 vs SCD Tipo 2 (Histórico Temporal Kimball)",
        "aliases": ["scd1", "scd2", "historico", "vigencia", "dtc_efetivacao", "dtc_expiracao", "hash", "dimensao"],
        "resumo": "Define como o Data Warehouse reage quando um atributo cadastral muda no sistema de origem.",
        "conteudo": [
            "| Tipo SCD | O que acontece quando o dado muda na origem? | Colunas Técnicas Exigidas no NINHO | Quando usar? |",
            "| :--- | :--- | :--- | :--- |",
            "| **SCD Tipo 0** | Nunca muda (imutável) | Apenas Chave Natural (`ID_*` / `COD_*`) | Data de nascimento, CPF/CNPJ, código original |",
            "| **SCD Tipo 1** | **Sobrescreve** o valor antigo sem guardar histórico | Nenhuma coluna extra de vigência | Correção de erro de digitação, telefone, e-mail |",
            "| **SCD Tipo 2** | **Fecha a linha antiga** (`DTC_EXPIRACAO = SYSDATE`) e **abre nova versão** com nova `SK_*` e `DTC_EFETIVACAO = SYSDATE` | `DTC_EFETIVACAO`, `DTC_EXPIRACAO` (`NULL` = vigente) e `DES_HASH_SCD2` | Mudança de cargo, secretaria/órgão, faixa salarial, porte de empresa |",
            "",
            "💡 **Na Camada Semântica:** As Views de Camada 1 (`VW_<PROJETO>_DIM_*_ATUAL`) aplicam automaticamente `WHERE DTC_EXPIRACAO IS NULL` para entregar apenas a foto vigente ao Power BI.",
        ],
        "proximos": [
            ("`/classificar-scd`", "Classifica interativamente os atributos das suas dimensões entre SCD1 e SCD2."),
            ("`/gerar-views-dim`", "Gera as Views de Dimensão Vigente (`WHERE DTC_EXPIRACAO IS NULL`)."),
        ],
    },
    "linha-default": {
        "titulo": "🛡️ Por que o Registro Sentinela `-1` (`Não Informado`) é Obrigatório?",
        "aliases": ["-1", "menos-um", "sentinela", "nao-informado", "kimball", "orfao", "inner-join"],
        "resumo": "Regra clássica de Ralph Kimball para garantir integridade referencial 100% e zero perda de linhas em relatórios de BI.",
        "conteudo": [
            "1. **O Problema Real:** Sistemas transacionais frequentemente possuem chaves estrangeiras `NULL` (ex: um contrato ainda sem fornecedor homologado ou sem unidade vinculada).",
            "2. **O Risco no BI:** Se a tabela Fato gravar `NULL` na coluna `SK_FORNECEDOR`, qualquer analista que fizer `INNER JOIN` entre `FATO_CONTRATO` e `DIM_FORNECEDOR` **perderá silenciosamente o valor financeiro daquele contrato**, fazendo o painel divergir da contabilidade oficial.",
            "3. **A Solução do NINHO:**",
            "   - Toda tabela `DIM_*` recebe no script `06_init_default_records.sql` (ou `91_patch_ajustes_dim.sql`) um registro idempotente (`MERGE INTO`) com **`SK = -1`** e descrições **`'Não Informado'`**.",
            "   - Toda carga de Fato no ODI aplica **`NVL(LKP.SK_DIM, -1)`**, garantindo que 100% dos fatos apontem para uma chave válida.",
        ],
        "proximos": [
            ("`/gerar-linha-default`", "Gera o script idempotente (`MERGE INTO`) da linha `-1` para todas as suas dimensões."),
            ("`/gerar-mock-bi`", "Gera CSV sintético de BI incluindo ~3% de chaves `-1` para testar visuais no Power BI."),
        ],
    },
    "camadas-views": {
        "titulo": "🧠 Arquitetura em 3 Camadas de Views Semânticas + Catálogo Ativo `META_*`",
        "aliases": ["semantica", "views", "vw_dim", "vw_evento", "vw_kpi", "meta", "catalogo", "ia", "text-to-sql"],
        "resumo": "A Camada Semântica do NINHO isola o Power BI e os Agentes de IA da complexidade física do Star Schema em 3 níveis claros:",
        "conteudo": [
            "| Camada | Padrão de Nome | Grão e Papel Analítico | Quem Consome? |",
            "| :--- | :--- | :--- | :--- |",
            "| **Camada 1 (Dimensão Vigente)** | `VW_<PROJ>_DIM_<ENT>_ATUAL` | 1 linha por entidade ativa (`WHERE DTC_EXPIRACAO IS NULL` + `NVL('Não Informado')`, sem colunas técnicas de ETL) | Filtros/Slicers do Power BI e Lookups |",
            "| **Camada 2 (Evento Detalhado)** | `VW_<PROJ>_EVENTO_<FATO>` | 1 linha por transação/evento da Fato já enriquecido com `LEFT JOIN` das dimensões principais e `IND_SITUACAO_EVENTO` | Tabelas detalhadas, drill-through e auditoria |",
            "| **Camada 3 (KPI Consolidado)** | `VW_<PROJ>_KPI_<FATO>` | 1 linha por grupo dimensional pré-agregado com `COUNT`, `SUM`, `AVG` e taxas protegidas por **`NULLIF(denominador, 0)`** | Cards executivos, gráficos e Agentes Text-to-SQL |",
            "",
            "📚 **Catálogo `META_*` (8 Tabelas):** Junto com as Views, o NINHO gera `01_meta_glossario.sql` até `08_meta_valor_dominio.sql` (incluindo *Golden Queries* e 36 diretrizes de Prompt Engineering para LLMs).",
        ],
        "proximos": [
            ("`/simular-semantica`", "Simula e permite editar todas as Views e KPIs antes de gerar o SQL."),
            ("`/iniciar-semantica`", "Gera imediatamente as 3 camadas de Views + 8 tabelas `META_*` + RLS."),
        ],
    },
    "arquitetura-etl": {
        "titulo": "🔄 Separação de Responsabilidades no ETL: Apache Hop / Python vs Oracle ODI 12c",
        "aliases": ["odi", "hop", "python", "ftps", "stg", "staging", "etl", "elt", "ikm", "lkm"],
        "resumo": "Entenda onde atua cada ferramenta de integração dentro do padrão corporativo NINHO:",
        "conteudo": [
            "```",
            "[APIs REST / Arquivos CSV / FTPS / Bancos Externos]",
            "        │",
            "        ▼  (Ingestão Bruta: Python Extrator, Apache Hop 2.x ou Carga CSV)",
            "[Camada de Staging no Oracle: Tabelas STG_*]",
            "        │",
            "        ▼  (Transformação, Lookups, SCD Tipo 2 e Carga Fato: EXCLUSIVO no ODI 12c)",
            "[Camada Dimensional no Oracle: ODI_DIM_* -> DIM_* e FATO_*]",
            "```",
            "",
            "- **Por que `STG_* -> DIM_*/FATO_*` é exclusivamente no ODI 12c?**",
            "  Porque o ODI utiliza arquitetura **ELT Pushdown** (executa todo o `MERGE`, cálculo de hash SCD2 e *lookups* dentro do próprio motor do banco Oracle via `IKM`), sem trafegar milhões de linhas pela rede como ferramentas ETL baseadas em memória.",
        ],
        "proximos": [
            ("`/gerar-selects-odi`", "Gera as consultas SQL de `STG -> DIM` e `STG -> FATO` para o ODI 12c."),
            ("`/auditar-mapa-odi`", "Audita XMLs do ODI 12c com as heurísticas preditivas `H1` a `H9`."),
        ],
    },
    "gate-governanca": {
        "titulo": "🏛️ Governança de Dados: Gate 0.5 (Qualidade na Origem), MongoDB PRODEB & AWS SageMaker",
        "aliases": ["governanca", "lgpd", "lai", "mongodb", "prodeb", "sagemaker", "datazone", "glue", "gate"],
        "resumo": "Na Governança de Dados, a curadoria do dicionário e dos dados brutos é responsabilidade exclusiva do cliente/órgão.",
        "conteudo": [
            "1. **🛑 Gate 0.5 (Devolução na Origem):**",
            "   - O script `inspecionar_insumos_governanca.py` audita as planilhas `.xlsx` (`Dados - Insumos` e `Dicionário de Dados`) e amostras `.csv` enviadas pelo cliente.",
            "   - Se houver colunas sem descrição, classificação LGPD/LAI em branco ou linhas fantasmas (`;;;`) no CSV, **a esteira bloqueia imediatamente** e gera o **Relatório de Devolução ao Cliente**.",
            "2. **🗄️ As 5 Coleções MongoDB Padrão PRODEB:**",
            "   - `tb_dataset` (Catálogo técnico + LGPD/LAI) | `tb_sem_dominios` | `tb_sem_conceitos` | `tb_auditoria_eventos` | `tb_quarentena`.",
            "3. **☁️ Publicação Cloud:**",
            "   - Transporte automatizado para o **AWS Glue Data Catalog** e **Amazon SageMaker Unified Studio / SageMaker Catalog** (substituto do antigo AWS DataZone).",
        ],
        "proximos": [
            ("`/inspecionar-governanca`", "Roda a auditoria do Gate 0.5 nas planilhas `.xlsx` e `.csv` depositadas."),
            ("`/gerar-governanca`", "Gera os artefatos MongoDB PRODEB e scripts AWS SageMaker Catalog."),
        ],
    },
    "simulacao": {
        "titulo": "🧪 Como Funciona a Simulação com Blueprint 100% Editável (`/simular-projeto`)",
        "aliases": ["blueprint", "simular", "dry-run", "preview", "editar"],
        "resumo": "Permite visualizar e customizar todo o projeto em um único arquivo Markdown antes de gerar qualquer script físico em `saida/`.",
        "conteudo": [
            "1. **Passo 1 — Gerar a Simulação (`/simular-projeto`):**",
            "   - O NINHO lê seus DDLs de origem e cria `entrega/planejador_dw/SIMULACAO_BLUEPRINT_DW.md` e `entrega/camada_semantica/SIMULACAO_BLUEPRINT_SEMANTICA.md`.",
            "2. **Passo 2 — Editar Livremente (O Engenheiro no Comando):**",
            "   - Quer remover uma coluna? Basta mudar `| [x] |` para `| [ ] |`.",
            "   - Quer mudar o nome de uma coluna, tipo Oracle, classificação SCD, descrição de negócio, fórmula de KPI ou escolher sugestões do **💡 Radar Consultivo da IA**? Basta editar o texto na tabela Markdown!",
            "3. **Passo 3 — Aprovar e Executar (`/executar-simulacao`):**",
            "   - Marque `- [x] SIMULAÇÃO 100% FECHADA E APROVADA PARA EXECUÇÃO REAL` no topo da Blueprint e rode `/executar-simulacao`. O **Parser Reverso** lê todas as suas edições e gera os arquivos finais em `saida/`.",
        ],
        "proximos": [
            ("`/simular-projeto`", "Gera agora as Blueprints editáveis de DW e Camada Semântica."),
            ("`/executar-simulacao`", "Materializa as Blueprints aprovadas na pasta `saida/`."),
        ],
    },
    "fast-track": {
        "titulo": "⚡ Modo Fast-Track & Micro-Processos Independentes (Melhoria de DW Existente)",
        "aliases": ["micro", "existente", "patch", "novalidate", "dicionario", "comentarios"],
        "resumo": "Ideal quando você já construiu as tabelas `DIM_*` e `FATO_*` no banco e não quer refazer o processo completo nem mexer no ETL.",
        "conteudo": [
            "- **Dispensa preenchimento de `INTAKE_*.md`:** Basta colocar o `.sql` com os `CREATE TABLE` atuais em `entrega/planejador_dw/ddl/`.",
            "- **100% Não-Destrutivo:**",
            "  - Constraints usam `ENABLE NOVALIDATE` / `RELY DISABLE NOVALIDATE` para não travar tabelas já populadas.",
            "  - A linha `-1` usa `MERGE INTO ... WHEN NOT MATCHED` para nunca duplicar registros.",
            "  - Você pode rodar tudo de uma vez (`/melhorar-dw-existente`) ou apenas o recorte que precisa (`/gerar-dicionario`, `/gerar-comentarios`, `/gerar-indices`, `/gerar-selects-odi`, `/gerar-guia-bi`).",
        ],
        "proximos": [
            ("`/melhorar-dw-existente`", "Executa o diagnóstico completo e gera todos os patches não-destrutivos."),
            ("`/gerar-dicionario`", "Gera apenas o Dicionário de Dados HTML interativo."),
        ],
    },
    "rls": {
        "titulo": "🔒 Row-Level Security (RLS) & Virtual Private Database (VPD) no Oracle",
        "aliases": ["vpd", "seguranca", "sys_context", "dbms_rls", "multi-tenant", "orgao"],
        "resumo": "Garante isolamento multi-tenant nativo no banco Oracle para que cada usuário/órgão enxergue apenas as linhas autorizadas.",
        "conteudo": [
            "- **Identidade efetiva resolvida pelo banco:**",
            "  - Power BI e agentes de IA conectam com uma conta de serviço única (pool). A aplicação informa o usuário final com `DBMS_SESSION.SET_IDENTIFIER`.",
            "  - O `CLIENT_IDENTIFIER` só é aceito se `SESSION_USER` estiver em `RLS_CONTAS_SERVICO`; qualquer outra sessão usa `SESSION_USER` (ninguém se passa por outro usuário).",
            "- **Arquitetura Fail-Closed (`1 = 0`):**",
            "  - Usuário efetivo sem vínculo em `USUARIO_SEGMENTOS`, ou qualquer erro na função de predicado, retorna `'1 = 0'` (bloqueia tudo por padrão).",
            "- **Sem limite de 4000 bytes:** o predicado usa subconsulta em `USUARIO_SEGMENTOS` (nada de `LISTAGG`), suportando centenas de unidades/municípios por usuário.",
            "- **Preservação do Sentinela `-1`:**",
            "  - O predicado sempre inclui `COLUNA_SEGREGACAO = -1`, permitindo identificar fatos não classificados.",
            "- **Política `DYNAMIC`:** reavaliada a cada execução, necessária quando o pool troca de usuário na mesma sessão.",
        ],
        "proximos": [
            ("`/gerar-rls`", "Gera o script `02_rls.sql` com tabelas de apoio, `PKG_SECURITY_<PROJETO>` e `DBMS_RLS.ADD_POLICY`."),
        ],
    },
}


# ==============================================================================
# 3. COMPONENTES VISUAIS DE UX (RODAPÉ BREADCRUMBS, ONBOARDING, BÚSSOLA, DOCTOR, DEMO)
# ==============================================================================

def formatar_rodape_proximos_passos(passos: List[Tuple[str, str]]) -> str:
    """Formata um bloco visual padronizado de próximos passos sugeridos no chat."""
    if not passos:
        return ""
    linhas = [
        "",
        "---",
        "### 🧭 O que você pode fazer agora (Próximos Passos Sugeridos):",
        "",
        "| Digite no Chat | Ação que será executada |",
        "| :--- | :--- |",
    ]
    for cmd, desc in passos:
        linhas.append(f"| {cmd} | {desc} |")
    linhas.append("")
    return "\n".join(linhas)


def renderizar_onboarding() -> str:
    """Renderiza o Guia Rápido de Boas-Vindas (/comecar ou /onboarding) com as 5 Missões Reais."""
    linhas = [
        "# 🚀 Bem-vindo ao NINHO — Por Onde Você Quer Começar Hoje? (`/comecar`)",
        "",
        "> Escolha abaixo o seu **cenário atual**. Cada trilha tem apenas **3 passos simples**:",
        "",
        "---",
        "",
        "### 🏗️ Cenário 1: Quero criar um Data Warehouse novo a partir de tabelas de origem (DDL/CSV)",
        "1. **Onde soltar o arquivo:** Coloque seu `.sql` (ou `.csv`) em [`entrega/planejador_dw/ddl/`](file:///"
        + str(ENTREGA_DIR / "planejador_dw" / "ddl").replace("\\", "/")
        + ")",
        "2. **Comando para simular e editar:** Digite **`/simular-projeto`** no chat (gera as Blueprints editáveis de DW + Semântica com prévia de dados e Radar da IA).",
        "3. **Comando para gerar tudo:** Após revisar/marcar `[x]` na Blueprint, digite **`/executar-simulacao`**.",
        "",
        "### ⚡ Cenário 2: Já construí meu DW (`DIM_*` e `FATO_*`) e quero apenas melhorá-lo (Fast-Track)",
        "1. **Onde soltar o arquivo:** Coloque o `.sql` das suas tabelas `DIM_*` e `FATO_*` em [`entrega/planejador_dw/ddl/`](file:///"
        + str(ENTREGA_DIR / "planejador_dw" / "ddl").replace("\\", "/")
        + ")",
        "2. **Comando para Raio-X completo:** Digite **`/melhorar-dw-existente`** (gera comentários, dicionário HTML, índices, linha `-1`, constraints `NOVALIDATE`, selects ODI e Guia BI sem tocar na sua carga).",
        "3. **Ou rode só um micro-processo isolado:** `/gerar-dicionario`, `/gerar-comentarios`, `/gerar-indices`, `/gerar-selects-odi`, `/gerar-guia-bi` ou `/gerar-mock-bi`.",
        "",
        "### 🧠 Cenário 3: Quero criar a Camada Semântica (Views em 3 Camadas + Catálogo IA `META_*` + RLS)",
        "1. **Onde soltar o arquivo:** Coloque os DDLs do DW em [`entrega/camada_semantica/sql_fontes/`](file:///"
        + str(ENTREGA_DIR / "camada_semantica" / "sql_fontes").replace("\\", "/")
        + ") *(ou use `/concluir-dw` se acabou de gerar o DW no NINHO)*.",
        "2. **Comando para simular ou gerar:** Digite **`/simular-semantica`** (para revisar KPIs antes) ou **`/iniciar-semantica`** (para gerar direto em `saida/camada_semantica/`).",
        "3. **Ou rode só uma parte:** `/gerar-views-kpi`, `/gerar-catalogo-meta` ou `/gerar-rls`.",
        "",
        "### 🔍 Cenário 4: Quero auditar Tuning no ODI 12c, Apache Hop 2.x ou Migrar um Power BI (`.pbix`)",
        "1. **Para ODI 12c (`H1`..`H9`):** Solte os XMLs em `entrega/planejador_dw/odi/` e digite **`/auditar-mapa-odi`**.",
        "2. **Para Apache Hop (`HOP-H1`..`H8`):** Solte os `.hpl`/`.hwf` em `entrega/planejador_dw/hop/` e digite **`/auditar-hop`**.",
        "3. **Para Power BI (`.pbix`):** Solte o arquivo `.pbix` em `entrega/planejador_dw/pbix/` e digite **`/inspecionar-pbix`**.",
        "",
        "### 🛡️ Cenário 5: Quero validar Planilhas de Governança (Gate 0.5), MongoDB PRODEB & AWS SageMaker",
        "1. **Onde soltar os arquivos:** Planilhas `.xlsx` em `entrega/governanca_dados/planilhas/` e amostras `.csv` em `entrega/governanca_dados/amostras/`.",
        "2. **Comando de Auditoria (Gate 0.5):** Digite **`/inspecionar-governanca`** (emite o Relatório de Devolução ao Cliente se houver falhas ou aprova a Matriz DE/PARA).",
        "3. **Comando de Geração:** Após aprovação no Gate 0.5, digite **`/gerar-governanca`**.",
    ]
    linhas.append(
        formatar_rodape_proximos_passos(
            [
                ("`/demo`", "Não tem arquivos agora? Roda um projeto completo de demonstração em 3 segundos!"),
                ("`/onde-estou`", "Verifica o que já existe nas suas pastas `entrega/` e `saida/` agora."),
                ("`/duvida listar`", "Consulta o Oráculo para tirar dúvidas sobre SCD2, Bitmap, Linha -1, ODI ou RLS."),
            ]
        )
    )
    return "\n".join(linhas)


def renderizar_explicacao(termo: str) -> str:
    """Busca e renderiza uma explicação arquitetural didática do Oráculo (/duvida ou /explicar)."""
    chave_busca = (termo or "").strip().lower()

    if not chave_busca or chave_busca in ("listar", "todos", "all", "ajuda", "help", "?"):
        linhas = [
            "# 💡 Oráculo de Arquitetura & FAQ Interativo do NINHO (`/duvida`)",
            "",
            "> Escolha qualquer tema abaixo digitando **`/duvida <tema>`** no chat (ou `--explicar <tema>` no CLI):",
            "",
            "| Tema (`/duvida <tema>`) | O que o Oráculo Explica | Palavras-Chave Aceitas |",
            "| :--- | :--- | :--- |",
        ]
        for k, info in BASE_CONHECIMENTO_ORACULO.items():
            aliases_str = ", ".join(f"`{a}`" for a in info["aliases"][:4])
            linhas.append(f"| **`/duvida {k}`** | {info['resumo']} | {aliases_str} |")
        linhas.append(
            formatar_rodape_proximos_passos(
                [
                    ("`/duvida estrategia-carga`", "Entenda quando usar BITMAP vs B-Tree na tabela Fato."),
                    ("`/duvida linha-default`", "Veja por que a chave sentinela `-1` é obrigatória no Kimball."),
                    ("`/comecar`", "Voltar para as 5 trilhas guiadas de início rápido."),
                ]
            )
        )
        return "\n".join(linhas)

    # Busca exata ou por alias/substring
    escolhido = BASE_CONHECIMENTO_ORACULO.get(chave_busca)
    if not escolhido:
        for k, info in BASE_CONHECIMENTO_ORACULO.items():
            if chave_busca in k or any(chave_busca in al or al in chave_busca for al in info["aliases"]):
                escolhido = info
                break

    if not escolhido:
        return (
            f"⚠️ Não encontrei um tópico exato para **`{termo}`** no Oráculo.\n\n"
            + renderizar_explicacao("listar")
        )

    linhas = [
        f"# 💡 Oráculo NINHO: {escolhido['titulo']}",
        "",
        f"> **Resumo Executivo:** {escolhido['resumo']}",
        "",
        *escolhido["conteudo"],
        formatar_rodape_proximos_passos(escolhido.get("proximos", [])),
    ]
    return "\n".join(linhas)


def detectar_arquivos_fora_do_lugar() -> List[Dict[str, Path]]:
    """Detecta arquivos depositados diretamente na raiz de `entrega/` ou na pasta errada do módulo."""
    achados: List[Dict[str, Path]] = []
    if not ENTREGA_DIR.exists():
        return achados

    locais_observados = [
        ENTREGA_DIR,
        ENTREGA_DIR / "planejador_dw",
        ENTREGA_DIR / "camada_semantica",
        ENTREGA_DIR / "governanca_dados",
    ]
    arquivos_legitimos_modulos = {
        "SIMULACAO_BLUEPRINT_DW.md",
        "SIMULACAO_BLUEPRINT_SEMANTICA.md",
        "RELATORIO_DEVOLUCAO_CLIENTE_GOVERNANCA.md",
        "MATRIZ_DE_PARA_MONGODB_PRODEB.md",
        ".gitkeep",
        "README.md",
    }

    for pasta in locais_observados:
        if not pasta.exists():
            continue
        for item in pasta.iterdir():
            if not item.is_file() or item.name in arquivos_legitimos_modulos:
                continue
            ext = item.suffix.lower()
            destino = None
            motivo = ""
            if ext == ".sql":
                if pasta == ENTREGA_DIR / "camada_semantica":
                    destino = ENTREGA_DIR / "camada_semantica" / "sql_fontes" / item.name
                    motivo = "Scripts SQL para a Camada Semântica devem ficar em `entrega/camada_semantica/sql_fontes/`."
                else:
                    destino = ENTREGA_DIR / "planejador_dw" / "ddl" / item.name
                    motivo = "Scripts DDL (.sql) para o Planejador DW devem ficar em `entrega/planejador_dw/ddl/`."
            elif ext == ".pbix":
                destino = ENTREGA_DIR / "planejador_dw" / "pbix" / item.name
                motivo = "Arquivos Power BI (.pbix) devem ficar em `entrega/planejador_dw/pbix/`."
            elif ext in (".hpl", ".hwf"):
                destino = ENTREGA_DIR / "planejador_dw" / "hop" / item.name
                motivo = "Pipelines/Workflows Apache Hop (.hpl/.hwf) devem ficar em `entrega/planejador_dw/hop/`."
            elif ext == ".xlsx":
                if pasta == ENTREGA_DIR / "planejador_dw":
                    # Planilhas de indicadores/metas de BI (ex: Indicadores - PRAES.xlsx) são legítimas em entrega/planejador_dw/
                    destino = None
                elif pasta == ENTREGA_DIR and any(k in item.name.lower() for k in ("indicador", "kpi", "meta", "bi", "dw")):
                    destino = ENTREGA_DIR / "planejador_dw" / item.name
                    motivo = "Planilhas de Indicadores/Metas de BI (.xlsx) devem ficar em `entrega/planejador_dw/`."
                else:
                    destino = ENTREGA_DIR / "governanca_dados" / "planilhas" / item.name
                    motivo = "Planilhas de Governança (.xlsx) devem ficar em `entrega/governanca_dados/planilhas/`."
            elif ext == ".csv":
                eh_ddl_csv = False
                try:
                    amostra_csv = item.read_text(encoding="utf-8", errors="ignore")[:8192].upper()
                    if "CREATE TABLE" in amostra_csv:
                        eh_ddl_csv = True
                except Exception as _exc:
                    _LOG.debug("Exceção tratada (ajuda_ninho.py:727): %r", _exc)
                if eh_ddl_csv:
                    if pasta == ENTREGA_DIR / "camada_semantica":
                        destino = ENTREGA_DIR / "camada_semantica" / "sql_fontes" / item.name
                        motivo = "Arquivos CSV contendo DDL (`CREATE TABLE`) devem ficar em `entrega/camada_semantica/sql_fontes/`."
                    else:
                        destino = ENTREGA_DIR / "planejador_dw" / "ddl" / item.name
                        motivo = "Arquivos CSV contendo DDL (`CREATE TABLE`) devem ficar em `entrega/planejador_dw/ddl/`."
                elif pasta == ENTREGA_DIR / "governanca_dados":
                    destino = ENTREGA_DIR / "governanca_dados" / "amostras" / item.name
                    motivo = "Amostras CSV de Governança devem ficar em `entrega/governanca_dados/amostras/`."
                else:
                    destino = ENTREGA_DIR / "planejador_dw" / "dados_amostra" / item.name
                    motivo = "Amostras CSV do DW devem ficar em `entrega/planejador_dw/dados_amostra/`."

            if destino and destino != item:
                achados.append({"origem": item, "destino": destino, "motivo": motivo})

    return achados


ARQUIVOS_PRESERVADOS_TEMPLATE = {".gitkeep", "README.md", "01_create_meta_tables.sql"}


def renderizar_onde_estou() -> str:
    """Escaneia o workspace e renderiza a Bússola Contextual (/onde-estou ou /status)."""
    pasta_ddl_dw = ENTREGA_DIR / "planejador_dw" / "ddl"
    ddls_dw = (
        [
            p for p in pasta_ddl_dw.iterdir()
            if p.is_file() and p.suffix.lower() in (".sql", ".ddl", ".csv", ".txt") and p.name.lower() != "readme.md"
        ]
        if pasta_ddl_dw.exists()
        else []
    )
    ind_xlsx_dw = (
        [p for p in (ENTREGA_DIR / "planejador_dw").glob("*.xlsx") if not p.name.startswith("~$")]
        if (ENTREGA_DIR / "planejador_dw").exists()
        else []
    )
    pbix_dw = list((ENTREGA_DIR / "planejador_dw" / "pbix").glob("*.pbix")) if (ENTREGA_DIR / "planejador_dw" / "pbix").exists() else []
    gov_xlsx = [
        p for p in (ENTREGA_DIR / "governanca_dados" / "planilhas").glob("*.xlsx")
        if not p.name.startswith("~$")
    ] if (ENTREGA_DIR / "governanca_dados" / "planilhas").exists() else []

    bp_dw = ENTREGA_DIR / "planejador_dw" / "SIMULACAO_BLUEPRINT_DW.md"
    bp_sem = ENTREGA_DIR / "camada_semantica" / "SIMULACAO_BLUEPRINT_SEMANTICA.md"
    bp_dw_existe = bp_dw.exists()
    bp_sem_existe = bp_sem.exists()

    bp_dw_aprovada = False
    if bp_dw_existe:
        bp_dw_aprovada = bool(
            re.search(r"-\s*\[[xX]\]\s*\*\*SIMULAÇÃO 100% FECHADA E APROVADA", bp_dw.read_text(encoding="utf-8", errors="ignore"))
        )
    bp_sem_aprovada = False
    if bp_sem_existe:
        bp_sem_aprovada = bool(
            re.search(r"-\s*\[[xX]\]\s*\*\*SIMULAÇÃO 100% FECHADA E APROVADA", bp_sem.read_text(encoding="utf-8", errors="ignore"))
        )

    arqs_saida_dw = [
        p for p in (SAIDA_DIR / "planejador_dw").rglob("*") if p.is_file() and p.name not in ARQUIVOS_PRESERVADOS_TEMPLATE
    ] if (SAIDA_DIR / "planejador_dw").exists() else []
    arqs_saida_sem = [
        p for p in (SAIDA_DIR / "camada_semantica").rglob("*") if p.is_file() and p.name not in ARQUIVOS_PRESERVADOS_TEMPLATE
    ] if (SAIDA_DIR / "camada_semantica").exists() else []
    arqs_saida_gov = [
        p for p in (SAIDA_DIR / "governanca_dados").rglob("*") if p.is_file() and p.name not in ARQUIVOS_PRESERVADOS_TEMPLATE
    ] if (SAIDA_DIR / "governanca_dados").exists() else []

    fora_do_lugar = detectar_arquivos_fora_do_lugar()

    # Determina a Fase Atual (0 a 5)
    tem_insumos = bool(ddls_dw or ind_xlsx_dw or pbix_dw or gov_xlsx)
    tem_blueprints = bool(bp_dw_existe or bp_sem_existe)
    tem_saida_dw = len(arqs_saida_dw) > 0
    tem_saida_sem = len(arqs_saida_sem) > 0

    if not tem_insumos and not tem_blueprints and not tem_saida_dw and not tem_saida_sem and not arqs_saida_gov:
        fase_num = 0
        barra = "[░░░░░] 0%"
        status_titulo = "Fase 0/5 — Workspace Limpo (Aguardando Insumos ou Modo Playground)"
        proximos = [
            ("`/comecar`", "Ver onde depositar seus arquivos de acordo com a sua missão de hoje."),
            ("`/demo`", "Rodar um projeto corporativo de demonstração completo em 1 comando."),
        ]
    elif tem_insumos and not tem_blueprints and not tem_saida_dw:
        fase_num = 1
        barra = "[█░░░░] 20%"
        status_titulo = "Fase 1/5 — Insumos Depositados em `entrega/` (Pronto para Inspecionar ou Simular)"
        proximos = [
            ("`/simular-projeto`", "Gerar as Blueprints 100% editáveis de DW + Camada Semântica."),
            ("`/melhorar-dw-existente`", "Se o DW já está construído no banco, gerar patches Fast-Track + Dicionário HTML."),
            ("`/inspecionar-fontes`", "Inspecionar DDLs e ver o Radar Consultivo da IA."),
        ]
    elif tem_blueprints and not (bp_dw_aprovada or bp_sem_aprovada) and not tem_saida_dw:
        fase_num = 2
        barra = "[██░░░] 40%"
        status_titulo = "Fase 2/5 — Blueprints de Simulação Geradas (Aguardando Revisão/Aprovação `[x]`)"
        proximos = [
            ("`/executar-simulacao`", "Após marcar `[x] SIMULAÇÃO 100% FECHADA E APROVADA` na Blueprint, gera os scripts reais."),
            ("`/duvida simulacao`", "Ver como editar colunas, fórmulas e KPIs do Radar dentro da Blueprint."),
        ]
    elif (bp_dw_aprovada or bp_sem_aprovada) and not tem_saida_dw:
        fase_num = 3
        barra = "[███░░] 60%"
        status_titulo = "Fase 3/5 — Blueprint Aprovada (`[x]`) e Pronta para Geração Física"
        proximos = [
            ("`/executar-status` -> `/executar-simulacao`", "Materializar todos os scripts em `saida/planejador_dw/` e `saida/camada_semantica/`."),
        ]
    elif tem_saida_dw and not tem_saida_sem:
        fase_num = 4
        barra = "[████░] 80%"
        status_titulo = "Fase 4/5 — Artefatos do DW Gerados em `saida/planejador_dw/` (Pronto para Camada Semântica)"
        proximos = [
            ("`/iniciar-semantica`", "Gerar as 3 camadas de Views Semânticas + 8 tabelas `META_*` + RLS."),
            ("`/gerar-mock-bi`", "Gerar dados sintéticos CSV com linha `-1` para o Analista de BI."),
            ("`/validar-entrega`", "Auditar todos os scripts gerados em `saida/`."),
        ]
    else:
        fase_num = 5
        barra = "[█████] 100%"
        status_titulo = "Fase 5/5 — Esteira Completa Gerada (`saida/planejador_dw/` + `saida/camada_semantica/`)"
        proximos = [
            ("`/validar-entrega`", "Executar o checklist automatizado de qualidade pós-geração."),
            ("`/gerar-mock-bi`", "Gerar CSV sintético dinâmico para testes no Power BI."),
            ("`/empacotar-projeto`", "Exportar a entrega completa em `.zip` ou limpar o workspace."),
        ]

    linhas = [
        "# 🧭 Bússola Contextual do NINHO (`/onde-estou`)",
        "",
        f"### {barra} — **{status_titulo}**",
        "",
        "| Camada do Workspace | Estado Atual | Detalhes Detectados |",
        "| :--- | :---: | :--- |",
        f"| **1. Insumos DW (`entrega/planejador_dw/`)** | {'🟢 Ativo' if (ddls_dw or ind_xlsx_dw or pbix_dw) else '⚪ Vazio'} | `{len(ddls_dw)}` DDL(s) (`.sql`/`.csv`), `{len(ind_xlsx_dw)}` planilha(s) `.xlsx`, `{len(pbix_dw)}` `.pbix` |",
        f"| **2. Blueprint DW (`SIMULACAO_BLUEPRINT_DW.md`)** | {'🟢 Aprovada `[x]`' if bp_dw_aprovada else ('🟡 Pendente `[ ]`' if bp_dw_existe else '⚪ Não gerada')} | {'Pronta para `/executar-simulacao`' if bp_dw_aprovada else ('Aguardando revisão do engenheiro' if bp_dw_existe else 'Use `/simular-dw` para criar')} |",
        f"| **3. Blueprint Semântica (`SIMULACAO_BLUEPRINT_SEMANTICA.md`)** | {'🟢 Aprovada `[x]`' if bp_sem_aprovada else ('🟡 Pendente `[ ]`' if bp_sem_existe else '⚪ Não gerada')} | {'Pronta para `/executar-simulacao`' if bp_sem_aprovada else ('Aguardando revisão do engenheiro' if bp_sem_existe else 'Use `/simular-semantica` para criar')} |",
        f"| **4. Saída Física DW (`saida/planejador_dw/`)** | {'🟢 Populada' if arqs_saida_dw else '⚪ Vazia'} | `{len(arqs_saida_dw)}` artefato(s) gerado(s) |",
        f"| **5. Saída Camada Semântica (`saida/camada_semantica/`)** | {'🟢 Populada' if arqs_saida_sem else '⚪ Vazia'} | `{len(arqs_saida_sem)}` artefato(s) gerado(s) |",
        f"| **6. Governança (`entrega/` & `saida/governanca_dados/`)** | {'🟢 Ativo' if (gov_xlsx or arqs_saida_gov) else '⚪ Vazio'} | `{len(gov_xlsx)}` planilha(s) `.xlsx` na entrada, `{len(arqs_saida_gov)}` artefato(s) na saída |",
    ]

    if fora_do_lugar:
        linhas.extend([
            "",
            "> [!WARNING]",
            f"> 🩺 **Atenção:** Encontrei **{len(fora_do_lugar)} arquivo(s) fora da subpasta canônica** em `entrega/`. "
            "Digite **`/doctor`** (ou `python core/scripts_comuns/ajuda_ninho.py --doctor --corrigir`) para movê-los automaticamente para a pasta certa!",
        ])

    linhas.append(formatar_rodape_proximos_passos(proximos))
    return "\n".join(linhas)


def _checagens_ambiente() -> List[str]:
    """Checa versão do Python, dependências opcionais, skills sincronizadas e proteção LGPD do Git."""
    import importlib.util

    linhas = []
    versao = sys.version_info
    if versao >= (3, 10):
        linhas.append(f"- ✅ **Versão do Python:** `{sys.version.split()[0]}` (mínimo 3.10)")
    else:
        linhas.append(f"- ❌ **Versão do Python:** `{sys.version.split()[0]}` — o NINHO exige 3.10 ou superior.")

    opcionais = {
        "openpyxl": "leitura nativa de planilhas .xlsx na Governança",
        "defusedxml": "parsing seguro de XMLs de terceiros (ODI, Hop, PBIX)",
    }
    for pacote, uso in opcionais.items():
        if importlib.util.find_spec(pacote):
            linhas.append(f"- ✅ **Pacote opcional `{pacote}`:** instalado ({uso}).")
        else:
            linhas.append(f"- 🟡 **Pacote opcional `{pacote}`:** ausente ({uso}). Instale com `pip install -r requirements.txt`.")

    try:
        spec = importlib.util.spec_from_file_location("ninho_cli", ROOT_DIR / "ninho.py")
        ninho_cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ninho_cli)
        faltando = [
            c
            for c in ninho_cli.DESCRICOES_SKILLS_SLASH
            if c not in ninho_cli.COMANDOS_RESERVADOS_IDE and not (ninho_cli.SKILLS_DIR / c / "SKILL.md").exists()
        ]
        if faltando:
            linhas.append(
                f"- ⚠️ **Skills de comando (`/`):** {len(faltando)} ausente(s) no menu da IDE "
                f"({', '.join('/' + c for c in faltando[:5])}). Rode `python ninho.py instalar-comandos`."
            )
        else:
            linhas.append("- ✅ **Skills de comando (`/`):** todas instaladas no menu da IDE.")
    except Exception as exc:  # o doctor nunca deve quebrar por causa de uma checagem
        linhas.append(f"- 🟡 **Skills de comando (`/`):** não foi possível verificar ({exc}).")

    gitignore = ROOT_DIR / ".gitignore"
    regras = gitignore.read_text(encoding="utf-8", errors="replace") if gitignore.exists() else ""
    if "/entrega/**" in regras and "/saida/**" in regras:
        linhas.append("- ✅ **Proteção LGPD no Git:** `entrega/` e `saida/` não são versionadas.")
    else:
        linhas.append(
            "- ❌ **Proteção LGPD no Git:** `.gitignore` não protege `entrega/` e `saida/`; "
            "dados de cliente podem ir para o repositório."
        )
    return linhas


def executar_doctor(corrigir: bool = False) -> str:
    """Executa o diagnóstico de saúde do workspace e organiza arquivos fora do lugar se --corrigir."""
    linhas = [
        "# 🩺 Diagnóstico de Saúde do Workspace NINHO (`/doctor`)",
        "",
    ]

    pastas_essenciais = [
        ENTREGA_DIR / "planejador_dw" / "ddl",
        ENTREGA_DIR / "camada_semantica" / "sql_fontes",
        ENTREGA_DIR / "governanca_dados" / "planilhas",
        SAIDA_DIR / "planejador_dw",
        SAIDA_DIR / "camada_semantica",
        SAIDA_DIR / "governanca_dados",
    ]
    for p in pastas_essenciais:
        p.mkdir(parents=True, exist_ok=True)

    fora_do_lugar = detectar_arquivos_fora_do_lugar()

    linhas.extend(_checagens_ambiente())
    linhas.append("- ✅ **Estrutura Canônica de Pastas (`entrega/` e `saida/`):** Verificada e íntegra.")

    if not fora_do_lugar:
        linhas.append("- ✅ **Organização de Insumos:** Nenhum arquivo órfão ou fora da pasta correta foi detectado.")
    else:
        linhas.append(f"- ⚠️ **Arquivos Fora da Subpasta Canônica:** `{len(fora_do_lugar)}` encontrado(s):")
        linhas.append("")
        linhas.append("| Arquivo Encontrado | Destino Canônico Correto | Status |")
        linhas.append("| :--- | :--- | :--- |")
        for item in fora_do_lugar:
            orig_rel = item["origem"].relative_to(ROOT_DIR)
            dest_rel = item["destino"].relative_to(ROOT_DIR)
            if corrigir:
                item["destino"].parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(item["origem"]), str(item["destino"]))
                status_acao = "✅ **Movido automaticamente**"
            else:
                status_acao = "🟡 Pendente (use `--corrigir`)"
            linhas.append(f"| `{orig_rel}` | `{dest_rel}` | {status_acao} |")

    linhas.append(
        formatar_rodape_proximos_passos(
            [
                ("`/onde-estou`", "Conferir a Bússola de Progresso do projeto após o check-up."),
                ("`/testar-ninho`", "Rodar a bateria automatizada E2E para certificar todos os motores."),
            ]
        )
    )
    return "\n".join(linhas)


DDL_DEMO_PLAYGROUND = """
-- =============================================================================
-- PROJETO DE DEMONSTRAÇÃO NINHO (PLAYGROUND): COMPRAS E CONTRATOS PÚBLICOS (SAEB)
-- =============================================================================

CREATE TABLE SAEB_ORIGEM.TB_ORGAO_PUBLICO (
    ID_ORGAO          NUMBER(10)     NOT NULL,
    COD_UNIDADE_GEST  VARCHAR2(20)   NOT NULL,
    NOM_ORGAO         VARCHAR2(150)  NOT NULL,
    SGL_ORGAO         VARCHAR2(20),
    DES_PODER_ESFERA  VARCHAR2(40),
    FLG_ATIVO         CHAR(1)        DEFAULT 'S',
    DTC_CADASTRO      DATE           DEFAULT SYSDATE,
    CONSTRAINT PK_TB_ORGAO_PUBLICO PRIMARY KEY (ID_ORGAO)
);

CREATE TABLE SAEB_ORIGEM.TB_FORNECEDOR (
    ID_FORNECEDOR     NUMBER(12)     NOT NULL,
    NUM_CNPJ_CPF      VARCHAR2(18)   NOT NULL,
    NOM_RAZAO_SOCIAL  VARCHAR2(200)  NOT NULL,
    DES_PORTE_EMPRESA VARCHAR2(40),
    SGL_UF_FORNECEDOR CHAR(2),
    DTC_ATUALIZACAO   DATE           DEFAULT SYSDATE,
    CONSTRAINT PK_TB_FORNECEDOR PRIMARY KEY (ID_FORNECEDOR)
);

CREATE TABLE SAEB_ORIGEM.TB_LICITACAO_CONTRATO (
    ID_CONTRATO            NUMBER(15)     NOT NULL,
    ID_ORGAO               NUMBER(10)     NOT NULL,
    ID_FORNECEDOR          NUMBER(12)     NOT NULL,
    NUM_PROCESSO_SEI       VARCHAR2(40)   NOT NULL,
    DES_MODALIDADE         VARCHAR2(60)   NOT NULL,
    DES_STATUS_CONTRATO    VARCHAR2(30)   NOT NULL,
    DTC_ASSINATURA         DATE           NOT NULL,
    DTC_VIGENCIA_FIM       DATE,
    QTD_ITENS_CONTRATO     NUMBER(8)      DEFAULT 1,
    VAL_ESTIMADO           NUMBER(18,2)   DEFAULT 0,
    VAL_CONTRATO           NUMBER(18,2)   NOT NULL,
    VAL_PAGO_ACUMULADO     NUMBER(18,2)   DEFAULT 0,
    CONSTRAINT PK_TB_LICITACAO_CONTRATO PRIMARY KEY (ID_CONTRATO)
);
"""


def limpar_demo() -> str:
    """Remove os arquivos de demonstração de `entrega/` e `saida/` preservando `.gitkeep`, `README.md` e base DDL."""
    removidos = 0
    for pasta_raiz in (ENTREGA_DIR, SAIDA_DIR):
        if not pasta_raiz.exists():
            continue
        for arq in list(pasta_raiz.rglob("*")):
            if arq.is_file() and arq.name not in ARQUIVOS_PRESERVADOS_TEMPLATE:
                try:
                    arq.unlink()
                    removidos += 1
                except OSError as _exc:
                    _LOG.debug("Exceção tratada (ajuda_ninho.py:1045): %r", _exc)
    from ninho_core.catalogo import restaurar_fichas_projeto

    removidos += restaurar_fichas_projeto()
    return (
        "# 🧹 Modo Playground Encerrado (`/limpar-demo`)\n\n"
        f"- Foram removidos **`{removidos}` arquivos de demonstração** de `entrega/` e `saida/`.\n"
        "- Seu workspace está **100% limpo** e pronto para receber um projeto real!\n"
        + formatar_rodape_proximos_passos(
            [
                ("`/comecar`", "Ver as 5 trilhas guiadas para iniciar seu projeto real."),
                ("`/onde-estou`", "Confirmar que o workspace está na Fase 0/5 (limpo)."),
            ]
        )
    )


def executar_demo() -> str:
    """Popula um projeto completo de demonstração e gera Blueprints, DW, Semântica, Dicionário HTML e Mock BI."""
    pasta_ddl = ENTREGA_DIR / "planejador_dw" / "ddl"
    pasta_ddl.mkdir(parents=True, exist_ok=True)
    arq_demo = pasta_ddl / "01_demo_licitacao_saeb.sql"
    arq_demo.write_text(DDL_DEMO_PLAYGROUND.strip() + "\n", encoding="utf-8")

    env_utf8 = {**os.environ, "PYTHONIOENCODING": "utf-8"}

    # 1. Gera as Blueprints de Simulação
    subprocess.run(
        [sys.executable, str(ROOT_DIR / "core" / "scripts_comuns" / "simular_projeto.py"), "--modulo", "ambos", "--acao", "simular"],
        cwd=str(ROOT_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env_utf8,
        check=True,
    )

    # 2. Marca ambas as Blueprints como aprovadas (e no /demo habilita todos os formatos de exportação) e executa a geração física
    for bp_path in (
        ENTREGA_DIR / "planejador_dw" / "SIMULACAO_BLUEPRINT_DW.md",
        ENTREGA_DIR / "camada_semantica" / "SIMULACAO_BLUEPRINT_SEMANTICA.md",
    ):
        if bp_path.exists():
            txt = bp_path.read_text(encoding="utf-8")
            txt = txt.replace(
                "- [ ] **SIMULAÇÃO 100% FECHADA E APROVADA PARA EXECUÇÃO REAL**",
                "- [x] **SIMULAÇÃO 100% FECHADA E APROVADA PARA EXECUÇÃO REAL**",
            )
            txt = txt.replace("- [ ] `12_apresentacao_executiva`", "- [x] `12_apresentacao_executiva`")
            txt = txt.replace("- [ ] `13_exportar_docx`", "- [x] `13_exportar_docx`")
            txt = txt.replace("- [ ] `14_exportar_pdf`", "- [x] `14_exportar_pdf`")
            bp_path.write_text(txt, encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(ROOT_DIR / "core" / "scripts_comuns" / "simular_projeto.py"),
            "--modulo",
            "ambos",
            "--acao",
            "executar",
            "--todos-formatos",
        ],
        cwd=str(ROOT_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env_utf8,
        check=True,
    )

    # 3. Gera o Mock CSV dinâmico para BI
    subprocess.run(
        [sys.executable, str(ROOT_DIR / "core" / "scripts_comuns" / "gerar_mock_dados.py"), "--linhas", "50"],
        cwd=str(ROOT_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env_utf8,
        check=True,
    )

    bp_dw_url = "file:///" + str(ENTREGA_DIR / "planejador_dw" / "SIMULACAO_BLUEPRINT_DW.md").replace("\\", "/")
    bp_sem_url = "file:///" + str(ENTREGA_DIR / "camada_semantica" / "SIMULACAO_BLUEPRINT_SEMANTICA.md").replace("\\", "/")
    dic_html_url = "file:///" + str(SAIDA_DIR / "planejador_dw" / "11_dicionario_dados" / "dicionario_dados.html").replace("\\", "/")
    mock_csv_url = "file:///" + str(SAIDA_DIR / "planejador_dw" / "08_datasets_bi" / "mock_dados_bi.csv").replace("\\", "/")
    prev_bi_url = "file:///" + str(SAIDA_DIR / "planejador_dw" / "08_datasets_bi" / "preview_painel_bi.html").replace("\\", "/")
    slides_url = "file:///" + str(SAIDA_DIR / "planejador_dw" / "08_datasets_bi" / "apresentacao_slides.html").replace("\\", "/")
    star_svg_url = "file:///" + str(SAIDA_DIR / "planejador_dw" / "11_dicionario_dados" / "diagrama_star_schema.svg").replace("\\", "/")
    odi_svg_url = "file:///" + str(SAIDA_DIR / "planejador_dw" / "09_relatorio_estrategias" / "mapa_canvas_odi.svg").replace("\\", "/")
    vw_kpi_url = "file:///" + str(SAIDA_DIR / "camada_semantica" / "vw_analiticas" / "03_vw_kpis.sql").replace("\\", "/")

    linhas = [
        "# 🎮 Projeto de Demonstração do NINHO Criado com Sucesso (`/demo`)",
        "",
        "> Um projeto completo de **Licitações & Contratos Públicos (`SAEB`)** foi simulado e gerado de ponta a ponta para você explorar na prática!",
        "",
        "### 📂 Artefatos Gerados para Você Abrir e Explorar Agora:",
        "",
        "| O que Explorar | Arquivo Gerado | O que observar nele |",
        "| :--- | :--- | :--- |",
        f"| **1. Mockup Visual do Painel BI (Novo)** | [preview_painel_bi.html]({prev_bi_url}) | Visão Executiva, **Dev Mode (`Redlines ①..⑦`)**, Tema Claro/Escuro e Download `.png` 2x |",
        f"| **2. Diagramas Star Schema & ODI SVG** | [diagrama_star_schema.svg]({star_svg_url}) / [mapa_canvas_odi.svg]({odi_svg_url}) | Desenho vetorial do modelo estrela (`1:N`) e do pacote/fluxo no Canvas ODI 12c |",
        f"| **3. Apresentação Executiva (`16:9`)** | [apresentacao_slides.html]({slides_url}) | Deck interativo de 6 slides (+ `.pptx`, `.xlsx` 3 abas e `.docx` em `08_datasets_bi/`) |",
        f"| **4. Blueprint Editável do DW** | [SIMULACAO_BLUEPRINT_DW.md]({bp_dw_url}) | Matriz De/Para com `[x]`/`[ ]`, amostra de 3 linhas + linha `-1` e Radar da IA |",
        f"| **5. Blueprint da Camada Semântica** | [SIMULACAO_BLUEPRINT_SEMANTICA.md]({bp_sem_url}) | Views em 3 camadas, catálogo `META_METRICA` e KPIs sugeridos pela IA |",
        f"| **6. Dicionário de Dados HTML** | [dicionario_dados.html]({dic_html_url}) | Página interativa com busca em tempo real, badges PK/FK e grão das tabelas |",
        f"| **7. Views de KPIs Consolidados** | [03_vw_kpis.sql]({vw_kpi_url}) | Fórmulas oficiais + KPIs do Radar (`TICKET_MEDIO_*`, `TAXA_QUALID_*`) com `NULLIF` |",
        f"| **8. Mock CSV Dinâmico para BI** | [mock_dados_bi.csv]({mock_csv_url}) | 50 linhas sintéticas das colunas reais + chaves sentinelas `-1` (`NAO INFORMADO`) |",
    ]
    linhas.append(
        formatar_rodape_proximos_passos(
            [
                ("`/onde-estou`", "Veja como a Bússola Contextual exibe o projeto em 100% (Fase 5/5)."),
                ("`/validar-entrega`", "Rode o auditor de qualidade sobre os arquivos gerados na demonstração."),
                ("`/limpar-demo`", "Quando terminar de explorar, zere tudo para começar seu projeto real."),
            ]
        )
    )
    return "\n".join(linhas)


def renderizar_catalogo(topico: str = "todos", busca: str = "") -> str:
    linhas: List[str] = []
    linhas.append("# 🧭 Central de Comandos do NINHO (`/help`)")
    linhas.append("")
    linhas.append(
        "> Digite qualquer **`/comando`** diretamente aqui no chat ou execute o comando **CLI** correspondente no terminal.\n"
        "> 💡 **Novo por aqui?** Digite **`/comecar`** para ver as 5 trilhas guiadas, **`/onde-estou`** para ver o status do projeto ou **`/duvida listar`** para consultar o Oráculo de Arquitetura!"
    )
    linhas.append("")

    topico_norm = (topico or "todos").strip().lower()
    termo_busca = (busca or "").strip().lower()

    chaves = (
        list(CATALOGO_TOPICOS.keys())
        if topico_norm in ("todos", "all", "")
        else [k for k in CATALOGO_TOPICOS if k == topico_norm]
    )

    if not chaves:
        linhas.append(
            f"⚠️ Tópico `{topico}` não encontrado. Tópicos disponíveis: `{', '.join(CATALOGO_TOPICOS.keys())}`."
        )
        return "\n".join(linhas)

    total_exibidos = 0
    for chave in chaves:
        bloco = CATALOGO_TOPICOS[chave]
        comandos_filtrados = []
        for item in bloco["comandos"]:
            if termo_busca:
                texto_item = f"{item['chat']} {item['objetivo']} {item['cli']}".lower()
                if termo_busca not in texto_item:
                    continue
            comandos_filtrados.append(item)

        if not comandos_filtrados:
            continue

        linhas.append(f"## {bloco['titulo']}")
        linhas.append(f"*{bloco['descricao']}*")
        linhas.append("")
        linhas.append("| Comando no Chat | O que Faz | Equivalente CLI (Terminal) |")
        linhas.append("| :--- | :--- | :--- |")
        for cmd in comandos_filtrados:
            linhas.append(f"| {cmd['chat']} | {cmd['objetivo']} | {cmd['cli']} |")
            total_exibidos += 1
        linhas.append("")

    if total_exibidos == 0:
        linhas.append(f"⚠️ Nenhum comando encontrado para o filtro `{busca}`.")
    else:
        linhas.append("---")
        linhas.append(
            f"💡 **Total de atalhos listados:** `{total_exibidos}` | "
            "📘 Documentação completa em [`GUIA_COMANDOS_RAPIDOS.md`](documentacao/guias/GUIA_COMANDOS_RAPIDOS.md)"
        )

    return "\n".join(linhas)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Central de Experiência Conversacional (/help, /onde-estou, /comecar, /duvida, /doctor, /demo) do NINHO."
    )
    parser.add_argument(
        "--topico",
        default="todos",
        choices=["todos", "ajuda", "simulacao", "micro", "auditoria", "dw", "semantica", "governanca", "qualidade"],
        help="Filtra os comandos do /help por tópico específico (default: todos).",
    )
    parser.add_argument(
        "--busca",
        default="",
        help="Filtra comandos do /help que contenham a palavra-chave informada.",
    )
    parser.add_argument(
        "--onboarding",
        "--comecar",
        action="store_true",
        dest="onboarding",
        help="Exibe o Guia Rápido de Boas-Vindas (/comecar) com as 5 trilhas de bolso.",
    )
    parser.add_argument(
        "--onde-estou",
        "--status",
        action="store_true",
        dest="onde_estou",
        help="Exibe a Bússola Contextual do workspace (/onde-estou) com barra de progresso e próximo passo.",
    )
    parser.add_argument(
        "--explicar",
        "--duvida",
        default="",
        dest="explicar",
        help="Aciona o Oráculo Interativo do NINHO para explicar um conceito arquitetural (use 'listar' para ver todos).",
    )
    parser.add_argument(
        "--doctor",
        action="store_true",
        help="Executa o diagnóstico de saúde do workspace e detecta arquivos fora da subpasta canônica.",
    )
    parser.add_argument(
        "--corrigir",
        action="store_true",
        help="Usado junto com --doctor para mover automaticamente arquivos fora do lugar para a subpasta correta.",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Popula e executa um projeto completo de demonstração (Playground) em 1 comando.",
    )
    parser.add_argument(
        "--limpar-demo",
        action="store_true",
        dest="limpar_demo",
        help="Remove todos os arquivos de demonstração de entrega/ e saida/.",
    )

    args = parser.parse_args()

    if args.onboarding:
        print(renderizar_onboarding())
        return 0
    if args.onde_estou:
        print(renderizar_onde_estou())
        return 0
    if args.explicar:
        print(renderizar_explicacao(args.explicar))
        return 0
    if args.doctor:
        print(executar_doctor(corrigir=args.corrigir))
        return 0
    if args.demo:
        print(executar_demo())
        return 0
    if args.limpar_demo:
        print(limpar_demo())
        return 0

    print(renderizar_catalogo(topico=args.topico, busca=args.busca))
    return 0


if __name__ == "__main__":
    sys.exit(main())
