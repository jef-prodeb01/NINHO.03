"""
Mockup visual Full HD do painel Power BI (SVG normal e Dev Mode com redlines) e preview HTML
com exportação PNG 2x.

Extraído de gerador_artefatos_visuais.py (que mantém uma fachada de reimportação).
"""

from ninho_core.prova_dax import (
    _extrair_contexto_bi,
    avaliar_medidas_guia_bi_amostra,
)
from ninho_core.visual_comum import (
    _esc,
    _svg_donut_arc,
)
from datetime import datetime
from pathlib import Path
from typing import List, Optional


def gerar_mockup_painel_bi_svg(
    dims: List[dict],
    fatos: List[dict],
    schema: str,
    projeto: str,
    dev_mode: bool = False,
    tema: str = "light",
    dados_amostra: Optional[dict] = None,
    base_dir: Optional[Path] = None,
    caminho_amostras: Optional[Path] = None,
    guia_md_texto: Optional[str] = None,
) -> str:
    """
    Gera o SVG vetorial Full HD (1440x960) do Painel Executivo de BI.
    - Quando `dev_mode=True`, adiciona a camada FigCraft Dev Mode (Redlines tracejados e
      Callouts numerados ① a ⑦ indicando exatamente qual medida DAX e coluna alimenta cada visual).
    - Suporta `tema="light"` (Institucional Governo/PRODEB) e `tema="dark"` (Executivo Noturno).
    - Se houver dados de amostra (`DIM_*` + `FATO_*`) carregados ou em `dados_amostra`,
      preenche todos os visuais com os valores reais calculados da carga e das medidas DAX.
    """
    ctx = _extrair_contexto_bi(dims, fatos, projeto)
    if dados_amostra is None and (base_dir is not None or caminho_amostras is not None):
        try:
            dados_amostra = avaliar_medidas_guia_bi_amostra(
                dims, fatos, schema, projeto,
                base_dir=base_dir,
                caminho_amostras=caminho_amostras,
                guia_md_texto=guia_md_texto,
            )
        except Exception:
            dados_amostra = None
    tem_amostra = bool(dados_amostra and dados_amostra.get("tem_amostra"))

    if tema == "dark":
        bg_canvas = "#0B0F19"
        bg_sidebar = "#111827"
        bg_card = "#1E293B"
        bg_card_alt = "#162032"
        border_card = "#334155"
        text_primary = "#F8FAFC"
        text_secondary = "#94A3B8"
        text_muted = "#64748B"
        grid_line = "#263349"
        table_row_even = "#192335"
        chip_bg = "#1E293B"
        chip_border = "#3B82F6"
    else:
        bg_canvas = "#F1F5F9"
        bg_sidebar = "#0F172A"
        bg_card = "#FFFFFF"
        bg_card_alt = "#F8FAFC"
        border_card = "#E2E8F0"
        text_primary = "#0F172A"
        text_secondary = "#475569"
        text_muted = "#64748B"
        grid_line = "#E2E8F0"
        table_row_even = "#F8FAFC"
        chip_bg = "#FFFFFF"
        chip_border = "#CBD5E1"

    accent_blue = "#2563EB"
    accent_indigo = "#4F46E5"
    accent_teal = "#0D9488"
    accent_amber = "#D97706"
    accent_green = "#16A34A"
    accent_red = "#DC2626"
    dev_magenta = "#E11D48"

    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1440 960" width="100%" height="100%">',
        "  <defs>",
        '    <style>',
        '      .font-ui { font-family: "Segoe UI", Inter, -apple-system, BlinkMacSystemFont, Roboto, sans-serif; }',
        '      .font-mono { font-family: "JetBrains Mono", Consolas, "Courier New", monospace; }',
        "    </style>",
        '    <filter id="cardShadow" x="-4%" y="-4%" width="108%" height="112%">',
        '      <feDropShadow dx="0" dy="3" stdDeviation="6" flood-color="#0F172A" flood-opacity="0.07"/>',
        "    </filter>",
        '    <filter id="calloutShadow" x="-10%" y="-10%" width="120%" height="125%">',
        '      <feDropShadow dx="0" dy="4" stdDeviation="5" flood-color="#881337" flood-opacity="0.28"/>',
        "    </filter>",
        '    <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">',
        f'      <stop offset="0%" stop-color="{accent_blue}" stop-opacity="0.34"/>',
        f'      <stop offset="100%" stop-color="{accent_blue}" stop-opacity="0.02"/>',
        "    </linearGradient>",
        '    <linearGradient id="headerGrad" x1="0" y1="0" x2="1" y2="0">',
        '      <stop offset="0%" stop-color="#1E3A8A"/>',
        '      <stop offset="100%" stop-color="#2563EB"/>',
        "    </linearGradient>",
        "  </defs>",
        "",
        '  <!-- Canvas Principal 1440x960 -->',
        f'  <rect width="1440" height="960" fill="{bg_canvas}"/>',
        "",
        '  <!-- Sidebar de Navegação (FigCraft Dashboard Shell) -->',
        f'  <rect x="0" y="0" width="232" height="960" fill="{bg_sidebar}"/>',
        '  <rect x="20" y="22" width="38" height="38" rx="9" fill="url(#headerGrad)"/>',
        '  <text x="39" y="47" text-anchor="middle" fill="#FFFFFF" font-size="17" font-weight="800" class="font-ui">N</text>',
        f'  <text x="68" y="39" fill="#FFFFFF" font-size="14" font-weight="700" class="font-ui">PAINEL { _esc(ctx["projeto"][:14]) }</text>',
        f'  <text x="68" y="55" fill="#94A3B8" font-size="10.5" class="font-mono">{ _esc(schema) } • Star Schema</text>',
        '  <line x1="20" y1="76" x2="212" y2="76" stroke="#1E293B" stroke-width="1"/>',
    ]

    # Páginas na Sidebar
    nav_items = [
        ("01. Visão Executiva", True, "KPIs & Tendência"),
        (f"02. Análise por {ctx['label_d1'][:14]}", False, "Ranking & Matriz"),
        ("03. Detalhamento & Auditoria", False, "Drill-through & SCD2"),
        ("04. Qualidade & Sentinelas (-1)", False, "Conferência DW"),
    ]
    ny = 96
    for titulo_nav, ativo, sub_nav in nav_items:
        if ativo:
            svg.append(f'  <rect x="14" y="{ny}" width="204" height="50" rx="8" fill="#1E293B" stroke="#3B82F6" stroke-width="1.2"/>')
            svg.append(f'  <rect x="14" y="{ny+10}" width="4" height="30" rx="2" fill="#3B82F6"/>')
            svg.append(f'  <text x="30" y="{ny+22}" fill="#FFFFFF" font-size="12" font-weight="700" class="font-ui">{_esc(titulo_nav)}</text>')
            svg.append(f'  <text x="30" y="{ny+38}" fill="#93C5FD" font-size="10" class="font-ui">{_esc(sub_nav)}</text>')
        else:
            svg.append(f'  <rect x="14" y="{ny}" width="204" height="46" rx="8" fill="transparent"/>')
            svg.append(f'  <text x="30" y="{ny+20}" fill="#CBD5E1" font-size="11.5" font-weight="600" class="font-ui">{_esc(titulo_nav)}</text>')
            svg.append(f'  <text x="30" y="{ny+35}" fill="#64748B" font-size="9.5" class="font-ui">{_esc(sub_nav)}</text>')
        ny += 60

    # Bloco Radar Consultivo IA na Sidebar
    svg.extend([
        '  <rect x="16" y="690" width="200" height="175" rx="10" fill="#1E1B4B" stroke="#4F46E5" stroke-width="1"/>',
        '  <text x="28" y="714" fill="#A5B4FC" font-size="11" font-weight="700" class="font-ui">💡 RADAR CONSULTIVO IA</text>',
        '  <text x="28" y="734" fill="#E0E7FF" font-size="10" class="font-ui">• Proteção SCD2 ativa via</text>',
        '  <text x="36" y="748" fill="#93C5FD" font-size="9.5" class="font-mono">FLG_ATUAL = \'S\'</text>',
        '  <text x="28" y="768" fill="#E0E7FF" font-size="10" class="font-ui">• Monitor de Não Informado</text>',
        '  <text x="36" y="782" fill="#93C5FD" font-size="9.5" class="font-mono">SK = -1 (&lt; 2,0% meta)</text>',
        '  <text x="28" y="802" fill="#E0E7FF" font-size="10" class="font-ui">• Inteligência Temporal YoY</text>',
        '  <text x="36" y="816" fill="#93C5FD" font-size="9.5" class="font-mono">SAMEPERIODLASTYEAR</text>',
        '  <rect x="28" y="832" width="176" height="22" rx="5" fill="#312E81"/>',
        '  <text x="116" y="847" text-anchor="middle" fill="#C7D2FE" font-size="9.5" font-weight="600" class="font-ui">Sync Slicers: Grupo Principal</text>',
        f'  <text x="24" y="936" fill="#64748B" font-size="10" class="font-ui">NINHO BI Mockup • {datetime.now().strftime("%d/%m/%Y")}</text>',
    ])

    # Top Header & Barra de Slicers Globais
    vis = dados_amostra.get("visuais", {}) if tem_amostra else {}
    sub_header = (
        f"Fonte Oficial DW: {schema}.{ctx['nome_fato']} • 🧪 Prova Real ({dados_amostra.get('total_linhas_fato', 0)} linhas na Fato)"
        if tem_amostra
        else f"Fonte Oficial DW: {schema}.{ctx['nome_fato']} • Atualização Diária D-1"
    )
    svg.extend([
        '  <!-- Header Principal + Filtros Globais (Sync Slicers) -->',
        f'  <rect x="252" y="18" width="1168" height="74" rx="12" fill="{bg_card}" stroke="{border_card}" filter="url(#cardShadow)"/>',
        f'  <text x="276" y="46" fill="{text_primary}" font-size="18" font-weight="800" class="font-ui">Painel Executivo — {_esc(ctx["label_fato"])}</text>',
        f'  <text x="276" y="68" fill="{text_secondary}" font-size="11.5" class="font-ui">{_esc(sub_header)}</text>',
    ])

    # Slicer Chips no Header
    slicers = [
        ("📅 Período", f"{ctx['dim_tempo']}[NUM_ANO]", "Amostra Pós-Carga" if tem_amostra else "2025 / 2026 (YTD)"),
        (f"🏢 {ctx['label_d1'][:14]}", f"{ctx['d1']}[{ctx['col_d1']}]", "Todas (Ativas)"),
        (f"🏷️ {ctx['label_d2'][:14]}", f"{ctx['d2']}[{ctx['col_d2']}]", "Todos os Grupos"),
        ("⚡ Status SCD2", "FLG_ATUAL", "Apenas Vigentes ('S')"),
    ]
    sx = 720
    for sl_title, sl_col, sl_val in slicers:
        sl_val_fmt = sl_val if len(sl_val) <= 22 else sl_val[:21] + "…"
        sl_col_fmt = sl_col if len(sl_col) <= 26 else sl_col[:24] + "…]" if "[" in sl_col and not sl_col[:25].endswith("]") else sl_col[:26]
        svg.extend([
            f'  <rect x="{sx}" y="27" width="166" height="54" rx="8" fill="{chip_bg}" stroke="{chip_border}" stroke-width="1"/>',
            f'  <text x="{sx+10}" y="44" fill="{text_muted}" font-size="9.5" font-weight="700" class="font-ui">{_esc(sl_title)}</text>',
            f'  <text x="{sx+10}" y="60" fill="{text_primary}" font-size="11" font-weight="700" class="font-ui">{_esc(sl_val_fmt)}</text>',
            f'  <text x="{sx+10}" y="73" fill="{accent_blue}" font-size="8.5" class="font-mono">{_esc(sl_col_fmt)}</text>',
        ])
        sx += 174

    # Linha 1: 4 Cards de KPI com Sparklines Vetoriais Contidos no Card (98px largura) e Badges Semânticos
    kpis_amostra = vis.get("kpis", []) if tem_amostra else []
    kpis = [
        {
            "titulo": kpis_amostra[0]["titulo"] if len(kpis_amostra) > 0 else f"Total {ctx['label_m1'][:22]}",
            "valor": kpis_amostra[0]["valor"] if len(kpis_amostra) > 0 else ("R$ 48,7 M" if any(k in ctx["m1"] for k in ("VAL_", "VLR_")) else "148.920"),
            "delta": kpis_amostra[0]["delta"] if len(kpis_amostra) > 0 else "+14,2% vs Ano Ant.",
            "delta_cor": accent_green,
            "delta_bg": "#DCFCE7" if tema == "light" else "#064E3B",
            "dax": kpis_amostra[0]["dax"] if len(kpis_amostra) > 0 else f"[Total {ctx['label_m1']}] = SUM({ctx['nome_fato']}[{ctx['m1']}])",
            "spark": "0,28 14,24 28,26 42,18 56,19 70,11 84,13 98,4",
            "spark_end": (98, 4),
            "cor_barra": accent_blue,
            "ia_badge": False,
        },
        {
            "titulo": kpis_amostra[1]["titulo"] if len(kpis_amostra) > 1 else f"Volume ({ctx['label_m2'][:20]})",
            "valor": kpis_amostra[1]["valor"] if len(kpis_amostra) > 1 else "32.410",
            "delta": kpis_amostra[1]["delta"] if len(kpis_amostra) > 1 else "+6,8% vs Meta Mensal",
            "delta_cor": accent_teal,
            "delta_bg": "#CCFBF1" if tema == "light" else "#134E4A",
            "dax": kpis_amostra[1]["dax"] if len(kpis_amostra) > 1 else f"[Qtd Registros] = COUNTROWS({ctx['nome_fato']})",
            "spark": "0,26 14,22 28,20 42,21 56,15 70,12 84,9 98,6",
            "spark_end": (98, 6),
            "cor_barra": accent_teal,
            "ia_badge": False,
        },
        {
            "titulo": kpis_amostra[2]["titulo"] if len(kpis_amostra) > 2 else f"Média / Ticket ({ctx['label_m3'][:15]})",
            "valor": kpis_amostra[2]["valor"] if len(kpis_amostra) > 2 else ("R$ 1.502,60" if any(k in ctx["m1"] for k in ("VAL_", "VLR_")) else "4,60 un"),
            "delta": kpis_amostra[2]["delta"] if len(kpis_amostra) > 2 else "-1,4% (Estável)",
            "delta_cor": accent_amber,
            "delta_bg": "#FEF3C7" if tema == "light" else "#78350F",
            "dax": kpis_amostra[2]["dax"] if len(kpis_amostra) > 2 else f"[Media {ctx['label_m1']}] = DIVIDE([Total {ctx['label_m1']}], [Qtd Registros], 0)",
            "spark": "0,16 14,13 28,17 42,14 56,18 70,15 84,17 98,15",
            "spark_end": (98, 15),
            "cor_barra": accent_indigo,
            "ia_badge": True,
        },
        {
            "titulo": kpis_amostra[3]["titulo"] if len(kpis_amostra) > 3 else "Índice Qualidade DW (SK ≠ -1)",
            "valor": kpis_amostra[3]["valor"] if len(kpis_amostra) > 3 else "98,7%",
            "delta": kpis_amostra[3]["delta"] if len(kpis_amostra) > 3 else "1,3% Não Informado (-1)",
            "delta_cor": accent_green,
            "delta_bg": "#DCFCE7" if tema == "light" else "#064E3B",
            "dax": kpis_amostra[3]["dax"] if len(kpis_amostra) > 3 else f"[% Qualidade] = 1 - DIVIDE(CALCULATE([Qtd Registros], {ctx['d1']}[SK]=-1), [Qtd Registros], 0)",
            "spark": "0,22 14,18 28,15 42,12 56,10 70,8 84,6 98,4",
            "spark_end": (98, 4),
            "cor_barra": accent_green,
            "ia_badge": True,
        },
    ]

    kx = 252
    kw = 280
    for idx, kpi in enumerate(kpis):
        dax_curto = kpi["dax"] if len(kpi["dax"]) <= 42 else kpi["dax"][:41] + "…"
        end_x, end_y = kpi["spark_end"]
        svg.extend([
            f'  <!-- KPI Card {idx+1} -->',
            f'  <clipPath id="clipKpi{idx+1}"><rect x="{kx}" y="108" width="{kw}" height="138" rx="12"/></clipPath>',
            f'  <rect x="{kx}" y="108" width="{kw}" height="138" rx="12" fill="{bg_card}" stroke="{border_card}" filter="url(#cardShadow)"/>',
            f'  <g clip-path="url(#clipKpi{idx+1})">',
            f'    <rect x="{kx}" y="108" width="{kw}" height="5" rx="2.5" fill="{kpi["cor_barra"]}"/>',
            f'    <text x="{kx+18}" y="134" fill="{text_secondary}" font-size="11.5" font-weight="700" class="font-ui">{_esc(kpi["titulo"])}</text>',
            f'    <text x="{kx+18}" y="172" fill="{text_primary}" font-size="27" font-weight="800" class="font-ui">{_esc(kpi["valor"])}</text>',
            f'    <rect x="{kx+18}" y="184" width="136" height="22" rx="11" fill="{kpi["delta_bg"]}"/>',
            f'    <text x="{kx+86}" y="199" text-anchor="middle" fill="{kpi["delta_cor"]}" font-size="10" font-weight="700" class="font-ui">{_esc(kpi["delta"])}</text>',
            f'    <g transform="translate({kx+164}, 174)">',
            f'      <polyline fill="none" stroke="{kpi["cor_barra"]}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" points="{kpi["spark"]}"/>',
            f'      <circle cx="{end_x}" cy="{end_y}" r="3" fill="{kpi["cor_barra"]}"/>',
            '    </g>',
            f'    <text x="{kx+18}" y="232" fill="{text_muted}" font-size="9" class="font-mono">{_esc(dax_curto)}</text>',
            '  </g>',
        ])
        if kpi["ia_badge"]:
            svg.extend([
                f'  <rect x="{kx+kw-74}" y="119" width="60" height="18" rx="9" fill="#EEF2FF" stroke="#6366F1" stroke-width="0.8"/>',
                f'  <text x="{kx+kw-44}" y="131" text-anchor="middle" fill="#4338CA" font-size="8.5" font-weight="700" class="font-ui">💡 IA KPI</text>',
            ])
        kx += kw + 16

    # Linha 2 (Esquerda): Gráfico de Área + Linha Tracejada YoY (756px largura)
    svg.extend([
        '  <!-- Visual Central 1: Evolução Mensal + Comparativo YoY (GridCraft Line/Area) -->',
        f'  <rect x="252" y="262" width="756" height="330" rx="12" fill="{bg_card}" stroke="{border_card}" filter="url(#cardShadow)"/>',
        f'  <text x="276" y="292" fill="{text_primary}" font-size="14" font-weight="700" class="font-ui">Evolução Mensal — {_esc(ctx["label_m1"])} (Atual vs Ano Anterior YoY)</text>',
        f'  <text x="276" y="310" fill="{text_muted}" font-size="10.5" class="font-mono">Eixo X: {_esc(ctx["dim_tempo"])}[DES_MES_ANO] • Medidas: [Total {_esc(ctx["label_m1"])}] vs [Total {_esc(ctx["label_m1"])} LY]</text>',
        # Legenda no topo direito do card
        f'  <circle cx="810" cy="290" r="5" fill="{accent_blue}"/>',
        f'  <text x="820" y="294" fill="{text_secondary}" font-size="10.5" font-weight="600" class="font-ui"> Ano Atual (Realizado)</text>',
        '  <line x1="925" y1="290" x2="945" y2="290" stroke="#94A3B8" stroke-width="2.2" stroke-dasharray="4,3"/>',
        f'  <text x="950" y="294" fill="{text_secondary}" font-size="10.5" font-weight="600" class="font-ui"> Ano Ant. (LY)</text>',
    ])

    # Grade horizontal do gráfico de linha
    y_levels = [(340, "100%"), (385, "75%"), (430, "50%"), (475, "25%"), (520, "0%")]
    for yl, y_txt in y_levels:
        svg.append(f'  <line x1="310" y1="{yl}" x2="980" y2="{yl}" stroke="{grid_line}" stroke-width="1" stroke-dasharray="3,3"/>')
        svg.append(f'  <text x="300" y="{yl+4}" text-anchor="end" fill="{text_muted}" font-size="9.5" class="font-mono">{y_txt}</text>')

    meses = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    pts_atual_y = [468, 452, 438, 444, 416, 398, 405, 382, 370, 362, 350, 336]
    pts_ly_y = [488, 476, 470, 462, 450, 438, 442, 425, 415, 404, 396, 384]
    coords_atual = []
    coords_ly = []
    for idx, mes in enumerate(meses):
        px = 330 + idx * 57
        coords_atual.append((px, pts_atual_y[idx]))
        coords_ly.append((px, pts_ly_y[idx]))
        svg.append(f'  <text x="{px}" y="542" text-anchor="middle" fill="{text_secondary}" font-size="10" font-weight="600" class="font-ui">{mes}</text>')

    poly_atual = " ".join(f"{x},{y}" for x, y in coords_atual)
    poly_ly = " ".join(f"{x},{y}" for x, y in coords_ly)
    area_path = f"M {coords_atual[0][0]},520 L " + " L ".join(f"{x},{y}" for x, y in coords_atual) + f" L {coords_atual[-1][0]},520 Z"

    svg.extend([
        f'  <path d="{area_path}" fill="url(#areaGrad)"/>',
        f'  <polyline fill="none" stroke="#94A3B8" stroke-width="2.2" stroke-dasharray="6,4" points="{poly_ly}"/>',
        f'  <polyline fill="none" stroke="{accent_blue}" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round" points="{poly_atual}"/>',
    ])
    for x, y in coords_atual:
        svg.append(f'  <circle cx="{x}" cy="{y}" r="4" fill="{bg_card}" stroke="{accent_blue}" stroke-width="2.5"/>')

    # Rodapé de Insight IA dentro do gráfico de evolução
    svg.extend([
        f'  <rect x="276" y="554" width="708" height="26" rx="6" fill="{bg_card_alt}" stroke="{border_card}"/>',
        f'  <text x="288" y="571" fill="{text_secondary}" font-size="10" class="font-ui">📌 <tspan font-weight="700">Regra de Negócio:</tspan> Eixo temporal contínuo garantido pela <tspan class="font-mono" fill="{accent_blue}">{_esc(ctx["dim_tempo"])}</tspan> (Datas Fiscais + Feriados Nacionais).</text>',
    ])

    # Linha 2 (Direita): Gráfico de Rosca Trigonométrico (Donut Chart 396px largura)
    svg.extend([
        '  <!-- Visual Central 2: Composição Percentual (GridCraft Trigonometric Donut) -->',
        f'  <rect x="1024" y="262" width="396" height="330" rx="12" fill="{bg_card}" stroke="{border_card}" filter="url(#cardShadow)"/>',
        f'  <text x="1046" y="292" fill="{text_primary}" font-size="14" font-weight="700" class="font-ui">Participação por {_esc(ctx["label_d2"][:20])}</text>',
        f'  <text x="1046" y="310" fill="{text_muted}" font-size="10" class="font-mono">{_esc(ctx["d2"])}[{_esc(ctx["col_d2"])}]</text>',
    ])

    cores_fatias = [accent_blue, accent_teal, accent_indigo, accent_amber]
    if tem_amostra and vis.get("fatias"):
        fatias = []
        for idx_f, (nome_f, pct_f, txt_pct) in enumerate(vis["fatias"][:4]):
            fatias.append((nome_f, max(0.02, float(pct_f)), cores_fatias[idx_f % len(cores_fatias)], txt_pct))
    else:
        fatias = [
            ("Grupo Principal A", 0.42, accent_blue, "42,0%"),
            ("Grupo Secundário B", 0.28, accent_teal, "28,0%"),
            ("Grupo Operacional C", 0.19, accent_indigo, "19,0%"),
            ("Outros / N.I. (-1)", 0.11, accent_amber, "11,0%"),
        ]
    cx_d, cy_d, r_d = 1132.0, 428.0, 74.0
    ang = 0.0
    for nome_f, pct_f, cor_f, txt_pct in fatias:
        prox_ang = ang + pct_f * 360.0
        arc_d = _svg_donut_arc(cx_d, cy_d, r_d, ang + 1.5, prox_ang - 1.5)
        svg.append(f'  <path d="{arc_d}" fill="none" stroke="{cor_f}" stroke-width="26" stroke-linecap="butt"/>')
        ang = prox_ang

    svg.extend([
        f'  <text x="{cx_d}" y="{cy_d-4}" text-anchor="middle" fill="{text_primary}" font-size="18" font-weight="800" class="font-ui">100%</text>',
        f'  <text x="{cx_d}" y="{cy_d+14}" text-anchor="middle" fill="{text_muted}" font-size="9.5" class="font-ui">Total Geral</text>',
    ])

    ly_leg = 356
    for nome_f, _, cor_f, txt_pct in fatias:
        svg.extend([
            f'  <rect x="1236" y="{ly_leg}" width="12" height="12" rx="3" fill="{cor_f}"/>',
            f'  <text x="1256" y="{ly_leg+10}" fill="{text_primary}" font-size="11" font-weight="600" class="font-ui">{_esc(nome_f)}</text>',
            f'  <text x="1256" y="{ly_leg+24}" fill="{text_muted}" font-size="10" class="font-mono">{txt_pct} do total</text>',
        ])
        ly_leg += 46

    svg.extend([
        f'  <rect x="1044" y="554" width="356" height="26" rx="6" fill="{bg_card_alt}" stroke="{border_card}"/>',
        f'  <text x="1056" y="571" fill="{text_secondary}" font-size="10" class="font-ui">🛡️ <tspan font-weight="700">Integridade:</tspan> Registros sem vínculo caem em <tspan class="font-mono" fill="{accent_amber}">SK = -1</tspan>.</text>',
    ])

    # Linha 3 (Esquerda): Ranking Horizontal por Dimensão D1 (520px largura)
    svg.extend([
        '  <!-- Visual Inferior 1: Top 5 Ranking Horizontal -->',
        f'  <rect x="252" y="608" width="520" height="330" rx="12" fill="{bg_card}" stroke="{border_card}" filter="url(#cardShadow)"/>',
        f'  <text x="276" y="638" fill="{text_primary}" font-size="14" font-weight="700" class="font-ui">Top 5 — {_esc(ctx["label_d1"])} por {_esc(ctx["label_m1"])}</text>',
        f'  <text x="276" y="656" fill="{text_muted}" font-size="10" class="font-mono">Dimensão: {_esc(ctx["d1"])}[{_esc(ctx["col_d1"])}] • Filtro SCD2 Vigente</text>',
    ])

    cores_rank = [accent_blue, accent_blue, accent_indigo, accent_teal, accent_teal]
    if tem_amostra and vis.get("ranking"):
        ranking_rows = []
        for idx_r, (r_nome, r_w, r_val, r_pct) in enumerate(vis["ranking"][:5]):
            ranking_rows.append((r_nome, r_w, r_val, r_pct, cores_rank[idx_r % len(cores_rank)]))
    else:
        ranking_rows = [
            (f"01. {ctx['label_d1']} Regional Norte", 250, "R$ 14,2 M", "31,4%", accent_blue),
            (f"02. {ctx['label_d1']} Central / Sede", 205, "R$ 11,8 M", "25,8%", accent_blue),
            (f"03. {ctx['label_d1']} Sul Metropolitana", 162, "R$ 9,1 M", "19,9%", accent_indigo),
            (f"04. {ctx['label_d1']} Leste Interior", 118, "R$ 6,4 M", "14,0%", accent_teal),
            (f"05. {ctx['label_d1']} Oeste Fronteira", 76, "R$ 4,1 M", "8,9%", accent_teal),
        ]
    ry = 678
    for r_nome, r_w, r_val, r_pct, r_cor in ranking_rows:
        r_nome_fmt = r_nome if len(r_nome) <= 28 else r_nome[:27] + "…"
        svg.extend([
            f'  <text x="276" y="{ry+14}" fill="{text_primary}" font-size="11" font-weight="600" class="font-ui">{_esc(r_nome_fmt)}</text>',
            f'  <rect x="478" y="{ry}" width="210" height="18" rx="4" fill="{bg_card_alt}"/>',
            f'  <rect x="478" y="{ry}" width="{r_w * 0.82:.1f}" height="18" rx="4" fill="{r_cor}"/>',
            f'  <text x="696" y="{ry+13}" fill="{text_primary}" font-size="10.5" font-weight="700" class="font-mono">{r_val}</text>',
            f'  <text x="276" y="{ry+28}" fill="{text_muted}" font-size="9" class="font-mono">Participação: {r_pct}</text>',
        ])
        ry += 48

    # Linha 3 (Direita): Matriz Analítica Detalhada com Data Bars GridCraft e Status Pills (632px largura)
    svg.extend([
        '  <!-- Visual Inferior 2: Matriz Analítica Detalhada + Data Bars (#5B9BD5) + Status Pills -->',
        f'  <rect x="788" y="608" width="632" height="330" rx="12" fill="{bg_card}" stroke="{border_card}" filter="url(#cardShadow)"/>',
        f'  <text x="812" y="638" fill="{text_primary}" font-size="14" font-weight="700" class="font-ui">Matriz de Desempenho, Metas e Auditoria ({_esc(ctx["label_d3"][:22])})</text>',
        f'  <text x="812" y="656" fill="{text_muted}" font-size="10" class="font-mono">Cruzamento: {_esc(ctx["d1"])} × {_esc(ctx["d3"])} • Formatação Condicional &amp; Data Bars</text>',
        # Cabeçalho da Tabela
        '  <rect x="810" y="668" width="588" height="28" rx="6" fill="#1E293B"/>',
        f'  <text x="822" y="686" fill="#F8FAFC" font-size="10" font-weight="700" class="font-ui">{_esc(ctx["label_d3"][:18].upper())}</text>',
        '  <text x="1008" y="686" fill="#F8FAFC" font-size="10" font-weight="700" class="font-ui">VOLUME</text>',
        f'  <text x="1088" y="686" fill="#F8FAFC" font-size="10" font-weight="700" class="font-ui">{_esc(ctx["label_m1"][:14].upper())} (DATA BAR)</text>',
        '  <text x="1256" y="686" fill="#F8FAFC" font-size="10" font-weight="700" class="font-ui">VAR. YoY</text>',
        '  <text x="1336" y="686" fill="#F8FAFC" font-size="10" font-weight="700" class="font-ui">STATUS META</text>',
    ])

    if tem_amostra and vis.get("matriz"):
        table_rows = vis["matriz"][:6]
    else:
        table_rows = [
            ("Unidade Salvador Centro", "9.840", "R$ 15,4 M", 132, "+18,4%", "ACIMA DA META", "#DCFCE7", "#15803D"),
            ("Unidade Feira de Santana", "7.410", "R$ 11,2 M", 98, "+11,2%", "DENTRO DA META", "#DCFCE7", "#15803D"),
            ("Unidade Vitória da Conquista", "5.920", "R$ 8,7 M", 76, "+4,5%", "DENTRO DA META", "#DBEAFE", "#1D4ED8"),
            ("Unidade Camaçari / RMS", "4.890", "R$ 7,1 M", 62, "-2,1%", "ATENÇÃO", "#FEF3C7", "#B45309"),
            ("Unidade Ilhéus / Itabuna", "3.930", "R$ 5,6 M", 48, "+9,0%", "DENTRO DA META", "#DCFCE7", "#15803D"),
            ("Não Informado (SK = -1)", "420", "R$ 0,7 M", 12, "-34,0%", "AUDITAR ORIGEM", "#FEE2E2", "#B91C1C"),
        ]
    ty = 700
    for idx, (t_unid, t_vol, t_val, bar_w, t_yoy, t_status, st_bg, st_fg) in enumerate(table_rows):
        row_bg = table_row_even if idx % 2 == 0 else bg_card
        yoy_color = accent_green if t_yoy.startswith("+") else accent_red
        svg.extend([
            f'  <rect x="810" y="{ty}" width="588" height="36" fill="{row_bg}"/>',
            f'  <line x1="810" y1="{ty+36}" x2="1398" y2="{ty+36}" stroke="{border_card}" stroke-width="0.8"/>',
            f'  <text x="822" y="{ty+22}" fill="{text_primary}" font-size="10.5" font-weight="600" class="font-ui">{_esc(t_unid)}</text>',
            f'  <text x="1008" y="{ty+22}" fill="{text_secondary}" font-size="10.5" class="font-mono">{t_vol}</text>',
            f'  <rect x="1088" y="{ty+9}" width="144" height="18" rx="3" fill="{bg_card_alt}"/>',
            f'  <rect x="1088" y="{ty+9}" width="{bar_w}" height="18" rx="3" fill="#5B9BD5" fill-opacity="0.45"/>',
            f'  <text x="1094" y="{ty+22}" fill="{text_primary}" font-size="10" font-weight="700" class="font-mono">{t_val}</text>',
            f'  <text x="1256" y="{ty+22}" fill="{yoy_color}" font-size="10.5" font-weight="700" class="font-mono">{t_yoy}</text>',
            f'  <rect x="1322" y="{ty+8}" width="72" height="20" rx="10" fill="{st_bg}"/>',
            f'  <text x="1358" y="{ty+21}" text-anchor="middle" fill="{st_fg}" font-size="7.8" font-weight="800" class="font-ui">{t_status}</text>',
        ])
        ty += 36

    # ==========================================================================
    # CAMADA DEV MODE (FIGCRAFT REDLINES + CALLOUTS NUMERADOS ① A ⑦)
    # ==========================================================================
    if dev_mode:
        svg.extend([
            "",
            "  <!-- ==================== CAMADA FIGCRAFT DEV MODE (REDLINES & DAX SPECS) ==================== -->",
            f'  <rect x="252" y="18" width="1168" height="74" rx="12" fill="none" stroke="{dev_magenta}" stroke-width="2" stroke-dasharray="6,4"/>',
            f'  <rect x="252" y="108" width="1168" height="138" rx="12" fill="none" stroke="{dev_magenta}" stroke-width="2" stroke-dasharray="6,4"/>',
            f'  <rect x="252" y="262" width="756" height="330" rx="12" fill="none" stroke="{dev_magenta}" stroke-width="2" stroke-dasharray="6,4"/>',
            f'  <rect x="1024" y="262" width="396" height="330" rx="12" fill="none" stroke="{dev_magenta}" stroke-width="2" stroke-dasharray="6,4"/>',
            f'  <rect x="252" y="608" width="520" height="330" rx="12" fill="none" stroke="{dev_magenta}" stroke-width="2" stroke-dasharray="6,4"/>',
            f'  <rect x="788" y="608" width="632" height="330" rx="12" fill="none" stroke="{dev_magenta}" stroke-width="2" stroke-dasharray="6,4"/>',
        ])

        callouts = [
            ("1", 700, 26, 290, 40, "① SLICERS GLOBAIS (SYNC SLICERS)", f"{ctx['dim_tempo']} + {ctx['d1']} (FLG_ATUAL='S')"),
            ("2", 262, 114, 270, 40, "② CARDS KPI + SPARKLINE", f"SUM({ctx['nome_fato']}[{ctx['m1']}]) + DIVIDE()"),
            ("3", 826, 114, 300, 40, "③ MONITOR DE SENTINELAS (-1)", "Audita % de FKs que caíram em SK = -1"),
            ("4", 520, 322, 310, 42, "④ SÉRIE TEMPORAL + YOY", f"SAMEPERIODLASTYEAR({ctx['dim_tempo']}[DT_REFERENCIA])"),
            ("5", 1046, 322, 290, 42, "⑤ COMPOSIÇÃO (DONUT CHART)", f"DIVIDE([Total], CALCULATE([Total], ALL({ctx['d2']})))"),
            ("6", 460, 618, 295, 42, "⑥ RANKING TOP-N HORIZONTAL", f"RANKX(ALLSELECTED({ctx['d1']}), [Total {ctx['label_m1']}])"),
            ("7", 1080, 618, 325, 42, "⑦ MATRIZ + DATA BARS (#5B9BD5)", "Formatação Condicional por [Status Meta]"),
        ]
        for num, cx_b, cy_b, cw_b, ch_b, c_title, c_sub in callouts:
            svg.extend([
                '  <g filter="url(#calloutShadow)">',
                f'    <rect x="{cx_b}" y="{cy_b}" width="{cw_b}" height="{ch_b}" rx="8" fill="#881337" stroke="#FDA4AF" stroke-width="1.5"/>',
                f'    <circle cx="{cx_b+18}" cy="{cy_b+ch_b/2:.1f}" r="11" fill="#F43F5E"/>',
                f'    <text x="{cx_b+18}" y="{cy_b+ch_b/2+4:.1f}" text-anchor="middle" fill="#FFFFFF" font-size="11" font-weight="800" class="font-ui">{num}</text>',
                f'    <text x="{cx_b+36}" y="{cy_b+16}" fill="#FFE4E6" font-size="10" font-weight="800" class="font-ui">{_esc(c_title)}</text>',
                f'    <text x="{cx_b+36}" y="{cy_b+31}" fill="#FECDD3" font-size="9" class="font-mono">{_esc(c_sub[:44])}</text>',
                '  </g>',
            ])

    svg.append("</svg>")
    return "\n".join(svg)


def gerar_preview_painel_bi_html(
    dims: List[dict],
    fatos: List[dict],
    schema: str,
    projeto: str,
    dados_amostra: Optional[dict] = None,
    base_dir: Optional[Path] = None,
    caminho_amostras: Optional[Path] = None,
    guia_md_texto: Optional[str] = None,
) -> str:
    """
    Gera o visualizador HTML interativo (`preview_painel_bi.html`) contendo:
      - Toggle ☀️ Light Mode (Institucional) vs 🌙 Dark Mode (Executivo)
      - Toggle 👁️ Visão Executiva (Cliente) vs 🛠️ Visão Dev Mode (Redlines DAX/SQL)
      - Botão 📸 Baixar PNG Alta Resolução (2880x1920 2x Retina via HTML5 Canvas)
      - Tabela de Prova Real Pós-Carga (`DIM_*` + `FATO_*`) e Conciliação de Medidas DAX.
    """
    ctx = _extrair_contexto_bi(dims, fatos, projeto)
    if dados_amostra is None and (base_dir is not None or caminho_amostras is not None):
        try:
            dados_amostra = avaliar_medidas_guia_bi_amostra(
                dims, fatos, schema, projeto,
                base_dir=base_dir,
                caminho_amostras=caminho_amostras,
                guia_md_texto=guia_md_texto,
            )
        except Exception:
            dados_amostra = None
    svg_light_exec = gerar_mockup_painel_bi_svg(dims, fatos, schema, projeto, dev_mode=False, tema="light", dados_amostra=dados_amostra)
    svg_light_dev = gerar_mockup_painel_bi_svg(dims, fatos, schema, projeto, dev_mode=True, tema="light", dados_amostra=dados_amostra)
    svg_dark_exec = gerar_mockup_painel_bi_svg(dims, fatos, schema, projeto, dev_mode=False, tema="dark", dados_amostra=dados_amostra)
    svg_dark_dev = gerar_mockup_painel_bi_svg(dims, fatos, schema, projeto, dev_mode=True, tema="dark", dados_amostra=dados_amostra)

    bloco_prova_html = ""
    if dados_amostra and dados_amostra.get("tem_amostra"):
        linhas_med_html = []
        for mr in dados_amostra.get("medidas_avaliadas", []):
            cor_st = "#22c55e" if mr["status"] == "OK" else "#f59e0b"
            txt_st = "✅ EXATA" if mr["status"] == "OK" else "⚠️ PARCIALMENTE CORRETA (CORRIGIDA)"
            corr_html = (
                f"<div style='margin-top:6px;padding:6px 8px;background:#064e3b;border:1px solid #10b981;border-radius:6px;font-size:11px;color:#d1fae5;'>"
                f"<b>🔧 DAX Corrigido:</b> <code>{_esc(mr['nome'])} = {_esc(mr['dax_corrigido'])}</code></div>"
                if mr.get("dax_corrigido")
                else ""
            )
            diag_html = "<br/>".join(_esc(d) for d in mr.get("diagnosticos", [])) or "Cálculo validado na amostra pós-carga."
            linhas_med_html.append(
                f"<tr>"
                f"<td style='padding:10px;border-bottom:1px solid #334155;font-weight:700;color:#f8fafc;'>[{_esc(mr['nome'])}]</td>"
                f"<td style='padding:10px;border-bottom:1px solid #334155;font-family:monospace;font-size:13px;font-weight:700;color:#60a5fa;'>{_esc(mr['valor_formatado'])}</td>"
                f"<td style='padding:10px;border-bottom:1px solid #334155;color:{cor_st};font-weight:700;font-size:11.5px;'>{txt_st}</td>"
                f"<td style='padding:10px;border-bottom:1px solid #334155;font-size:11.5px;color:#cbd5e1;'>"
                f"<div><code>{_esc(mr['expressao'])}</code></div>"
                f"<div style='margin-top:4px;color:#94a3b8;'>{diag_html}</div>{corr_html}</td>"
                f"</tr>"
            )
        bloco_prova_html = f"""
    <section style="margin-top:22px;background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:18px;">
      <h2 style="margin:0 0 8px;font-size:15px;color:#93c5fd;">🧪 Prova Real Pós-Carga (DIM + FATO) e Conciliação de Medidas DAX</h2>
      <p style="margin:0 0 12px;font-size:12.5px;color:#cbd5e1;">
        Amostra avaliada em banco relacional in-memory: <b>{dados_amostra.get('total_linhas_fato', 0)} linhas</b> em <code>{_esc(ctx['nome_fato'])}</code>
        • Sentinelas (<code>SK = -1</code>): <b>{dados_amostra.get('qtd_sentinela_fato', 0)} ({dados_amostra.get('pct_sentinela_fato', 0.0):.1f}%)</b>
        • FKs Órfãs: <b>{dados_amostra.get('qtd_orfaos_fato', 0)}</b>
        • Medidas auditadas: <b>{len(dados_amostra.get('medidas_avaliadas', []))}</b> (Parcialmente corretas corrigidas: <b>{dados_amostra.get('qtd_parciais', 0)}</b>)
      </p>
      <div style="overflow-x:auto;">
        <table style="width:100%;border-collapse:collapse;text-align:left;">
          <thead>
            <tr style="background:#0f172a;color:#94a3b8;font-size:11px;text-transform:uppercase;">
              <th style="padding:10px;border-bottom:1px solid #334155;">Medida DAX (Guia BI)</th>
              <th style="padding:10px;border-bottom:1px solid #334155;">Valor Calculado na Amostra</th>
              <th style="padding:10px;border-bottom:1px solid #334155;">Status Conciliação</th>
              <th style="padding:10px;border-bottom:1px solid #334155;">Expressão &amp; Diagnóstico / Correção</th>
            </tr>
          </thead>
          <tbody>
            {''.join(linhas_med_html)}
          </tbody>
        </table>
      </div>
    </section>
"""

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Preview Interativo do Painel BI — {_esc(ctx['projeto'])}</title>
  <style>
    :root {{
      --bg: #0f172a;
      --panel: #1e293b;
      --border: #334155;
      --text: #f8fafc;
      --muted: #94a3b8;
      --accent: #3b82f6;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      padding: 0;
      background: var(--bg);
      color: var(--text);
      font-family: "Segoe UI", Inter, system-ui, sans-serif;
    }}
    .topbar {{
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 14px 24px;
      background: var(--panel);
      border-bottom: 1px solid var(--border);
      position: sticky;
      top: 0;
      z-index: 20;
    }}
    .brand h1 {{
      margin: 0;
      font-size: 16px;
      font-weight: 800;
    }}
    .brand p {{
      margin: 2px 0 0;
      font-size: 12px;
      color: var(--muted);
    }}
    .controls {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }}
    button {{
      background: #0f172a;
      color: var(--text);
      border: 1px solid var(--border);
      padding: 8px 14px;
      border-radius: 8px;
      font-size: 12.5px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.15s ease;
    }}
    button:hover {{ border-color: var(--accent); }}
    button.active {{
      background: var(--accent);
      border-color: var(--accent);
      color: #fff;
    }}
    button.btn-png {{
      background: #059669;
      border-color: #10b981;
      color: #fff;
    }}
    .viewport {{
      max-width: 1480px;
      margin: 20px auto;
      padding: 0 18px 36px;
    }}
    .canvas-wrap {{
      background: #0b0f19;
      border: 1px solid var(--border);
      border-radius: 14px;
      overflow: hidden;
      box-shadow: 0 20px 50px rgba(0,0,0,0.45);
    }}
    .svg-layer {{ display: none; }}
    .svg-layer.visible {{ display: block; }}
    .spec-grid {{
      margin-top: 22px;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(310px, 1fr));
      gap: 14px;
    }}
    .spec-card {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 14px 16px;
    }}
    .spec-card h3 {{
      margin: 0 0 6px;
      font-size: 13.5px;
      color: #93c5fd;
    }}
    .spec-card code {{
      display: block;
      background: #0f172a;
      padding: 8px 10px;
      border-radius: 6px;
      font-size: 11.5px;
      color: #e2e8f0;
      overflow-x: auto;
      margin-top: 6px;
    }}
  </style>
</head>
<body>
  <header class="topbar">
    <div class="brand">
      <h1>🎨 Mockup Homologável do Painel Power BI — {_esc(ctx['projeto'])}</h1>
      <p>Gerado automaticamente pelo motor visual NINHO (FigCraft + GridCraft) a partir de {_esc(schema)}.{_esc(ctx['nome_fato'])}</p>
    </div>
    <div class="controls">
      <button id="btnExec" class="active" onclick="setMode('exec')">👁️ Visão Executiva (Cliente)</button>
      <button id="btnDev" onclick="setMode('dev')">🛠️ Visão Dev Mode (Redlines DAX/SQL)</button>
      <button id="btnLight" class="active" onclick="setTheme('light')">☀️ Tema Claro (Institucional)</button>
      <button id="btnDark" onclick="setTheme('dark')">🌙 Tema Escuro (Executivo)</button>
      <button class="btn-png" onclick="baixarPNG()">📸 Baixar PNG (Alta Resolução 2x)</button>
    </div>
  </header>

  <main class="viewport">
    <div class="canvas-wrap" id="mockupContainer">
      <div id="layer_light_exec" class="svg-layer visible">{svg_light_exec}</div>
      <div id="layer_light_dev" class="svg-layer">{svg_light_dev}</div>
      <div id="layer_dark_exec" class="svg-layer">{svg_dark_exec}</div>
      <div id="layer_dark_dev" class="svg-layer">{svg_dark_dev}</div>
    </div>

    <section class="spec-grid">
      <div class="spec-card">
        <h3>① Slicers Globais &amp; Proteção SCD Tipo 2</h3>
        <p style="margin:0;font-size:12px;color:#cbd5e1;">Sincronizar em todas as páginas via <b>View &gt; Sync Slicers</b> (Grupo: <code>Filtro_Global</code>).</p>
        <code>{_esc(ctx['dim_tempo'])}[NUM_ANO] | {_esc(ctx['d1'])}[{_esc(ctx['col_d1'])}] (FLG_ATUAL = 'S')</code>
      </div>
      <div class="spec-card">
        <h3>② &amp; ③ Cards Principais + Auditoria Sentinela (-1)</h3>
        <p style="margin:0;font-size:12px;color:#cbd5e1;">Medidas base seguras com <code>DIVIDE()</code> e monitoramento da linha default.</p>
        <code>[Total {_esc(ctx['label_m1'])}] = SUM({_esc(ctx['nome_fato'])}[{_esc(ctx['m1'])}])</code>
      </div>
      <div class="spec-card">
        <h3>④ &amp; ⑤ Inteligência Temporal YoY &amp; Rosca</h3>
        <p style="margin:0;font-size:12px;color:#cbd5e1;">Comparativo contínuo Ano Atual vs Ano Anterior e participação percentual.</p>
        <code>[Total LY] = CALCULATE([Total {_esc(ctx['label_m1'])}], SAMEPERIODLASTYEAR({_esc(ctx['dim_tempo'])}[DT_REFERENCIA]))</code>
      </div>
      <div class="spec-card">
        <h3>⑥ &amp; ⑦ Ranking Top-N &amp; Matriz com Data Bars</h3>
        <p style="margin:0;font-size:12px;color:#cbd5e1;">Data Bars azuis (<code>#5B9BD5</code>) e Status Pills dinâmicos por meta.</p>
        <code>[Ranking] = RANKX(ALLSELECTED({_esc(ctx['d1'])}[{_esc(ctx['col_d1'])}]), [Total {_esc(ctx['label_m1'])}], , DESC, Dense)</code>
      </div>
    </section>
    {bloco_prova_html}
  </main>

  <script>
    let currentMode = 'exec';
    let currentTheme = 'light';

    function updateLayers() {{
      document.querySelectorAll('.svg-layer').forEach(el => el.classList.remove('visible'));
      const activeId = 'layer_' + currentTheme + '_' + currentMode;
      const target = document.getElementById(activeId);
      if (target) target.classList.add('visible');

      document.getElementById('btnExec').classList.toggle('active', currentMode === 'exec');
      document.getElementById('btnDev').classList.toggle('active', currentMode === 'dev');
      document.getElementById('btnLight').classList.toggle('active', currentTheme === 'light');
      document.getElementById('btnDark').classList.toggle('active', currentTheme === 'dark');
    }}

    function setMode(m) {{ currentMode = m; updateLayers(); }}
    function setTheme(t) {{ currentTheme = t; updateLayers(); }}

    function baixarPNG() {{
      const visibleLayer = document.querySelector('.svg-layer.visible svg');
      if (!visibleLayer) return;
      const serializer = new XMLSerializer();
      const svgStr = serializer.serializeToString(visibleLayer);
      const svgBlob = new Blob([svgStr], {{type: 'image/svg+xml;charset=utf-8'}});
      const url = URL.createObjectURL(svgBlob);
      const img = new Image();
      img.onload = function() {{
        const canvas = document.createElement('canvas');
        canvas.width = 2880;
        canvas.height = 1920;
        const ctx2d = canvas.getContext('2d');
        ctx2d.scale(2, 2);
        ctx2d.drawImage(img, 0, 0, 1440, 960);
        URL.revokeObjectURL(url);
        const a = document.createElement('a');
        a.download = 'mockup_painel_bi_{_esc(ctx["projeto"].lower())}_' + currentTheme + '_' + currentMode + '.png';
        a.href = canvas.toDataURL('image/png');
        a.click();
      }};
      img.src = url;
    }}
  </script>
</body>
</html>
"""
