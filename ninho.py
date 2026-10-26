#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
🦅 NINHO CLI — DISPATCHER UNIFICADO DE COMANDOS (TERMINAL & SLASH COMMANDS)
================================================================================
Transforma todos os comandos "/<comando>" da plataforma NINHO em comandos
executáveis reais e determinísticos, tanto via terminal quanto via Skills
nativas da IDE (`.agents/skills/<comando>/SKILL.md`).

Exemplos de uso:
  python ninho.py ajuda
  python ninho.py /help simulacao
  python ninho.py onde-estou
  python ninho.py comecar
  python ninho.py duvida estrategia-carga
  python ninho.py doctor
  python ninho.py demo
  python ninho.py limpar-demo
  python ninho.py simular-dw
  python ninho.py simular-semantica
  python ninho.py simular-projeto
  python ninho.py executar-simulacao
  python ninho.py melhorar-dw-existente
  python ninho.py auditar-mapa-odi <caminho_xml_ou_pasta>
  python ninho.py auditar-hop <pasta_hop>
  python ninho.py inspecionar-pbix <arquivo.pbix>
  python ninho.py inspecionar-fontes
  python ninho.py inspecionar-governanca
  python ninho.py validar-entrega
  python ninho.py testar-ninho
  python ninho.py empacotar-projeto
================================================================================
"""

import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = ROOT_DIR / "core" / "scripts_comuns"
SKILLS_DIR = ROOT_DIR / ".agents" / "skills"

# As 10 skills arquiteturais de domínio NUNCA devem ser sobrescritas pelo instalador de atalhos
SKILLS_ARQUITETURAIS_PROTEGIDAS = {
    "planejador-dw-oracle",
    "gerador-etl-hop",
    "gerador-consultas-odi",
    "extrator-api-python",
    "extrator-ftps-lote-hop",
    "camada-semantica-oracle",
    "seguranca-rls-oracle",
    "governanca-dados-corporativa",
    "engenharia-reversa-pbix",
    "validador-qualidade-entrega",
}

# Comandos que colidem com comandos reservados de IDEs (Antigravity, Claude Code, Cursor)
COMANDOS_RESERVADOS_IDE = {"help", "status"}

# Descrições canônicas para as Skills de comando (/comando) no menu da IDE
DESCRICOES_SKILLS_SLASH: Dict[str, str] = {
    "instalar-comandos": "Registra e sincroniza todos os comandos /<comando> do NINHO como Skills nativas (.agents/skills/) na IDE.",
    "ajuda": "Exibe o catálogo completo de comandos da plataforma NINHO organizado por tópico (use /ajuda para não colidir com o /help nativo da IDE).",
    "onde-estou": "Exibe a Bússola Contextual do projeto com barra de progresso, arquivos detectados em entrega/ e saida/ e o próximo passo recomendado.",
    "comecar": "Exibe o Assistente de Boas-Vindas (Onboarding) com as 5 trilhas guiadas de 3 passos para iniciar um projeto no NINHO.",
    "duvida": "Consulta o Oráculo Arquitetural sobre conceitos do NINHO (estrategia-carga, scd, linha-default, camadas-views, arquitetura-etl, gate-governanca, simulacao, fast-track, rls).",
    "doctor": "Diagnostica a saúde das pastas de entrega/, detecta arquivos soltos fora da subpasta canônica e os organiza automaticamente.",
    "demo": "Cria e executa um Projeto Playground completo (DDL + Simulação + DW + Camada Semântica + Dicionário HTML + Mock BI) em 1 comando.",
    "limpar-demo": "Remove todos os artefatos de demonstração gerados pelo comando /demo, deixando entrega/ e saida/ limpos.",
    "simular-dw": "Gera a Blueprint 100% editável de simulação do Data Warehouse (entrega/planejador_dw/SIMULACAO_BLUEPRINT_DW.md).",
    "simular-semantica": "Gera a Blueprint 100% editável de simulação da Camada Semântica (entrega/camada_semantica/SIMULACAO_BLUEPRINT_SEMANTICA.md).",
    "simular-projeto": "Gera simultaneamente as Blueprints editáveis de simulação do Planejador DW e da Camada Semântica.",
    "executar-simulacao": "Lê as edições feitas nas Blueprints aprovadas e executa a geração física dos scripts em saida/planejador_dw/ e saida/camada_semantica/.",
    "melhorar-dw-existente": "Executa o Raio-X não-destrutivo de um DW já construído e gera patches de comentários, dicionário HTML, índices, linha -1 e constraints.",
    "gerar-guia-bi": "Gera o Guia Completo de Implementação no Power BI (Star Schema, DAX, Indicadores/Metas de planilhas .xlsx/.ods, Sync Slicers, Mockup SVG/HTML/PNG 2x, Apresentação .pptx e Word .docx).",
    "gerar-mockup-bi": "Gera o Mockup Visual Full HD do Painel Power BI (mockup_painel_bi.svg, mockup_painel_bi_devmode.svg com Redlines DAX ①..⑦ e preview_painel_bi.html com exportação PNG 2x).",
    "validar-medidas-bi": "Executa a Prova Real Pós-Carga das medidas DAX do Guia do Analista de BI contra amostras de DIM_* e FATO_*, corrige medidas parcialmente corretas e popula o Mockup Visual com os valores reais.",
    "gerar-apresentacao": "Gera a Apresentação Executiva do projeto em PowerPoint nativo (.pptx) e Deck HTML 16:9 (apresentacao_slides.html).",
    "exportar-docx": "Exporta os Guias do Analista de BI e de Estratégias ODI 12c em documentos Microsoft Word corporativos (.docx).",
    "exportar-pdf": "Exporta os Guias do Analista de BI e de Estratégias ODI 12c em documentos PDF 1.4 oficiais (.pdf) prontos para SEI/Ofícios.",
    "gerar-comentarios": "Gera apenas scripts não-destrutivos de COMMENT ON TABLE/COLUMN + Dicionário de Dados HTML interativo.",
    "gerar-dicionario": "Gera exclusivamente o Dicionário de Dados HTML interativo (11_dicionario_dados/dicionario_dados.html).",
    "gerar-indices": "Gera apenas índices de tuning (Bitmap/B-Tree) + procedures PRC_PRE_CARGA_FATO e PRC_POS_CARGA_FATO.",
    "gerar-linha-default": "Gera apenas o script idempotente MERGE INTO do registro sentinela -1 ('Não Informado') nas dimensões.",
    "gerar-constraints": "Gera apenas constraints PK/FK não-destrutivas (ENABLE/RELY NOVALIDATE) sobre DW existente.",
    "gerar-testes-dw": "Gera a suíte SQL de auditoria de integridade pós-carga adaptada às tabelas do DW.",
    "gerar-selects-odi": "Gera as tabelas auxiliares ODI_DIM_* e as consultas analíticas SQL (SCD2 e Fato) para o ODI 12c.",
    "gerar-guia-odi": "Gera os guias modulares passo a passo de implementação no Canvas do ODI 12c.",
    "gerar-mock-bi": "Gera massa CSV sintética relacionalmente íntegra (~3% de chaves -1) para homologação de dashboards no Power BI.",
    "gerar-views-semantica": "Gera as 3 camadas de Views da Camada Semântica (VW_DIM, VW_EVENTO, VW_KPI) sobre o DW.",
    "gerar-catalogo-meta": "Gera o DDL e scripts MERGE INTO idempotentes das 8 tabelas META_* da Camada Semântica.",
    "gerar-rls": "Gera o script de segurança Row-Level Security (RLS / VPD Oracle via DBMS_RLS) para a Camada Semântica.",
    "iniciar-semantica": "Executa a geração completa da Camada Semântica (Views + Catálogo META_* + RLS + Validações).",
    "concluir-dw": "Faz o handoff automático dos DDLs e relatórios do Planejador de DW para entrega/camada_semantica/.",
    "inspecionar-fontes": "Inspeciona DDLs SQL/CSV depositados em entrega/planejador_dw/ddl/, extrai metadados e gera sugestões analíticas.",
    "inspecionar-pbix": "Descompacta e audita arquivos .pbix do Power BI, extraindo filtros AST/DAX e executando as heurísticas PBIX-H1 a PBIX-H5.",
    "auditar-mapa-odi": "Executa o auditor de tuning e qualidade dimensional (heurísticas H1 a H9) em XMLs ou pastas do ODI 12c.",
    "auditar-hop": "Audita projetos Apache Hop 2.x (.hpl, .hwf, .json) e extratores Python/FTPS aplicando as heurísticas HOP-H1..H8, hop-lint oficial e THREAT_MODEL.md (HOP-SEC-01/02).",
    "migrar-kettle-hop": "Migra projetos legados do Pentaho Kettle (.ktr, .kjb, shared.xml) para Apache Hop 2.x (.hpl, .hwf, metadata/rdbms/*.json e diagrama SVG).",
    "gerar-pacote-hop": "Gera um pacote completo Apache Hop 2.x (wf_*.hwf, ppl_*.hpl com TableOutput ou OraBulkLoader, hop-lint.yml, hop-pwd.json, diagrama_esteira_hop.svg e DOCUMENTACAO_HOP.md).",
    "inspecionar-governanca": "Executa a auditoria do Gate 0.5 sobre planilhas .xlsx e amostras .csv de governança de dados.",
    "validar-entrega": "Executa a bateria de auditoria pré-voo dos insumos e validação pós-geração da pasta saida/.",
    "testar-ninho": "Executa a suíte automatizada de testes End-to-End (E2E) em todos os motores do NINHO e limpa o workspace ao final.",
    "empacotar-projeto": "Verifica o status do projeto, exporta a entrega completa em .zip ou limpa o workspace para um novo projeto.",
}

# Mapa determinístico: comando -> (script, args_base, descricao)
ROTAS_COMANDOS: Dict[str, Tuple[str, List[str], str]] = {
    # 0. Setup / Instalador de Comandos e UX
    "instalar-comandos": (
        "__interno_instalar__",
        [],
        "Registra e sincroniza todos os comandos /<comando> como Skills nativas na IDE",
    ),
    "setup": (
        "__interno_instalar__",
        [],
        "Alias para 'instalar-comandos' (configuração inicial dos atalhos de chat)",
    ),
    "configurar": (
        "__interno_instalar__",
        [],
        "Alias para 'instalar-comandos' (configuração inicial dos atalhos de chat)",
    ),
    "sincronizar-comandos": (
        "__interno_instalar__",
        [],
        "Alias para 'instalar-comandos' (sincroniza .agents/skills/<cmd>/SKILL.md)",
    ),
    "ajuda": ("ajuda_ninho.py", [], "Exibe o catálogo completo de comandos do NINHO"),
    "help": ("ajuda_ninho.py", [], "Alias para 'ajuda' (catálogo de comandos)"),
    "comandos": ("ajuda_ninho.py", [], "Alias para 'ajuda' (catálogo de comandos)"),
    "ninho-help": ("ajuda_ninho.py", [], "Alias seguro para ajuda sem colidir com /help da IDE"),
    "onde-estou": ("ajuda_ninho.py", ["--onde-estou"], "Bússola contextual do projeto e próximo passo"),
    "status": ("ajuda_ninho.py", ["--onde-estou"], "Alias para 'onde-estou'"),
    "comecar": ("ajuda_ninho.py", ["--onboarding"], "Trilhas guiadas de 3 passos para iniciar um projeto"),
    "onboarding": ("ajuda_ninho.py", ["--onboarding"], "Alias para 'comecar'"),
    "duvida": ("ajuda_ninho.py", ["--explicar"], "Oráculo arquitetural interativo (ex: duvida scd)"),
    "explicar": ("ajuda_ninho.py", ["--explicar"], "Alias para 'duvida'"),
    "doctor": ("ajuda_ninho.py", ["--doctor", "--corrigir"], "Audita e organiza arquivos soltos em entrega/"),
    "demo": ("ajuda_ninho.py", ["--demo"], "Executa projeto Playground completo em 1 comando"),
    "limpar-demo": ("ajuda_ninho.py", ["--limpar-demo"], "Remove todos os artefatos gerados pelo modo demo"),
    # 1. Simulação Ponta a Ponta & Blueprint Editável
    "simular-dw": ("simular_projeto.py", ["--modulo", "dw", "--acao", "simular"], "Gera Blueprint editável do DW"),
    "gerar-blueprint": ("simular_projeto.py", ["--modulo", "dw", "--acao", "simular"], "Alias para 'simular-dw'"),
    "simular-semantica": (
        "simular_projeto.py",
        ["--modulo", "semantica", "--acao", "simular"],
        "Gera Blueprint editável da Camada Semântica",
    ),
    "simular-projeto": (
        "simular_projeto.py",
        ["--modulo", "ambos", "--acao", "simular"],
        "Gera Blueprints editáveis de DW e Semântica simultaneamente",
    ),
    "executar-simulacao": (
        "simular_projeto.py",
        ["--modulo", "ambos", "--acao", "executar"],
        "Executa geração física a partir das Blueprints aprovadas",
    ),
    "executar-simulacao-dw": (
        "simular_projeto.py",
        ["--modulo", "dw", "--acao", "executar"],
        "Executa geração física apenas do DW a partir da Blueprint aprovada",
    ),
    "aprovar-blueprint": (
        "simular_projeto.py",
        ["--modulo", "dw", "--acao", "executar"],
        "Alias para 'executar-simulacao-dw'",
    ),
    "executar-simulacao-semantica": (
        "simular_projeto.py",
        ["--modulo", "semantica", "--acao", "executar"],
        "Executa geração física apenas da Camada Semântica",
    ),
    # 2. Micro-Processos Independentes & Fast-Track (DW, ODI e Semântica)
    "melhorar-dw-existente": (
        "melhorar_dw_existente.py",
        ["--modo", "tudo"],
        "Raio-X não-destrutivo completo de DW existente + geração de patches",
    ),
    "gerar-comentarios": (
        "melhorar_dw_existente.py",
        ["--modo", "comentarios"],
        "Gera apenas COMMENT ON TABLE/COLUMN + Dicionário HTML",
    ),
    "gerar-dicionario": (
        "melhorar_dw_existente.py",
        ["--modo", "dicionario"],
        "Gera exclusivamente o Dicionário de Dados HTML interativo",
    ),
    "gerar-indices": (
        "melhorar_dw_existente.py",
        ["--modo", "indices"],
        "Gera apenas índices de tuning (Bitmap/B-Tree) + PRC_POS_CARGA_FATO",
    ),
    "gerar-linha-default": (
        "melhorar_dw_existente.py",
        ["--modo", "linha-default"],
        "Gera apenas script MERGE INTO do registro sentinela -1",
    ),
    "gerar-constraints": (
        "melhorar_dw_existente.py",
        ["--modo", "constraints"],
        "Gera apenas constraints PK/FK não-destrutivas (ENABLE/RELY NOVALIDATE)",
    ),
    "gerar-testes-dw": (
        "melhorar_dw_existente.py",
        ["--modo", "testes"],
        "Gera suíte SQL de auditoria de integridade pós-carga",
    ),
    "gerar-guia-bi": (
        "melhorar_dw_existente.py",
        ["--modo", "guia-bi"],
        "Gera Guia do Analista de BI (.md) + Mockup SVG/HTML/PNG 2x + Planilha .xlsx",
    ),
    "gerar-mockup-bi": (
        "melhorar_dw_existente.py",
        ["--modo", "mockup-bi"],
        "Gera Mockup Visual Full HD do Painel BI (SVG + Dev Mode Redlines ①..⑦ + HTML/PNG 2x)",
    ),
    "validar-medidas-bi": (
        "melhorar_dw_existente.py",
        ["--modo", "validar-medidas-bi"],
        "Prova Real Pós-Carga das medidas DAX em amostras DIM/FATO + Mockup populado",
    ),
    "provar-medidas-bi": (
        "melhorar_dw_existente.py",
        ["--modo", "validar-medidas-bi"],
        "Alias para 'validar-medidas-bi'",
    ),
    "gerar-apresentacao": (
        "melhorar_dw_existente.py",
        ["--modo", "apresentacao"],
        "Gera Apresentação Executiva (.pptx + apresentacao_slides.html 16:9)",
    ),
    "exportar-docx": (
        "melhorar_dw_existente.py",
        ["--modo", "exportar-docx"],
        "Exporta Guias em formato Microsoft Word corporativo (.docx)",
    ),
    "exportar-pdf": (
        "melhorar_dw_existente.py",
        ["--modo", "exportar-pdf"],
        "Exporta Guias e Relatórios em formato PDF 1.4 corporativo (.pdf) pronto para SEI/Ofícios",
    ),
    "gerar-selects-odi": (
        "melhorar_dw_existente.py",
        ["--modo", "selects-odi"],
        "Gera tabelas ODI_DIM_* e consultas SQL de carga ODI",
    ),
    "gerar-guia-odi": (
        "melhorar_dw_existente.py",
        ["--modo", "guia-odi"],
        "Gera Guia passo a passo de implementação no Canvas do ODI 12c",
    ),
    "gerar-mock-bi": (
        "gerar_mock_dados.py",
        ["--linhas", "150"],
        "Gera CSV de dados sintéticos dinâmicos para BI com ~3% de chaves -1",
    ),
    "gerar-views-semantica": (
        "modular_semantica.py",
        ["--modo", "views-semantica"],
        "Gera as 3 camadas de Views da Camada Semântica (VW_DIM, VW_EVENTO, VW_KPI)",
    ),
    "gerar-views-dim": (
        "modular_semantica.py",
        ["--modo", "views-dim"],
        "Gera apenas Camada 1 (VW_DIM_*_ATUAL)",
    ),
    "gerar-views-evento": (
        "modular_semantica.py",
        ["--modo", "views-evento"],
        "Gera apenas Camada 2 (VW_EVENTO_*)",
    ),
    "gerar-views-kpi": (
        "modular_semantica.py",
        ["--modo", "views-kpi"],
        "Gera apenas Camada 3 (VW_KPI_*)",
    ),
    "gerar-catalogo-meta": (
        "modular_semantica.py",
        ["--modo", "catalogo-meta"],
        "Gera DDL e MERGE INTO idempotente das 8 tabelas META_*",
    ),
    "gerar-rls": (
        "modular_semantica.py",
        ["--modo", "rls"],
        "Gera script de segurança Row-Level Security / VPD Oracle",
    ),
    "gerar-rls-semantica": (
        "modular_semantica.py",
        ["--modo", "rls"],
        "Alias para 'gerar-rls'",
    ),
    "iniciar-semantica": (
        "modular_semantica.py",
        ["--modo", "tudo"],
        "Gera pacote completo da Camada Semântica em saida/camada_semantica/",
    ),
    "concluir-dw": (
        "transicionar_dw_para_semantica.py",
        [],
        "Transfere artefatos do DW para entrega/camada_semantica/",
    ),
    "transicionar-semantica": (
        "transicionar_dw_para_semantica.py",
        [],
        "Alias para 'concluir-dw'",
    ),
    # 3. Inspeção de Fontes, Engenharia Reversa & Auditoria Técnica
    "inspecionar-fontes": (
        "inspecionar_ddl_origem.py",
        [],
        "Audita DDLs/CSVs de origem e gera sugestões analíticas",
    ),
    "inspecionar-pbix": (
        "inspecionar_pbix.py",
        [],
        "Desconstrói arquivo .pbix do Power BI e audita anti-padrões PBIX-H1..H5",
    ),
    "auditar-mapa-odi": (
        "auditar_mapa_odi.py",
        [],
        "Audita XMLs ou pastas do ODI 12c aplicando heurísticas H1 a H9",
    ),
    "auditar-hop": (
        "auditar_esteira_hop.py",
        [],
        "Audita projetos Apache Hop 2.x (.hpl, .hwf, .json) com HOP-H1..H8, hop-lint e THREAT_MODEL.md",
    ),
    "migrar-kettle-hop": (
        "auditar_esteira_hop.py",
        ["--migrar-kettle", "saida/planejador_dw/06_pipelines_hop"],
        "Migra projetos Pentaho Kettle (.ktr/.kjb/shared.xml) para Apache Hop 2.x (.hpl/.hwf + metadata + SVG)",
    ),
    "gerar-pacote-hop": (
        "auditar_esteira_hop.py",
        ["--gerar-pacote-hop"],
        "Gera pacote completo Apache Hop 2.x (wf_*.hwf, ppl_*.hpl, hop-lint.yml, hop-pwd.json, SVG e DOC)",
    ),
    "inspecionar-governanca": (
        "inspecionar_insumos_governanca.py",
        [],
        "Executa Gate 0.5 sobre planilhas .xlsx e amostras .csv de governança",
    ),
    # 4. Qualidade, Testes E2E, Consultoria Arquitetural e Empacotamento
    "desafiar-grao": (
        "ajuda_ninho.py",
        ["--explicar", "estrategia-carga"],
        "Consulta diretrizes arquiteturais de granularidade e estratégia de carga",
    ),
    "classificar-scd": (
        "ajuda_ninho.py",
        ["--explicar", "scd"],
        "Consulta diretrizes de classificação SCD Tipo 1 e Tipo 2",
    ),
    "definir-estrategia-carga": (
        "ajuda_ninho.py",
        ["--explicar", "estrategia-carga"],
        "Compara Estratégia A (Truncate & Load + Bitmap) vs Estratégia B (MERGE + B-Tree)",
    ),
    "gerar-governanca": (
        "inspecionar_insumos_governanca.py",
        [],
        "Executa Gate 0.5 e gera artefatos MongoDB PRODEB e matriz LGPD/LAI",
    ),
    "diagnosticar-erro-carga": (
        "ajuda_ninho.py",
        ["--explicar", "arquitetura-etl"],
        "Exibe arquitetura ETL e roteiro de diagnóstico de falhas de carga",
    ),
    "validar-entrega": (
        "validar_entrega.py",
        [],
        "Executa auditoria de qualidade pré-voo ou pós-geração (all, fast-track, saida)",
    ),
    "auditar-ddl": (
        "validar_entrega.py",
        ["saida"],
        "Audita sintaxe Oracle, linha -1, sequences e índices em saida/",
    ),
    "testar-ninho": (
        "testar_ninho.py",
        [],
        "Executa a suíte oficial automatizada de testes E2E (T01 a T11)",
    ),
    "empacotar-projeto": (
        "gerenciar_projeto.py",
        [],
        "Gerencia status, exportação .zip ou limpeza do workspace",
    ),
}


def _gerar_conteudo_skill_comando(cmd: str, descricao: str) -> str:
    return (
        f"---\n"
        f"name: {cmd}\n"
        f"description: {descricao}\n"
        f"---\n\n"
        f"# /{cmd}\n\n"
        f"{descricao}\n\n"
        f"## Execução Determinística\n\n"
        f"Ao receber o comando /{cmd} (ou pedido equivalente), execute imediatamente no terminal via `run_command`:\n\n"
        f"```bash\n"
        f"python ninho.py {cmd}\n"
        f"```\n\n"
        f"Se o usuário informar argumentos adicionais (ex.: tópico, tema, caminho de arquivo ou flag), "
        f"repasse-os ao final do comando python ninho.py {cmd} <argumentos> e apresente o resultado de forma clara no chat.\n"
    )


def instalar_comandos_chat(extra_args: List[str]) -> int:
    incluir_todos = "--todos" in extra_args or "--all" in extra_args
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)

    alvos: Dict[str, str] = dict(DESCRICOES_SKILLS_SLASH)
    if incluir_todos:
        for cmd, (_, _, desc) in ROTAS_COMANDOS.items():
            if cmd in COMANDOS_RESERVADOS_IDE or cmd in SKILLS_ARQUITETURAIS_PROTEGIDAS:
                continue
            if cmd not in alvos and not desc.startswith("Alias para"):
                alvos[cmd] = desc

    criadas: List[str] = []
    atualizadas: List[str] = []
    sincronizadas: List[str] = []

    for cmd, desc in alvos.items():
        if cmd in SKILLS_ARQUITETURAIS_PROTEGIDAS or cmd in COMANDOS_RESERVADOS_IDE:
            continue
        pasta_skill = SKILLS_DIR / cmd
        arq_skill = pasta_skill / "SKILL.md"
        novo_conteudo = _gerar_conteudo_skill_comando(cmd, desc)

        if not arq_skill.exists():
            pasta_skill.mkdir(parents=True, exist_ok=True)
            arq_skill.write_text(novo_conteudo, encoding="utf-8")
            criadas.append(cmd)
        else:
            atual = arq_skill.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")
            if atual.strip() != novo_conteudo.strip():
                arq_skill.write_text(novo_conteudo, encoding="utf-8")
                atualizadas.append(cmd)
            else:
                sincronizadas.append(cmd)

    protegidas_ok = sum(1 for s in SKILLS_ARQUITETURAIS_PROTEGIDAS if (SKILLS_DIR / s / "SKILL.md").exists())

    print("=" * 84)
    print("⚙️  NINHO — INSTALADOR & SINCRONIZADOR DE COMANDOS DE CHAT (/comando)")
    print("=" * 84)
    print(f"  📁 Diretório de Skills da IDE : {SKILLS_DIR}")
    print(f"  🛡️  Skills Arquiteturais Core  : {protegidas_ok}/{len(SKILLS_ARQUITETURAIS_PROTEGIDAS)} protegidas e intactas")
    print(f"  ✨ Skills de Comando Criadas  : {len(criadas)}")
    print(f"  🔄 Skills de Comando Atualiz. : {len(atualizadas)}")
    print(f"  ✅ Skills Já Sincronizadas    : {len(sincronizadas)}")
    print(f"  🚀 Total de Rotas no ninho.py : {len(ROTAS_COMANDOS)} comandos disponíveis")
    print("-" * 84)
    if criadas:
        print("  Novos atalhos registrados: " + ", ".join(f"/{c}" for c in criadas))
    print("  Dica: Digite '/' no chat da IDE para usar o autocompletar dos comandos (ex: /comecar, /ajuda, /onde-estou).")
    print("        Para instalar também todos os micro-comandos no menu '/', use: python ninho.py instalar-comandos --todos")
    print("=" * 84)
    return 0


def main() -> int:
    args = sys.argv[1:]
    if not args:
        # Sem argumentos, exibe o catálogo de ajuda
        cmd_script = SCRIPTS_DIR / "ajuda_ninho.py"
        return subprocess.call([sys.executable, str(cmd_script)], cwd=str(ROOT_DIR))

    raw_cmd = args[0].strip().lstrip("/").lower()
    extra_args = args[1:]

    if raw_cmd in ("-h", "--help"):
        cmd_script = SCRIPTS_DIR / "ajuda_ninho.py"
        return subprocess.call([sys.executable, str(cmd_script)], cwd=str(ROOT_DIR))

    if raw_cmd not in ROTAS_COMANDOS:
        print(f"[ERRO] Comando desconhecido: '{args[0]}'")
        print("Execute 'python ninho.py ajuda' para listar todos os comandos disponíveis.")
        return 1

    script_name, base_args, _ = ROTAS_COMANDOS[raw_cmd]
    if script_name == "__interno_instalar__":
        return instalar_comandos_chat(extra_args)

    script_path = SCRIPTS_DIR / script_name

    # Ajustes inteligentes de argumentos posicionais para comandos amigáveis
    final_args = list(base_args)
    if raw_cmd in ("ajuda", "help", "comandos", "ninho-help") and extra_args:
        if not extra_args[0].startswith("-"):
            final_args.extend(["--topico", extra_args[0]])
            final_args.extend(extra_args[1:])
        else:
            final_args.extend(extra_args)
    elif raw_cmd in ("duvida", "explicar"):
        if not extra_args:
            final_args.append("listar")
        else:
            final_args.extend(extra_args)
    elif raw_cmd == "validar-entrega":
        if not extra_args:
            final_args.append("all")
        else:
            final_args.extend(extra_args)
    elif raw_cmd == "empacotar-projeto":
        if not extra_args:
            final_args.append("--status")
        else:
            final_args.extend(extra_args)
    else:
        final_args.extend(extra_args)

    return subprocess.call([sys.executable, str(script_path)] + final_args, cwd=str(ROOT_DIR))


if __name__ == "__main__":
    sys.exit(main())
