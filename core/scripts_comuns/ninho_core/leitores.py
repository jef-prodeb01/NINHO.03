"""
Leitores de documentos enviados por clientes, só com a biblioteca padrão:
.xlsx (OOXML), .ods, .docx, .odt e .pdf (texto nativo).

Extraído de gerador_artefatos_visuais.py (que mantém uma fachada de reimportação).
Toda descompactação usa `zip_seguro.ler_membro` e todo XML usa `xml_seguro`.
"""

import logging as _logging_ninho

_LOG = _logging_ninho.getLogger("ninho.core.leitores")

import html
import os
import re
import zipfile
import zlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

from ninho_core import xml_seguro
from ninho_core.zip_seguro import ler_membro


def _converter_valor_celula(val: Any, papel_col: str = "") -> Any:
    """Converte strings de CSV/SQL/Excel para tipos nativos SQLite (int, float, str, None)."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return val
    s = str(val).strip()
    if not s or s.upper() in ("NULL", "NONE", "N/A", "<NULL>"):
        return None
    # Trata funções Oracle TO_DATE('2025-03-10', ...) ou SYSDATE
    m_dt = re.match(r"^TO_(?:DATE|TIMESTAMP)\s*\(\s*'([^']+)'", s, flags=re.IGNORECASE)
    if m_dt:
        return m_dt.group(1).strip()
    if s.upper() in ("SYSDATE", "SYSTIMESTAMP", "CURRENT_DATE"):
        return datetime.now().strftime("%Y-%m-%d")
    if s.startswith("'") and s.endswith("'"):
        s = s[1:-1].replace("''", "'")

    # Tenta converter número se coluna for PK, FK ou METRICA, ou se parecer número puro
    s_num = re.sub(r"^R\$\s*", "", s).strip()
    if re.match(r"^-?\d{1,3}(\.\d{3})+,\d+$", s_num):
        s_num = s_num.replace(".", "").replace(",", ".")
    elif re.match(r"^-?\d+,\d+$", s_num):
        s_num = s_num.replace(",", ".")

    if re.match(r"^-?\d+$", s_num):
        try:
            return int(s_num)
        except ValueError as _exc:
            _LOG.debug("Exceção tratada (leitores.py:50): %r", _exc)
    if re.match(r"^-?\d+\.\d+$", s_num):
        try:
            return float(s_num)
        except ValueError as _exc:
            _LOG.debug("Exceção tratada (leitores.py:55): %r", _exc)
    return s


def _ler_planilha_xlsx_abas(caminho_xlsx: Path) -> Dict[str, List[Dict[str, Any]]]:
    """Lê todas as abas de um arquivo `.xlsx` (OOXML) usando apenas `zipfile` + `xml.etree.ElementTree`."""
    abas: Dict[str, List[Dict[str, Any]]] = {}
    if not caminho_xlsx.exists():
        return abas
    try:
        with zipfile.ZipFile(caminho_xlsx, "r") as zf:
            shared_strings: List[str] = []
            if "xl/sharedStrings.xml" in zf.namelist():
                root_ss = xml_seguro.fromstring(ler_membro(zf, "xl/sharedStrings.xml"))
                for si in root_ss.findall(".//{*}si"):
                    textos = [t.text or "" for t in si.findall(".//{*}t")]
                    shared_strings.append("".join(textos))

            mapa_abas: List[Tuple[str, str]] = []
            if "xl/workbook.xml" in zf.namelist():
                root_wb = xml_seguro.fromstring(ler_membro(zf, "xl/workbook.xml"))
                rels_map = {}
                if "xl/_rels/workbook.xml.rels" in zf.namelist():
                    root_rels = xml_seguro.fromstring(ler_membro(zf, "xl/_rels/workbook.xml.rels"))
                    for rel in root_rels.findall(".//{*}Relationship"):
                        rid = rel.attrib.get("Id", "")
                        target = rel.attrib.get("Target", "").lstrip("/")
                        if not target.startswith("xl/"):
                            target = f"xl/{target}"
                        rels_map[rid] = target
                for idx_s, sh in enumerate(root_wb.findall(".//{*}sheet"), 1):
                    nome_aba = sh.attrib.get("name", f"Sheet{idx_s}")
                    rid = next((v for k, v in sh.attrib.items() if k.endswith("id")), "")
                    caminho_xml = rels_map.get(rid, f"xl/worksheets/sheet{idx_s}.xml")
                    mapa_abas.append((nome_aba, caminho_xml))

            for nome_aba, arq_sheet in mapa_abas:
                if arq_sheet not in zf.namelist():
                    continue
                root_sh = xml_seguro.fromstring(ler_membro(zf, arq_sheet))
                linhas_matriz: List[List[str]] = []
                for row_el in root_sh.findall(".//{*}row"):
                    vals_linha = []
                    for c_el in row_el.findall("{*}c"):
                        t_attr = c_el.attrib.get("t", "")
                        v_el = c_el.find("{*}v")
                        is_el = c_el.find("{*}is")
                        val_str = ""
                        if t_attr == "s" and v_el is not None and v_el.text:
                            idx_ss = int(v_el.text)
                            if 0 <= idx_ss < len(shared_strings):
                                val_str = shared_strings[idx_ss]
                        elif t_attr == "inlineStr" and is_el is not None:
                            val_str = "".join(t.text or "" for t in is_el.findall(".//{*}t"))
                        elif v_el is not None and v_el.text is not None:
                            val_str = v_el.text
                        vals_linha.append(val_str.strip())
                    if any(vals_linha):
                        linhas_matriz.append(vals_linha)
                if len(linhas_matriz) >= 2:
                    headers = [h.strip().upper() for h in linhas_matriz[0]]
                    regs = []
                    for r in linhas_matriz[1:]:
                        d_row = {}
                        for i_h, h in enumerate(headers):
                            if h and i_h < len(r):
                                d_row[h] = _converter_valor_celula(r[i_h])
                        if d_row:
                            regs.append(d_row)
                    abas[nome_aba.strip().upper()] = regs
    except Exception as _exc:
        _LOG.debug("Exceção tratada (leitores.py:126): %r", _exc)
    return abas


def ler_planilha_ods(caminho_ods: str) -> List[List[str]]:
    """
    Lê nativamente planilhas OpenDocument Spreadsheet (`.ods` / LibreOffice Calc)
    extraindo `content.xml` via `zipfile` + `xml.etree.ElementTree`, respeitando
    `table:number-columns-repeated`. Blindado contra arquivos corrompidos (Panic Hunt).
    """
    linhas_resultado: List[List[str]] = []
    try:
        if not os.path.isfile(caminho_ods):
            return []
        with zipfile.ZipFile(caminho_ods, "r") as zf:
            if "content.xml" not in zf.namelist():
                return []
            xml_bytes = ler_membro(zf, "content.xml")
        root = xml_seguro.fromstring(xml_bytes)
        ns = {
            "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
            "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
        }
        for table_el in root.findall(".//table:table", ns):
            for row_el in table_el.findall("table:table-row", ns):
                row_vals: List[str] = []
                for cell_el in row_el.findall("table:table-cell", ns):
                    rep_attr = cell_el.attrib.get(
                        "{urn:oasis:names:tc:opendocument:xmlns:table:1.0}number-columns-repeated", "1"
                    )
                    try:
                        repeat = min(int(rep_attr), 30)
                    except ValueError:
                        repeat = 1
                    textos = []
                    for p_el in cell_el.findall(".//text:p", ns):
                        txt = "".join(p_el.itertext()).strip()
                        if txt:
                            textos.append(txt)
                    cell_text = " ".join(textos)
                    for _ in range(repeat):
                        row_vals.append(cell_text)
                # Remover colunas vazias à direita
                while row_vals and row_vals[-1] == "":
                    row_vals.pop()
                if any(v.strip() for v in row_vals):
                    linhas_resultado.append(row_vals)
    except Exception:
        return []
    return linhas_resultado


def extrair_texto_pdf_nativo(caminho_pdf: str, max_chars: int = 12000) -> str:
    """
    Extrai texto de documentos `.pdf` usando apenas a biblioteca padrão do Python (`zlib` + `re`),
    inspirado na arquitetura do `pdfcraft/crates/core`:
      - Descompacta objetos `stream ... endstream` (com ou sem `/FlateDecode`)
      - Interpreta operadores de texto PostScript/PDF `(...) Tj` e `[...] TJ`
      - Decodifica escapes octais/literais e recupera também strings legíveis de PDFs sem compressão.
      - 100% blindado (`panic_hunt`): jamais levanta exceção mesmo diante de PDFs truncados ou binários hostis.
    """
    try:
        if not os.path.isfile(caminho_pdf):
            return ""
        with open(caminho_pdf, "rb") as f:
            raw_bytes = f.read(8 * 1024 * 1024)  # Limite seguro de 8 MB
        if not raw_bytes.startswith(b"%PDF"):
            return ""

        text_chunks: List[str] = []

        def _parse_pdf_content_stream(data_bytes: bytes) -> None:
            txt_latin = data_bytes.decode("latin-1", errors="ignore")
            # Operadores (texto) Tj — suporta tanto parênteses escapados \(\) quanto parênteses balanceados aninhados (padrão PDF 1.4+)
            for m in re.finditer(r"\(((?:[^()\\]|\\.|(?:\([^()\\]*\)))*)\)\s*Tj", txt_latin):
                frag = m.group(1)
                frag = frag.replace(r"\(", "(").replace(r"\)", ")").replace(r"\n", " ").replace(r"\r", " ")
                if frag.strip():
                    text_chunks.append(frag.strip())
            # Operadores [(texto) -12 (continuação)] TJ
            for m in re.finditer(r"\[(.*?)\]\s*TJ", txt_latin, flags=re.DOTALL):
                arr_body = m.group(1)
                parts = re.findall(r"\(((?:[^()\\]|\\.|(?:\([^()\\]*\)))*)\)", arr_body)
                if parts:
                    joined = "".join(parts).replace(r"\(", "(").replace(r"\)", ")")
                    if joined.strip():
                        text_chunks.append(joined.strip())

        for stream_match in re.finditer(rb"stream[\r\n]+(.*?)[\r\n]+endstream", raw_bytes, flags=re.DOTALL):
            stream_data = stream_match.group(1)
            decompressed = None
            for wbits in (zlib.MAX_WBITS, -zlib.MAX_WBITS):
                try:
                    decompressed = zlib.decompress(stream_data, wbits)
                    break
                except Exception:
                    continue
            if decompressed is not None:
                _parse_pdf_content_stream(decompressed)
            else:
                _parse_pdf_content_stream(stream_data)

        if not text_chunks:
            _parse_pdf_content_stream(raw_bytes)

        resultado = " ".join(text_chunks)
        resultado = re.sub(r"\s+", " ", resultado).strip()
        return resultado[:max_chars]
    except Exception:
        return ""


def ler_documento_docx(caminho_docx: str) -> dict:
    """
    Lê nativamente documentos Microsoft Word (`.docx` OOXML), extraindo parágrafos
    (`<w:p>`) e tabelas (`<w:tbl>`) de `word/document.xml`, com fallback resiliente
    `panic_hunt` inspirado em `wordcraft/crates/formats`.
    """
    paragrafos: List[str] = []
    tabelas: List[List[List[str]]] = []
    try:
        with zipfile.ZipFile(caminho_docx, "r") as zf:
            if "word/document.xml" not in zf.namelist():
                return {"formato": "DOCX", "texto": "", "paragrafos": [], "tabelas": []}
            xml_bytes = ler_membro(zf, "word/document.xml")

        root = xml_seguro.fromstring(xml_bytes)
        for elem in root.iter():
            tag = elem.tag.split("}")[-1]
            if tag == "p":
                partes_p: List[str] = []
                for sub in elem.iter():
                    sub_tag = sub.tag.split("}")[-1]
                    if sub_tag == "t" and sub.text:
                        partes_p.append(sub.text)
                    elif sub_tag == "tab":
                        partes_p.append("\t")
                    elif sub_tag in ("br", "cr"):
                        partes_p.append("\n")
                txt_p = "".join(partes_p).strip()
                if txt_p:
                    paragrafos.append(txt_p)
            elif tag == "tbl":
                linhas_tbl: List[List[str]] = []
                for tr in elem:
                    if tr.tag.split("}")[-1] != "tr":
                        continue
                    linha_cells: List[str] = []
                    for tc in tr:
                        if tc.tag.split("}")[-1] != "tc":
                            continue
                        textos_tc = [
                            t.text.strip()
                            for t in tc.iter()
                            if t.tag.split("}")[-1] == "t" and t.text and t.text.strip()
                        ]
                        linha_cells.append(" ".join(textos_tc))
                    if any(linha_cells):
                        linhas_tbl.append(linha_cells)
                if linhas_tbl:
                    tabelas.append(linhas_tbl)
    except Exception:
        # Panic Hunt fallback para .docx truncado/malformado
        try:
            with open(caminho_docx, "rb") as f:
                raw = f.read().decode("utf-8", errors="ignore")
            for m in re.finditer(r"<w:t[^>]*>([^<]+)</w:t>", raw):
                val = html.unescape(m.group(1)).strip()
                if val:
                    paragrafos.append(val)
        except Exception as _exc:
            _LOG.debug("Exceção tratada (leitores.py:297): %r", _exc)

    blocos_txt = list(paragrafos)
    for tbl in tabelas:
        for row in tbl:
            blocos_txt.append(" | ".join(row))
    return {
        "formato": "DOCX",
        "texto": "\n".join(blocos_txt),
        "paragrafos": paragrafos,
        "tabelas": tabelas,
    }


def ler_documento_odt(caminho_odt: str) -> dict:
    """
    Lê nativamente documentos OpenDocument Text (`.odt` / LibreOffice Writer),
    extraindo parágrafos (`<text:p>`, `<text:h>`) e tabelas (`<table:table>`) de
    `content.xml`, com fallback `panic_hunt` inspirado em `wordcraft/crates/formats`.
    """
    paragrafos: List[str] = []
    tabelas: List[List[List[str]]] = []
    try:
        with zipfile.ZipFile(caminho_odt, "r") as zf:
            if "content.xml" not in zf.namelist():
                return {"formato": "ODT", "texto": "", "paragrafos": [], "tabelas": []}
            xml_bytes = ler_membro(zf, "content.xml")

        root = xml_seguro.fromstring(xml_bytes)
        for elem in root.iter():
            tag = elem.tag.split("}")[-1]
            if tag in ("p", "h"):
                txt_p = "".join(elem.itertext()).strip()
                if txt_p and txt_p not in paragrafos[-1:]:
                    paragrafos.append(txt_p)
            elif tag == "table":
                linhas_tbl: List[List[str]] = []
                for tr in elem:
                    if tr.tag.split("}")[-1] != "table-row":
                        continue
                    linha_cells: List[str] = []
                    for tc in tr:
                        if tc.tag.split("}")[-1] != "table-cell":
                            continue
                        txt_c = " ".join(t.strip() for t in tc.itertext() if t.strip())
                        linha_cells.append(txt_c)
                    if any(linha_cells):
                        linhas_tbl.append(linha_cells)
                if linhas_tbl:
                    tabelas.append(linhas_tbl)
    except Exception:
        try:
            with open(caminho_odt, "rb") as f:
                raw = f.read().decode("utf-8", errors="ignore")
            for m in re.finditer(r"<text:[ph][^>]*>([^<]+)</text:[ph]>", raw):
                val = html.unescape(m.group(1)).strip()
                if val:
                    paragrafos.append(val)
        except Exception as _exc:
            _LOG.debug("Exceção tratada (leitores.py:356): %r", _exc)

    blocos_txt = list(paragrafos)
    for tbl in tabelas:
        for row in tbl:
            blocos_txt.append(" | ".join(row))
    return {
        "formato": "ODT",
        "texto": "\n".join(blocos_txt),
        "paragrafos": paragrafos,
        "tabelas": tabelas,
    }
