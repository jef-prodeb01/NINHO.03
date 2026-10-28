#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Motor Fast-Track de Melhoria Pontual para DW Oracle Já Construído (Sem Alterar Carga)
Plataforma NINHO — Funcionalidades Rápidas (Quick Wins / Brownfield DW)

Quando o Engenheiro de Dados já construiu o DW (DIM_*, FATO_*, STG_*) e não vai
mexer na esteira de carga (ODI / Hop / Python), este utilitário lê o DDL existente
e gera apenas os ajustes cirúrgicos solicitados, sem exigir o fluxo completo do
INTAKE_DW.md e sem recriar tabelas (zero DROP/CREATE destrutivo):

Modos de Operação (--modo):
  1. comentarios (/gerar-comentarios):
     - Gera scripts SQL não-destrutivos de COMMENT ON TABLE (com grão explícito) e
       COMMENT ON COLUMN para todas as tabelas e colunas do DDL.
     - Gera o Dicionário de Dados interativo em HTML (11_dicionario_dados/dicionario_dados.html).
  2. indices (/gerar-indices):
     - Analisa os índices já existentes no DDL e gera apenas os índices faltantes:
       * Fatos: BITMAP INDEX (Estratégia A) ou B-TREE COMPRESS 1 (Estratégia B) em todas as FKs,
         com PARALLEL 4 NOLOGGING -> ALTER INDEX NOPARALLEL LOGGING + DBMS_STATS.
       * Dimensões: B-TREE INDEX na PK (se ausente), Lookup SCD2 composto (Chave Natural + Vigência)
         e colunas de filtro, garantindo zero Bitmap em Dimensões (prevenção de ORA-00060).
     - Gera a procedure PRC_PRE_CARGA_FATO e PRC_POS_CARGA_FATO (05_procedimentos_manutencao/).
  3. patch (/melhorar-dw-existente) ou tudo:
     - Executa o Raio-X completo do DDL existente (DIAGNOSTICO_MELHORIAS_DW_EXISTENTE.md).
     - Gera scripts não-destrutivos de evolução (ALTER TABLE ENABLE NOVALIDATE para PKs/FKs
       faltantes + MERGE idempotente do registro padrão -1 'NAO INFORMADO' adaptado às colunas
       NOT NULL e tamanhos de cada DIM_*).
     - Inclui Comentários, Dicionário HTML, Índices, PRC_POS_CARGA_FATO, Testes de Integridade
       (10_testes_integridade/) e Guia do Analista de BI com medidas DAX (08_datasets_bi/).

Uso:
    python core/scripts_comuns/melhorar_dw_existente.py --modo comentarios
    python core/scripts_comuns/melhorar_dw_existente.py --modo indices --estrategia A
    python core/scripts_comuns/melhorar_dw_existente.py --modo patch
    python core/scripts_comuns/melhorar_dw_existente.py --caminho entrega/planejador_dw/ddl/meu_dw.sql --modo tudo
"""

import logging as _logging_ninho

_LOG = _logging_ninho.getLogger("ninho.melhorar_dw_existente")

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ninho_core.guia_bi import (  # noqa: E402,F401 — fachada de compatibilidade
    _col_letter_to_idx,
    carregar_indicadores_negocio_entrega,
    construir_guia_bi_rapido,
)
from ninho_core.odi import (  # noqa: E402,F401 — fachada de compatibilidade
    abreviar_identificador_odi,
    construir_guias_odi_modulares,
    construir_scripts_odi,
    derivar_sigla_curta_odi,
    validar_tamanho_identificador_odi,
)
from ninho_core.dw_patches import (  # noqa: E402,F401 — fachada de compatibilidade
    construir_dicionario_html,
    construir_patches_ajustes_nao_destrutivos,
    construir_relatorio_diagnostico,
    construir_script_comentarios,
    construir_script_controle_carga_eta,
    construir_script_linha_default,
    construir_scripts_indices,
    construir_testes_integridade,
)
from ninho_core.dw_modelo import (  # noqa: E402,F401 — fachada de compatibilidade
    COLUNAS_PADRAO_CONHECIDAS,
    PREFIXOS_SEMANTICOS,
    _eh_nk_textual,
    _fato_possui_sk_propria,
    _obter_nk_dim,
    _obter_sk_dim,
    classificar_tabela_dw,
    coluna_ja_indexada,
    extrair_schema_e_projeto,
    gerar_comentario_coluna,
    gerar_comentario_tabela,
    gerar_valor_default_menos_um,
    humanizar_identificador,
    identificar_fks_fato,
)
from ninho_core.diagramas import gerar_diagrama_star_schema_svg, gerar_mapa_canvas_odi_svg  # noqa: E402
from ninho_core.mockup_bi import gerar_mockup_painel_bi_svg, gerar_preview_painel_bi_html  # noqa: E402
from ninho_core.office import (  # noqa: E402
    exportar_markdown_para_docx,
    gerar_apresentacao_executiva,
    gerar_planilha_indicadores_xlsx,
)
from ninho_core.pdf import exportar_markdown_para_pdf  # noqa: E402
from ninho_core.prova_dax import avaliar_medidas_guia_bi_amostra  # noqa: E402

_TEM_ARTEFATOS_VISUAIS = True

# Configura encoding UTF-8 no Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception as _exc:
        _LOG.debug("Exceção tratada (melhorar_dw_existente.py:99): %r", _exc)

from ninho_core.console import VERDE, AMARELO, VERMELHO, CIANO, NEGRITO, RESET  # noqa: E402
from ninho_core.paths import get_base_dir  # noqa: E402


# Importa o parser determinístico de DDL do módulo irmão
sys.path.insert(0, str(Path(__file__).resolve().parent))
from inspecionar_ddl_origem import parse_ddl_text, ler_texto_sql  # noqa: E402


# Dicionário semântico de prefixos corporativos para geração inteligente de comentários

def executar_melhoria_rapida(
    caminho_ddl: Path,
    modo: str = "tudo",
    estrategia: str = "A",
    schema_cli: str = None,
    projeto_cli: str = None,
    ts_idx_cli: str = None,
    caminho_amostras: Path = None,
    incluir_extras: bool = False,
) -> dict:
    base_dir = get_base_dir()
    saida_dw = base_dir / "saida" / "planejador_dw"

    if caminho_ddl.is_file():
        arquivos_sql = [caminho_ddl]
    elif caminho_ddl.is_dir():
        arquivos_sql = sorted([
            f for f in caminho_ddl.rglob("*")
            if f.is_file() and f.suffix.lower() in (".sql", ".txt", ".ddl", ".csv") and f.name.lower() != "readme.md"
        ])
    else:
        arquivos_sql = []

    if not arquivos_sql:
        print(f"{VERMELHO}[ERRO] Nenhum arquivo DDL (.sql/.txt/.ddl) encontrado em: {caminho_ddl}{RESET}")
        print(f"{AMARELO}Dica: Deposite o DDL do seu DW já construído em 'entrega/planejador_dw/ddl/' ou informe '--caminho <arquivo.sql>'.{RESET}")
        return {"erros": 1, "arquivos_gerados": []}

    tabelas = []
    for arq in arquivos_sql:
        sql_txt = ler_texto_sql(arq)
        tabs_arq = parse_ddl_text(sql_txt, arq.name)
        tabelas.extend(tabs_arq)

    if not tabelas:
        print(f"{VERMELHO}[ERRO] Nenhuma instrução CREATE TABLE encontrada nos arquivos lidos ({len(arquivos_sql)} arquivo(s)).{RESET}")
        return {"erros": 1, "arquivos_gerados": []}

    schema, projeto, _ts_dados, ts_idx_intake = extrair_schema_e_projeto(tabelas, schema_cli, projeto_cli)
    ts_idx = ts_idx_cli or ts_idx_intake

    tabelas_classificadas = [(t, classificar_tabela_dw(t)) for t in tabelas]
    dims = [t for t, c in tabelas_classificadas if c == "DIM"]
    fatos = [t for t, c in tabelas_classificadas if c == "FATO"]
    stgs = [t for t, c in tabelas_classificadas if c not in ("DIM", "FATO")]

    print(f"\n{CIANO}{NEGRITO}{'=' * 72}{RESET}")
    print(f"{CIANO}{NEGRITO}  ⚡ NINHO MICRO-PROCESSO / FAST-TRACK DE DW ({modo.upper()}){RESET}")
    print(f"{CIANO}{NEGRITO}{'=' * 72}{RESET}")
    print(f"  • Projeto / Schema : {NEGRITO}{projeto}{RESET} ({schema})")
    print(f"  • Tabelas Lidas    : {len(tabelas)} ({len(dims)} Dimensão(ões), {len(fatos)} Fato(s), {len(stgs)} Staging/Outras)")
    print(f"  • Modo Selecionado : {NEGRITO}{modo.upper()}{RESET}\n")

    arquivos_gerados = []
    modo_norm = modo.lower().strip()

    gerar_comm = modo_norm in ("comentarios", "comentario", "patch", "melhorias", "tudo", "all")
    gerar_dic = modo_norm in ("dicionario", "comentarios", "comentario", "patch", "melhorias", "tudo", "all")
    gerar_idx = modo_norm in ("indices", "indice", "index", "patch", "melhorias", "tudo", "all")
    gerar_linha_def = modo_norm in ("linha-default", "patch", "melhorias", "ajustes", "tudo", "all")
    gerar_constraints = modo_norm in ("constraints", "patch", "melhorias", "ajustes", "tudo", "all")
    gerar_testes = modo_norm in ("testes", "patch", "melhorias", "ajustes", "tudo", "all")
    gerar_guia_bi = modo_norm in (
        "guia-bi",
        "mockup-bi",
        "validar-medidas-bi",
        "apresentacao",
        "exportar-docx",
        "exportar-pdf",
        "patch",
        "melhorias",
        "ajustes",
        "tudo",
        "all",
    )
    gerar_sel_odi = modo_norm in ("selects-odi", "odi")
    gerar_guia_odi = modo_norm in ("guia-odi", "odi", "exportar-docx", "exportar-pdf")

    # Formatos alternativos (.docx, .pdf) e Apresentação Executiva (.pptx / slides HTML)
    # são gerados SOMENTE quando solicitados explicitamente pelo modo ou via --todos-formatos (incluir_extras=True)
    gerar_apresentacao_flag = (modo_norm == "apresentacao") or incluir_extras
    gerar_docx_flag = (modo_norm == "exportar-docx") or incluir_extras
    gerar_pdf_flag = (modo_norm == "exportar-pdf") or incluir_extras

    # 1. Comentários SQL (COMMENT ON TABLE / COLUMN)
    if gerar_comm:
        if dims:
            sql_comm_dim, qt_d, qc_d = construir_script_comentarios([(d, "DIM") for d in dims], schema, "Dimensões")
            p_comm_dim = saida_dw / "03_dimensoes" / "90_patch_comentarios_dimensoes.sql"
            p_comm_dim.parent.mkdir(parents=True, exist_ok=True)
            p_comm_dim.write_text(sql_comm_dim, encoding="utf-8")
            arquivos_gerados.append(str(p_comm_dim.relative_to(base_dir).as_posix()))
            print(f"  {VERDE}[OK]{RESET} Comentários de Dimensões ({qt_d} tabelas, {qc_d} colunas) -> {p_comm_dim.relative_to(base_dir)}")

        if fatos:
            sql_comm_fato, qt_f, qc_f = construir_script_comentarios([(f, "FATO") for f in fatos], schema, "Tabelas Fato")
            p_comm_fato = saida_dw / "04_fatos" / "90_patch_comentarios_fatos.sql"
            p_comm_fato.parent.mkdir(parents=True, exist_ok=True)
            p_comm_fato.write_text(sql_comm_fato, encoding="utf-8")
            arquivos_gerados.append(str(p_comm_fato.relative_to(base_dir).as_posix()))
            print(f"  {VERDE}[OK]{RESET} Comentários de Fatos ({qt_f} tabelas, {qc_f} colunas) -> {p_comm_fato.relative_to(base_dir)}")

        if stgs:
            sql_comm_stg, qt_s, qc_s = construir_script_comentarios([(s, "STG") for s in stgs], schema, "Staging / Apoio")
            p_comm_stg = saida_dw / "02_staging" / "90_patch_comentarios_staging.sql"
            p_comm_stg.parent.mkdir(parents=True, exist_ok=True)
            p_comm_stg.write_text(sql_comm_stg, encoding="utf-8")
            arquivos_gerados.append(str(p_comm_stg.relative_to(base_dir).as_posix()))
            print(f"  {VERDE}[OK]{RESET} Comentários de Staging ({qt_s} tabelas, {qc_s} colunas) -> {p_comm_stg.relative_to(base_dir)}")

    # 1.1 Dicionário de Dados HTML Interativo + Diagrama Star Schema SVG
    if gerar_dic:
        html_dic = construir_dicionario_html(tabelas_classificadas, schema, projeto)
        p_dic = saida_dw / "11_dicionario_dados" / "dicionario_dados.html"
        p_dic.parent.mkdir(parents=True, exist_ok=True)
        p_dic.write_text(html_dic, encoding="utf-8")
        arquivos_gerados.append(str(p_dic.relative_to(base_dir).as_posix()))
        print(f"  {VERDE}[OK]{RESET} Dicionário de Dados HTML interativo -> {p_dic.relative_to(base_dir)}")

        if _TEM_ARTEFATOS_VISUAIS and gerar_diagrama_star_schema_svg is not None:
            svg_star = gerar_diagrama_star_schema_svg(dims, fatos, schema, projeto)
            p_star = saida_dw / "11_dicionario_dados" / "diagrama_star_schema.svg"
            p_star.write_text(svg_star, encoding="utf-8")
            arquivos_gerados.append(str(p_star.relative_to(base_dir).as_posix()))
            print(f"  {VERDE}[OK]{RESET} Diagrama Vetorial Star Schema (SVG) -> {p_star.relative_to(base_dir)}")

    # 2. Índices e PRC_POS_CARGA_FATO
    if gerar_idx:
        sql_idx_dim, sql_idx_fato, q_id, q_if = construir_scripts_indices(dims, fatos, schema, ts_idx, estrategia)
        if dims:
            p_idx_dim = saida_dw / "03_dimensoes" / "91_patch_indices_dimensoes.sql"
            p_idx_dim.parent.mkdir(parents=True, exist_ok=True)
            p_idx_dim.write_text(sql_idx_dim, encoding="utf-8")
            arquivos_gerados.append(str(p_idx_dim.relative_to(base_dir).as_posix()))
            print(f"  {VERDE}[OK]{RESET} Índices B-Tree de Dimensões ({q_id} novos índices + DBMS_STATS) -> {p_idx_dim.relative_to(base_dir)}")

        if fatos:
            p_idx_fato = saida_dw / "04_fatos" / "91_patch_indices_fatos.sql"
            p_idx_fato.parent.mkdir(parents=True, exist_ok=True)
            p_idx_fato.write_text(sql_idx_fato, encoding="utf-8")
            arquivos_gerados.append(str(p_idx_fato.relative_to(base_dir).as_posix()))
            print(f"  {VERDE}[OK]{RESET} Índices de Fatos (Estratégia {estrategia.upper()}: {q_if} novos índices + DBMS_STATS) -> {p_idx_fato.relative_to(base_dir)}")

            tpl_prc = base_dir / "modulos" / "planejador_dw" / "templates" / "07_prc_pos_carga_fato.sql"
            if tpl_prc.exists():
                prc_txt = tpl_prc.read_text(encoding="utf-8", errors="ignore").replace("<SCHEMA_ALVO>", schema)
                p_prc = saida_dw / "05_procedimentos_manutencao" / "07_prc_pos_carga_fato.sql"
                p_prc.parent.mkdir(parents=True, exist_ok=True)
                p_prc.write_text(prc_txt, encoding="utf-8")
                arquivos_gerados.append(str(p_prc.relative_to(base_dir).as_posix()))
                print(f"  {VERDE}[OK]{RESET} Procedures PRC_PRE_CARGA_FATO e PRC_POS_CARGA_FATO -> {p_prc.relative_to(base_dir)}")

    # 3. Linha Default -1 isolada
    if gerar_linha_def and dims:
        sql_def = construir_script_linha_default(dims, schema)
        p_def = saida_dw / "03_dimensoes" / "06_init_default_records.sql"
        p_def.parent.mkdir(parents=True, exist_ok=True)
        p_def.write_text(sql_def, encoding="utf-8")
        arquivos_gerados.append(str(p_def.relative_to(base_dir).as_posix()))
        print(f"  {VERDE}[OK]{RESET} Script de Linha Padrão (-1 / Não Informado) -> {p_def.relative_to(base_dir)}")

    # 4. Constraints ENABLE NOVALIDATE e Ajustes Não-Destrutivos
    if gerar_constraints:
        sql_aj_dim, sql_aj_fato = construir_patches_ajustes_nao_destrutivos(dims, fatos, schema)
        if dims:
            p_aj_dim = saida_dw / "03_dimensoes" / "92_patch_ajustes_dimensoes.sql"
            p_aj_dim.parent.mkdir(parents=True, exist_ok=True)
            p_aj_dim.write_text(sql_aj_dim, encoding="utf-8")
            arquivos_gerados.append(str(p_aj_dim.relative_to(base_dir).as_posix()))
            print(f"  {VERDE}[OK]{RESET} Patch Não-Destrutivo de Dimensões (PKs + Linha -1) -> {p_aj_dim.relative_to(base_dir)}")

        if fatos:
            p_aj_fato = saida_dw / "04_fatos" / "92_patch_ajustes_fatos.sql"
            p_aj_fato.parent.mkdir(parents=True, exist_ok=True)
            p_aj_fato.write_text(sql_aj_fato, encoding="utf-8")
            arquivos_gerados.append(str(p_aj_fato.relative_to(base_dir).as_posix()))
            print(f"  {VERDE}[OK]{RESET} Patch Não-Destrutivo de Fatos (FKs ENABLE NOVALIDATE) -> {p_aj_fato.relative_to(base_dir)}")

    # 5. Testes de Integridade
    if gerar_testes:
        sql_testes = construir_testes_integridade(dims, fatos, schema, projeto)
        p_testes = saida_dw / "10_testes_integridade" / "13_testes_integridade.sql"
        p_testes.parent.mkdir(parents=True, exist_ok=True)
        p_testes.write_text(sql_testes, encoding="utf-8")
        arquivos_gerados.append(str(p_testes.relative_to(base_dir).as_posix()))
        print(f"  {VERDE}[OK]{RESET} Suíte de Testes de Integridade adaptada ao DW -> {p_testes.relative_to(base_dir)}")

    # 6. Guia do Analista de BI + Mockup Visual (SVG/HTML/PNG 2x) + Planilha .xlsx + Deck .pptx + Word .docx
    if gerar_guia_bi:
        pasta_bi = saida_dw / "08_datasets_bi"
        pasta_bi.mkdir(parents=True, exist_ok=True)
        # Garante que exista apenas 1 Guia do Analista de BI na pasta (remove versões órfãs de siglas anteriores)
        for padrao_antigo in ("GUIA_ANALISTA_BI_*.*", "Indicadores_PowerBI_*.xlsx", "apresentacao_executiva_*.pptx"):
            for arq_ant in list(pasta_bi.glob(padrao_antigo)):
                nome_up = arq_ant.stem.upper()
                if not nome_up.endswith(f"_{projeto.upper()}"):
                    try:
                        arq_ant.unlink()
                    except OSError as _exc:
                        _LOG.debug("Exceção tratada (melhorar_dw_existente.py:311): %r", _exc)

        md_bi_previa = construir_guia_bi_rapido(dims, fatos, schema, projeto, base_dir=base_dir, dados_amostra=None)
        p_bi = pasta_bi / f"GUIA_ANALISTA_BI_{projeto}.md"

        dados_amostra = None
        if _TEM_ARTEFATOS_VISUAIS and avaliar_medidas_guia_bi_amostra is not None:
            try:
                dados_amostra = avaliar_medidas_guia_bi_amostra(
                    dims,
                    fatos,
                    schema,
                    projeto,
                    base_dir=base_dir,
                    caminho_amostras=caminho_amostras,
                    guia_md_texto=md_bi_previa,
                )
            except Exception:
                dados_amostra = None

        promover_para_oficial = bool(
            dados_amostra
            and dados_amostra.get("tem_amostra")
            and (
                modo_norm == "validar-medidas-bi"
                or dados_amostra.get("origem_amostra") == "AMOSTRA_FORNECIDA"
                or caminho_amostras is not None
            )
        )

        if promover_para_oficial:
            md_bi = construir_guia_bi_rapido(
                dims, fatos, schema, projeto, base_dir=base_dir, dados_amostra=dados_amostra
            )
            label_versao_guia = "VERSÃO OFICIAL — HOMOLOGADA PÓS-CARGA"
        else:
            md_bi = md_bi_previa
            label_versao_guia = "VERSÃO PRÉVIA — PRÉ-CARGA"

        p_bi.write_text(md_bi, encoding="utf-8")
        arquivos_gerados.append(str(p_bi.relative_to(base_dir).as_posix()))
        print(
            f"  {VERDE}[OK]{RESET} Guia do Analista de BI ({label_versao_guia}) -> {p_bi.relative_to(base_dir)}"
        )

        if promover_para_oficial and dados_amostra:
            p_rel_prova = pasta_bi / "RELATORIO_PROVA_REAL_MEDIDAS.md"
            p_rel_prova.write_text(dados_amostra.get("relatorio_md", ""), encoding="utf-8")
            arquivos_gerados.append(str(p_rel_prova.relative_to(base_dir).as_posix()))
            print(
                f"  {VERDE}[OK]{RESET} Prova Real de Medidas DAX na Amostra ({len(dados_amostra.get('medidas_avaliadas', []))} medidas, "
                f"{dados_amostra.get('qtd_parciais', 0)} corrigida(s)) -> {p_rel_prova.relative_to(base_dir)}"
            )

        if _TEM_ARTEFATOS_VISUAIS:
            ind_neg = carregar_indicadores_negocio_entrega(base_dir)
            pasta_bi = saida_dw / "08_datasets_bi"

            # Garante também o diagrama Star Schema caso gerar_dic não tenha rodado neste modo isolado
            p_star = saida_dw / "11_dicionario_dados" / "diagrama_star_schema.svg"
            if not p_star.exists() and gerar_diagrama_star_schema_svg is not None:
                p_star.parent.mkdir(parents=True, exist_ok=True)
                p_star.write_text(gerar_diagrama_star_schema_svg(dims, fatos, schema, projeto), encoding="utf-8")
                arquivos_gerados.append(str(p_star.relative_to(base_dir).as_posix()))

            if gerar_mockup_painel_bi_svg is not None and gerar_preview_painel_bi_html is not None:
                svg_mock_l = gerar_mockup_painel_bi_svg(
                    dims, fatos, schema, projeto, dev_mode=False, tema="light", dados_amostra=dados_amostra
                )
                svg_dev_l = gerar_mockup_painel_bi_svg(
                    dims, fatos, schema, projeto, dev_mode=True, tema="light", dados_amostra=dados_amostra
                )

                p_mock = pasta_bi / "mockup_painel_bi.svg"
                p_mock.write_text(svg_mock_l, encoding="utf-8")
                arquivos_gerados.append(str(p_mock.relative_to(base_dir).as_posix()))

                p_mock_dev = pasta_bi / "mockup_painel_bi_devmode.svg"
                p_mock_dev.write_text(svg_dev_l, encoding="utf-8")
                arquivos_gerados.append(str(p_mock_dev.relative_to(base_dir).as_posix()))

                p_prev = pasta_bi / "preview_painel_bi.html"
                p_prev.write_text(
                    gerar_preview_painel_bi_html(dims, fatos, schema, projeto, dados_amostra=dados_amostra),
                    encoding="utf-8",
                )
                arquivos_gerados.append(str(p_prev.relative_to(base_dir).as_posix()))
                print(f"  {VERDE}[OK]{RESET} Mockup Visual do Painel BI (SVG + Dev Mode Redlines + HTML/PNG 2x) -> {p_prev.relative_to(base_dir)}")

            if gerar_planilha_indicadores_xlsx is not None:
                p_xlsx = pasta_bi / f"Indicadores_PowerBI_{projeto}.xlsx"
                gerar_planilha_indicadores_xlsx(dims, fatos, schema, projeto, str(p_xlsx), ind_neg)
                arquivos_gerados.append(str(p_xlsx.relative_to(base_dir).as_posix()))
                print(f"  {VERDE}[OK]{RESET} Planilha Estilizada de Indicadores e Metas (3 abas .xlsx) -> {p_xlsx.relative_to(base_dir)}")

            if gerar_apresentacao_flag and gerar_apresentacao_executiva is not None:
                p_pptx, p_slides = gerar_apresentacao_executiva(
                    dims, fatos, schema, projeto, str(pasta_bi)
                )
                arquivos_gerados.append(str(Path(p_pptx).relative_to(base_dir).as_posix()))
                arquivos_gerados.append(str(Path(p_slides).relative_to(base_dir).as_posix()))
                print(f"  {VERDE}[OK]{RESET} Apresentação Executiva (.pptx + .html 16:9) -> {Path(p_pptx).relative_to(base_dir)}")

            if gerar_docx_flag and exportar_markdown_para_docx is not None:
                p_docx_bi = pasta_bi / f"GUIA_ANALISTA_BI_{projeto}.docx"
                exportar_markdown_para_docx(str(p_bi), str(p_docx_bi), titulo=f"Guia do Analista de BI — {projeto}")
                arquivos_gerados.append(str(p_docx_bi.relative_to(base_dir).as_posix()))
                print(f"  {VERDE}[OK]{RESET} Guia do Analista de BI em Word (.docx) -> {p_docx_bi.relative_to(base_dir)}")

            if gerar_pdf_flag and exportar_markdown_para_pdf is not None:
                p_pdf_bi = pasta_bi / f"GUIA_ANALISTA_BI_{projeto}.pdf"
                exportar_markdown_para_pdf(str(p_bi), str(p_pdf_bi), titulo=f"Guia Oficial do Analista de BI - {projeto}")
                arquivos_gerados.append(str(p_pdf_bi.relative_to(base_dir).as_posix()))
                print(f"  {VERDE}[OK]{RESET} Guia do Analista de BI em PDF Oficial (.pdf) -> {p_pdf_bi.relative_to(base_dir)}")

    # 7. Micro-Processo ODI: Consultas SQL e Tabelas ODI_DIM_*
    if gerar_sel_odi:
        sql_odi_ddl, sql_odi_dim, sql_odi_fato = construir_scripts_odi(dims, fatos, stgs, schema, projeto, estrategia)
        if dims:
            p_odi_ddl = saida_dw / "03_dimensoes" / "03_create_odi_dim_tables.sql"
            p_odi_ddl.parent.mkdir(parents=True, exist_ok=True)
            p_odi_ddl.write_text(sql_odi_ddl, encoding="utf-8")
            arquivos_gerados.append(str(p_odi_ddl.relative_to(base_dir).as_posix()))
            print(f"  {VERDE}[OK]{RESET} Tabelas Auxiliares ODI (ODI_DIM_*) -> {p_odi_ddl.relative_to(base_dir)}")

            p_odi_sdim = saida_dw / "03_dimensoes" / "03_selects_odi_dimensoes.sql"
            p_odi_sdim.write_text(sql_odi_dim, encoding="utf-8")
            arquivos_gerados.append(str(p_odi_sdim.relative_to(base_dir).as_posix()))
            print(f"  {VERDE}[OK]{RESET} Consultas Analíticas SCD2 para ODI (ROW_NUMBER + LEAD) -> {p_odi_sdim.relative_to(base_dir)}")

        if fatos:
            p_odi_sfato = saida_dw / "04_fatos" / "04_select_odi_fato.sql"
            p_odi_sfato.parent.mkdir(parents=True, exist_ok=True)
            p_odi_sfato.write_text(sql_odi_fato, encoding="utf-8")
            arquivos_gerados.append(str(p_odi_sfato.relative_to(base_dir).as_posix()))
            print(f"  {VERDE}[OK]{RESET} Consulta de Resolução de SKs da Fato para ODI -> {p_odi_sfato.relative_to(base_dir)}")

    # 8. Micro-Processo ODI: Guias Modulares do Canvas ODI 12c + Diagrama SVG + Word .docx + PDF .pdf
    if gerar_guia_odi:
        guias_odi = construir_guias_odi_modulares(dims, fatos, schema, projeto, estrategia)
        pasta_rel = saida_dw / "09_relatorio_estrategias"
        pasta_rel.mkdir(parents=True, exist_ok=True)
        for nome_arq, conteudo_md in guias_odi.items():
            p_g = pasta_rel / nome_arq
            p_g.write_text(conteudo_md, encoding="utf-8")
            arquivos_gerados.append(str(p_g.relative_to(base_dir).as_posix()))
            print(f"  {VERDE}[OK]{RESET} Guia Modular ODI 12c -> {p_g.relative_to(base_dir)}")

        if _TEM_ARTEFATOS_VISUAIS:
            if gerar_mapa_canvas_odi_svg is not None:
                p_odi_svg = pasta_rel / "mapa_canvas_odi.svg"
                p_odi_svg.write_text(
                    gerar_mapa_canvas_odi_svg(dims, fatos, schema, projeto, estrategia=estrategia),
                    encoding="utf-8",
                )
                arquivos_gerados.append(str(p_odi_svg.relative_to(base_dir).as_posix()))
                print(f"  {VERDE}[OK]{RESET} Diagrama Vetorial do Canvas ODI 12c (SVG) -> {p_odi_svg.relative_to(base_dir)}")

            if gerar_docx_flag and exportar_markdown_para_docx is not None and "RELATORIO_ESTRATEGIAS.md" in guias_odi:
                p_docx_odi = pasta_rel / "RELATORIO_ESTRATEGIAS.docx"
                exportar_markdown_para_docx(
                    str(pasta_rel / "RELATORIO_ESTRATEGIAS.md"),
                    str(p_docx_odi),
                    titulo=f"Relatório de Estratégias ODI 12c — {projeto}",
                )
                arquivos_gerados.append(str(p_docx_odi.relative_to(base_dir).as_posix()))
                print(f"  {VERDE}[OK]{RESET} Relatório de Estratégias ODI em Word (.docx) -> {p_docx_odi.relative_to(base_dir)}")

            if gerar_pdf_flag and exportar_markdown_para_pdf is not None and "RELATORIO_ESTRATEGIAS.md" in guias_odi:
                p_pdf_odi = pasta_rel / "RELATORIO_ESTRATEGIAS.pdf"
                exportar_markdown_para_pdf(
                    str(pasta_rel / "RELATORIO_ESTRATEGIAS.md"),
                    str(p_pdf_odi),
                    titulo=f"Relatorio de Estrategias ODI 12c - {projeto}",
                )
                arquivos_gerados.append(str(p_pdf_odi.relative_to(base_dir).as_posix()))
                print(f"  {VERDE}[OK]{RESET} Relatório de Estratégias ODI em PDF Oficial (.pdf) -> {p_pdf_odi.relative_to(base_dir)}")

    # Gera o diagnóstico consolidado apenas nos modos de auditoria/patch amplo (evita poluir micro-processos isolados como guia-bi)
    if modo_norm in ("patch", "melhorias", "ajustes", "tudo", "all", "diagnostico"):
        rel_md = construir_relatorio_diagnostico(tabelas_classificadas, schema, projeto, modo_norm, arquivos_gerados)
        p_rel = saida_dw / "09_relatorio_estrategias" / "DIAGNOSTICO_MELHORIAS_DW_EXISTENTE.md"
        p_rel.parent.mkdir(parents=True, exist_ok=True)
        p_rel.write_text(rel_md, encoding="utf-8")
        arquivos_gerados.append(str(p_rel.relative_to(base_dir).as_posix()))
        print(f"  {VERDE}[OK]{RESET} Relatório Diagnóstico -> {p_rel.relative_to(base_dir)}")

    print(f"\n{VERDE}{NEGRITO}✅ Micro-processo '{modo_norm}' concluído com sucesso! {len(arquivos_gerados)} artefato(s) gerado(s) em 'saida/planejador_dw/'.{RESET}")
    print(f"{CIANO}🧭 O que você pode fazer agora:{RESET}")
    print("  • `/iniciar-semantica`  ➔ Gerar as 3 camadas de Views Semânticas + Catálogo META_* sobre este DW")
    print("  • `/exportar-docx` / `/exportar-pdf` / `/gerar-apresentacao` ➔ Exportar guias (.docx/.pdf) ou Apresentação (.pptx) sob demanda")
    print("  • `/gerar-mock-bi`      ➔ Gerar massa CSV sintética para testar dashboards no Power BI")
    print("  • `/validar-entrega`    ➔ Rodar o auditor de qualidade Fast-Track (`validar_entrega.py fast-track`)")
    print("  • `/onde-estou`         ➔ Consultar o status completo do workspace\n")
    return {"erros": 0, "arquivos_gerados": arquivos_gerados}


def main():
    parser = argparse.ArgumentParser(
        description="Motor de Micro-Processos e Melhoria Rápida (Fast-Track) para DW Oracle e ODI 12c"
    )
    parser.add_argument(
        "--caminho",
        "--ddl",
        dest="caminho",
        type=str,
        default="entrega/planejador_dw/ddl",
        help="Caminho do arquivo .sql ou pasta contendo os DDLs do DW (padrão: entrega/planejador_dw/ddl)",
    )
    parser.add_argument(
        "--modo",
        type=str,
        default="tudo",
        choices=[
            "comentarios",
            "dicionario",
            "indices",
            "linha-default",
            "constraints",
            "testes",
            "guia-bi",
            "mockup-bi",
            "validar-medidas-bi",
            "apresentacao",
            "exportar-docx",
            "exportar-pdf",
            "selects-odi",
            "guia-odi",
            "odi",
            "patch",
            "tudo",
        ],
        help=(
            "Micro-processo a executar: 'comentarios', 'dicionario', 'indices', 'linha-default', "
            "'constraints', 'testes', 'guia-bi', 'validar-medidas-bi', 'selects-odi', 'guia-odi', 'odi', 'patch' ou 'tudo'"
        ),
    )
    parser.add_argument(
        "--estrategia",
        type=str,
        default="A",
        choices=["A", "B", "a", "b"],
        help="Estratégia de índices nas FKs da Fato: 'A' (BITMAP INDEX) ou 'B' (B-TREE COMPRESS 1)",
    )
    parser.add_argument("--schema", type=str, default=None, help="Nome do Schema Oracle alvo (opcional, inferido do DDL)")
    parser.add_argument("--projeto", type=str, default=None, help="Sigla do Projeto (opcional, inferido do DDL)")
    parser.add_argument("--tablespace-idx", type=str, default=None, help="Tablespace de Índices opcional")
    parser.add_argument(
        "--amostras",
        type=str,
        default=None,
        help="Caminho opcional de arquivo/pasta com amostras pós-carga (DIM_* e FATO_* em CSV/SQL/XLSX/ODS)",
    )
    parser.add_argument(
        "--todos-formatos",
        "--incluir-extras",
        dest="incluir_extras",
        action="store_true",
        help="Gera também os formatos sob demanda (.docx, .pdf e Apresentação Executiva .pptx/.html)",
    )

    args = parser.parse_args()
    base_dir = get_base_dir()
    caminho_alvo = Path(args.caminho)
    if not caminho_alvo.is_absolute():
        caminho_alvo = base_dir / caminho_alvo

    caminho_amostras = None
    if args.amostras:
        caminho_amostras = Path(args.amostras)
        if not caminho_amostras.is_absolute():
            caminho_amostras = base_dir / caminho_amostras

    res = executar_melhoria_rapida(
        caminho_ddl=caminho_alvo,
        modo=args.modo,
        estrategia=args.estrategia.upper(),
        schema_cli=args.schema,
        projeto_cli=args.projeto,
        ts_idx_cli=args.tablespace_idx,
        caminho_amostras=caminho_amostras,
        incluir_extras=args.incluir_extras,
    )
    sys.exit(1 if res["erros"] > 0 else 0)


if __name__ == "__main__":
    main()

