"""
Geração OOXML nativa (sem dependências): planilha de indicadores .xlsx, apresentação
executiva .pptx e exportação de Markdown para .docx.

Extraído de gerador_artefatos_visuais.py (que mantém uma fachada de reimportação).
"""

import os
import re
import zipfile
from ninho_core.mockup_bi import (
    gerar_mockup_painel_bi_svg,
)
from ninho_core.prova_dax import (
    _extrair_contexto_bi,
)
from ninho_core.visual_comum import (
    _esc,
    _normalizar_dims_fatos,
    approx_text_width,
)
from datetime import datetime
from typing import List, Optional, Tuple


def _col_letter(col_idx_1based: int) -> str:
    res = ""
    n = col_idx_1based
    while n > 0:
        n, rem = divmod(n - 1, 26)
        res = chr(65 + rem) + res
    return res


def _build_worksheet_xml(
    rows: List[List[str]],
    freeze_header: bool = True,
    auto_filter: bool = True,
    conditional_formatting_xml: str = "",
    data_validations_xml: str = "",
) -> str:
    """
    Constrói o XML de uma aba OOXML (`xl/worksheets/sheetN.xml`) com:
      - Cálculo automático de largura de colunas via `approx_text_width` (GridCraft)
      - Painel congelado na linha 1 (`<pane ySplit="1" state="frozen"/>`)
      - `<autoFilter>` habilitado no cabeçalho
      - Estilo diferenciado para o cabeçalho (`s="1"`) e linhas de dados (`s="2"`)
      - Suporte opcional a `<conditionalFormatting>` e `<dataValidations>` (listas suspensas).
    """
    if not rows:
        rows = [["Sem Dados"]]

    num_cols = max(len(r) for r in rows)
    num_rows = len(rows)
    last_col_let = _col_letter(num_cols)
    dim_ref = f"A1:{last_col_let}{num_rows}"

    # Calcular larguras das colunas usando approx_text_width
    col_widths = []
    for c_idx in range(num_cols):
        max_w = 12.0
        for r_idx, row in enumerate(rows):
            val = str(row[c_idx]) if c_idx < len(row) else ""
            px = approx_text_width(val[:65], font_size=11.0, bold=(r_idx == 0))
            excel_w = max(12.0, min(58.0, round(px / 6.2 + 4.0, 1)))
            if excel_w > max_w:
                max_w = excel_w
        col_widths.append(max_w)

    xml_parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">',
        f'  <dimension ref="{dim_ref}"/>',
    ]

    if freeze_header:
        xml_parts.extend([
            "  <sheetViews>",
            '    <sheetView tabSelected="1" workbookViewId="0">',
            '      <pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>',
            '      <selection pane="bottomLeft" activeCell="A2" sqref="A2"/>',
            "    </sheetView>",
            "  </sheetViews>",
        ])

    xml_parts.append("  <cols>")
    for idx, w in enumerate(col_widths, start=1):
        xml_parts.append(f'    <col min="{idx}" max="{idx}" width="{w}" customWidth="1"/>')
    xml_parts.append("  </cols>")

    xml_parts.append("  <sheetData>")
    for r_idx, row in enumerate(rows, start=1):
        row_ht = ' ht="26" customHeight="1"' if r_idx == 1 else ' ht="20" customHeight="1"'
        xml_parts.append(f'    <row r="{r_idx}"{row_ht}>')
        for c_idx in range(1, num_cols + 1):
            val = str(row[c_idx - 1]) if (c_idx - 1) < len(row) else ""
            cell_ref = f"{_col_letter(c_idx)}{r_idx}"
            style_id = "1" if r_idx == 1 else "2"
            xml_parts.append(
                f'      <c r="{cell_ref}" t="inlineStr" s="{style_id}"><is><t>{_esc(val)}</t></is></c>'
            )
        xml_parts.append("    </row>")
    xml_parts.append("  </sheetData>")

    if auto_filter and num_rows >= 1:
        xml_parts.append(f'  <autoFilter ref="{dim_ref}"/>')

    if conditional_formatting_xml:
        xml_parts.append(conditional_formatting_xml)

    if data_validations_xml:
        xml_parts.append(data_validations_xml)

    xml_parts.append("</worksheet>")
    return "\n".join(xml_parts)


def gerar_planilha_indicadores_xlsx(
    dims: List[dict],
    fatos: List[dict],
    schema: str,
    projeto: str,
    caminho_saida: str,
    indicadores_existentes: Optional[List[dict]] = None,
) -> str:
    """
    Gera a planilha corporativa `Indicadores_PowerBI_<PROJETO>.xlsx` (3 abas estilizadas
    no padrão GridCraft: `Catalogo_Indicadores`, `Metas_e_Thresholds`, `Guia_Preenchimento`).
    """
    ctx = _extrair_contexto_bi(dims, fatos, projeto)

    aba1_rows = [
        [
            "ID_KPI",
            "Nome do Indicador (KPI)",
            "Origem da Especificação",
            "Fórmula / Regra de Negócio",
            "Medida DAX Sugerida",
            "Tabela / Coluna DW",
            "Formato",
            "Visual Recomendado",
        ],
        [
            "KPI-001",
            f"Total {ctx['label_m1']}",
            "Modelo Dimensional DW",
            f"Somatório oficial da métrica {ctx['m1']} na tabela fato {ctx['nome_fato']}.",
            f"Total {ctx['label_m1']} = SUM({ctx['nome_fato']}[{ctx['m1']}])",
            f"{schema}.{ctx['nome_fato']}.{ctx['m1']}",
            "R$ #,##0.00" if any(p in ctx["m1"] for p in ("VAL_", "VLR_")) else "#,##0",
            "Card Principal + Gráfico de Área",
        ],
        [
            "KPI-002",
            f"Volume Total de Registros ({ctx['label_fato']})",
            "Modelo Dimensional DW",
            f"Contagem total de eventos/transações registrados na {ctx['nome_fato']}.",
            f"Qtd Registros = COUNTROWS({ctx['nome_fato']})",
            f"{schema}.{ctx['nome_fato']}",
            "#,##0",
            "Card KPI + Matriz Analítica",
        ],
        [
            "KPI-003",
            f"Média / Ticket Médio ({ctx['label_m1']})",
            "💡 Sugestão Radar IA",
            f"Razão segura entre o Total {ctx['label_m1']} e a quantidade de registros.",
            f"Media {ctx['label_m1']} = DIVIDE([Total {ctx['label_m1']}], [Qtd Registros], 0)",
            f"{schema}.{ctx['nome_fato']}.{ctx['m1']}",
            "R$ #,##0.00",
            "Card KPI com Sparkline",
        ],
        [
            "KPI-004",
            f"Variação Anual YoY ({ctx['label_m1']} %)",
            "💡 Sugestão Radar IA",
            "Comparação percentual entre o período atual e o mesmo período do ano anterior.",
            f"% Var YoY = DIVIDE([Total {ctx['label_m1']}] - [Total {ctx['label_m1']} LY], [Total {ctx['label_m1']} LY], 0)",
            f"{schema}.{ctx['dim_tempo']}.DT_REFERENCIA",
            "0.0%",
            "Gráfico de Área + Linha Tracejada",
        ],
        [
            "KPI-005",
            "Índice de Qualidade Dimensional (SK ≠ -1)",
            "💡 Sugestão Governança NINHO",
            "Percentual de registros na Fato que encontraram correspondência exata nas Dimensões (SK diferente de -1).",
            f"% Qualidade DW = 1 - DIVIDE(CALCULATE([Qtd Registros], {ctx['d1']}[SK]=-1), [Qtd Registros], 0)",
            f"{schema}.{ctx['nome_fato']} (FKs)",
            "0.00%",
            "Card Semafórico de Qualidade",
        ],
    ]

    if indicadores_existentes:
        for idx, ind in enumerate(indicadores_existentes, start=6):
            aba1_rows.append([
                f"KPI-{idx:03d}",
                str(ind.get("nome", f"Indicador {idx}")),
                "Planilha do Cliente",
                str(ind.get("formula", "Definido na matriz do cliente")),
                str(ind.get("dax", "")),
                str(ind.get("dimensoes", ctx["nome_fato"])),
                str(ind.get("meta", "#,##0.00")),
                "Card / Matriz de Metas",
            ])

    aba2_rows = [
        [
            "ID_KPI",
            "Nome do Indicador",
            "Meta Oficial",
            "Faixa Verde (Ótimo)",
            "Faixa Amarela (Atenção)",
            "Faixa Vermelha (Crítico)",
            " Cor Hex Verde",
            "Cor Hex Vermelho",
        ],
        ["KPI-001", f"Total {ctx['label_m1']}", ">= 100% do Planejado", ">= 98%", "90% a 97,9%", "< 90%", "#16A34A", "#DC2626"],
        ["KPI-004", f"Variação YoY ({ctx['label_m1']})", "> +5,0% a.a.", ">= +5,0%", "0,0% a +4,9%", "< 0,0%", "#16A34A", "#DC2626"],
        ["KPI-005", "Índice Qualidade DW (SK ≠ -1)", ">= 98,0%", ">= 98,0%", "95,0% a 97,9%", "< 95,0%", "#16A34A", "#DC2626"],
    ]

    aba3_rows = [
        ["Seção", "Orientação Técnica para o Analista de BI e Gestor de Negócio"],
        ["1. Como usar esta planilha", "Esta planilha é gerada automaticamente pelo NINHO e pode ser editada e devolvida em entrega/planejador_dw/ para regerar o Guia de BI."],
        ["2. Filtro SCD Tipo 2", "Todas as dimensões históricas possuem FLG_ATUAL ('S'/'N'). Para contagens cadastrais atuais, filtre FLG_ATUAL = 'S'."],
        ["3. Tratamento da Linha -1", "Nunca oculte o registro SK = -1 com INNER JOIN; exiba-o nos cartões de auditoria para monitorar falhas de cadastro na origem."],
        ["4. Formatos Suportados", "O motor NINHO lê nativamente tanto arquivos Microsoft Excel (.xlsx) quanto LibreOffice Calc (.ods)."],
    ]

    styles_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="3">
    <font><sz val="11"/><color theme="1"/><name val="Segoe UI"/></font>
    <font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Segoe UI"/></font>
    <font><sz val="10.5"/><color rgb="FF0F172A"/><name val="Segoe UI"/></font>
  </fonts>
  <fills count="4">
    <fill><patternFill patternType="none"/></fill>
    <fill><patternFill patternType="gray125"/></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FF1E3A8A"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFF8FAFC"/></patternFill></fill>
  </fills>
  <borders count="2">
    <border><left/><right/><top/><bottom/><diagonal/></border>
    <border>
      <left style="thin"><color rgb="FFCBD5E1"/></left>
      <right style="thin"><color rgb="FFCBD5E1"/></right>
      <top style="thin"><color rgb="FFCBD5E1"/></top>
      <bottom style="thin"><color rgb="FFCBD5E1"/></bottom>
      <diagonal/>
    </border>
  </borders>
  <cellStyleXfs count="1">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0"/>
  </cellStyleXfs>
  <cellXfs count="3">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
    <xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1">
      <alignment vertical="center" wrapText="1"/>
    </xf>
    <xf numFmtId="0" fontId="2" fillId="0" borderId="1" xfId="0" applyFont="1" applyBorder="1" applyAlignment="1">
      <alignment vertical="center" wrapText="1"/>
    </xf>
  </cellXfs>
  <dxfs count="1">
    <dxf>
      <font><b/><color rgb="FF991B1B"/></font>
      <fill><patternFill patternType="solid"><fgColor rgb="FFFEE2E2"/><bgColor rgb="FFFEE2E2"/></patternFill></fill>
    </dxf>
  </dxfs>
</styleSheet>"""

    cf_sheet1_xml = """  <conditionalFormatting sqref="B2:E30">
    <cfRule type="containsBlanks" dxfId="0" priority="1">
      <formula>LEN(TRIM(B2))=0</formula>
    </cfRule>
  </conditionalFormatting>"""

    dv_sheet1_xml = """  <dataValidations count="3">
    <dataValidation type="list" allowBlank="1" showInputMessage="1" showErrorMessage="1" sqref="C2:C100">
      <formula1>"Modelo Dimensional DW,Especificação do Cliente,Radar Consultivo da IA,Camada Semântica"</formula1>
    </dataValidation>
    <dataValidation type="list" allowBlank="1" showInputMessage="1" showErrorMessage="1" sqref="G2:G100">
      <formula1>"#,##0,R$ #,##0.00,0.0%,0.00,dd/mm/yyyy"</formula1>
    </dataValidation>
    <dataValidation type="list" allowBlank="1" showInputMessage="1" showErrorMessage="1" sqref="H2:H100">
      <formula1>"Card Principal + Gráfico de Área,Card KPI + Matriz Analítica,Card de Alerta + Semáforo,Gráfico de Barras Horizontal,Gráfico de Linha Temporal,Tabela Detalhada"</formula1>
    </dataValidation>
  </dataValidations>"""

    cf_sheet2_xml = """  <conditionalFormatting sqref="C2:F30">
    <cfRule type="containsBlanks" dxfId="0" priority="1">
      <formula>LEN(TRIM(C2))=0</formula>
    </cfRule>
  </conditionalFormatting>"""

    dv_sheet2_xml = """  <dataValidations count="2">
    <dataValidation type="list" allowBlank="1" showInputMessage="1" showErrorMessage="1" sqref="G2:G100">
      <formula1>"Maior é Melhor,Menor é Melhor,Estabilidade na Faixa"</formula1>
    </dataValidation>
    <dataValidation type="list" allowBlank="1" showInputMessage="1" showErrorMessage="1" sqref="H2:H100">
      <formula1>"Mensal,Diária,Semanal,Trimestral,Anual"</formula1>
    </dataValidation>
  </dataValidations>"""

    workbook_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
          xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="Catalogo_Indicadores" sheetId="1" r:id="rId1"/>
    <sheet name="Metas_e_Thresholds" sheetId="2" r:id="rId2"/>
    <sheet name="Guia_Preenchimento" sheetId="3" r:id="rId3"/>
  </sheets>
</workbook>"""

    wb_rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet3.xml"/>
  <Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""

    root_rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""

    content_types_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/worksheets/sheet3.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>"""

    os.makedirs(os.path.dirname(os.path.abspath(caminho_saida)), exist_ok=True)
    with zipfile.ZipFile(caminho_saida, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types_xml)
        zf.writestr("_rels/.rels", root_rels_xml)
        zf.writestr("xl/workbook.xml", workbook_xml)
        zf.writestr("xl/_rels/workbook.xml.rels", wb_rels_xml)
        zf.writestr("xl/styles.xml", styles_xml)
        zf.writestr(
            "xl/worksheets/sheet1.xml",
            _build_worksheet_xml(
                aba1_rows,
                conditional_formatting_xml=cf_sheet1_xml,
                data_validations_xml=dv_sheet1_xml,
            ),
        )
        zf.writestr(
            "xl/worksheets/sheet2.xml",
            _build_worksheet_xml(
                aba2_rows,
                conditional_formatting_xml=cf_sheet2_xml,
                data_validations_xml=dv_sheet2_xml,
            ),
        )
        zf.writestr("xl/worksheets/sheet3.xml", _build_worksheet_xml(aba3_rows, auto_filter=False))

    return caminho_saida


def _build_pptx_slide_xml(titulo: str, subtitulo: str, bullets: List[str], badge: str = "NINHO DW & BI") -> str:
    """Constrói um slide DrawingML OOXML 16:9 (`ppt/slides/slideN.xml`) válido no PowerPoint / LibreOffice Impress."""
    paras = []
    for b in bullets[:7]:
        paras.append(
            f"""          <a:p>
            <a:pPr marL="228600" indent="-228600"><a:buChar char="•"/></a:pPr>
            <a:r><a:rPr lang="pt-BR" sz="1800" dirty="0"><a:solidFill><a:srgbClr val="1E293B"/></a:solidFill></a:rPr><a:t>{_esc(b)}</a:t></a:r>
          </a:p>"""
        )
    paras_xml = "\n".join(paras)
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
       xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
       xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld>
    <p:spTree>
      <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
      <p:grpSpPr>
        <a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm>
      </p:grpSpPr>
      <p:sp>
        <p:nvSpPr><p:cNvPr id="2" name="Title"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
        <p:spPr>
          <a:xfrm><a:off x="609600" y="365760"/><a:ext cx="10972800" cy="1158240"/></a:xfrm>
          <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
          <a:solidFill><a:srgbClr val="0F172A"/></a:solidFill>
        </p:spPr>
        <p:txBody>
          <a:bodyPr anchor="ctr" lIns="182880" rIns="182880"/>
          <a:lstStyle/>
          <a:p>
            <a:r><a:rPr lang="pt-BR" sz="2400" b="1" dirty="0"><a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill></a:rPr><a:t>{_esc(titulo)}</a:t></a:r>
          </a:p>
          <a:p>
            <a:r><a:rPr lang="pt-BR" sz="1300" dirty="0"><a:solidFill><a:srgbClr val="93C5FD"/></a:solidFill></a:rPr><a:t>{_esc(subtitulo)}  |  {_esc(badge)}</a:t></a:r>
          </a:p>
        </p:txBody>
      </p:sp>
      <p:sp>
        <p:nvSpPr><p:cNvPr id="3" name="Content"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
        <p:spPr>
          <a:xfrm><a:off x="609600" y="1767840"/><a:ext cx="10972800" cy="4632960"/></a:xfrm>
          <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
          <a:solidFill><a:srgbClr val="F8FAFC"/></a:solidFill>
        </p:spPr>
        <p:txBody>
          <a:bodyPr lIns="228600" tIns="228600" rIns="228600" bIns="228600"/>
          <a:lstStyle/>
{paras_xml}
        </p:txBody>
      </p:sp>
    </p:spTree>
  </p:cSld>
</p:sld>"""


def gerar_apresentacao_executiva(
    dims: List[dict],
    fatos: List[dict],
    schema: str,
    projeto: str,
    pasta_saida: str,
) -> Tuple[str, str]:
    """
    Gera a Apresentação Executiva para Kickoff / Homologação de BI & DW (inspirado no DeckCraft):
      1. `apresentacao_executiva_<PROJETO>.pptx` (Pacote OOXML PowerPoint nativo com 5 slides 16:9)
      2. `apresentacao_slides.html` (Deck interativo widescreen 1920x1080 com navegação por teclado e SVG embutido).
    """
    os.makedirs(pasta_saida, exist_ok=True)
    dims, fatos = _normalizar_dims_fatos(dims, fatos)
    ctx = _extrair_contexto_bi(dims, fatos, projeto)
    nomes_dims = ", ".join(d.get("nome", "") for d in dims[:6]) or f"{ctx['dim_tempo']}, {ctx['d1']}, {ctx['d2']}"

    slides_data = [
        (
            f"1. Arquitetura Dimensional & BI — Projeto {ctx['projeto']}",
            f"Schema Oficial: {schema} • Homologação Técnica & Executiva",
            [
                f"Tabela Fato Central: {schema}.{ctx['nome_fato']} (Modelagem Kimball Star Schema).",
                f"Dimensões Conformadas ({len(dims)}): {nomes_dims}.",
                "Integridade Referencial Blindada: Registro Sentinela SK = -1 ('Não Informado') ativo em todas as dimensões.",
                "Histórico SCD Tipo 2: Rastreabilidade temporal via DT_INICIO, DT_FIM e FLG_ATUAL = 'S'.",
                "Performance Oracle: Índices Bitmap nas FKs da Fato e B-Tree nas NKs das Dimensões.",
            ],
        ),
        (
            "2. Catálogo de Indicadores Oficiais & Fórmulas DAX",
            "Medidas auditadas com proteção contra divisão por zero (DIVIDE) e SCD2",
            [
                f"KPI Principal: [Total {ctx['label_m1']}] = SUM({ctx['nome_fato']}[{ctx['m1']}]).",
                f"Volume Transacional: [Qtd Registros] = COUNTROWS({ctx['nome_fato']}).",
                f"Média Operacional: [Media {ctx['label_m1']}] = DIVIDE([Total {ctx['label_m1']}], [Qtd Registros], 0).",
                f"Inteligência Temporal: Comparativo YoY contínuo sobre {ctx['dim_tempo']}[DT_REFERENCIA].",
                "Qualidade Dimensional: Monitoramento automático do percentual de chaves em SK = -1 (Meta < 2%).",
            ],
        ),
        (
            "3. 💡 Radar Consultivo da IA — Novos Indicadores Sugeridos",
            "Insights proativos extraídos da estrutura das tabelas para agregar valor ao negócio",
            [
                f"Ranking Dinâmico Top-N por {ctx['label_d1']} com participação Pareto 80/20.",
                f"Matriz de Desempenho cruzando {ctx['label_d1']} × {ctx['label_d3']} com Data Bars (#5B9BD5).",
                "Índice de Maturidade Cadastral: Alerta automático caso registros Não Informados (-1) subam.",
                "Análise de Sazonalidade Mensal e Ritmo de Execução (Run-Rate) até o fechamento do exercício.",
            ],
        ),
        (
            "4. Governança Visual & Padrão de Construção no Power BI",
            "Diretrizes de UX, Sync Slicers e Relacionamentos no Modelo Semântico",
            [
                "Relacionamentos 1:* com filtro Único (Single Direction) das Dimensões para a Fato.",
                f"Marcar {ctx['dim_tempo']} como Tabela de Data oficial (Mark as Date Table).",
                "Sync Slicers ativado no cabeçalho para Período, Unidade e Flag SCD2 Vigente (FLG_ATUAL = 'S').",
                "Mockup vetorial homologável disponível em Visão Executiva e Visão Dev Mode (Redlines DAX).",
            ],
        ),
        (
            "5. Checklist de Homologação & Próximos Passos",
            "Conferência cruzada SQL Oracle vs Power BI antes da publicação em Produção",
            [
                "Passo 1: Validar batimento do totalizador geral no Oracle vs Card Principal do Power BI.",
                "Passo 2: Auditar percentual de registros em SK = -1 na página de Qualidade de Dados.",
                "Passo 3: Validar aprovação dos gestores sobre as metas da planilha Indicadores_PowerBI.xlsx.",
                "Passo 4: Publicar dataset certificado e liberar acesso com Row-Level Security (RLS) se aplicável.",
            ],
        ),
    ]

    caminho_pptx = os.path.join(pasta_saida, f"apresentacao_executiva_{projeto.lower()}.pptx")

    # Construir pacote OOXML .pptx mínimo e 100% compatível
    content_types = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
        '  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
        '  <Default Extension="xml" ContentType="application/xml"/>',
        '  <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>',
        '  <Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>',
        '  <Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>',
    ]
    pres_rels = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">',
        '  <Relationship Id="rIdMaster1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>',
    ]
    sld_id_lst = []
    for idx in range(1, len(slides_data) + 1):
        content_types.append(
            f'  <Override PartName="/ppt/slides/slide{idx}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
        )
        pres_rels.append(
            f'  <Relationship Id="rIdSlide{idx}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{idx}.xml"/>'
        )
        sld_id_lst.append(f'    <p:sldId id="{255 + idx}" r:id="rIdSlide{idx}"/>')

    content_types.append("</Types>")
    pres_rels.append("</Relationships>")

    presentation_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
                xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
                xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:sldMasterIdLst>
    <p:sldMasterId id="2147483648" r:id="rIdMaster1"/>
  </p:sldMasterIdLst>
  <p:sldIdLst>
{chr(10).join(sld_id_lst)}
  </p:sldIdLst>
  <p:sldSz cx="12192000" cy="6858000"/>
  <p:notesSz cx="6858000" cy="9144000"/>
</p:presentation>"""

    slide_master_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
             xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
             xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/></p:spTree></p:cSld>
  <p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>
  <p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rIdLayout1"/></p:sldLayoutIdLst>
</p:sldMaster>"""

    slide_layout_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
             xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
             xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" type="blank">
  <p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/></p:spTree></p:cSld>
</p:sldLayout>"""

    master_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rIdLayout1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
</Relationships>"""

    layout_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rIdMaster1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/>
</Relationships>"""

    slide_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rIdLayout1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
</Relationships>"""

    root_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
</Relationships>"""

    with zipfile.ZipFile(caminho_pptx, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", "\n".join(content_types))
        zf.writestr("_rels/.rels", root_rels)
        zf.writestr("ppt/presentation.xml", presentation_xml)
        zf.writestr("ppt/_rels/presentation.xml.rels", "\n".join(pres_rels))
        zf.writestr("ppt/slideMasters/slideMaster1.xml", slide_master_xml)
        zf.writestr("ppt/slideMasters/_rels/slideMaster1.xml.rels", master_rels)
        zf.writestr("ppt/slideLayouts/slideLayout1.xml", slide_layout_xml)
        zf.writestr("ppt/slideLayouts/_rels/slideLayout1.xml.rels", layout_rels)
        for idx, (s_tit, s_sub, s_bul) in enumerate(slides_data, start=1):
            zf.writestr(f"ppt/slides/slide{idx}.xml", _build_pptx_slide_xml(s_tit, s_sub, s_bul))
            zf.writestr(f"ppt/slides/_rels/slide{idx}.xml.rels", slide_rels)

    # Também gerar o Deck HTML interativo Widescreen 16:9 (`apresentacao_slides.html`)
    caminho_html_slides = os.path.join(pasta_saida, "apresentacao_slides.html")
    svg_mockup = gerar_mockup_painel_bi_svg(dims, fatos, schema, projeto, dev_mode=False, tema="light")

    slides_html_blocks = []
    for idx, (s_tit, s_sub, s_bul) in enumerate(slides_data, start=1):
        li_items = "".join(f"<li>{_esc(b)}</li>" for b in s_bul)
        active_cls = " active" if idx == 1 else ""
        slides_html_blocks.append(
            f"""    <section class="slide{active_cls}">
      <div class="slide-header">
        <span class="badge">SLIDE {idx:02d} / {len(slides_data)+1:02d}</span>
        <h2>{_esc(s_tit)}</h2>
        <p>{_esc(s_sub)}</p>
      </div>
      <ul class="bullet-list">{li_items}</ul>
    </section>"""
        )

    # Slide extra com o Mockup Vetorial embutido em tela cheia
    slides_html_blocks.append(
        f"""    <section class="slide">
      <div class="slide-header">
        <span class="badge">SLIDE {len(slides_data)+1:02d} / {len(slides_data)+1:02d}</span>
        <h2>6. Protótipo Visual Homologável do Painel BI ({_esc(ctx['projeto'])})</h2>
        <p>Preview vetorial gerado automaticamente a partir do modelo Star Schema</p>
      </div>
      <div style="max-height:540px;overflow:hidden;border-radius:12px;border:1px solid #334155;">{svg_mockup}</div>
    </section>"""
    )

    html_deck = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8"/>
  <title>Apresentação Executiva BI &amp; DW — {_esc(ctx['projeto'])}</title>
  <style>
    body {{
      margin: 0; background: #090d16; color: #f8fafc;
      font-family: "Segoe UI", Inter, system-ui, sans-serif;
    }}
    .deck-bar {{
      display: flex; justify-content: space-between; align-items: center;
      padding: 12px 28px; background: #111827; border-bottom: 1px solid #1e293b;
    }}
    .slide {{
      display: none; max-width: 1280px; min-height: 680px; margin: 28px auto;
      padding: 42px 54px; background: linear-gradient(145deg, #111827, #1e293b);
      border: 1px solid #334155; border-radius: 18px;
      box-shadow: 0 24px 60px rgba(0,0,0,0.5);
    }}
    .slide.active {{ display: block; }}
    .badge {{
      display: inline-block; background: #2563eb; color: #fff;
      font-size: 11px; font-weight: 800; padding: 4px 10px; border-radius: 999px;
    }}
    .slide-header h2 {{ margin: 12px 0 6px; font-size: 28px; color: #fff; }}
    .slide-header p {{ margin: 0 0 28px; font-size: 15px; color: #93c5fd; }}
    .bullet-list {{ font-size: 19px; line-height: 1.75; color: #e2e8f0; }}
    .bullet-list li {{ margin-bottom: 14px; }}
    button {{
      background: #2563eb; color: #fff; border: none; padding: 8px 16px;
      border-radius: 8px; font-weight: 700; cursor: pointer; margin-left: 8px;
    }}
  </style>
</head>
<body>
  <header class="deck-bar">
    <div><strong>📊 Deck Executivo NINHO (DeckCraft 16:9)</strong> — Projeto {_esc(ctx['projeto'])}</div>
    <div>
      <button onclick="prevSlide()">◀ Anterior</button>
      <button onclick="nextSlide()">Próximo ▶</button>
      <button onclick="window.print()" style="background:#059669;">🖨️ Imprimir / Salvar PDF</button>
    </div>
  </header>
{chr(10).join(slides_html_blocks)}
  <script>
    let idx = 0;
    const slides = document.querySelectorAll('.slide');
    function show(n) {{
      slides.forEach(s => s.classList.remove('active'));
      idx = (n + slides.length) % slides.length;
      slides[idx].classList.add('active');
    }}
    function nextSlide() {{ show(idx + 1); }}
    function prevSlide() {{ show(idx - 1); }}
    document.addEventListener('keydown', e => {{
      if (e.key === 'ArrowRight' || e.key === ' ') nextSlide();
      if (e.key === 'ArrowLeft') prevSlide();
    }});
  </script>
</body>
</html>"""

    with open(caminho_html_slides, "w", encoding="utf-8") as f:
        f.write(html_deck)

    return caminho_pptx, caminho_html_slides


def exportar_markdown_para_docx(
    caminho_md: str,
    caminho_docx: str,
    titulo: Optional[str] = None,
    subtitulo: Optional[str] = None,
    status_badge: str = "DOCUMENTO OFICIAL HOMOLOGADO",
) -> str:
    """
    Converte qualquer relatório ou guia Markdown do NINHO em um documento corporativo
    Microsoft Word (`.docx` OOXML nativo inspirado no WordCraft), preservando:
      - Cabeçalho Institucional + Badge de Status
      - Títulos H1 / H2 / H3 com cores corporativas
      - Tabelas Markdown convertidas em `<w:tbl>` com cabeçalho azul marinho
      - Blocos de código SQL/DAX em fonte monoespaçada e fundo sombreado.
    """
    if not os.path.isfile(caminho_md):
        return ""
    with open(caminho_md, "r", encoding="utf-8", errors="replace") as f:
        conteudo_md = f.read()

    linhas = conteudo_md.splitlines()
    doc_title = titulo or os.path.basename(caminho_md).replace(".md", "").replace("_", " ")
    doc_sub = subtitulo or f"Gerado automaticamente pela Plataforma NINHO em {datetime.now().strftime('%d/%m/%Y %H:%M')}"

    body_elements: List[str] = []

    def _w_para(texto: str, bold: bool = False, color: str = "0F172A", sz: int = 21, fill: Optional[str] = None, mono: bool = False) -> str:
        rpr = [f'<w:color w:val="{color}"/>', f'<w:sz w:val="{sz}"/>']
        if bold:
            rpr.append("<w:b/>")
        if mono:
            rpr.append('<w:rFonts w:ascii="Consolas" w:hAnsi="Consolas"/>')
        else:
            rpr.append('<w:rFonts w:ascii="Segoe UI" w:hAnsi="Segoe UI"/>')
        ppr = ""
        if fill:
            ppr = f'<w:pPr><w:shd w:val="clear" w:color="auto" w:fill="{fill}"/><w:spacing w:before="80" w:after="80"/></w:pPr>'
        else:
            ppr = '<w:pPr><w:spacing w:before="60" w:after="100"/></w:pPr>'
        limpo = re.sub(r"\*\*(.+?)\*\*", r"\1", texto)
        limpo = re.sub(r"`(.+?)`", r"\1", limpo)
        return f'<w:p>{ppr}<w:r><w:rPr>{"".join(rpr)}</w:rPr><w:t xml:space="preserve">{_esc(limpo)}</w:t></w:r></w:p>'

    def _w_table(table_rows: List[List[str]]) -> str:
        if not table_rows:
            return ""
        tbl = [
            "<w:tbl>",
            "  <w:tblPr>",
            '    <w:tblW w:w="5000" w:type="pct"/>',
            "    <w:tblBorders>",
            '      <w:top w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>',
            '      <w:left w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>',
            '      <w:bottom w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>',
            '      <w:right w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>',
            '      <w:insideH w:val="single" w:sz="4" w:space="0" w:color="E2E8F0"/>',
            '      <w:insideV w:val="single" w:sz="4" w:space="0" w:color="E2E8F0"/>',
            "    </w:tblBorders>",
            "  </w:tblPr>",
        ]
        for r_idx, row in enumerate(table_rows):
            tbl.append("  <w:tr>")
            for cell in row:
                if r_idx == 0:
                    tc_pr = '<w:tcPr><w:shd w:val="clear" w:color="auto" w:fill="1E3A8A"/></w:tcPr>'
                    p_xml = _w_para(cell, bold=True, color="FFFFFF", sz=19)
                else:
                    fill_c = "F8FAFC" if r_idx % 2 == 1 else "FFFFFF"
                    tc_pr = f'<w:tcPr><w:shd w:val="clear" w:color="auto" w:fill="{fill_c}"/></w:tcPr>'
                    p_xml = _w_para(cell, bold=False, color="1E293B", sz=18)
                tbl.append(f"    <w:tc>{tc_pr}{p_xml}</w:tc>")
            tbl.append("  </w:tr>")
        tbl.append("</w:tbl>")
        return "\n".join(tbl)

    # Capa / Banner de Topo
    body_elements.append(_w_para(f"[{status_badge}]", bold=True, color="FFFFFF", sz=20, fill="1D4ED8"))
    body_elements.append(_w_para(doc_title, bold=True, color="0F172A", sz=34))
    body_elements.append(_w_para(doc_sub, bold=False, color="475569", sz=19))

    in_code = False
    current_table: List[List[str]] = []

    for raw_line in linhas:
        line = raw_line.rstrip()
        if line.strip().startswith("```"):
            if current_table:
                body_elements.append(_w_table(current_table))
                current_table = []
            in_code = not in_code
            continue

        if in_code:
            body_elements.append(_w_para(line, bold=False, color="0F172A", sz=17, fill="F1F5F9", mono=True))
            continue

        if line.strip().startswith("|") and line.strip().endswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if all(set(c) <= set("-: ") for c in cells):
                continue
            current_table.append(cells)
            continue
        elif current_table:
            body_elements.append(_w_table(current_table))
            current_table = []

        if not line.strip():
            continue
        if line.startswith("# "):
            body_elements.append(_w_para(line[2:].strip(), bold=True, color="1E3A8A", sz=28))
        elif line.startswith("## "):
            body_elements.append(_w_para(line[3:].strip(), bold=True, color="1D4ED8", sz=24, fill="EFF6FF"))
        elif line.startswith("### "):
            body_elements.append(_w_para(line[4:].strip(), bold=True, color="0F172A", sz=22))
        elif line.lstrip().startswith(("- ", "* ")):
            txt_b = line.lstrip()[2:].strip()
            body_elements.append(_w_para(f"• {txt_b}", bold=False, color="1E293B", sz=20))
        else:
            body_elements.append(_w_para(line.strip(), bold=False, color="1E293B", sz=20))

    if current_table:
        body_elements.append(_w_table(current_table))

    document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    {chr(10).join(body_elements)}
    <w:sectPr>
      <w:pgSz w:w="11906" w:h="16838"/>
      <w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134"/>
    </w:sectPr>
  </w:body>
</w:document>"""

    content_types_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""

    root_rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

    os.makedirs(os.path.dirname(os.path.abspath(caminho_docx)), exist_ok=True)
    with zipfile.ZipFile(caminho_docx, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types_xml)
        zf.writestr("_rels/.rels", root_rels_xml)
        zf.writestr("word/document.xml", document_xml)

    return caminho_docx
