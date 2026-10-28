#!/usr/bin/env python3
"""
Motor Visual & Documental NINHO (Craft Engine Integration)
==========================================================
Inspirado nas arquiteturas determinísticas open-source:
  1. FigCraft + GridCraft Chart -> Gerador de Mockup Visual SVG/HTML/PNG do Painel BI
     (com Visão Executiva, Visão Dev Mode Redlines DAX/SQL e Toggle Light/Dark).
  2. FigCraft + PhotoCraft      -> Diagramas Vetoriais SVG do Star Schema e do Canvas ODI 12c
     (com badges numerados ①..⑥, sombras e conectores ortogonais).
  3. GridCraft Engine           -> Gerador de Planilha Indicadores_PowerBI_<PROJETO>.xlsx
     (auto-ajuste ApproxMeasure, freeze panes, autoFilter, 3 abas) + Leitor nativo .ods.
  4. DeckCraft + WordCraft      -> Gerador de Apresentação Executiva (.pptx + HTML 16:9)
     e Exportador Corporativo Markdown -> Word (.docx OOXML).
  5. PdfCraft + Panic Hunt      -> Extrator nativo de texto de insumos .pdf (/FlateDecode + Tj/TJ)
     com blindagem anti-crash para arquivos corrompidos ou truncados.

Zero dependências externas (100% Python Standard Library: zipfile, xml, zlib, math, html, re).
"""

import logging as _logging_ninho

_LOG = _logging_ninho.getLogger("ninho.gerador_artefatos_visuais")

import os

from ninho_core.office import (  # noqa: E402,F401 — fachada de compatibilidade
    _build_pptx_slide_xml,
    _build_worksheet_xml,
    _col_letter,
    exportar_markdown_para_docx,
    gerar_apresentacao_executiva,
    gerar_planilha_indicadores_xlsx,
)
from ninho_core.diagramas import (  # noqa: E402,F401 — fachada de compatibilidade
    _HOP_TYPE_PALETTE,
    gerar_diagrama_star_schema_svg,
    gerar_documentacao_esteira_hop,
    gerar_mapa_canvas_odi_svg,
    gerar_svg_canvas_hop,
)
from ninho_core.mockup_bi import (  # noqa: E402,F401 — fachada de compatibilidade
    gerar_mockup_painel_bi_svg,
    gerar_preview_painel_bi_html,
)
from ninho_core.prova_dax import (  # noqa: E402,F401 — fachada de compatibilidade
    _dividir_valores_sql_insert,
    _extrair_contexto_bi,
    _extrair_inserts_sql,
    avaliar_medidas_guia_bi_amostra,
    carregar_amostras_dw_sqlite,
    extrair_medidas_dax_guia,
)
from ninho_core.pdf import (  # noqa: E402,F401 — fachada de compatibilidade
    _pdf_escape_winansi,
    exportar_markdown_para_pdf,
)
from ninho_core.visual_comum import (  # noqa: E402,F401 — fachada de compatibilidade
    _esc,
    _formatar_numero_br,
    _inferir_sk_nk_dim,
    _limpar_label,
    _mapear_relacionamentos_star,
    _normalizar_dims_fatos,
    _normalizar_tabela,
    _svg_donut_arc,
    approx_text_width,
)
from ninho_core.lgpd import (  # noqa: E402,F401 — fachada: mantém os imports antigos funcionando
    _validar_luhn,
    mascarar_pii_texto,
    escanear_pii_em_texto_ou_linhas,
)
from ninho_core.leitores import (  # noqa: E402,F401 — fachada: mantém os imports antigos funcionando
    _converter_valor_celula,
    _ler_planilha_xlsx_abas,
    ler_planilha_ods,
    extrair_texto_pdf_nativo,
    ler_documento_docx,
    ler_documento_odt,
)
from typing import Dict, List, Optional


# ==============================================================================
# 0. UTILITÁRIOS DE MEDIÇÃO E FORMATAÇÃO (INSPIRADO NO GRIDCRAFT APPROXMEASURE)
# ==============================================================================

# ==============================================================================
# 1. GERADOR DE MOCKUP VISUAL DO PAINEL BI (FIGCRAFT + GRIDCRAFT CHART)
# ==============================================================================

# ==============================================================================
# 0.5 MOTOR DE PROVA REAL PÓS-CARGA (SQLITE IN-MEMORY + AUDITORIA DE MEDIDAS DAX)
# ==============================================================================

# ==============================================================================
# 2. DIAGRAMAS VETORIAIS SVG: STAR SCHEMA & MAPA DO CANVAS ODI 12C
# ==============================================================================

# ==============================================================================
# 3. GRIDCRAFT ENGINE: PLANILHA INDICADORES_POWERBI.XLSX & LEITOR NATIVO .ODS
# ==============================================================================

# ==============================================================================
# 4. DECKCRAFT + WORDCRAFT: APRESENTAÇÃO EXECUTIVA (.PPTX / HTML) & EXPORTADOR .DOCX
# ==============================================================================

# ==============================================================================
# 5. PDFCRAFT + PANIC HUNT: EXTRATOR NATIVO DE TEXTO .PDF (ZERO DEPENDÊNCIAS)
# ==============================================================================



# ==============================================================================
# 5.5 LEITORES NATIVOS DE DOCUMENTOS (.DOCX / .ODT) & SCANNER LGPD DE CONTEÚDO
# ==============================================================================











# ==============================================================================
# 6. ORQUESTRADOR INTEGRADO DE ARTEFATOS VISUAIS & OOXML DO DW
# ==============================================================================

def gerar_pacote_visual_completo_dw(
    dims: List[dict],
    fatos: List[dict],
    schema: str,
    projeto: str,
    pasta_saida_dw: str,
    indicadores_existentes: Optional[List[dict]] = None,
    estrategia: str = "A",
    incluir_apresentacao: bool = False,
    incluir_docx: bool = False,
    incluir_pdf: bool = False,
    incluir_todos_formatos: bool = False,
) -> Dict[str, str]:
    """
    Gera os artefatos visuais e corporativos nas subpastas canônicas de `saida/planejador_dw/`.
    Por padrão (geração estritamente condicional), gera apenas os artefatos base:
      - `08_datasets_bi/mockup_painel_bi.svg`
      - `08_datasets_bi/mockup_painel_bi_devmode.svg`
      - `08_datasets_bi/preview_painel_bi.html`
      - `08_datasets_bi/Indicadores_PowerBI_<PROJETO>.xlsx`
      - `09_relatorio_estrategias/mapa_canvas_odi.svg`
      - `11_dicionario_dados/diagrama_star_schema.svg`

    Sob demanda (quando solicitado via `/gerar-apresentacao`, `/exportar-docx`, `/exportar-pdf`,
    checkboxes na Blueprint ou no modo `/demo` via `incluir_todos_formatos=True`):
      - `08_datasets_bi/apresentacao_executiva_<PROJETO>.pptx` + `apresentacao_slides.html`
      - `08_datasets_bi/GUIA_ANALISTA_BI_<PROJETO>.docx` + `.pdf`
      - `09_relatorio_estrategias/RELATORIO_ESTRATEGIAS.docx` + `.pdf`
    """
    if incluir_todos_formatos:
        incluir_apresentacao = True
        incluir_docx = True
        incluir_pdf = True

    pasta_08 = os.path.join(pasta_saida_dw, "08_datasets_bi")
    pasta_09 = os.path.join(pasta_saida_dw, "09_relatorio_estrategias")
    pasta_11 = os.path.join(pasta_saida_dw, "11_dicionario_dados")
    os.makedirs(pasta_08, exist_ok=True)
    os.makedirs(pasta_09, exist_ok=True)
    os.makedirs(pasta_11, exist_ok=True)

    # Higienizar versões antigas de outros nomes de projeto na pasta_08 para garantir apenas 1 Guia do Analista ativo
    proj_up = projeto.upper()
    for nome_ant in os.listdir(pasta_08):
        if (
            nome_ant.startswith("GUIA_ANALISTA_BI_")
            or nome_ant.startswith("Indicadores_PowerBI_")
            or nome_ant.startswith("apresentacao_executiva_")
        ):
            base_sem_ext = os.path.splitext(nome_ant)[0]
            if not base_sem_ext.upper().endswith(f"_{proj_up}"):
                try:
                    os.remove(os.path.join(pasta_08, nome_ant))
                except OSError as _exc:
                    _LOG.debug("Exceção tratada (gerador_artefatos_visuais.py:181): %r", _exc)

    arquivos: Dict[str, str] = {}

    # 1. Mockup BI SVG (Executivo + Dev Mode) + Preview HTML
    p_svg_exec = os.path.join(pasta_08, "mockup_painel_bi.svg")
    with open(p_svg_exec, "w", encoding="utf-8") as f:
        f.write(gerar_mockup_painel_bi_svg(dims, fatos, schema, projeto, dev_mode=False, tema="light"))
    arquivos["mockup_svg"] = p_svg_exec

    p_svg_dev = os.path.join(pasta_08, "mockup_painel_bi_devmode.svg")
    with open(p_svg_dev, "w", encoding="utf-8") as f:
        f.write(gerar_mockup_painel_bi_svg(dims, fatos, schema, projeto, dev_mode=True, tema="light"))
    arquivos["mockup_devmode_svg"] = p_svg_dev

    p_html_preview = os.path.join(pasta_08, "preview_painel_bi.html")
    with open(p_html_preview, "w", encoding="utf-8") as f:
        f.write(gerar_preview_painel_bi_html(dims, fatos, schema, projeto))
    arquivos["preview_html"] = p_html_preview

    # 2. Planilha Indicadores_PowerBI_<PROJETO>.xlsx
    p_xlsx = os.path.join(pasta_08, f"Indicadores_PowerBI_{projeto.upper()}.xlsx")
    gerar_planilha_indicadores_xlsx(dims, fatos, schema, projeto, p_xlsx, indicadores_existentes)
    arquivos["indicadores_xlsx"] = p_xlsx

    # 3. Apresentação Executiva (.pptx + .html) — gerada somente quando solicitada
    if incluir_apresentacao:
        p_pptx, p_slides_html = gerar_apresentacao_executiva(dims, fatos, schema, projeto, pasta_08)
        arquivos["apresentacao_pptx"] = p_pptx
        arquivos["apresentacao_html"] = p_slides_html

    # 4. Diagrama Star Schema SVG
    p_star_svg = os.path.join(pasta_11, "diagrama_star_schema.svg")
    with open(p_star_svg, "w", encoding="utf-8") as f:
        f.write(gerar_diagrama_star_schema_svg(dims, fatos, schema, projeto))
    arquivos["star_schema_svg"] = p_star_svg

    # 5. Mapa Visual do Canvas ODI 12c SVG
    p_odi_svg = os.path.join(pasta_09, "mapa_canvas_odi.svg")
    with open(p_odi_svg, "w", encoding="utf-8") as f:
        f.write(gerar_mapa_canvas_odi_svg(dims, fatos, schema, projeto, estrategia=estrategia))
    arquivos["mapa_odi_svg"] = p_odi_svg

    # 6. Exportação sob demanda para .docx e .pdf dos guias Markdown caso já existam
    p_guia_bi_md = os.path.join(pasta_08, f"GUIA_ANALISTA_BI_{projeto.upper()}.md")
    if os.path.isfile(p_guia_bi_md):
        if incluir_docx:
            p_guia_bi_docx = os.path.join(pasta_08, f"GUIA_ANALISTA_BI_{projeto.upper()}.docx")
            exportar_markdown_para_docx(
                p_guia_bi_md,
                p_guia_bi_docx,
                titulo=f"Guia Oficial do Analista de BI — Projeto {projeto.upper()}",
            )
            arquivos["guia_bi_docx"] = p_guia_bi_docx

        if incluir_pdf:
            p_guia_bi_pdf = os.path.join(pasta_08, f"GUIA_ANALISTA_BI_{projeto.upper()}.pdf")
            exportar_markdown_para_pdf(
                p_guia_bi_md,
                p_guia_bi_pdf,
                titulo=f"Guia Oficial do Analista de BI - Projeto {projeto.upper()}",
            )
            arquivos["guia_bi_pdf"] = p_guia_bi_pdf

    p_rel_odi_md = os.path.join(pasta_09, "RELATORIO_ESTRATEGIAS.md")
    if os.path.isfile(p_rel_odi_md):
        if incluir_docx:
            p_rel_odi_docx = os.path.join(pasta_09, "RELATORIO_ESTRATEGIAS.docx")
            exportar_markdown_para_docx(
                p_rel_odi_md,
                p_rel_odi_docx,
                titulo=f"Guia Completo de Construção no ODI 12c — Projeto {projeto.upper()}",
            )
            arquivos["relatorio_odi_docx"] = p_rel_odi_docx

        if incluir_pdf:
            p_rel_odi_pdf = os.path.join(pasta_09, "RELATORIO_ESTRATEGIAS.pdf")
            exportar_markdown_para_pdf(
                p_rel_odi_md,
                p_rel_odi_pdf,
                titulo=f"Guia Completo de Construcao no ODI 12c - Projeto {projeto.upper()}",
            )
            arquivos["relatorio_odi_pdf"] = p_rel_odi_pdf

    # 7. Se houver pipelines/workflows Apache Hop em 06_pipelines_hop/, desenha o Canvas Hop SVG + Documentação
    pasta_06_hop = os.path.join(pasta_saida_dw, "06_pipelines_hop")
    if os.path.isdir(pasta_06_hop):
        tem_hop = any(
            fn.endswith((".hpl", ".hwf"))
            for _, _, fns in os.walk(pasta_06_hop)
            for fn in fns
        )
        if tem_hop:
            docs_hop = gerar_documentacao_esteira_hop(pasta_06_hop, pasta_06_hop)
            arquivos.update(docs_hop)

    return arquivos


# ==============================================================================
# 7. DESENHADOR VISUAL DE CANVAS APACHE HOP (.HPL / .HWF) & AUTO-DOCUMENTAÇÃO
#    (INSPIRADO EM PipelineSvgPainter, WorkflowSvgPainter & DocBuilder DO HOP)
# ==============================================================================

