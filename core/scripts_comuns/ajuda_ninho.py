#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
🧭 CENTRAL DE AJUDA INTERATIVA & CATÁLOGO DE COMANDOS (/help) — NINHO
================================================================================
Exibe todos os comandos rápidos do chat (/comando) e seus equivalentes CLI
organizados por tópico, permitindo filtragem por categoria ou busca textual.

Exemplos de uso:
  python core/scripts_comuns/ajuda_ninho.py
  python core/scripts_comuns/ajuda_ninho.py --topico simulacao
  python core/scripts_comuns/ajuda_ninho.py --topico micro
  python core/scripts_comuns/ajuda_ninho.py --busca indices
================================================================================
"""

import argparse
import sys
from typing import Dict, List

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


CATALOGO_TOPICOS: Dict[str, Dict] = {
    "ajuda": {
        "titulo": "🧭 0. Central de Ajuda & Status do Projeto",
        "descricao": "Comandos para listar o catálogo de atalhos ou consultar o estado atual do workspace.",
        "comandos": [
            {
                "chat": "`/help` (ou `/ajuda`, `/comandos`)",
                "objetivo": "Exibe no chat este catálogo completo de comandos organizado por tópico.",
                "cli": "`python core/scripts_comuns/ajuda_ninho.py`",
            },
            {
                "chat": "`/help <topico>`",
                "objetivo": "Filtra os comandos de um tópico específico (`simulacao`, `micro`, `auditoria`, `dw`, `semantica`, `governanca`, `qualidade`).",
                "cli": "`python core/scripts_comuns/ajuda_ninho.py --topico <topico>`",
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
                "objetivo": "Gera apenas o Guia do Analista de BI (`08_datasets_bi/GUIA_ANALISTA_BI_<PROJETO>.md`).",
                "cli": "`python core/scripts_comuns/melhorar_dw_existente.py --modo guia-bi`",
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
                "objetivo": "Audita projetos Apache Hop 2.x (`.hpl`, `.hwf`, `.json`) e extratores Python/FTPS com as heurísticas `HOP-H1` a `HOP-H8`.",
                "cli": "`python core/scripts_comuns/auditar_esteira_hop.py <pasta_hop>`",
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
                "chat": "`/iniciar-semantica`",
                "objetivo": "Gera o pacote completo da Camada Semântica (Views em 3 camadas, RLS/VPD, 8 tabelas `META_*`, validações e documento) em `saida/camada_semantica/`.",
                "cli": "`python core/scripts_comuns/modular_semantica.py --modo tudo`",
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
                "chat": "`/gerar-governanca`",
                "objetivo": "Gera os schemas/scripts das 5 coleções MongoDB padrão PRODEB (`tb_dataset`, `tb_sem_dominios`, `tb_sem_conceitos`, `tb_auditoria_eventos`, `tb_quarentena`), matriz LGPD/LAI e AWS SageMaker Catalog.",
                "cli": "Interativo via Agente (`governanca-dados-corporativa`)",
            },
        ],
    },
    "qualidade": {
        "titulo": "✅ 7. Qualidade, Diagnóstico de Erros & Empacotamento",
        "descricao": "Validação automatizada de entregas, troubleshooting de erros de banco/ETL e exportação/limpeza do workspace.",
        "comandos": [
            {
                "chat": "`/validar-entrega`",
                "objetivo": "Executa a bateria de auditoria pré-voo (`all`, `dw`, `fast-track`, `semantica`, `governanca`) e pós-geração (`saida`).",
                "cli": "`python core/scripts_comuns/validar_entrega.py {all,fast-track,saida}`",
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


def renderizar_catalogo(topico: str = "todos", busca: str = "") -> str:
    linhas: List[str] = []
    linhas.append("# 🧭 Central de Comandos do NINHO (`/help`)")
    linhas.append("")
    linhas.append(
        "> Digite qualquer **`/comando`** diretamente aqui no chat ou execute o comando **CLI** correspondente no terminal. "
        "Para filtrar por categoria, digite `/help <topico>` (`simulacao`, `micro`, `auditoria`, `dw`, `semantica`, `governanca`, `qualidade`)."
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
        description="Exibe a Central de Comandos (/help) do NINHO organizada por tópicos."
    )
    parser.add_argument(
        "--topico",
        default="todos",
        choices=["todos", "ajuda", "simulacao", "micro", "auditoria", "dw", "semantica", "governanca", "qualidade"],
        help="Filtra os comandos por tópico específico (default: todos).",
    )
    parser.add_argument(
        "--busca",
        default="",
        help="Filtra comandos que contenham a palavra-chave informada.",
    )
    args = parser.parse_args()
    print(renderizar_catalogo(topico=args.topico, busca=args.busca))
    return 0


if __name__ == "__main__":
    sys.exit(main())

