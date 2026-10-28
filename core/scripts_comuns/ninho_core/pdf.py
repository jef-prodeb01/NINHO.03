"""
Exportação de Markdown para PDF 1.4 nativo (sem dependências), com cabeçalho institucional
e paginação — usado nos guias, relatórios de estratégia e devolução da Governança.

Extraído de gerador_artefatos_visuais.py (que mantém uma fachada de reimportação).
"""

import os
import re
import zlib
from typing import List, Optional


def _pdf_escape_winansi(texto: str) -> bytes:
    """
    Converte string UTF-8 para bytes WinAnsi (CP1252) escapando '\\', '(' e ')'
    para operadores de texto PDF `(...) Tj`.
    """
    substituicoes = {
        "•": "-",
        "—": "-",
        "–": "-",
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
        "→": "->",
        "←": "<-",
        "≥": ">=",
        "≤": "<=",
        "≠": "!=",
        "✓": "[OK]",
        "✅": "[OK]",
        "⚠️": "[!]",
        "❌": "[X]",
    }
    limpo = texto
    for k, v in substituicoes.items():
        limpo = limpo.replace(k, v)
    raw = limpo.encode("cp1252", errors="ignore")
    raw = raw.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")
    return raw


def exportar_markdown_para_pdf(
    caminho_md: str,
    caminho_pdf: str,
    titulo: Optional[str] = None,
    subtitulo: Optional[str] = None,
) -> str:
    """
    Converte um documento Markdown (`.md`) em um arquivo PDF 1.4 corporativo
    multi-página (`595 x 842 pt` A4), inspirado no `pdfcraft/crates/create`,
    com banner institucional azul-marinho, fontes padrão Type1 (`/Helvetica`,
    `/Helvetica-Bold`, `/Courier` em `/WinAnsiEncoding`), tabelas, blocos de código
    e paginação automática, usando apenas a biblioteca padrão do Python.
    """
    if os.path.isfile(caminho_md):
        with open(caminho_md, "r", encoding="utf-8", errors="ignore") as f:
            conteudo_md = f.read()
    else:
        conteudo_md = str(caminho_md or "")

    linhas_md = conteudo_md.splitlines()
    doc_titulo = titulo or "Relatorio Tecnico Oficial - Plataforma NINHO"
    doc_subtitulo = subtitulo or "Arquitetura de Dados, BI, ETL ODI 12c e Governanca Corporativa"

    for ln in linhas_md:
        if ln.startswith("# ") and not titulo:
            doc_titulo = ln[2:].strip()
            break

    # Estrutura de páginas: cada página é uma lista de comandos PDF (bytes)
    paginas_cmds: List[List[bytes]] = []
    cmds_atuais: List[bytes] = []
    y_cursor = 730.0

    def _iniciar_nova_pagina(primeira: bool = False) -> None:
        nonlocal cmds_atuais, y_cursor
        if cmds_atuais:
            paginas_cmds.append(cmds_atuais)
        cmds_atuais = []
        if primeira:
            # Banner institucional no topo da Página 1
            cmds_atuais.append(b"0.06 0.09 0.16 rg 0 758 595 84 re f")
            cmds_atuais.append(b"0.15 0.39 0.92 rg 0 754 595 4 re f")
            cmds_atuais.append(
                b"BT /F2 15 Tf 1 1 1 rg 42 806 Td ("
                + _pdf_escape_winansi(doc_titulo[:72])
                + b") Tj ET"
            )
            cmds_atuais.append(
                b"BT /F1 9.5 Tf 0.75 0.84 0.98 rg 42 786 Td ("
                + _pdf_escape_winansi(doc_subtitulo[:95])
                + b") Tj ET"
            )
            cmds_atuais.append(
                b"BT /F1 8 Tf 0.58 0.64 0.72 rg 42 768 Td ("
                + _pdf_escape_winansi("Documento Oficial Gerado Automaticamente pela Esteira NINHO (PDF 1.4 Nativo)")
                + b") Tj ET"
            )
            y_cursor = 730.0
        else:
            # Cabeçalho compacto nas páginas seguintes
            cmds_atuais.append(b"0.95 0.96 0.98 rg 0 806 595 36 re f")
            cmds_atuais.append(b"0.82 0.86 0.92 RG 0.8 w 42 806 m 553 806 l S")
            cmds_atuais.append(
                b"BT /F2 8.5 Tf 0.12 0.23 0.54 rg 42 818 Td ("
                + _pdf_escape_winansi(doc_titulo[:85])
                + b") Tj ET"
            )
            y_cursor = 784.0

    def _garantir_espaco(altura_necessaria: float) -> None:
        nonlocal y_cursor
        if y_cursor - altura_necessaria < 56.0:
            _iniciar_nova_pagina(primeira=False)

    def _quebrar_linha(texto_limpo: str, max_col: int = 86) -> List[str]:
        palavras = texto_limpo.split()
        if not palavras:
            return [""]
        partes: List[str] = []
        atual = palavras[0]
        for p in palavras[1:]:
            if len(atual) + 1 + len(p) <= max_col:
                atual += " " + p
            else:
                partes.append(atual)
                atual = p
        partes.append(atual)
        return partes

    _iniciar_nova_pagina(primeira=True)
    em_codigo = False

    for raw_line in linhas_md:
        linha = raw_line.rstrip()
        if linha.strip().startswith("```"):
            em_codigo = not em_codigo
            continue

        if em_codigo:
            _garantir_espaco(14.0)
            cmds_atuais.append(
                f"0.94 0.96 0.98 rg 42 {y_cursor - 3:.1f} 511 13 re f".encode("ascii")
            )
            cmds_atuais.append(
                f"BT /F3 8 Tf 0.12 0.16 0.23 rg 46 {y_cursor:.1f} Td (".encode("ascii")
                + _pdf_escape_winansi(linha[:96])
                + b") Tj ET"
            )
            y_cursor -= 13.0
            continue

        if not linha.strip():
            y_cursor -= 6.0
            continue

        # Limpar marcações inline simples (**negrito**, `codigo`)
        linha_limpa = re.sub(r"\*\*([^*]+)\*\*", r"\1", linha)
        linha_limpa = re.sub(r"`([^`]+)`", r"\1", linha_limpa)

        if linha.startswith("# "):
            _garantir_espaco(28.0)
            y_cursor -= 6.0
            cmds_atuais.append(
                f"BT /F2 13.5 Tf 0.06 0.09 0.16 rg 42 {y_cursor:.1f} Td (".encode("ascii")
                + _pdf_escape_winansi(linha_limpa[2:].strip()[:78])
                + b") Tj ET"
            )
            y_cursor -= 6.0
            cmds_atuais.append(
                f"0.15 0.39 0.92 RG 1.2 w 42 {y_cursor:.1f} m 553 {y_cursor:.1f} l S".encode("ascii")
            )
            y_cursor -= 14.0
        elif linha.startswith("## "):
            _garantir_espaco(24.0)
            y_cursor -= 4.0
            cmds_atuais.append(
                f"BT /F2 11.5 Tf 0.12 0.23 0.54 rg 42 {y_cursor:.1f} Td (".encode("ascii")
                + _pdf_escape_winansi(linha_limpa[3:].strip()[:82])
                + b") Tj ET"
            )
            y_cursor -= 15.0
        elif linha.startswith("### "):
            _garantir_espaco(20.0)
            cmds_atuais.append(
                f"BT /F2 10.2 Tf 0.09 0.32 0.48 rg 42 {y_cursor:.1f} Td (".encode("ascii")
                + _pdf_escape_winansi(linha_limpa[4:].strip()[:86])
                + b") Tj ET"
            )
            y_cursor -= 14.0
        elif linha.strip().startswith("|") and linha.strip().endswith("|"):
            # Linha de tabela Markdown
            if re.match(r"^\|[\s\-:|]+\|$", linha.strip()):
                continue
            celulas = [c.strip() for c in linha.strip().strip("|").split("|")]
            linha_tab = " | ".join(c[:26] for c in celulas[:6])
            _garantir_espaco(14.0)
            cmds_atuais.append(
                f"0.97 0.98 0.99 rg 42 {y_cursor - 3:.1f} 511 13 re f".encode("ascii")
            )
            cmds_atuais.append(
                f"BT /F3 8 Tf 0.12 0.16 0.23 rg 46 {y_cursor:.1f} Td (".encode("ascii")
                + _pdf_escape_winansi(linha_tab[:95])
                + b") Tj ET"
            )
            y_cursor -= 13.0
        elif linha.lstrip().startswith(("- ", "* ")):
            item_txt = "- " + linha_limpa.lstrip()[2:].strip()
            for idx_w, w_line in enumerate(_quebrar_linha(item_txt, max_col=86)):
                _garantir_espaco(14.0)
                x_pos = 48 if idx_w == 0 else 58
                cmds_atuais.append(
                    f"BT /F1 9.5 Tf 0.12 0.16 0.23 rg {x_pos} {y_cursor:.1f} Td (".encode("ascii")
                    + _pdf_escape_winansi(w_line)
                    + b") Tj ET"
                )
                y_cursor -= 13.0
        else:
            for w_line in _quebrar_linha(linha_limpa.strip(), max_col=88):
                _garantir_espaco(14.0)
                cmds_atuais.append(
                    f"BT /F1 9.5 Tf 0.15 0.20 0.28 rg 42 {y_cursor:.1f} Td (".encode("ascii")
                    + _pdf_escape_winansi(w_line)
                    + b") Tj ET"
                )
                y_cursor -= 13.0

    if cmds_atuais:
        paginas_cmds.append(cmds_atuais)

    total_paginas = len(paginas_cmds)
    for idx_p, cmds in enumerate(paginas_cmds, start=1):
        cmds.append(b"0.82 0.86 0.92 RG 0.6 w 42 42 m 553 42 l S")
        rodape = f"NINHO Data Platform - Pagina {idx_p} de {total_paginas}"
        cmds.append(
            b"BT /F1 8 Tf 0.45 0.50 0.58 rg 42 28 Td ("
            + _pdf_escape_winansi(rodape)
            + b") Tj ET"
        )

    # Montagem binária dos objetos PDF 1.4 com tabela xref exata
    objetos: List[bytes] = []

    # 1: Catalog, 2: Pages, 3: Helvetica, 4: Helvetica-Bold, 5: Courier
    kids_refs = " ".join(f"{6 + 2 * i} 0 R" for i in range(total_paginas))
    objetos.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objetos.append(f"<< /Type /Pages /Kids [{kids_refs}] /Count {total_paginas} >>".encode("ascii"))
    objetos.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    objetos.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")
    objetos.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier /Encoding /WinAnsiEncoding >>")

    for i, cmds in enumerate(paginas_cmds):
        page_obj_num = 6 + 2 * i
        content_obj_num = page_obj_num + 1
        stream_raw = b"\n".join(cmds)
        stream_comp = zlib.compress(stream_raw)
        page_dict = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            f"/Resources << /Font << /F1 3 0 R /F2 4 0 R /F3 5 0 R >> >> "
            f"/Contents {content_obj_num} 0 R >>"
        ).encode("ascii")
        content_dict = (
            f"<< /Length {len(stream_comp)} /Filter /FlateDecode >>\nstream\n".encode("ascii")
            + stream_comp
            + b"\nendstream"
        )
        objetos.append(page_dict)
        objetos.append(content_dict)

    os.makedirs(os.path.dirname(os.path.abspath(caminho_pdf)), exist_ok=True)
    partes_pdf: List[bytes] = [b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"]
    offsets: List[int] = [0]
    cursor_bytes = len(partes_pdf[0])

    for idx_obj, corpo_obj in enumerate(objetos, start=1):
        offsets.append(cursor_bytes)
        bloco = f"{idx_obj} 0 obj\n".encode("ascii") + corpo_obj + b"\nendobj\n"
        partes_pdf.append(bloco)
        cursor_bytes += len(bloco)

    xref_offset = cursor_bytes
    linhas_xref = [f"xref\n0 {len(objetos) + 1}\n0000000000 65535 f \n".encode("ascii")]
    for off in offsets[1:]:
        linhas_xref.append(f"{off:010d} 00000 n \n".encode("ascii"))

    trailer = (
        f"trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n"
    ).encode("ascii")

    with open(caminho_pdf, "wb") as f:
        for p in partes_pdf:
            f.write(p)
        for lx in linhas_xref:
            f.write(lx)
        f.write(trailer)

    return caminho_pdf
