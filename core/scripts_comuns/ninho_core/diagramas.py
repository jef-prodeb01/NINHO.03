"""
Diagramas SVG: Star Schema, canvas de mapeamentos ODI 12c e canvas de pipelines/workflows
Apache Hop (com documentação DocBuilder).

Extraído de gerador_artefatos_visuais.py (que mantém uma fachada de reimportação).
"""

import math
import xml.etree.ElementTree as ET
from ninho_core import xml_seguro
from ninho_core.visual_comum import (
    _esc,
    _normalizar_dims_fatos,
)
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def gerar_diagrama_star_schema_svg(dims: List[dict], fatos: List[dict], schema: str, projeto: str) -> str:
    """
    Gera o diagrama vetorial SVG do Star Schema (`diagrama_star_schema.svg`) com a tabela
    FATO_* no centro, dimensões satélites ao redor, conectores ortogonais (1 -> *),
    destaque de PK/FK/SCD2 e badge de Linha Sentinela (-1).
    """
    dims, fatos = _normalizar_dims_fatos(dims, fatos)
    fato = fatos[0] if fatos else {"nome": f"FATO_{projeto.upper()}", "colunas": []}
    nome_fato = fato.get("nome", f"FATO_{projeto.upper()}")
    cols_fato = fato.get("colunas", [])[:10]

    dims_plot = dims[:6] if dims else [
        {"nome": "DIM_TEMPO", "colunas": [{"nome": "SK_TEMPO", "papel": "PK"}, {"nome": "DT_REFERENCIA", "papel": "NK"}]},
        {"nome": "DIM_UNIDADE", "colunas": [{"nome": "SK_UNIDADE", "papel": "PK"}, {"nome": "COD_UNIDADE", "papel": "NK"}, {"nome": "FLG_ATUAL", "papel": "SCD2"}]},
        {"nome": "DIM_CATEGORIA", "colunas": [{"nome": "SK_CATEGORIA", "papel": "PK"}, {"nome": "DES_CATEGORIA", "papel": "ATRIBUTO"}]},
        {"nome": "DIM_LOCALIDADE", "colunas": [{"nome": "SK_LOCALIDADE", "papel": "PK"}, {"nome": "NOM_MUNICIPIO", "papel": "ATRIBUTO"}]},
    ]

    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 820" width="100%" height="100%">',
        "  <defs>",
        '    <style>',
        '      .font-ui { font-family: "Segoe UI", Inter, system-ui, sans-serif; }',
        '      .font-mono { font-family: "JetBrains Mono", Consolas, monospace; }',
        "    </style>",
        '    <filter id="boxShadow" x="-5%" y="-5%" width="110%" height="115%">',
        '      <feDropShadow dx="0" dy="4" stdDeviation="6" flood-color="#0F172A" flood-opacity="0.12"/>',
        "    </filter>",
        "  </defs>",
        '  <rect width="1280" height="820" fill="#F8FAFC"/>',
        '  <rect x="24" y="20" width="1232" height="58" rx="10" fill="#0F172A"/>',
        f'  <text x="44" y="46" fill="#FFFFFF" font-size="16" font-weight="800" class="font-ui">⭐ Diagrama Dimensional Star Schema — {_esc(schema)}.{_esc(nome_fato)}</text>',
        '  <text x="44" y="64" fill="#94A3B8" font-size="11" class="font-ui">Relacionamentos Single Direction (1 ───&lt; *) • Integridade Referencial Garantida por SK = -1 (Não Informado)</text>',
    ]

    # Posições satélites para até 6 dimensões ao redor do centro (cx=640, cy=430)
    slots = [
        (50, 110),
        (930, 110),
        (50, 355),
        (930, 355),
        (50, 595),
        (930, 595),
    ]
    fx, fy, fw, fh = 470, 235, 340, 340

    # Conectores ortogonais antes das caixas
    for idx, d in enumerate(dims_plot):
        dx, dy = slots[idx]
        dw, dh = 300, 190
        start_x = dx + dw if dx < fx else dx
        start_y = dy + dh / 2
        end_x = fx if dx < fx else fx + fw
        end_y = fy + 65 + idx * 42
        mid_x = (start_x + end_x) / 2
        svg.extend([
            f'  <path d="M {start_x} {start_y} L {mid_x} {start_y} L {mid_x} {end_y} L {end_x} {end_y}" fill="none" stroke="#2563EB" stroke-width="2.2"/>',
            f'  <circle cx="{start_x}" cy="{start_y}" r="10" fill="#1D4ED8"/>',
            f'  <text x="{start_x}" y="{start_y+4}" text-anchor="middle" fill="#FFFFFF" font-size="10" font-weight="800" class="font-mono">1</text>',
            f'  <circle cx="{end_x}" cy="{end_y}" r="10" fill="#D97706"/>',
            f'  <text x="{end_x}" y="{end_y+4}" text-anchor="middle" fill="#FFFFFF" font-size="11" font-weight="800" class="font-mono">*</text>',
        ])

    # Caixa Central FATO_*
    svg.extend([
        '  <g filter="url(#boxShadow)">',
        f'    <rect x="{fx}" y="{fy}" width="{fw}" height="{fh}" rx="12" fill="#FFFFFF" stroke="#D97706" stroke-width="2.5"/>',
        f'    <rect x="{fx}" y="{fy}" width="{fw}" height="44" rx="10" fill="#B45309"/>',
        f'    <text x="{fx+16}" y="{fy+27}" fill="#FFFFFF" font-size="13.5" font-weight="800" class="font-mono">📊 {_esc(nome_fato)}</text>',
        f'    <rect x="{fx+fw-90}" y="{fy+12}" width="76" height="20" rx="10" fill="#FEF3C7"/>',
        f'    <text x="{fx+fw-52}" y="{fy+26}" text-anchor="middle" fill="#92400E" font-size="9.5" font-weight="800" class="font-ui">TABELA FATO</text>',
        '  </g>',
    ])

    cy_col = fy + 66
    for c in cols_fato[:9]:
        papel = c.get("papel", "ATRIBUTO")
        badge_bg = "#DBEAFE" if papel == "FK" else ("#DCFCE7" if papel == "METRICA" else "#F1F5F9")
        badge_fg = "#1D4ED8" if papel == "FK" else ("#15803D" if papel == "METRICA" else "#475569")
        svg.extend([
            f'  <rect x="{fx+14}" y="{cy_col-12}" width="54" height="17" rx="4" fill="{badge_bg}"/>',
            f'  <text x="{fx+41}" y="{cy_col}" text-anchor="middle" fill="{badge_fg}" font-size="8.5" font-weight="800" class="font-mono">{_esc(papel[:7])}</text>',
            f'  <text x="{fx+76}" y="{cy_col}" fill="#0F172A" font-size="10.5" font-weight="600" class="font-mono">{_esc(c["nome"][:28])}</text>',
        ])
        cy_col += 26

    # Caixas das Dimensões Satélites
    for idx, d in enumerate(dims_plot):
        dx, dy = slots[idx]
        dw, dh = 300, 190
        d_nome = d.get("nome", f"DIM_{idx+1}")
        d_cols = d.get("colunas", [])[:5]
        svg.extend([
            '  <g filter="url(#boxShadow)">',
            f'    <rect x="{dx}" y="{dy}" width="{dw}" height="{dh}" rx="10" fill="#FFFFFF" stroke="#2563EB" stroke-width="1.8"/>',
            f'    <rect x="{dx}" y="{dy}" width="{dw}" height="36" rx="8" fill="#1E40AF"/>',
            f'    <text x="{dx+14}" y="{dy+23}" fill="#FFFFFF" font-size="12" font-weight="800" class="font-mono">🗂️ {_esc(d_nome[:24])}</text>',
            f'    <rect x="{dx+dw-78}" y="{dy+9}" width="66" height="18" rx="9" fill="#DBEAFE"/>',
            f'    <text x="{dx+dw-45}" y="{dy+21}" text-anchor="middle" fill="#1E3A8A" font-size="8.5" font-weight="800" class="font-ui">SK -1 OK</text>',
            '  </g>',
        ])
        cy_d = dy + 56
        for c in d_cols:
            papel = c.get("papel", "ATTR")
            svg.extend([
                f'  <text x="{dx+14}" y="{cy_d}" fill="#2563EB" font-size="9.5" font-weight="800" class="font-mono">[{_esc(papel[:4])}]</text>',
                f'  <text x="{dx+62}" y="{cy_d}" fill="#1E293B" font-size="10.5" class="font-mono">{_esc(c["nome"][:25])}</text>',
            ])
            cy_d += 23
        svg.append(f'  <text x="{dx+14}" y="{dy+dh-12}" fill="#64748B" font-size="9" class="font-ui">• SCD Tipo 2 (DT_INICIO / DT_FIM / FLG_ATUAL)</text>')

    svg.append("</svg>")
    return "\n".join(svg)


def gerar_mapa_canvas_odi_svg(dims: List[dict], fatos: List[dict], schema: str, projeto: str, estrategia: str = "A") -> str:
    """
    Gera o diagrama vetorial SVG do Canvas do ODI 12c (`mapa_canvas_odi.svg`) com
    trilha de Dimensão (`MAP_DIM_*`) e trilha de Fato (`MAP_FATO_*`) + Callouts numerados
    no estilo PhotoCraft/FigCraft explicando cada componente do Canvas.
    """
    dims, fatos = _normalizar_dims_fatos(dims, fatos)
    fato = fatos[0]["nome"] if fatos else f"FATO_{projeto.upper()}"
    dim_ex = dims[0]["nome"] if dims else "DIM_UNIDADE"
    stg_fato = fato.replace("FATO_", "STG_").replace("FAT_", "STG_")
    stg_dim = dim_ex.replace("DIM_", "STG_")

    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1360 780" width="100%" height="100%">',
        "  <defs>",
        '    <style>',
        '      .font-ui { font-family: "Segoe UI", Inter, system-ui, sans-serif; }',
        '      .font-mono { font-family: "JetBrains Mono", Consolas, monospace; }',
        "    </style>",
        '    <filter id="nodeShadow" x="-5%" y="-5%" width="110%" height="115%">',
        '      <feDropShadow dx="0" dy="3" stdDeviation="5" flood-color="#0F172A" flood-opacity="0.12"/>',
        "    </filter>",
        '    <marker id="arrowBlue" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">',
        '      <path d="M 0 1 L 10 5 L 0 9 z" fill="#2563EB"/>',
        "    </marker>",
        "  </defs>",
        '  <rect width="1360" height="780" fill="#F8FAFC"/>',
        '  <rect x="24" y="18" width="1312" height="58" rx="10" fill="#0F172A"/>',
        f'  <text x="44" y="44" fill="#FFFFFF" font-size="16" font-weight="800" class="font-ui">⚙️ Topologia Visual do Canvas ODI 12c — Projeto {_esc(projeto.upper())} (Estratégia {_esc(estrategia)})</text>',
        '  <text x="44" y="62" fill="#94A3B8" font-size="11" class="font-ui">Guia Visual de Componentes para Construção dos Mappings MAP_DIM_* (SCD Tipo 2) e MAP_FATO_* no Oracle Data Integrator 12c</text>',
        "",
        "  <!-- Raia 1: Mapping de Dimensão SCD Tipo 2 -->",
        '  <rect x="24" y="92" width="1312" height="210" rx="12" fill="#FFFFFF" stroke="#CBD5E1" filter="url(#nodeShadow)"/>',
        '  <text x="44" y="118" fill="#1E3A8A" font-size="13.5" font-weight="800" class="font-ui">TRILHA A — MAPPING DE DIMENSÃO (Padrão MAP_DIM_* com Slowly Changing Dimension Tipo 2)</text>',
    ]

    nodes_dim = [
        (48, 140, 210, 115, "#EFF6FF", "#2563EB", "1", f"DATASTORE: {stg_dim[:18]}", "Camada Staging (LKM None)", "SELECT * FROM STG_*"),
        (310, 140, 210, 115, "#FEF3C7", "#D97706", "2", "FILTER: FIL_VALIDOS", "Higienização de NK Nula", "NK IS NOT NULL"),
        (572, 140, 220, 115, "#F3E8FF", "#7C3AED", "3", "DISTINCT / DEDUP", "Deduplicação por NK", "ROW_NUMBER() = 1"),
        (844, 140, 220, 115, "#ECFDF5", "#059669", "4", "EXPRESSION: EXP_SCD2", "Padronização + Datas Vigência", "UPPER(TRIM(DES_*))"),
        (1112, 140, 200, 115, "#DBEAFE", "#1D4ED8", "5", f"TARGET: {dim_ex[:18]}", "IKM Oracle Slowly Changing Dim", "SEQ_DIM_*.NEXTVAL"),
    ]
    for nx, ny, nw, nh, bg, bd, num, t1, t2, t3 in nodes_dim:
        svg.extend([
            f'  <rect x="{nx}" y="{ny}" width="{nw}" height="{nh}" rx="10" fill="{bg}" stroke="{bd}" stroke-width="2"/>',
            f'  <circle cx="{nx+20}" cy="{ny+22}" r="11" fill="{bd}"/>',
            f'  <text x="{nx+20}" y="{ny+26}" text-anchor="middle" fill="#FFFFFF" font-size="11" font-weight="800" class="font-ui">{num}</text>',
            f'  <text x="{nx+38}" y="{ny+26}" fill="#0F172A" font-size="11" font-weight="800" class="font-mono">{_esc(t1)}</text>',
            f'  <text x="{nx+16}" y="{ny+56}" fill="#334155" font-size="10.5" font-weight="600" class="font-ui">{_esc(t2)}</text>',
            f'  <rect x="{nx+14}" y="{ny+72}" width="{nw-28}" height="26" rx="5" fill="#FFFFFF" stroke="{bd}" stroke-width="0.8"/>',
            f'  <text x="{nx+22}" y="{ny+89}" fill="#0F172A" font-size="9.5" class="font-mono">{_esc(t3)}</text>',
        ])

    for x_start, x_end in [(258, 306), (520, 568), (792, 840), (1064, 1108)]:
        svg.append(f'  <line x1="{x_start}" y1="198" x2="{x_end}" y2="198" stroke="#2563EB" stroke-width="2.4" marker-end="url(#arrowBlue)"/>')

    # Raia 2: Mapping de Fato
    svg.extend([
        "  <!-- Raia 2: Mapping de Tabela Fato -->",
        '  <rect x="24" y="320" width="1312" height="235" rx="12" fill="#FFFFFF" stroke="#CBD5E1" filter="url(#nodeShadow)"/>',
        f'  <text x="44" y="346" fill="#92400E" font-size="13.5" font-weight="800" class="font-ui">TRILHA B — MAPPING DE TABELA FATO (MAP_{_esc(fato[:24])} com Lookups Left Outer Join e Fallback -1)</text>',
    ])

    nodes_fato = [
        (48, 372, 210, 125, "#FFFBEB", "#D97706", "1", f"SOURCE: {stg_fato[:18]}", "Extração Incremental / Janela", "DT_CARGA >= V_DT_INI"),
        (310, 372, 210, 125, "#F3E8FF", "#7C3AED", "2", "DEDUP: RN_TRANSACAO", "Evita Duplicidade no Grão", "PARTITION BY ID_ORIGEM"),
        (572, 372, 235, 125, "#EFF6FF", "#2563EB", "3", "LOOKUP: LKP_DIM_*", "Left Join Vigente ou Temporal", "FLG_ATUAL = 'S' (+)"),
        (856, 372, 215, 125, "#ECFDF5", "#059669", "4", "EXP: NVL(SK, -1)", "Blindagem de Órfãos + Métricas", "COALESCE(SK_DIM, -1)"),
        (1116, 372, 196, 125, "#FEF2F2", "#DC2626", "5", f"TARGET: {fato[:18]}", "IKM Oracle Incremental / Append", "Hint /*+ APPEND */"),
    ]
    for nx, ny, nw, nh, bg, bd, num, t1, t2, t3 in nodes_fato:
        svg.extend([
            f'  <rect x="{nx}" y="{ny}" width="{nw}" height="{nh}" rx="10" fill="{bg}" stroke="{bd}" stroke-width="2"/>',
            f'  <circle cx="{nx+20}" cy="{ny+22}" r="11" fill="{bd}"/>',
            f'  <text x="{nx+20}" y="{ny+26}" text-anchor="middle" fill="#FFFFFF" font-size="11" font-weight="800" class="font-ui">{num}</text>',
            f'  <text x="{nx+38}" y="{ny+26}" fill="#0F172A" font-size="11" font-weight="800" class="font-mono">{_esc(t1)}</text>',
            f'  <text x="{nx+16}" y="{ny+56}" fill="#334155" font-size="10.5" font-weight="600" class="font-ui">{_esc(t2)}</text>',
            f'  <rect x="{nx+14}" y="{ny+74}" width="{nw-28}" height="28" rx="5" fill="#FFFFFF" stroke="{bd}" stroke-width="0.8"/>',
            f'  <text x="{nx+22}" y="{ny+92}" fill="#0F172A" font-size="9.5" class="font-mono">{_esc(t3)}</text>',
        ])

    for x_start, x_end in [(258, 306), (520, 568), (807, 852), (1071, 1112)]:
        svg.append(f'  <line x1="{x_start}" y1="434" x2="{x_end}" y2="434" stroke="#2563EB" stroke-width="2.4" marker-end="url(#arrowBlue)"/>')

    # Rodapé: Callouts Numerados PhotoCraft / Checklist de Orquestração do Pacote PKG_CARGA_DW
    svg.extend([
        "  <!-- Raia 3: Orquestração do Package ODI (PKG_CARGA_DW) -->",
        '  <rect x="24" y="572" width="1312" height="186" rx="12" fill="#0F172A"/>',
        '  <text x="44" y="600" fill="#F8FAFC" font-size="13.5" font-weight="800" class="font-ui">📦 ORQUESTRAÇÃO NO PACOTE ODI 12C (PACK_CARGA_DW) — SEQUÊNCIA DE EXECUÇÃO OBRIGATÓRIA</text>',
    ])

    pkg_steps = [
        ("PASSO 1", "PRC_LINHA_DEFAULT", "Garante registro sentinela SK = -1 em todas as DIM_*", "#3B82F6"),
        ("PASSO 2", "MAP_DIM_* (Paralelo/Seq)", "Atualiza dimensões SCD2 antes da carga da Fato", "#10B981"),
        ("PASSO 3", "PRC_PRE_CARGA_FATO", "Marca índices Bitmap UNUSABLE antes do Bulk Insert", "#F59E0B"),
        ("PASSO 4", f"MAP_{fato[:18]}", "Executa carga da Fato com COALESCE(SK, -1)", "#8B5CF6"),
        ("PASSO 5", "PRC_POS_CARGA_FATO", "REBUILD NOLOGGING dos índices + DBMS_STATS", "#EC4899"),
    ]
    px = 44
    for p_step, p_name, p_desc, p_col in pkg_steps:
        svg.extend([
            f'  <rect x="{px}" y="618" width="242" height="120" rx="8" fill="#1E293B" stroke="{p_col}" stroke-width="1.5"/>',
            f'  <rect x="{px+12}" y="630" width="68" height="20" rx="4" fill="{p_col}"/>',
            f'  <text x="{px+46}" y="644" text-anchor="middle" fill="#FFFFFF" font-size="9.5" font-weight="800" class="font-ui">{p_step}</text>',
            f'  <text x="{px+12}" y="672" fill="#FFFFFF" font-size="11" font-weight="700" class="font-mono">{_esc(p_name[:22])}</text>',
            f'  <text x="{px+12}" y="696" fill="#94A3B8" font-size="9.8" class="font-ui">{_esc(p_desc[:32])}</text>',
            f'  <text x="{px+12}" y="712" fill="#94A3B8" font-size="9.8" class="font-ui">{_esc(p_desc[32:])}</text>',
        ])
        px += 256

    svg.append("</svg>")
    return "\n".join(svg)


_HOP_TYPE_PALETTE: Dict[str, Tuple[str, str, str]] = {
    # (cor_borda, cor_fundo_badge, sigla_icone)
    "START": ("#16A34A", "#DCFCE7", "▶"),
    "SPECIAL": ("#16A34A", "#DCFCE7", "▶"),
    "SUCCESS": ("#16A34A", "#DCFCE7", "✓"),
    "ABORT": ("#DC2626", "#FEE2E2", "⛔"),
    "PIPELINE": ("#2563EB", "#DBEAFE", "PPL"),
    "WORKFLOW": ("#7C3AED", "#EDE9FE", "WF"),
    "PipelineExecutor": ("#2563EB", "#DBEAFE", "PPL"),
    "WorkflowExecutor": ("#7C3AED", "#EDE9FE", "WF"),
    "SQL": ("#0D9488", "#CCFBF1", "SQL"),
    "ExecSQL": ("#0D9488", "#CCFBF1", "SQL"),
    "TableInput": ("#0284C7", "#E0F2FE", "IN"),
    "TableOutput": ("#4F46E5", "#E0E7FF", "OUT"),
    "InsertUpdate": ("#4F46E5", "#E0E7FF", "UPS"),
    "OraBulkLoader": ("#EA580C", "#FFEDD5", "BLK"),
    "CSVInput": ("#0891B2", "#CFFAFE", "CSV"),
    "TextFileInput2": ("#0891B2", "#CFFAFE", "TXT"),
    "ExcelInput": ("#15803D", "#DCFCE7", "XLS"),
    "SelectValues": ("#6366F1", "#E0E7FF", "SEL"),
    "SetVariable": ("#D97706", "#FEF3C7", "VAR"),
    "GetVariable": ("#D97706", "#FEF3C7", "GET"),
    "WorkflowLogging": ("#9333EA", "#F3E8FF", "LOG"),
    "MAIL": ("#E11D48", "#FFE4E6", "✉"),
    "Mail": ("#E11D48", "#FFE4E6", "✉"),
    "SHELL": ("#334155", "#E2E8F0", "SH"),
    "Rest": ("#0EA5E9", "#E0F2FE", "API"),
}


def gerar_svg_canvas_hop(caminho_ou_xml: str, titulo: str = "") -> str:
    """
    Renderiza o Canvas vetorial SVG de uma Pipeline (`.hpl`), Workflow (`.hwf`) ou
    diretório Apache Hop 2.x, inspirado no `PipelineSvgPainter` e `WorkflowSvgPainter`
    de `ideias/hop-main/hop-main/plugins/misc/documentation`.

    Destaques visuais:
      - Lê coordenadas reais `<GUI><xloc>/<yloc>` (ou `<xloc>/<yloc>` de actions);
      - Renderiza sticky notes `<notepads><notepad>` com as cores originais do canvas;
      - Diferencia hops de Sucesso (`evaluation=Y` verde), Erro/Exceção (`evaluation=N` ou
        `<transform_error_handling>` vermelho), Incondicional (`unconditional=Y` âmbar) e
        Desabilitado (`enabled=N` cinza tracejado);
      - Sinaliza visualmente Transforms/Actions órfãos (`TRANS-002` / `WORKFLOW-002`) com
        halo vermelho de alerta.
    """
    xml_text = ""
    nome_arq = titulo or "esteira_hop"
    p_cand = Path(str(caminho_ou_xml)) if len(str(caminho_ou_xml)) < 400 and "<" not in str(caminho_ou_xml) else None

    if p_cand is not None and p_cand.exists():
        if p_cand.is_dir():
            hwfs = sorted(p_cand.rglob("*.hwf"))
            hpls = sorted(p_cand.rglob("*.hpl"))
            escolhido = hwfs[0] if hwfs else (hpls[0] if hpls else None)
            if escolhido is not None:
                nome_arq = escolhido.name
                xml_text = escolhido.read_text(encoding="utf-8", errors="ignore")
        else:
            nome_arq = p_cand.name
            xml_text = p_cand.read_text(encoding="utf-8", errors="ignore")
    else:
        xml_text = str(caminho_ou_xml or "")

    try:
        root = xml_seguro.fromstring(xml_text) if xml_text.strip() else ET.Element("pipeline")
    except Exception:
        root = ET.Element("pipeline")

    tag_root = root.tag.lower()
    is_workflow = tag_root in ("workflow", "job")
    tipo_canvas = "WORKFLOW (.hwf)" if is_workflow else "PIPELINE (.hpl)"
    nome_meta = (
        root.findtext("info/name")
        or root.findtext("name")
        or Path(nome_arq).stem
        or "esteira_hop"
    )
    desc_meta = (
        root.findtext("info/description")
        or root.findtext("description")
        or ""
    ).strip()

    # 1. Extrair Notepads (<notepads><notepad>)
    notepads = []
    for np in root.findall(".//notepads/notepad"):
        nota_txt = (
            np.findtext("note")
            or " — ".join(filter(None, [np.findtext("heading"), np.findtext("text")]))
            or ""
        ).strip()
        if not nota_txt:
            continue
        try:
            nx = int(float(np.findtext("xloc", "48")))
            ny = int(float(np.findtext("yloc", "24")))
            nw = max(240, int(float(np.findtext("width", "360"))))
            nh = max(44, int(float(np.findtext("heigth") or np.findtext("height") or "52")))
        except ValueError:
            nx, ny, nw, nh = 48, 24, 360, 52
        notepads.append({"text": nota_txt, "x": nx, "y": ny, "w": nw, "h": nh})

    # 2. Extrair Nós (Transforms em .hpl ou Actions em .hwf)
    nodes: List[dict] = []
    node_by_name: Dict[str, dict] = {}
    raw_items = root.findall(".//actions/action") if is_workflow else root.findall("transform")
    if not raw_items and not is_workflow:
        raw_items = root.findall("step")  # fallback Kettle .ktr

    for idx, item in enumerate(raw_items):
        n_name = (item.findtext("name") or f"Node_{idx+1}").strip()
        n_type = (item.findtext("type") or ("SPECIAL" if idx == 0 and is_workflow else "Dummy")).strip()
        x_str = item.findtext("GUI/xloc") or item.findtext("xloc") or str(120 + (idx % 4) * 240)
        y_str = item.findtext("GUI/yloc") or item.findtext("yloc") or str(160 + (idx // 4) * 140)
        try:
            nx = int(float(x_str))
            ny = int(float(y_str))
        except ValueError:
            nx, ny = 120 + (idx % 4) * 240, 160 + (idx // 4) * 140

        detalhe = (
            item.findtext("table")
            or item.findtext("lookup/table")
            or item.findtext("filename")
            or item.findtext("connection")
            or ""
        ).strip()
        if len(detalhe) > 28:
            detalhe = "..." + detalhe[-25:]

        nd = {
            "name": n_name,
            "type": n_type,
            "x": nx,
            "y": ny,
            "detail": detalhe,
            "connected": False,
        }
        nodes.append(nd)
        node_by_name[n_name] = nd

    # 3. Extrair Hops (<order><hop>, <hops><hop> e <transform_error_handling><error>)
    hops: List[dict] = []
    hop_elems = root.findall(".//hops/hop") if is_workflow else root.findall(".//order/hop")
    for hp in hop_elems:
        fr = (hp.findtext("from") or "").strip()
        to = (hp.findtext("to") or "").strip()
        en = (hp.findtext("enabled") or "Y").strip().upper()
        ev = (hp.findtext("evaluation") or "Y").strip().upper()
        un = (hp.findtext("unconditional") or "N").strip().upper()
        if not fr or not to:
            continue
        if fr in node_by_name:
            node_by_name[fr]["connected"] = True
        if to in node_by_name:
            node_by_name[to]["connected"] = True

        if en == "N":
            kind = "DISABLED"
        elif is_workflow:
            if un == "Y":
                kind = "UNCONDITIONAL"
            elif ev == "N":
                kind = "ERROR"
            else:
                kind = "SUCCESS"
        else:
            kind = "NORMAL"

        hops.append({"from": fr, "to": to, "kind": kind})

    # Error handling hops em Pipelines (.hpl)
    if not is_workflow:
        for err in root.findall(".//transform_error_handling/error"):
            is_en = (err.findtext("is_enabled") or "Y").strip().upper()
            fr = (err.findtext("source_transform") or err.findtext("source_step") or "").strip()
            to = (err.findtext("target_transform") or err.findtext("target_step") or "").strip()
            if fr and to:
                if fr in node_by_name:
                    node_by_name[fr]["connected"] = True
                if to in node_by_name:
                    node_by_name[to]["connected"] = True
                hops.append({
                    "from": fr,
                    "to": to,
                    "kind": "DISABLED" if is_en == "N" else "ERROR",
                })

    # 4. Calcular dimensões do Canvas SVG
    max_x = max(
        [960]
        + [n["x"] + 220 for n in nodes]
        + [np["x"] + np["w"] + 60 for np in notepads]
    )
    max_y = max(
        [460]
        + [n["y"] + 150 for n in nodes]
        + [np["y"] + np["h"] + 100 for np in notepads]
    )
    offset_y = 74  # espaço para a barra superior do Canvas Hop
    canvas_w = min(max(max_x, 980), 2200)
    canvas_h = min(max(max_y + offset_y + 40, 520), 1600)

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {canvas_w} {canvas_h}" width="100%" height="100%">',
        "  <defs>",
        "    <style>",
        '      .hop-ui { font-family: "Segoe UI", Inter, Roboto, sans-serif; }',
        '      .hop-mono { font-family: "JetBrains Mono", Consolas, monospace; }',
        "    </style>",
        '    <pattern id="hopGrid" width="24" height="24" patternUnits="userSpaceOnUse">',
        '      <path d="M 24 0 L 0 0 0 24" fill="none" stroke="#E2E8F0" stroke-width="0.7"/>',
        "    </pattern>",
        '    <filter id="hopShadow" x="-6%" y="-6%" width="114%" height="120%">',
        '      <feDropShadow dx="0" dy="3" stdDeviation="4" flood-color="#0F172A" flood-opacity="0.10"/>',
        "    </filter>",
        '    <marker id="arrowNormal" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto-start-reverse">',
        '      <path d="M 0 1 L 10 5 L 0 9 z" fill="#2563EB"/>',
        "    </marker>",
        '    <marker id="arrowSuccess" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto-start-reverse">',
        '      <path d="M 0 1 L 10 5 L 0 9 z" fill="#16A34A"/>',
        "    </marker>",
        '    <marker id="arrowError" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto-start-reverse">',
        '      <path d="M 0 1 L 10 5 L 0 9 z" fill="#DC2626"/>',
        "    </marker>",
        '    <marker id="arrowUncond" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto-start-reverse">',
        '      <path d="M 0 1 L 10 5 L 0 9 z" fill="#D97706"/>',
        "    </marker>",
        '    <marker id="arrowDisabled" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto-start-reverse">',
        '      <path d="M 0 1 L 10 5 L 0 9 z" fill="#94A3B8"/>',
        "    </marker>",
        "  </defs>",
        "",
        '  <!-- Fundo com Grade Oficial Apache Hop -->',
        f'  <rect width="{canvas_w}" height="{canvas_h}" fill="#F8FAFC"/>',
        f'  <rect y="{offset_y}" width="{canvas_w}" height="{canvas_h - offset_y}" fill="url(#hopGrid)"/>',
        "",
        '  <!-- Header Institucional Apache Hop 2.x -->',
        f'  <rect width="{canvas_w}" height="64" fill="#0F172A"/>',
        '  <rect x="18" y="13" width="38" height="38" rx="8" fill="#2563EB"/>',
        '  <text x="37" y="38" text-anchor="middle" fill="#FFFFFF" font-size="16" font-weight="800" class="hop-ui">H</text>',
        f'  <text x="68" y="29" fill="#FFFFFF" font-size="14" font-weight="700" class="hop-ui">APACHE HOP 2.x CANVAS — {_esc(nome_meta)}</text>',
        f'  <text x="68" y="48" fill="#94A3B8" font-size="11" class="hop-mono">{_esc(tipo_canvas)} • {len(nodes)} {"Actions" if is_workflow else "Transforms"} • {len(hops)} Hops{(" • " + _esc(desc_meta[:65])) if desc_meta else ""}</text>',
        "",
        '  <!-- Legenda de Hops no Topo Direito -->',
        f'  <g transform="translate({canvas_w - 490}, 18)">',
        '    <rect width="472" height="28" rx="6" fill="#1E293B" stroke="#334155"/>',
        '    <circle cx="18" cy="14" r="4.5" fill="#2563EB"/><text x="28" y="18" fill="#E2E8F0" font-size="10" class="hop-ui">Stream (.hpl)</text>',
        '    <circle cx="112" cy="14" r="4.5" fill="#16A34A"/><text x="122" y="18" fill="#E2E8F0" font-size="10" class="hop-ui">Sucesso (Y)</text>',
        '    <circle cx="204" cy="14" r="4.5" fill="#DC2626"/><text x="214" y="18" fill="#E2E8F0" font-size="10" class="hop-ui">Erro / Reject (N)</text>',
        '    <circle cx="318" cy="14" r="4.5" fill="#D97706"/><text x="328" y="18" fill="#E2E8F0" font-size="10" class="hop-ui">Incondicional</text>',
        '    <circle cx="412" cy="14" r="4.5" fill="#94A3B8"/><text x="422" y="18" fill="#94A3B8" font-size="10" class="hop-ui">Inativo</text>',
        "  </g>",
    ]

    # 5. Renderizar Sticky Notes (<notepads><notepad>)
    for np in notepads:
        nx = np["x"]
        ny = np["y"] + offset_y
        nw = np["w"]
        nh = np["h"]
        svg.extend([
            '  <g class="hop-notepad" filter="url(#hopShadow)">',
            f'    <rect x="{nx}" y="{ny}" width="{nw}" height="{nh}" rx="6" fill="#FEF9C3" stroke="#F59E0B" stroke-width="1.3"/>',
            f'    <polygon points="{nx+nw-14},{ny} {nx+nw},{ny+14} {nx+nw-14},{ny+14}" fill="#FDE047"/>',
            f'    <text x="{nx+12}" y="{ny+22}" fill="#78350F" font-size="11" font-weight="600" class="hop-ui">📝 {_esc(np["text"][:88])}</text>',
            "  </g>",
        ])

    # 6. Renderizar Hops (Setas Direcionais com Badges de Avaliação)
    node_w, node_h = 156, 56
    for hp in hops:
        n_fr = node_by_name.get(hp["from"])
        n_to = node_by_name.get(hp["to"])
        if not n_fr or not n_to:
            continue
        x1 = n_fr["x"] + node_w / 2
        y1 = n_fr["y"] + offset_y + node_h / 2
        x2 = n_to["x"] + node_w / 2
        y2 = n_to["y"] + offset_y + node_h / 2

        dx = x2 - x1
        dy = y2 - y1
        dist = math.hypot(dx, dy) or 1.0
        # Ajustar início e fim para tocar a borda do card
        sx = x1 + (dx / dist) * 58
        sy = y1 + (dy / dist) * 28
        ex = x2 - (dx / dist) * 64
        ey = y2 - (dy / dist) * 32

        kind = hp["kind"]
        if kind == "SUCCESS":
            stroke, marker, dash, badge_txt, badge_bg = "#16A34A", "url(#arrowSuccess)", "", "✓", "#DCFCE7"
        elif kind == "ERROR":
            stroke, marker, dash, badge_txt, badge_bg = "#DC2626", "url(#arrowError)", 'stroke-dasharray="5,4"', "✕", "#FEE2E2"
        elif kind == "UNCONDITIONAL":
            stroke, marker, dash, badge_txt, badge_bg = "#D97706", "url(#arrowUncond)", "", "🔒", "#FEF3C7"
        elif kind == "DISABLED":
            stroke, marker, dash, badge_txt, badge_bg = "#94A3B8", "url(#arrowDisabled)", 'stroke-dasharray="4,4"', "OFF", "#F1F5F9"
        else:
            stroke, marker, dash, badge_txt, badge_bg = "#2563EB", "url(#arrowNormal)", "", "", "#DBEAFE"

        svg.append(
            f'  <line x1="{sx:.1f}" y1="{sy:.1f}" x2="{ex:.1f}" y2="{ey:.1f}" '
            f'stroke="{stroke}" stroke-width="2.2" {dash} marker-end="{marker}"/>'
        )
        if badge_txt:
            mx = (sx + ex) / 2
            my = (sy + ey) / 2
            svg.append(f'  <circle cx="{mx:.1f}" cy="{my:.1f}" r="9" fill="{badge_bg}" stroke="{stroke}" stroke-width="1.2"/>')
            svg.append(
                f'  <text x="{mx:.1f}" y="{my+3.5:.1f}" text-anchor="middle" fill="{stroke}" font-size="9.5" font-weight="800" class="hop-ui">{badge_txt}</text>'
            )

    # 7. Renderizar Cards de Transforms / Actions
    for nd in nodes:
        nx = nd["x"]
        ny = nd["y"] + offset_y
        ntype = nd["type"]
        border_col, badge_bg, icon_txt = _HOP_TYPE_PALETTE.get(
            ntype, ("#2563EB", "#DBEAFE", ntype[:3].upper() or "TX")
        )
        is_orphan = len(nodes) > 1 and not nd["connected"]

        svg.append(f'  <g transform="translate({nx}, {ny})" filter="url(#hopShadow)">')
        if is_orphan:
            svg.append(
                f'    <rect x="-5" y="-5" width="{node_w+10}" height="{node_h+10}" rx="12" '
                f'fill="none" stroke="#DC2626" stroke-width="2" stroke-dasharray="5,3"/>'
            )
        svg.append(
            f'    <rect width="{node_w}" height="{node_h}" rx="9" fill="#FFFFFF" '
            f'stroke="{("#DC2626" if is_orphan else border_col)}" stroke-width="1.8"/>'
        )
        svg.append(f'    <rect x="8" y="10" width="34" height="36" rx="7" fill="{badge_bg}"/>')
        svg.append(
            f'    <text x="25" y="32" text-anchor="middle" fill="{border_col}" font-size="11" font-weight="800" class="hop-mono">{_esc(icon_txt)}</text>'
        )
        label_curto = nd["name"][:18] + ("…" if len(nd["name"]) > 18 else "")
        svg.append(
            f'    <text x="48" y="23" fill="#0F172A" font-size="11" font-weight="700" class="hop-ui">{_esc(label_curto)}</text>'
        )
        svg.append(
            f'    <text x="48" y="37" fill="#64748B" font-size="9.5" class="hop-mono">{_esc(ntype[:18])}</text>'
        )
        if nd["detail"]:
            svg.append(
                f'    <text x="48" y="49" fill="#0284C7" font-size="8.5" class="hop-mono">{_esc(nd["detail"][:20])}</text>'
            )
        if is_orphan:
            regra_orfao = "WORKFLOW-002" if is_workflow else "TRANS-002"
            svg.append('    <rect x="86" y="-11" width="74" height="15" rx="4" fill="#DC2626"/>')
            svg.append(
                f'    <text x="123" y="-1" text-anchor="middle" fill="#FFFFFF" font-size="8" font-weight="700" class="hop-mono">ÓRFÃO {regra_orfao}</text>'
            )
        svg.append("  </g>")

    svg.append("</svg>")
    return "\n".join(svg)


def gerar_documentacao_esteira_hop(
    pasta_hop: str,
    pasta_saida: Optional[str] = None,
) -> Dict[str, str]:
    """
    Inspirado em `DocBuilder.java`, `PipelineDocDelegate.java` e `WorkflowDocDelegate.java`
    (`plugins/misc/documentation` do Apache Hop):
      1. Gera o SVG do Canvas principal (`diagrama_esteira_hop.svg`) e SVGs individuais;
      2. Gera `DOCUMENTACAO_HOP.md` com Sumário (TOC), Parâmetros, Inventário de Transforms/Actions,
         Notas de Canvas (`<notepad>`), SQLs embutidos e Metadados (`metadata/`).
    """
    src_dir = Path(pasta_hop)
    out_dir = Path(pasta_saida) if pasta_saida else src_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    arquivos_gerados: Dict[str, str] = {}
    hwfs = sorted(src_dir.rglob("*.hwf"))
    hpls = sorted(src_dir.rglob("*.hpl"))
    todos_hop = hwfs + hpls

    if not todos_hop:
        return arquivos_gerados

    # Renderiza o SVG principal (prioriza o workflow orquestrador ou o primeiro pipeline)
    alvo_principal = hwfs[0] if hwfs else hpls[0]
    svg_principal = gerar_svg_canvas_hop(str(alvo_principal))
    p_svg_main = out_dir / "diagrama_esteira_hop.svg"
    p_svg_main.write_text(svg_principal, encoding="utf-8")
    arquivos_gerados["hop_canvas_svg"] = str(p_svg_main)
    arquivos_gerados["svg_esteira_hop"] = str(p_svg_main)

    # Monta a Auto-Documentação Markdown (Padrão Hop DocBuilder)
    md = [
        f"# 📘 Auto-Documentação da Esteira Apache Hop 2.x (`{src_dir.name}`)",
        "",
        f"- **Gerado em:** `{datetime.now().strftime('%d/%m/%Y %H:%M')}`",
        f"- **Workflows (`.hwf`):** `{len(hwfs)}` | **Pipelines (`.hpl`):** `{len(hpls)}`",
        "- **Diagrama Vetorial Principal:** [`diagrama_esteira_hop.svg`](diagrama_esteira_hop.svg)",
        "",
        "## 🗺️ 1. Diagrama Visual do Canvas Principal",
        "",
        "![Diagrama Canvas Apache Hop](diagrama_esteira_hop.svg)",
        "",
        "## 📑 2. Sumário de Artefatos (TOC)",
        "",
        "| Tipo | Arquivo | Nome Interno | Qtd. Etapas | Descrição |",
        "| :--- | :--- | :--- | :---: | :--- |",
    ]

    detalhes_secoes: List[str] = []
    for arq in todos_hop:
        rel_name = str(arq.relative_to(src_dir)) if arq.is_relative_to(src_dir) else arq.name
        try:
            root = xml_seguro.fromstring(arq.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            continue
        is_wf = root.tag.lower() in ("workflow", "job")
        tipo_lbl = "Workflow" if is_wf else "Pipeline"
        nome_int = (root.findtext("info/name") or root.findtext("name") or arq.stem).strip()
        desc_int = (root.findtext("info/description") or root.findtext("description") or "—").strip()
        etapas = root.findall(".//actions/action") if is_wf else root.findall("transform")
        md.append(f"| **{tipo_lbl}** | `{rel_name}` | `{nome_int}` | `{len(etapas)}` | {desc_int} |")

        detalhes_secoes.extend([
            f"### 🔹 {tipo_lbl}: `{nome_int}` (`{rel_name}`)",
            "",
            f"- **Descrição:** {desc_int}",
        ])

        # Parâmetros
        params = root.findall(".//parameters/parameter")
        if params:
            detalhes_secoes.append("- **Parâmetros Declarados:**")
            for prm in params:
                pname = prm.findtext("name", "")
                pdef = prm.findtext("default_value", "")
                pdesc = prm.findtext("description", "")
                detalhes_secoes.append(f"  - `{pname}` (default: `{pdef}`): {pdesc}")

        # Notas de Canvas
        notas = [
            (np.findtext("note") or np.findtext("text") or "").strip()
            for np in root.findall(".//notepads/notepad")
        ]
        notas = [n for n in notas if n]
        if notas:
            detalhes_secoes.append("- **Notas do Canvas (`<notepad>`):**")
            for nt in notas:
                detalhes_secoes.append(f"  > 📝 {nt}")

        # Tabela de Transforms / Actions
        if etapas:
            detalhes_secoes.extend([
                "",
                "| Etapa | Plugin / Tipo | Alvo / Tabela / Arquivo |",
                "| :--- | :--- | :--- |",
            ])
            for et in etapas:
                ename = et.findtext("name", "")
                etype = et.findtext("type", "")
                ealvo = (
                    et.findtext("table")
                    or et.findtext("lookup/table")
                    or et.findtext("filename")
                    or et.findtext("connection")
                    or "—"
                ).strip()
                detalhes_secoes.append(f"| `{ename}` | `{etype}` | `{ealvo}` |")
        detalhes_secoes.append("")

    md.extend([
        "",
        "## 🔍 3. Detalhamento Técnico de Workflows e Pipelines",
        "",
        *detalhes_secoes,
    ])

    p_doc_md = out_dir / "DOCUMENTACAO_HOP.md"
    p_doc_md.write_text("\n".join(md), encoding="utf-8")
    arquivos_gerados["hop_doc_md"] = str(p_doc_md)
    arquivos_gerados["doc_esteira_hop"] = str(p_doc_md)

    return arquivos_gerados
