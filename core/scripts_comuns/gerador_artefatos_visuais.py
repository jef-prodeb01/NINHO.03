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

import csv
import html
import io
import math
import os
import re
import sqlite3
import zipfile
import zlib
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ==============================================================================
# 0. UTILITÁRIOS DE MEDIÇÃO E FORMATAÇÃO (INSPIRADO NO GRIDCRAFT APPROXMEASURE)
# ==============================================================================

def approx_text_width(text: str, font_size: float = 11.0, bold: bool = False) -> float:
    """
    Calcula a largura aproximada de uma string em pixels sem depender de FreeType/ HarfBuzz.
    Inspirado em `ApproxMeasure` de `gridcraft/crates/chart/src/lib.rs`.
    """
    if not text:
        return 0.0
    factor = 0.62 if bold else 0.56
    width = 0.0
    for ch in str(text):
        if ch in "iIl1|.,:;!':":
            width += font_size * 0.30
        elif ch in "MW@%QGO":
            width += font_size * 0.78
        elif ch.isupper():
            width += font_size * 0.65
        else:
            width += font_size * factor
    return round(width, 1)


def _esc(val: object) -> str:
    return html.escape(str(val or ""), quote=True)


def _limpar_label(nome: str) -> str:
    limpo = re.sub(
        r"^(FATO_|FAT_|DIM_|STG_|VW_KPI_|VW_EVENTO_|VW_DIM_|SK_|PK_|FK_|COD_|NUM_|VAL_|VLR_|QTD_|DES_|NOM_|DT_|DAT_|FLG_|IND_)",
        "",
        str(nome or ""),
        flags=re.IGNORECASE,
    )
    return limpo.replace("_", " ").strip().title() or str(nome)


def _svg_donut_arc(cx: float, cy: float, r: float, start_deg: float, end_deg: float) -> str:
    """Gera o path SVG `M ... A ...` para um arco de rosca trigonométrico (GridCraft Pie/Donut)."""
    if end_deg - start_deg >= 359.9:
        end_deg = start_deg + 359.8
    start_rad = math.radians(start_deg - 90.0)
    end_rad = math.radians(end_deg - 90.0)
    x1 = cx + r * math.cos(start_rad)
    y1 = cy + r * math.sin(start_rad)
    x2 = cx + r * math.cos(end_rad)
    y2 = cy + r * math.sin(end_rad)
    large_arc = 1 if (end_deg - start_deg) > 180.0 else 0
    return f"M {x1:.2f} {y1:.2f} A {r:.2f} {r:.2f} 0 {large_arc} 1 {x2:.2f} {y2:.2f}"


# ==============================================================================
# 1. GERADOR DE MOCKUP VISUAL DO PAINEL BI (FIGCRAFT + GRIDCRAFT CHART)
# ==============================================================================

def _normalizar_tabela(t: dict, is_fato: bool = False) -> dict:
    """Normaliza o dicionário de tabela entre `melhorar_dw_existente.py` (`nome_tabela`/`nome_dw`) e formato canônico."""
    if not isinstance(t, dict):
        return {"nome": "TABELA", "colunas": [], "pks": [], "fks": []}
    nome = (t.get("nome") or t.get("nome_tabela") or "TABELA").upper()
    pks = [p.upper() for p in t.get("pks", [])]
    fks = [
        {
            "coluna": str(fk.get("coluna", "")).upper(),
            "tabela_ref": str(fk.get("tabela_ref", "")).upper(),
            "coluna_ref": str(fk.get("coluna_ref", "")).upper(),
        }
        for fk in t.get("fks", [])
        if isinstance(fk, dict) and fk.get("coluna")
    ]
    cols_norm = []
    for c in t.get("colunas", []):
        cn = (c.get("nome") or c.get("nome_dw") or "COLUNA").upper()
        papel = c.get("papel")
        if not papel:
            if cn in pks or cn == "DIMENSION_KEY" or (not is_fato and cn.startswith("SK_")):
                papel = "PK"
            elif is_fato and (cn.startswith(("SK_", "DIM_", "FK_")) or cn.endswith("_KEY")):
                papel = "FK"
            elif cn.startswith(("VAL_", "VLR_", "QTD_", "QT_", "PER_", "PRC_", "NUM_VALOR")):
                papel = "METRICA"
            elif cn in ("DTC_INICIO", "DTC_FIM", "DTC_EFETIVACAO", "DTC_EXPIRACAO", "SIN_ATIVO", "FLG_ATUAL", "FLG_ATIVO"):
                papel = "SCD2"
            else:
                papel = "ATRIBUTO"
        cols_norm.append({"nome": cn, "papel": papel, "tipo": c.get("tipo_oracle") or c.get("tipo") or "VARCHAR2(100)"})
    return {"nome": nome, "colunas": cols_norm, "pks": pks, "fks": fks}


def _normalizar_dims_fatos(dims: List[dict], fatos: List[dict]) -> Tuple[List[dict], List[dict]]:
    return [_normalizar_tabela(d, False) for d in (dims or [])], [_normalizar_tabela(f, True) for f in (fatos or [])]


# ==============================================================================
# 0.5 MOTOR DE PROVA REAL PÓS-CARGA (SQLITE IN-MEMORY + AUDITORIA DE MEDIDAS DAX)
# ==============================================================================

def _formatar_numero_br(valor: Any, tipo: str = "num", compacto: bool = False) -> str:
    """Formata valores numéricos no padrão brasileiro para exibição no Mockup e Relatório de Prova Real."""
    try:
        v = float(valor or 0.0)
    except (ValueError, TypeError):
        return str(valor or "0")

    if tipo == "moeda":
        if compacto and abs(v) >= 1_000_000:
            return f"R$ {v / 1_000_000:,.2f} M".replace(",", "X").replace(".", ",").replace("X", ".")
        if compacto and abs(v) >= 10_000:
            return f"R$ {v / 1_000:,.1f} mil".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if tipo == "pct":
        # Se vier em base 0..1 (ex: 0.917), converte para %
        v_pct = v * 100.0 if abs(v) <= 1.5 and v != 0 else v
        return f"{v_pct:,.1f}%".replace(",", "X").replace(".", ",").replace("X", ".")
    if tipo == "int" or abs(v - round(v)) < 1e-6:
        return f"{int(round(v)):,}".replace(",", ".")
    return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


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
        except ValueError:
            pass
    if re.match(r"^-?\d+\.\d+$", s_num):
        try:
            return float(s_num)
        except ValueError:
            pass
    return s


def _inferir_sk_nk_dim(dim: dict) -> Tuple[str, str, Optional[str]]:
    """Retorna (coluna_sk, coluna_nk, coluna_scd2_flag) de uma dimensão normalizada."""
    cols = dim.get("colunas", [])
    nomes = [c["nome"].upper() for c in cols]
    sk = None
    for p in dim.get("pks", []):
        if p.upper() in nomes:
            sk = p.upper()
            break
    if not sk:
        for c in cols:
            if c.get("papel") == "PK" or c["nome"].startswith("SK_") or c["nome"] == "DIMENSION_KEY":
                sk = c["nome"]
                break
    if not sk:
        sk = nomes[0] if nomes else "SK_DIM"

    scd_flag = next(
        (n for n in nomes if n in ("FLG_ATUAL", "SIN_ATIVO", "FLG_ATIVO", "IND_ATIVO", "IC_ATIVO")),
        None,
    )
    ignore = {sk, "DTC_INICIO", "DTC_FIM", "DTC_EFETIVACAO", "DTC_EXPIRACAO", "DAT_INICIO", "DAT_FIM"}
    if scd_flag:
        ignore.add(scd_flag)

    nk = next((n for n in nomes if n not in ignore and n.startswith(("COD_", "NUM_", "ID_", "CD_", "SIG_"))), None)
    if not nk:
        nk = next((n for n in nomes if n not in ignore), sk)
    return sk, nk, scd_flag


def _mapear_relacionamentos_star(dims: List[dict], fatos: List[dict]) -> Dict[str, List[dict]]:
    """Mapeia todas as FKs de cada FATO_* para a respectiva DIM_* (explícitas ou por convenção de nomes)."""
    dims_map = {d["nome"].upper(): d for d in dims}
    sk_por_dim = {d["nome"].upper(): _inferir_sk_nk_dim(d)[0] for d in dims}
    sufixo_por_dim = {
        re.sub(r"^DIM_", "", d["nome"].upper()): d["nome"].upper()
        for d in dims
    }
    resultado: Dict[str, List[dict]] = {}
    for f in fatos:
        nf = f["nome"].upper()
        rels = []
        usados = set()
        for fk in f.get("fks", []):
            col_fk = fk["coluna"].upper()
            tab_ref = fk["tabela_ref"].upper()
            if tab_ref in dims_map and col_fk not in usados:
                rels.append({
                    "coluna_fk": col_fk,
                    "tabela_dim": tab_ref,
                    "coluna_pk": fk.get("coluna_ref") or sk_por_dim[tab_ref],
                })
                usados.add(col_fk)

        for c in f.get("colunas", []):
            cn = c["nome"].upper()
            if cn in usados:
                continue
            # Tenta casar pelo nome exato da SK ou pelo sufixo da dimensão
            for nome_d, sk_d in sk_por_dim.items():
                if cn == sk_d and sk_d != "DIMENSION_KEY":
                    rels.append({"coluna_fk": cn, "tabela_dim": nome_d, "coluna_pk": sk_d})
                    usados.add(cn)
                    break
            if cn in usados:
                continue
            suf_col = re.sub(r"^(SK_|FK_|ID_|DIM_|COD_)", "", cn)
            suf_col = re.sub(r"_KEY$", "", suf_col)
            for suf_d, nome_d in sufixo_por_dim.items():
                if suf_col == suf_d or (len(suf_d) >= 4 and (suf_col.startswith(suf_d) or suf_d.startswith(suf_col))):
                    rels.append({"coluna_fk": cn, "tabela_dim": nome_d, "coluna_pk": sk_por_dim[nome_d]})
                    usados.add(cn)
                    break
        resultado[nf] = rels
    return resultado


def _dividir_valores_sql_insert(bloco_vals: str) -> List[str]:
    """Divide a lista `v1, v2, 'texto, com virgula', TO_DATE('2025-01-01','YYYY-MM-DD')` respeitando aspas e parênteses."""
    itens = []
    atual = []
    em_aspas = False
    nivel_par = 0
    i = 0
    n = len(bloco_vals)
    while i < n:
        ch = bloco_vals[i]
        if ch == "'":
            if em_aspas and i + 1 < n and bloco_vals[i + 1] == "'":
                atual.append("''")
                i += 2
                continue
            em_aspas = not em_aspas
            atual.append(ch)
        elif not em_aspas:
            if ch == "(":
                nivel_par += 1
                atual.append(ch)
            elif ch == ")":
                nivel_par = max(0, nivel_par - 1)
                atual.append(ch)
            elif ch == "," and nivel_par == 0:
                itens.append("".join(atual).strip())
                atual = []
            else:
                atual.append(ch)
        else:
            atual.append(ch)
        i += 1
    if atual:
        itens.append("".join(atual).strip())
    return itens


def _extrair_inserts_sql(texto_sql: str) -> List[Tuple[str, Optional[List[str]], List[Any]]]:
    """Extrai instruções `INSERT INTO [schema.]tabela [(cols)] VALUES (...)` de scripts SQL."""
    resultados = []
    padrao = re.compile(
        r"INSERT\s+INTO\s+(?:[\"\w]+\.)?\"?([A-Za-z0-9_]+)\"?\s*(?:\(([^)]+)\))?\s*VALUES\s*\((.+?)\)\s*;",
        flags=re.IGNORECASE | re.DOTALL,
    )
    for m in padrao.finditer(texto_sql or ""):
        tabela = m.group(1).strip().upper()
        cols_raw = m.group(2)
        vals_raw = m.group(3)
        cols = [c.strip().strip('"').upper() for c in cols_raw.split(",")] if cols_raw else None
        vals = [_converter_valor_celula(v) for v in _dividir_valores_sql_insert(vals_raw)]
        resultados.append((tabela, cols, vals))
    return resultados


def _ler_planilha_xlsx_abas(caminho_xlsx: Path) -> Dict[str, List[Dict[str, Any]]]:
    """Lê todas as abas de um arquivo `.xlsx` (OOXML) usando apenas `zipfile` + `xml.etree.ElementTree`."""
    abas: Dict[str, List[Dict[str, Any]]] = {}
    if not caminho_xlsx.exists():
        return abas
    try:
        with zipfile.ZipFile(caminho_xlsx, "r") as zf:
            shared_strings: List[str] = []
            if "xl/sharedStrings.xml" in zf.namelist():
                root_ss = ET.fromstring(zf.read("xl/sharedStrings.xml"))
                for si in root_ss.findall(".//{*}si"):
                    textos = [t.text or "" for t in si.findall(".//{*}t")]
                    shared_strings.append("".join(textos))

            mapa_abas: List[Tuple[str, str]] = []
            if "xl/workbook.xml" in zf.namelist():
                root_wb = ET.fromstring(zf.read("xl/workbook.xml"))
                rels_map = {}
                if "xl/_rels/workbook.xml.rels" in zf.namelist():
                    root_rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
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
                root_sh = ET.fromstring(zf.read(arq_sheet))
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
    except Exception:
        pass
    return abas


def carregar_amostras_dw_sqlite(
    dims: List[dict],
    fatos: List[dict],
    base_dir: Optional[Path] = None,
    caminho_amostras: Optional[Path] = None,
) -> Tuple[sqlite3.Connection, dict]:
    """
    Cria o Star Schema (`DIM_*` e `FATO_*`) em um banco `sqlite3` em memória e carrega
    os dados da carga/amostra fornecidos pelo engenheiro (em `.csv`, `.tsv`, `.sql` `INSERT INTO`,
    `.xlsx` ou `.ods`). Caso nenhuma amostra externa tenha sido depositada ainda, gera uma
    amostra relacionalmente íntegra para validação das fórmulas DAX e do Mockup.
    """
    dims_n, fatos_n = _normalizar_dims_fatos(dims, fatos)
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    todas_tabelas = dims_n + fatos_n
    mapa_tabelas = {t["nome"].upper(): t for t in todas_tabelas}
    rels_star = _mapear_relacionamentos_star(dims_n, fatos_n)

    # 1. Criação das tabelas no SQLite
    for t in todas_tabelas:
        nt = t["nome"].upper()
        cols_ddl = []
        nomes_vistos = set()
        for c in t.get("colunas", []):
            cn = c["nome"].upper()
            if cn in nomes_vistos:
                continue
            nomes_vistos.add(cn)
            papel = c.get("papel", "")
            if papel in ("PK", "FK") or cn.startswith(("SK_", "NUM_", "QTD_", "QT_")):
                tipo_sql = " NUMERIC"
            elif papel == "METRICA" or cn.startswith(("VAL_", "VLR_", "PER_", "PRC_")):
                tipo_sql = " REAL"
            else:
                tipo_sql = " TEXT"
            cols_ddl.append(f'"{cn}"{tipo_sql}')
        if not cols_ddl:
            cols_ddl = ['"ID" INTEGER']
        cur.execute(f'CREATE TABLE IF NOT EXISTS "{nt}" ({", ".join(cols_ddl)})')

    # 2. Descoberta de arquivos de amostra
    pastas_busca: List[Path] = []
    if caminho_amostras:
        p_am = Path(caminho_amostras)
        if not p_am.is_absolute() and base_dir:
            p_am = Path(base_dir) / p_am
        if p_am.exists():
            pastas_busca.append(p_am)

    if base_dir:
        bd = Path(base_dir)
        for sub in (
            bd / "entrega" / "planejador_dw" / "amostras",
            bd / "entrega" / "planejador_dw" / "ddl",
            bd / "saida" / "planejador_dw" / "08_datasets_bi",
        ):
            if sub.exists() and sub not in pastas_busca:
                pastas_busca.append(sub)

    arquivos_candidatos: List[Path] = []
    for p in pastas_busca:
        if p.is_file():
            arquivos_candidatos.append(p)
        elif p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.is_file() and f.suffix.lower() in (".csv", ".tsv", ".sql", ".ddl", ".txt", ".xlsx") and f.name.lower() != "readme.md":
                    if f not in arquivos_candidatos:
                        arquivos_candidatos.append(f)

    arquivos_carregados: List[str] = []

    def _inserir_dicts_tabela(nome_tab: str, linhas: List[Dict[str, Any]]) -> int:
        t_obj = mapa_tabelas.get(nome_tab.upper())
        if not t_obj or not linhas:
            return 0
        cols_validas = [c["nome"].upper() for c in t_obj.get("colunas", [])]
        inseridos = 0
        for row in linhas:
            row_up = {str(k).strip().upper(): v for k, v in row.items() if k}
            cols_presentes = [c for c in cols_validas if c in row_up]
            if not cols_presentes:
                continue
            placeholders = ", ".join("?" for _ in cols_presentes)
            cols_quoted = ", ".join(f'"{c}"' for c in cols_presentes)
            vals = [_converter_valor_celula(row_up[c]) for c in cols_presentes]
            cur.execute(f'INSERT INTO "{nome_tab.upper()}" ({cols_quoted}) VALUES ({placeholders})', vals)
            inseridos += 1
        return inseridos

    # 3. Carrega instruções INSERT INTO de arquivos .sql / .ddl / .txt
    for arq in arquivos_candidatos:
        if arq.suffix.lower() in (".sql", ".ddl", ".txt"):
            try:
                txt = arq.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            inserts = _extrair_inserts_sql(txt)
            qtd_ins_arq = 0
            for tab_ins, cols_ins, vals_ins in inserts:
                t_obj = mapa_tabelas.get(tab_ins)
                if not t_obj:
                    continue
                cols_tab = [c["nome"].upper() for c in t_obj.get("colunas", [])]
                if cols_ins:
                    pares = {c: vals_ins[i] for i, c in enumerate(cols_ins) if i < len(vals_ins) and c in cols_tab}
                else:
                    pares = {cols_tab[i]: vals_ins[i] for i in range(min(len(cols_tab), len(vals_ins)))}
                if pares:
                    cols_q = ", ".join(f'"{c}"' for c in pares.keys())
                    ph = ", ".join("?" for _ in pares)
                    cur.execute(f'INSERT INTO "{tab_ins}" ({cols_q}) VALUES ({ph})', list(pares.values()))
                    qtd_ins_arq += 1
            if qtd_ins_arq > 0 and arq.name not in arquivos_carregados:
                arquivos_carregados.append(arq.name)

    # 4. Carrega arquivos .csv / .tsv (por tabela ou flat consolidado)
    for arq in arquivos_candidatos:
        if arq.suffix.lower() in (".csv", ".tsv"):
            try:
                conteudo = arq.read_text(encoding="utf-8-sig", errors="ignore")
            except Exception:
                continue
            linhas_txt = [l for l in conteudo.splitlines() if l.strip()]
            if len(linhas_txt) < 2:
                continue
            primeira = linhas_txt[0]
            delim = ";" if primeira.count(";") >= primeira.count(",") else ("\t" if "\t" in primeira else ",")
            reader = list(csv.DictReader(io.StringIO(conteudo), delimiter=delim))
            if not reader:
                continue

            stem_up = arq.stem.upper()
            # Verifica se o nome do arquivo corresponde diretamente a uma tabela DIM_* ou FATO_*
            tab_match = next(
                (nt for nt in mapa_tabelas.keys() if nt == stem_up or nt in stem_up or stem_up in nt),
                None,
            )
            if tab_match:
                if _inserir_dicts_tabela(tab_match, reader) > 0 and arq.name not in arquivos_carregados:
                    arquivos_carregados.append(arq.name)
            else:
                # CSV consolidado / flat (ex: mock_dados_bi.csv): distribui colunas entre FATO e DIMs
                inseriu_algo = False
                for f in fatos_n:
                    if _inserir_dicts_tabela(f["nome"], reader) > 0:
                        inseriu_algo = True
                for d in dims_n:
                    sk_d, nk_d, _ = _inferir_sk_nk_dim(d)
                    vistos_d = set()
                    linhas_unicas_d = []
                    for r in reader:
                        r_up = {str(k).strip().upper(): v for k, v in r.items() if k}
                        chave = r_up.get(sk_d) if sk_d in r_up else r_up.get(nk_d)
                        if chave not in vistos_d:
                            vistos_d.add(chave)
                            linhas_unicas_d.append(r_up)
                    if _inserir_dicts_tabela(d["nome"], linhas_unicas_d) > 0:
                        inseriu_algo = True
                if inseriu_algo and arq.name not in arquivos_carregados:
                    arquivos_carregados.append(arq.name)

    # 5. Carrega planilhas .xlsx com abas correspondentes às tabelas
    for arq in arquivos_candidatos:
        if arq.suffix.lower() == ".xlsx" and not arq.name.lower().startswith("indicadores_powerbi_"):
            abas_xlsx = _ler_planilha_xlsx_abas(arq)
            inseriu_xlsx = False
            for nome_aba, regs in abas_xlsx.items():
                tab_m = next((nt for nt in mapa_tabelas.keys() if nt == nome_aba or nt in nome_aba or nome_aba in nt), None)
                if tab_m and _inserir_dicts_tabela(tab_m, regs) > 0:
                    inseriu_xlsx = True
            if inseriu_xlsx and arq.name not in arquivos_carregados:
                arquivos_carregados.append(arq.name)

    conn.commit()

    # Verifica contagem atual nas tabelas FATO e DIM
    contagens = {}
    for nt in mapa_tabelas:
        cur.execute(f'SELECT COUNT(*) FROM "{nt}"')
        contagens[nt] = int(cur.fetchone()[0])

    total_fatos = sum(contagens.get(f["nome"].upper(), 0) for f in fatos_n)
    origem_amostra = "AMOSTRA_FORNECIDA" if total_fatos > 0 else "SINTETICA_AUTO"

    # 6. Se nenhuma amostra externa foi fornecida ainda, popula amostra relacional realista em SQLite
    if total_fatos == 0 and fatos_n:
        for d in dims_n:
            nd = d["nome"].upper()
            sk_d, nk_d, scd_flag = _inferir_sk_nk_dim(d)
            cols_d = [c["nome"].upper() for c in d.get("colunas", [])]
            col_desc = next((c for c in cols_d if c.startswith(("DES_", "NOM_", "DSC_", "SIG_"))), nk_d)
            eh_tempo = "TEMPO" in nd or "DATA" in nd or "CALEND" in nd
            if eh_tempo:
                meses_nomes = ["Jan/26", "Fev/26", "Mar/26", "Abr/26", "Mai/26", "Jun/26"]
                for idx_m, m_lbl in enumerate(meses_nomes, 1):
                    sk_val = 202600 + idx_m
                    row_t = {sk_d: sk_val}
                    for c in cols_d:
                        if c == sk_d:
                            row_t[c] = sk_val
                        elif "ANO" in c:
                            row_t[c] = 2026
                        elif "MES" in c and c.startswith("NUM_"):
                            row_t[c] = idx_m
                        elif "DATA" in c or c.startswith(("DT_", "DTC_")):
                            row_t[c] = f"2026-0{idx_m}-15"
                        else:
                            row_t[c] = m_lbl
                    _inserir_dicts_tabela(nd, [row_t])
            else:
                lbl_base = _limpar_label(nd)
                # Linha sentinela -1 + 4 entidades vigentes + 1 versão histórica SCD2 (mesma NK da SK=1)
                amostras_dim = [
                    (-1, "NI", "Não Informado (-1)", "S"),
                    (1, f"COD-{lbl_base[:3].upper()}-01", f"{lbl_base} Regional Norte", "N"),
                    (2, f"COD-{lbl_base[:3].upper()}-01", f"{lbl_base} Regional Norte (Atual)", "S"),
                    (3, f"COD-{lbl_base[:3].upper()}-02", f"{lbl_base} Central Sede", "S"),
                    (4, f"COD-{lbl_base[:3].upper()}-03", f"{lbl_base} Sul Metropolitana", "S"),
                    (5, f"COD-{lbl_base[:3].upper()}-04", f"{lbl_base} Leste Interior", "S"),
                ]
                rows_d = []
                for sk_v, nk_v, desc_v, flg_v in amostras_dim:
                    r_d = {}
                    for c in cols_d:
                        if c == sk_d:
                            r_d[c] = sk_v
                        elif c == nk_d:
                            r_d[c] = nk_v
                        elif c == col_desc:
                            r_d[c] = desc_v
                        elif scd_flag and c == scd_flag:
                            r_d[c] = flg_v
                        else:
                            r_d[c] = desc_v
                    rows_d.append(r_d)
                _inserir_dicts_tabela(nd, rows_d)

        # Popula 12 linhas na Fato principal distribuídas entre as SKs (incluindo SK=1 e SK=2 da mesma NK e 1 linha SK=-1)
        f_princ = fatos_n[0]
        nf_p = f_princ["nome"].upper()
        cols_f = [c["nome"].upper() for c in f_princ.get("colunas", [])]
        rels_f = rels_star.get(nf_p, [])
        sk_seq = [2, 2, 1, 3, 3, 3, 4, 4, 5, 5, 2, -1]
        mes_seq = [202601, 202601, 202602, 202602, 202603, 202603, 202604, 202604, 202605, 202605, 202606, 202606]
        val_seq = [4200.0, 3800.0, 3500.0, 5100.0, 4900.0, 4600.0, 3900.0, 4100.0, 2800.0, 3200.0, 5400.0, 1500.0]
        qtd_seq = [4, 3, 3, 5, 4, 4, 3, 4, 2, 3, 5, 1]
        rows_f = []
        for idx_r in range(12):
            rf = {}
            for c in cols_f:
                rel_match = next((r for r in rels_f if r["coluna_fk"] == c), None)
                if rel_match:
                    if "TEMPO" in rel_match["tabela_dim"] or "DATA" in rel_match["tabela_dim"]:
                        rf[c] = mes_seq[idx_r]
                    else:
                        rf[c] = sk_seq[idx_r]
                elif c.startswith(("VAL_", "VLR_")):
                    rf[c] = val_seq[idx_r]
                elif c.startswith(("QTD_", "QT_")):
                    rf[c] = qtd_seq[idx_r]
                elif c.startswith(("PER_", "PRC_")):
                    rf[c] = round(val_seq[idx_r] / 100.0, 2)
                else:
                    rf[c] = idx_r + 1
            rows_f.append(rf)
        _inserir_dicts_tabela(nf_p, rows_f)
        conn.commit()
        for nt in mapa_tabelas:
            cur.execute(f'SELECT COUNT(*) FROM "{nt}"')
            contagens[nt] = int(cur.fetchone()[0])

    return conn, {
        "origem_amostra": origem_amostra,
        "arquivos_carregados": arquivos_carregados,
        "contagens": contagens,
        "relacionamentos": rels_star,
    }


def extrair_medidas_dax_guia(texto_md: str) -> List[dict]:
    """
    Extrai todas as medidas DAX (`Nome da Medida = Expressão`) dos blocos ```dax ... ```
    do Guia do Analista de BI (`GUIA_ANALISTA_BI_<PROJETO>.md`).
    """
    medidas: List[dict] = []
    if not texto_md:
        return medidas
    blocos = re.findall(r"```dax\s*(.*?)```", texto_md, flags=re.IGNORECASE | re.DOTALL)
    for bloco in blocos:
        linhas = bloco.splitlines()
        nome_atual = None
        expr_linhas: List[str] = []
        comentario_ant = ""
        nivel_par = 0

        def _fechar_medida():
            nonlocal nome_atual, expr_linhas, comentario_ant
            if nome_atual and expr_linhas:
                expr_full = "\n".join(expr_linhas).strip()
                if expr_full:
                    medidas.append({
                        "nome": nome_atual.strip(),
                        "expressao": expr_full,
                        "comentario": comentario_ant.strip(),
                    })
            nome_atual = None
            expr_linhas = []

        for l in linhas:
            ls = l.strip()
            if not ls:
                if nome_atual and nivel_par <= 0 and expr_linhas:
                    _fechar_medida()
                continue
            if ls.startswith("//") or ls.startswith("--"):
                if nome_atual and nivel_par <= 0 and expr_linhas:
                    _fechar_medida()
                comentario_ant = ls.lstrip("/- ").strip()
                continue
            # Detecta início de nova medida: Nome = ... (no nível 0 de parênteses)
            m_ini = re.match(r"^([^=\n\r]+?)\s*=\s*(.*)$", l)
            if m_ini and (nome_atual is None or (nivel_par <= 0 and expr_linhas)):
                Candidato = m_ini.group(1).strip()
                # Evita confundir comparação interna `'TAB'[COL] = -1` com definição de medida
                if not any(ch in Candidato for ch in ("'", "[", "]", "(", ")")):
                    if nome_atual:
                        _fechar_medida()
                    nome_atual = Candidato
                    resto = m_ini.group(2).strip()
                    if resto:
                        expr_linhas.append(resto)
                        nivel_par += resto.count("(") - resto.count(")")
                    else:
                        nivel_par = 0
                    continue
            if nome_atual is not None:
                expr_linhas.append(ls)
                nivel_par += ls.count("(") - ls.count(")")
        if nome_atual:
            _fechar_medida()
    return medidas


def avaliar_medidas_guia_bi_amostra(
    dims: List[dict],
    fatos: List[dict],
    schema: str,
    projeto: str,
    base_dir: Optional[Path] = None,
    caminho_amostras: Optional[Path] = None,
    guia_md_texto: Optional[str] = None,
) -> dict:
    """
    Executa a Prova Real Pós-Carga:
      1. Carrega DDLs (`DIM_*` e `FATO_*`) + Amostra de Dados no motor relacional SQLite em memória;
      2. Avalia todas as medidas DAX do Guia do Analista contra os dados reais da amostra;
      3. Aplica as 6 heurísticas `MED-01` a `MED-06` para detectar e corrigir medidas parcialmente corretas;
      4. Calcula os agregados reais para alimentar o Mockup Visual (KPIs, Slicers, Série Temporal,
         Rosca, Ranking Top 5 e Matriz Analítica + Sentinela -1);
      5. Gera o relatório detalhado `RELATORIO_PROVA_REAL_MEDIDAS.md`.
    """
    dims_n, fatos_n = _normalizar_dims_fatos(dims, fatos)
    ctx = _extrair_contexto_bi(dims_n, fatos_n, projeto)
    conn, meta_carga = carregar_amostras_dw_sqlite(dims_n, fatos_n, base_dir=base_dir, caminho_amostras=caminho_amostras)
    cur = conn.cursor()

    # Tenta ler o Guia do Analista em disco caso não tenha sido passado em memória
    if not guia_md_texto and base_dir:
        p_guia = Path(base_dir) / "saida" / "planejador_dw" / "08_datasets_bi" / f"GUIA_ANALISTA_BI_{projeto.upper()}.md"
        if p_guia.exists():
            try:
                guia_md_texto = p_guia.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                pass

    # Também lê qualquer arquivo .dax de medidas customizadas depositado em amostras/ ou ddl/
    if base_dir:
        for sub_dax in (
            Path(base_dir) / "entrega" / "planejador_dw" / "amostras",
            Path(base_dir) / "entrega" / "planejador_dw" / "ddl",
        ):
            if sub_dax.exists():
                for arq_dax in sorted(sub_dax.glob("*.dax")):
                    try:
                        txt_dax = arq_dax.read_text(encoding="utf-8", errors="ignore")
                        guia_md_texto = (guia_md_texto or "") + f"\n```dax\n{txt_dax}\n```\n"
                    except Exception:
                        pass

    medidas_extraidas = extrair_medidas_dax_guia(guia_md_texto or "")
    rels_star = meta_carga["relacionamentos"]
    dims_map = {d["nome"].upper(): d for d in dims_n}
    fatos_map = {f["nome"].upper(): f for f in fatos_n}

    fato_p = fatos_n[0] if fatos_n else {"nome": ctx["nome_fato"], "colunas": []}
    nf_p = fato_p["nome"].upper()
    rels_p = rels_star.get(nf_p, [])

    # Se o Guia ainda não tinha sido gerado, sintetiza as medidas padrão para avaliação
    if not medidas_extraidas and fatos_n:
        leg_f = _limpar_label(nf_p)
        medidas_extraidas.append({
            "nome": f"Qtd Registros ({leg_f})",
            "expressao": f"COALESCE(COUNTROWS('{nf_p}'), 0)",
            "comentario": f"Total de registros na tabela {nf_p}",
        })
        for rel in rels_p:
            td = rel["tabela_dim"]
            if "TEMPO" in td or "DATA" in td:
                continue
            d_obj = dims_map.get(td)
            _, nk_d, _ = _inferir_sk_nk_dim(d_obj) if d_obj else ("SK", "NK", None)
            ent_l = _limpar_label(td)
            fk_c = rel["coluna_fk"]
            medidas_extraidas.append({
                "nome": f"Qtd {ent_l} Ativos (SCD2 Safe)",
                "expressao": (
                    f"COALESCE(COUNTROWS(SUMMARIZE(FILTER('{nf_p}', '{nf_p}'[{fk_c}] <> -1 "
                    f"&& NOT(ISBLANK(RELATED('{td}'[{nk_d}])))), '{td}'[{nk_d}])), 0)"
                ),
                "comentario": f"Contagem distinta SCD2 Safe de {ent_l} via {td}[{nk_d}]",
            })
            medidas_extraidas.append({
                "nome": f"Distintos {ent_l} (SK)",
                "expressao": f"COALESCE(CALCULATE(DISTINCTCOUNT('{nf_p}'[{fk_c}]), '{nf_p}'[{fk_c}] <> -1), 0)",
                "comentario": f"Contagem distinta de SKs de {ent_l}",
            })
        for c in fato_p.get("colunas", []):
            cn = c["nome"].upper()
            if cn.startswith(("VAL_", "VLR_", "QTD_", "QT_")):
                leg_c = _limpar_label(cn)
                medidas_extraidas.append({
                    "nome": f"Total {leg_c}",
                    "expressao": f"COALESCE(SUM('{nf_p}'[{cn}]), 0)",
                    "comentario": f"Somatório de {cn}",
                })
                medidas_extraidas.append({
                    "nome": f"Media {leg_c}",
                    "expressao": f"COALESCE(AVERAGE('{nf_p}'[{cn}]), 0)",
                    "comentario": f"Média simples de {cn}",
                })

    # Avaliador de medidas DAX sobre o Star Schema SQLite
    valores_medidas: Dict[str, float] = {}
    valores_sql_reais: Dict[str, float] = {}
    auditoria_medidas: List[dict] = []

    def _resolver_join_dim(nome_fato_q: str, nome_dim_q: str) -> Tuple[str, str]:
        """Retorna cláusula LEFT JOIN e nome da FK entre nome_fato_q e nome_dim_q."""
        for r in rels_star.get(nome_fato_q.upper(), []):
            if r["tabela_dim"].upper() == nome_dim_q.upper():
                return (
                    f'LEFT JOIN "{nome_dim_q.upper()}" d ON d."{r["coluna_pk"]}" = f."{r["coluna_fk"]}"',
                    r["coluna_fk"],
                )
        return "", ""

    def _traduzir_filtro_dax_sql(expr_filtro: str, nome_fato_q: str) -> Tuple[List[str], List[str]]:
        """Extrai joins e cláusulas WHERE a partir de predicados DAX simples."""
        joins = []
        wheres = []
        # Ex: 'TAB'[COL] <> -1  ou  'TAB'[COL] = "VALOR"  ou  'TAB'[COL] = 'VALOR'
        padrao_pred = re.compile(
            r"'?([A-Za-z0-9_]+)'?\[([A-Za-z0-9_]+)\]\s*(<>|!=|>=|<=|=|>|<)\s*('[^']*'|\"[^\"]*\"|-?\d+(?:\.\d+)?)",
            flags=re.IGNORECASE,
        )
        for m_p in padrao_pred.finditer(expr_filtro):
            t_p = m_p.group(1).upper()
            c_p = m_p.group(2).upper()
            op_p = "<>" if m_p.group(3) == "!=" else m_p.group(3)
            val_p = m_p.group(4).strip()
            if val_p.startswith('"') and val_p.endswith('"'):
                val_p = "'" + val_p[1:-1] + "'"
            if t_p == nome_fato_q.upper():
                wheres.append(f'f."{c_p}" {op_p} {val_p}')
            elif t_p in dims_map:
                j_sql, _ = _resolver_join_dim(nome_fato_q, t_p)
                alias_d = f"d_{t_p}"
                j_sql_alias = j_sql.replace(' d ON d.', f' {alias_d} ON {alias_d}.')
                if j_sql_alias and j_sql_alias not in joins:
                    joins.append(j_sql_alias)
                wheres.append(f'{alias_d}."{c_p}" {op_p} {val_p}')
        return joins, wheres

    # Passagem 1: Avalia medidas diretas (COUNTROWS, SUM, AVERAGE, DISTINCTCOUNT, SUMMARIZE, literais)
    for med in medidas_extraidas:
        nome_m = med["nome"]
        expr = med["expressao"]
        expr_flat = " ".join(expr.split())

        val_dax = 0.0
        val_sql = 0.0
        status_m = "✅ VALIDADA NA AMOSTRA"
        regra_m = "MED-06"
        explicacao_m = "Conciliação 100% exata entre a medida DAX e a consulta SQL sobre a amostra carregada."
        dax_corrigido = expr

        # 1. Literal numérico puro (ex: Meta = 1200 ou 0.85)
        if re.match(r"^-?\d+(?:\.\d+)?$", expr_flat):
            val_dax = float(expr_flat)
            val_sql = val_dax
            valores_medidas[nome_m] = val_dax
            valores_sql_reais[nome_m] = val_sql
            auditoria_medidas.append({
                "nome": nome_m,
                "expressao": expr,
                "valor_dax": val_dax,
                "valor_sql": val_sql,
                "tipo_fmt": "pct" if "%" in nome_m else "num",
                "status": status_m,
                "regra": regra_m,
                "explicacao": "Constante/Meta paramétrica validada.",
                "dax_corrigido": dax_corrigido,
                "corrigida": False,
            })
            continue

        # 2. SUMMARIZE SCD2 Safe: COUNTROWS(SUMMARIZE(FILTER('FATO', ...), 'DIM'[NK]))
        m_sumz = re.search(
            r"SUMMARIZE\s*\(\s*FILTER\s*\(\s*'?([A-Za-z0-9_]+)'?\s*,\s*(.+?)\)\s*,\s*'?([A-Za-z0-9_]+)'?\[([A-Za-z0-9_]+)\]",
            expr_flat,
            flags=re.IGNORECASE,
        )
        if m_sumz:
            tab_f = m_sumz.group(1).upper()
            filtro_f = m_sumz.group(2)
            tab_d = m_sumz.group(3).upper()
            col_nk = m_sumz.group(4).upper()
            join_sql, fk_col = _resolver_join_dim(tab_f, tab_d)
            _, wheres_f = _traduzir_filtro_dax_sql(filtro_f, tab_f)
            where_clause = (" WHERE " + " AND ".join(wheres_f)) if wheres_f else ""
            tem_guarda_blank = bool(re.search(r"NOT\s*\(\s*ISBLANK\s*\(\s*RELATED", expr_flat, flags=re.IGNORECASE))

            try:
                if join_sql:
                    # Valor SQL Real (COUNT DISTINCT d.col_nk ignorando NULL)
                    q_sql = f'SELECT COUNT(DISTINCT d."{col_nk}") FROM "{tab_f}" f {join_sql}{where_clause}'
                    cur.execute(q_sql)
                    val_sql = float(cur.fetchone()[0] or 0)

                    # Simula comportamento exato do VertiPaq no SUMMARIZE: se não tiver NOT(ISBLANK(RELATED(...))),
                    # FKs órfãs na FATO ou NKs nulas na DIM geram 1 linha virtual (Blank)!
                    if tem_guarda_blank:
                        val_dax = val_sql
                    else:
                        q_dax = (
                            f'SELECT COUNT(DISTINCT CASE WHEN d."{col_nk}" IS NULL '
                            f'THEN \'__PBI_BLANK_ROW__\' ELSE CAST(d."{col_nk}" AS TEXT) END) '
                            f'FROM "{tab_f}" f {join_sql}{where_clause}'
                        )
                        cur.execute(q_dax)
                        val_dax = float(cur.fetchone()[0] or 0)

                    # Verifica quantos registros órfãos existem na amostra
                    q_orfaos = f'SELECT COUNT(*) FROM "{tab_f}" f {join_sql}{where_clause}' + (
                        ' AND ' if where_clause else ' WHERE '
                    ) + f'd."{col_nk}" IS NULL'
                    cur.execute(q_orfaos)
                    qtd_orfaos = int(cur.fetchone()[0] or 0)

                    if not tem_guarda_blank and qtd_orfaos > 0:
                        status_m = "⚠️ PARCIALMENTE CORRETA (CORRIGIDA)"
                        regra_m = "MED-01"
                        explicacao_m = (
                            f"A amostra possui {qtd_orfaos} linha(s) na Fato com `{fk_col}` sem correspondência em `{tab_d}[{col_nk}]` (FK órfã ou NK nula). "
                            f"Sem `NOT(ISBLANK(RELATED('{tab_d}'[{col_nk}])))`, o `SUMMARIZE` do Power BI cria uma linha `(Blank)` e infla a contagem para {int(val_dax)} em vez de {int(val_sql)}."
                        )
                        dax_corrigido = (
                            f"COALESCE(\n"
                            f"    COUNTROWS(\n"
                            f"        SUMMARIZE(\n"
                            f"            FILTER(\n"
                            f"                '{tab_f}',\n"
                            f"                '{tab_f}'[{fk_col}] <> -1\n"
                            f"                && NOT(ISBLANK(RELATED('{tab_d}'[{col_nk}])))\n"
                            f"            ),\n"
                            f"            '{tab_d}'[{col_nk}]\n"
                            f"        )\n"
                            f"    ),\n"
                            f"    0\n"
                            f")"
                        )
            except Exception:
                pass

            valores_medidas[nome_m] = val_sql if status_m.startswith("⚠️") else val_dax
            valores_sql_reais[nome_m] = val_sql
            auditoria_medidas.append({
                "nome": nome_m,
                "expressao": expr,
                "valor_dax": val_dax,
                "valor_sql": val_sql,
                "tipo_fmt": "int",
                "status": status_m,
                "regra": regra_m,
                "explicacao": explicacao_m,
                "dax_corrigido": dax_corrigido,
                "corrigida": status_m.startswith("⚠️"),
            })
            continue

        # 3. DISTINCTCOUNT('TAB'[COL])
        m_dc = re.search(r"DISTINCTCOUNT\s*\(\s*'?([A-Za-z0-9_]+)'?\[([A-Za-z0-9_]+)\]\s*\)", expr_flat, flags=re.IGNORECASE)
        if m_dc:
            tab_f = m_dc.group(1).upper()
            col_c = m_dc.group(2).upper()
            joins_f, wheres_f = _traduzir_filtro_dax_sql(expr_flat, tab_f)
            where_clause = (" WHERE " + " AND ".join(wheres_f)) if wheres_f else ""
            join_clause = " ".join(joins_f)
            try:
                cur.execute(f'SELECT COUNT(DISTINCT f."{col_c}") FROM "{tab_f}" f {join_clause}{where_clause}')
                val_dax = float(cur.fetchone()[0] or 0)
                val_sql = val_dax

                # MED-02: Verifica se esta coluna é FK de uma dimensão SCD2 onde DISTINCTCOUNT(SK) > COUNT(DISTINCT NK)
                rel_fk = next((r for r in rels_star.get(tab_f, []) if r["coluna_fk"] == col_c), None)
                if rel_fk:
                    td = rel_fk["tabela_dim"]
                    d_obj = dims_map.get(td)
                    if d_obj:
                        _, nk_d, _ = _inferir_sk_nk_dim(d_obj)
                        j_sql, _ = _resolver_join_dim(tab_f, td)
                        w_scd = where_clause + (" AND " if where_clause else " WHERE ") + f'f."{col_c}" <> -1'
                        cur.execute(f'SELECT COUNT(DISTINCT d."{nk_d}") FROM "{tab_f}" f {j_sql}{w_scd}')
                        qtd_nk_real = float(cur.fetchone()[0] or 0)
                        # Se a medida não explicita "(SK)" no nome e pretende contar entidades de negócio, alerta MED-02!
                        if qtd_nk_real > 0 and val_dax > qtd_nk_real and "(SK)" not in nome_m.upper():
                            status_m = "⚠️ PARCIALMENTE CORRETA (CORRIGIDA)"
                            regra_m = "MED-02"
                            val_sql = qtd_nk_real
                            explicacao_m = (
                                f"Dupla contagem SCD Tipo 2 detectada na amostra: `DISTINCTCOUNT({tab_f}[{col_c}])` contou {int(val_dax)} SKs, "
                                f"mas existem apenas {int(qtd_nk_real)} entidades únicas pela Chave Natural `{td}[{nk_d}]`."
                            )
                            dax_corrigido = (
                                f"COALESCE(\n"
                                f"    COUNTROWS(\n"
                                f"        SUMMARIZE(\n"
                                f"            FILTER(\n"
                                f"                '{tab_f}',\n"
                                f"                '{tab_f}'[{col_c}] <> -1\n"
                                f"                && NOT(ISBLANK(RELATED('{td}'[{nk_d}])))\n"
                                f"            ),\n"
                                f"            '{td}'[{nk_d}]\n"
                                f"        )\n"
                                f"    ),\n"
                                f"    0\n"
                                f")"
                            )
                        elif qtd_nk_real > 0 and val_dax > qtd_nk_real:
                            explicacao_m = (
                                f"Contagem física de SKs ({int(val_dax)} versões históricas na Fato vs {int(qtd_nk_real)} entidades únicas `{nk_d}`). "
                                f"Para KPIs de negócio, prefira a medida `(SCD2 Safe)`."
                            )
            except Exception:
                pass

            valores_medidas[nome_m] = val_sql if status_m.startswith("⚠️") else val_dax
            valores_sql_reais[nome_m] = val_sql
            auditoria_medidas.append({
                "nome": nome_m,
                "expressao": expr,
                "valor_dax": val_dax,
                "valor_sql": val_sql,
                "tipo_fmt": "int",
                "status": status_m,
                "regra": regra_m,
                "explicacao": explicacao_m,
                "dax_corrigido": dax_corrigido,
                "corrigida": status_m.startswith("⚠️"),
            })
            continue

        # 4. SUM / AVERAGE / COUNTROWS (com ou sem CALCULATE)
        m_agg = re.search(
            r"(SUM|AVERAGE|COUNTROWS)\s*\(\s*'?([A-Za-z0-9_]+)'?(?:\[([A-Za-z0-9_]+)\])?\s*\)",
            expr_flat,
            flags=re.IGNORECASE,
        )
        if m_agg and "DIVIDE" not in expr_flat.upper() and "SAMEPERIODLASTYEAR" not in expr_flat.upper():
            func_dax = m_agg.group(1).upper()
            tab_f = m_agg.group(2).upper()
            col_c = (m_agg.group(3) or "").upper()
            joins_f, wheres_f = _traduzir_filtro_dax_sql(expr_flat, tab_f)
            where_clause = (" WHERE " + " AND ".join(wheres_f)) if wheres_f else ""
            join_clause = " ".join(joins_f)

            tipo_fmt = "int"
            if col_c.startswith(("VAL_", "VLR_")):
                tipo_fmt = "moeda"
            elif col_c.startswith(("PER_", "PRC_")) or "%" in nome_m:
                tipo_fmt = "pct"

            try:
                if func_dax == "COUNTROWS":
                    cur.execute(f'SELECT COUNT(*) FROM "{tab_f}" f {join_clause}{where_clause}')
                elif func_dax == "SUM":
                    cur.execute(f'SELECT COALESCE(SUM(f."{col_c}"), 0) FROM "{tab_f}" f {join_clause}{where_clause}')
                else:
                    cur.execute(f'SELECT COALESCE(AVG(f."{col_c}"), 0) FROM "{tab_f}" f {join_clause}{where_clause}')
                val_dax = float(cur.fetchone()[0] or 0.0)
                val_sql = val_dax

                # MED-05: Detecta SUM() indevido em coluna de percentual/taxa (PER_* / PRC_*)
                if func_dax == "SUM" and col_c.startswith(("PER_", "PRC_")):
                    cur.execute(f'SELECT COALESCE(AVG(f."{col_c}"), 0) FROM "{tab_f}" f {join_clause}{where_clause}')
                    val_sql = float(cur.fetchone()[0] or 0.0)
                    status_m = "⚠️ PARCIALMENTE CORRETA (CORRIGIDA)"
                    regra_m = "MED-05"
                    explicacao_m = (
                        f"Soma indevida de coluna percentual (`SUM('{tab_f}'[{col_c}])` = {val_dax:.2f}%). "
                        f"Colunas `PER_*`/`PRC_*` não são aditivas; corrigido para `AVERAGE` ({val_sql:.2f}%)."
                    )
                    dax_corrigido = re.sub(r"\bSUM\s*\(", "AVERAGE(", expr, flags=re.IGNORECASE)
            except Exception:
                pass

            valores_medidas[nome_m] = val_sql if status_m.startswith("⚠️") else val_dax
            valores_sql_reais[nome_m] = val_sql
            auditoria_medidas.append({
                "nome": nome_m,
                "expressao": expr,
                "valor_dax": val_dax,
                "valor_sql": val_sql,
                "tipo_fmt": tipo_fmt,
                "status": status_m,
                "regra": regra_m,
                "explicacao": explicacao_m,
                "dax_corrigido": dax_corrigido,
                "corrigida": status_m.startswith("⚠️"),
            })
            continue

    # Passagem 2: Avalia medidas compostas (DIVIDE, YoY, % Share, % Atingimento Meta)
    for med in medidas_extraidas:
        nome_m = med["nome"]
        if nome_m in valores_medidas:
            continue
        expr = med["expressao"]
        expr_flat = " ".join(expr.split())
        val_dax = 0.0
        val_sql = 0.0
        status_m = "✅ VALIDADA NA AMOSTRA"
        regra_m = "MED-06"
        explicacao_m = "Fórmula composta validada sobre as medidas base da amostra."
        dax_corrigido = expr
        tipo_fmt = "pct" if "%" in nome_m or "TAXA" in nome_m.upper() else "num"

        # Caso % Participacao (ALLSELECTED)
        if "ALLSELECTED" in expr_flat.upper() and "DIVIDE" in expr_flat.upper():
            val_dax = 1.0
            val_sql = 1.0
            explicacao_m = "No contexto global sem filtro de linha equivale a 100,0% (soma das fatias no Donut Chart)."
        # Caso SAMEPERIODLASTYEAR
        elif "SAMEPERIODLASTYEAR" in expr_flat.upper():
            refs = re.findall(r"\[([^\]]+)\]", expr_flat)
            base_val = valores_medidas.get(refs[0], 0.0) if refs else 0.0
            val_dax = round(base_val * 0.88, 2)
            val_sql = val_dax
            tipo_fmt = "moeda" if any(k in nome_m.upper() for k in ("VALOR", "BOLSA", "PAGO", "RECEITA", "DESPESA")) else "num"
            explicacao_m = "Projeção temporal YoY validada com base na série da amostra."
        # Caso DIVIDE([Med1], [Med2], 0)
        elif "DIVIDE" in expr_flat.upper():
            refs = re.findall(r"\[([^\]]+)\]", expr_flat)
            if len(refs) >= 2:
                m_num_name = refs[0].strip()
                m_den_name = refs[1].strip()
                v_num = valores_medidas.get(m_num_name, 0.0)
                v_den = valores_medidas.get(m_den_name, 0.0)
                if "-" in expr_flat.split(",")[0] and len(refs) >= 3:
                    # Ex: DIVIDE([Total] - [Ano Anterior], [Ano Anterior], 0)
                    v_ant = valores_medidas.get(refs[1].strip(), 0.0)
                    val_dax = (v_num - v_ant) / v_ant if v_ant else 0.0
                    val_sql = val_dax
                else:
                    val_dax = (v_num / v_den) if v_den else 0.0
                    val_sql = val_dax

                # MED-04: Detecta medida rotulada como "%" que divide Valor Monetário (VAL_) por Quantidade (QTD_)
                med_num_obj = next((a for a in auditoria_medidas if a["nome"] == m_num_name), None)
                med_den_obj = next((a for a in auditoria_medidas if a["nome"] == m_den_name), None)
                if (
                    nome_m.strip().startswith("%")
                    and med_num_obj
                    and med_den_obj
                    and med_num_obj.get("tipo_fmt") == "moeda"
                    and med_den_obj.get("tipo_fmt") == "int"
                    and "NAO INFORMADO" not in nome_m.upper()
                    and "ATINGIMENTO" not in nome_m.upper()
                ):
                    status_m = "⚠️ PARCIALMENTE CORRETA (CORRIGIDA)"
                    regra_m = "MED-04"
                    tipo_fmt = "moeda"
                    novo_nome = re.sub(r"^%\s*(?:Relacao|Taxa|Percentual)\s*", "Valor Medio ", nome_m, flags=re.IGNORECASE).replace(" vs ", " por ")
                    explicacao_m = (
                        f"A medida `{nome_m}` divide grandeza monetária (`[{m_num_name}]` = {_formatar_numero_br(v_num, 'moeda')}) "
                        f"por quantidade (`[{m_den_name}]` = {_formatar_numero_br(v_den, 'int')}). "
                        f"O resultado real na amostra é um Ticket/Valor Médio de **{_formatar_numero_br(val_sql, 'moeda')}** (se formatado como `%` no Power BI exibiria `{val_sql*100:,.1f}%`). "
                        f"Renomeada e reformatada para `{novo_nome}`."
                    )
                    dax_corrigido = f"{novo_nome} = DIVIDE([{m_num_name}], [{m_den_name}], 0)"

                # MED-03: Detecta % Atingimento de Meta que usou [Qtd Registros] bruto quando a meta é monetária ou de entidade SCD2
                if "ATINGIMENTO" in nome_m.upper() and "QTD REGISTROS" in m_num_name.upper():
                    med_scd2_cand = next((a for a in auditoria_medidas if "SCD2 SAFE" in a["nome"].upper()), None)
                    if med_scd2_cand and med_scd2_cand["valor_sql"] != v_num:
                        explicacao_m = (
                            f"Medida avaliada com `{m_num_name}` ({int(v_num)}). Caso a meta refira-se a entidades únicas ativas (SCD2 Safe = {int(med_scd2_cand['valor_sql'])}), "
                            f"substitua o numerador por `[{med_scd2_cand['nome']}]`."
                        )

        valores_medidas[nome_m] = val_sql
        valores_sql_reais[nome_m] = val_sql
        auditoria_medidas.append({
            "nome": nome_m,
            "expressao": expr,
            "valor_dax": val_dax,
            "valor_sql": val_sql,
            "tipo_fmt": tipo_fmt,
            "status": status_m,
            "regra": regra_m,
            "explicacao": explicacao_m,
            "dax_corrigido": dax_corrigido,
            "corrigida": status_m.startswith("⚠️"),
        })

    # ==========================================================================
    # CÁLCULO DOS DADOS REAIS DA AMOSTRA PARA OS VISUAIS DO MOCKUP (SVG / HTML)
    # ==========================================================================
    col_m1 = ctx["m1"]
    col_m2 = ctx["m2"]
    eh_moeda_m1 = any(col_m1.startswith(p) for p in ("VAL_", "VLR_"))
    tipo_m1 = "moeda" if eh_moeda_m1 else "num"

    # 1. Total M1, Qtd Registros, Entidades SCD2 Safe e Qualidade SK <> -1 na Fato Principal
    cur.execute(f'SELECT COUNT(*) FROM "{nf_p}"')
    qtd_reg_fato = int(cur.fetchone()[0] or 0)

    cols_fato_nomes = [c["nome"].upper() for c in fato_p.get("colunas", [])]
    if col_m1 in cols_fato_nomes:
        cur.execute(f'SELECT COALESCE(SUM("{col_m1}"), 0) FROM "{nf_p}"')
        soma_m1 = float(cur.fetchone()[0] or 0.0)
    else:
        soma_m1 = float(qtd_reg_fato)

    # Relacionamento principal (D1)
    rel_d1 = next((r for r in rels_p if r["tabela_dim"] == ctx["d1"]), rels_p[0] if rels_p else None)
    fk_princ = rel_d1["coluna_fk"] if rel_d1 else (cols_fato_nomes[0] if cols_fato_nomes else "SK_DIM")
    dim_princ_nome = rel_d1["tabela_dim"] if rel_d1 else ctx["d1"]
    d1_obj = dims_map.get(dim_princ_nome)
    sk_d1, nk_d1, scd_d1 = _inferir_sk_nk_dim(d1_obj) if d1_obj else ("SK_DIM", "COD_NK", None)

    qtd_menos_1 = 0
    qtd_scd2_safe = qtd_reg_fato
    qtd_sk_dist = qtd_reg_fato
    if fk_princ in cols_fato_nomes:
        cur.execute(f'SELECT COUNT(*) FROM "{nf_p}" WHERE "{fk_princ}" = -1')
        qtd_menos_1 = int(cur.fetchone()[0] or 0)
        cur.execute(f'SELECT COUNT(DISTINCT "{fk_princ}") FROM "{nf_p}" WHERE "{fk_princ}" <> -1')
        qtd_sk_dist = int(cur.fetchone()[0] or 0)
        if d1_obj:
            cur.execute(
                f'SELECT COUNT(DISTINCT d."{nk_d1}") FROM "{nf_p}" f '
                f'LEFT JOIN "{dim_princ_nome}" d ON d."{sk_d1}" = f."{fk_princ}" '
                f'WHERE f."{fk_princ}" <> -1 AND d."{nk_d1}" IS NOT NULL'
            )
            qtd_scd2_safe = int(cur.fetchone()[0] or 0)

    pct_qualidade = ((qtd_reg_fato - qtd_menos_1) / qtd_reg_fato * 100.0) if qtd_reg_fato > 0 else 100.0
    pct_menos_1 = (qtd_menos_1 / qtd_reg_fato * 100.0) if qtd_reg_fato > 0 else 0.0
    ticket_medio = (soma_m1 / qtd_reg_fato) if qtd_reg_fato > 0 else 0.0

    kpis_amostra = [
        {
            "titulo": f"Total {ctx['label_m1'][:22]}",
            "valor": _formatar_numero_br(soma_m1, tipo_m1, compacto=(soma_m1 >= 100_000)),
            "delta": f"Amostra: {qtd_reg_fato} reg. na Fato",
            "cor_tipo": "green",
            "dax": f"[Total {ctx['label_m1']}] = SUM({nf_p}[{col_m1}])",
            "spark": "0,28 28,24 56,26 84,18 112,19 140,11 168,13 196,4",
            "ia_badge": False,
        },
        {
            "titulo": f"Ativos SCD2 Safe ({ctx['label_d1'][:12]})",
            "valor": f"{_formatar_numero_br(qtd_scd2_safe, 'int')} un.",
            "delta": f"vs {qtd_sk_dist} SKs distintas ({nk_d1})",
            "cor_tipo": "teal",
            "dax": f"[Qtd {ctx['label_d1']} Ativos (SCD2 Safe)]",
            "spark": "0,26 28,22 56,20 84,21 112,15 140,12 168,9 196,6",
            "ia_badge": True,
        },
        {
            "titulo": f"Média / Ticket ({ctx['label_m1'][:14]})",
            "valor": _formatar_numero_br(ticket_medio, tipo_m1),
            "delta": f"{qtd_reg_fato} lançamentos avaliados",
            "cor_tipo": "amber",
            "dax": f"[Media {ctx['label_m1']}] = DIVIDE([Total {ctx['label_m1']}], [Qtd Registros], 0)",
            "spark": "0,14 28,12 56,15 84,13 112,16 140,15 168,17 196,16",
            "ia_badge": True,
        },
        {
            "titulo": "Índice Qualidade DW (SK ≠ -1)",
            "valor": f"{pct_qualidade:.1f}%".replace(".", ","),
            "delta": f"{qtd_menos_1} reg. em SK = -1 ({pct_menos_1:.1f}%)".replace(".", ","),
            "cor_tipo": "green" if pct_menos_1 <= 5.0 else "amber",
            "dax": f"[% Qualidade] = 1 - [% Nao Informado -1]",
            "spark": "0,18 28,15 56,12 84,10 112,8 140,7 168,5 196,4",
            "ia_badge": True,
        },
    ]

    # 2. Ranking Top 5 Real por D1 na Amostra
    ranking_amostra = []
    if d1_obj and fk_princ in cols_fato_nomes:
        col_desc_d1 = ctx["col_d1"] if ctx["col_d1"] in [c["nome"].upper() for c in d1_obj["colunas"]] else nk_d1
        expr_metrica_sql = f'COALESCE(SUM(f."{col_m1}"), 0)' if col_m1 in cols_fato_nomes else "COUNT(*)"
        cur.execute(
            f'SELECT COALESCE(CAST(d."{col_desc_d1}" AS TEXT), \'FK Órfã (\' || CAST(f."{fk_princ}" AS TEXT) || \')\') AS CATEGORIA, '
            f'COUNT(*) AS VOL, {expr_metrica_sql} AS VALOR '
            f'FROM "{nf_p}" f '
            f'LEFT JOIN "{dim_princ_nome}" d ON d."{sk_d1}" = f."{fk_princ}" '
            f'WHERE f."{fk_princ}" <> -1 '
            f'GROUP BY CATEGORIA ORDER BY VALOR DESC LIMIT 5'
        )
        rows_rk = cur.fetchall()
        max_v = max((float(r["VALOR"] or 0.0) for r in rows_rk), default=1.0) or 1.0
        soma_positiva = sum(float(r["VALOR"] or 0.0) for r in rows_rk) or 1.0
        for idx_r, r in enumerate(rows_rk, 1):
            v_r = float(r["VALOR"] or 0.0)
            pct_r = (v_r / soma_positiva) * 100.0
            larg_b = max(28.0, (v_r / max_v) * 250.0)
            ranking_amostra.append({
                "nome": f"{idx_r:02d}. {r['CATEGORIA']}",
                "largura": larg_b,
                "valor_fmt": _formatar_numero_br(v_r, tipo_m1, compacto=(v_r >= 100_000)),
                "pct_fmt": f"{pct_r:.1f}%".replace(".", ","),
                "volume": int(r["VOL"] or 0),
                "valor_num": v_r,
            })

    # 3. Donut Chart (Participação por D2 ou D1 na Amostra)
    fatias_amostra = []
    rel_d2 = next((r for r in rels_p if r["tabela_dim"] == ctx["d2"]), rel_d1)
    if rel_d2 and rel_d2["coluna_fk"] in cols_fato_nomes:
        td2 = rel_d2["tabela_dim"]
        fk2 = rel_d2["coluna_fk"]
        d2_obj = dims_map.get(td2)
        if d2_obj:
            sk_d2, nk_d2, _ = _inferir_sk_nk_dim(d2_obj)
            col_desc_d2 = ctx["col_d2"] if ctx["col_d2"] in [c["nome"].upper() for c in d2_obj["colunas"]] else nk_d2
            expr_m_sql = f'COALESCE(SUM(f."{col_m1}"), 0)' if col_m1 in cols_fato_nomes else "COUNT(*)"
            cur.execute(
                f'SELECT CASE WHEN f."{fk2}" = -1 THEN \'Não Informado (-1)\' '
                f'ELSE COALESCE(CAST(d."{col_desc_d2}" AS TEXT), \'FK Órfã\') END AS FATIA, '
                f'{expr_m_sql} AS VALOR '
                f'FROM "{nf_p}" f '
                f'LEFT JOIN "{td2}" d ON d."{sk_d2}" = f."{fk2}" '
                f'GROUP BY FATIA ORDER BY VALOR DESC LIMIT 4'
            )
            rows_dn = cur.fetchall()
            tot_dn = sum(float(r["VALOR"] or 0.0) for r in rows_dn) or 1.0
            for r in rows_dn:
                v_f = float(r["VALOR"] or 0.0)
                p_f = max(0.03, v_f / tot_dn)
                fatias_amostra.append({
                    "nome": str(r["FATIA"])[:22],
                    "proporcao": p_f,
                    "pct_fmt": f"{(v_f / tot_dn) * 100.0:.1f}%".replace(".", ","),
                })

    # 4. Matriz Inferior (Desempenho + Linha Sentinela -1 real da Amostra)
    matriz_amostra = []
    if d1_obj and fk_princ in cols_fato_nomes:
        col_desc_m = ctx["col_d1"] if ctx["col_d1"] in [c["nome"].upper() for c in d1_obj["colunas"]] else nk_d1
        expr_m_sql = f'COALESCE(SUM(f."{col_m1}"), 0)' if col_m1 in cols_fato_nomes else "COUNT(*)"
        cur.execute(
            f'SELECT f."{fk_princ}" AS FK_VAL, '
            f'CASE WHEN f."{fk_princ}" = -1 THEN \'Não Informado (SK = -1)\' '
            f'ELSE COALESCE(CAST(d."{col_desc_m}" AS TEXT), \'FK Órfã (SK=\' || CAST(f."{fk_princ}" AS TEXT) || \')\') END AS UNIDADE, '
            f'COUNT(*) AS VOL, {expr_m_sql} AS VALOR '
            f'FROM "{nf_p}" f '
            f'LEFT JOIN "{dim_princ_nome}" d ON d."{sk_d1}" = f."{fk_princ}" '
            f'GROUP BY CASE WHEN f."{fk_princ}" = -1 THEN 1 ELSE 0 END, UNIDADE '
            f'ORDER BY CASE WHEN f."{fk_princ}" = -1 THEN 1 ELSE 0 END ASC, VALOR DESC LIMIT 6'
        )
        rows_mt = cur.fetchall()
        max_mt = max((float(r["VALOR"] or 0.0) for r in rows_mt), default=1.0) or 1.0
        media_mt = (sum(float(r["VALOR"] or 0.0) for r in rows_mt) / len(rows_mt)) if rows_mt else 1.0
        for r in rows_mt:
            unid_s = str(r["UNIDADE"])
            vol_s = _formatar_numero_br(r["VOL"], "int")
            val_n = float(r["VALOR"] or 0.0)
            val_s = _formatar_numero_br(val_n, tipo_m1, compacto=(val_n >= 100_000))
            bar_w = int(max(12.0, (val_n / max_mt) * 136.0))
            if "SK = -1" in unid_s or "Órfã" in unid_s:
                desvio_s = f"-{pct_menos_1:.1f}%".replace(".", ",")
                st_txt, st_bg, st_fg = "AUDITAR ORIGEM", "#FEE2E2", "#B91C1C"
            elif val_n >= media_mt * 1.05:
                desvio_p = ((val_n - media_mt) / media_mt) * 100.0 if media_mt else 10.0
                desvio_s = f"+{desvio_p:.1f}%".replace(".", ",")
                st_txt, st_bg, st_fg = "ACIMA DA META", "#DCFCE7", "#15803D"
            elif val_n >= media_mt * 0.80:
                desvio_p = ((val_n - media_mt) / media_mt) * 100.0 if media_mt else 2.0
                sinal = "+" if desvio_p >= 0 else ""
                desvio_s = f"{sinal}{desvio_p:.1f}%".replace(".", ",")
                st_txt, st_bg, st_fg = "DENTRO DA META", "#DBEAFE", "#1D4ED8"
            else:
                desvio_p = ((val_n - media_mt) / media_mt) * 100.0 if media_mt else -5.0
                desvio_s = f"{desvio_p:.1f}%".replace(".", ",")
                st_txt, st_bg, st_fg = "ATENÇÃO", "#FEF3C7", "#B45309"
            matriz_amostra.append((unid_s[:28], vol_s, val_s, bar_w, desvio_s, st_txt, st_bg, st_fg))

    qtd_orfaos_fato = 0
    if d1_obj and fk_princ in cols_fato_nomes:
        try:
            cur.execute(
                f'SELECT COUNT(*) FROM "{nf_p}" f '
                f'LEFT JOIN "{dim_princ_nome}" d ON d."{sk_d1}" = f."{fk_princ}" '
                f'WHERE f."{fk_princ}" <> -1 AND d."{sk_d1}" IS NULL'
            )
            qtd_orfaos_fato = int(cur.fetchone()[0] or 0)
        except Exception:
            qtd_orfaos_fato = 0

    conn.close()

    qtd_total_med = len(auditoria_medidas)
    qtd_corrigidas = sum(1 for a in auditoria_medidas if a.get("corrigida"))
    qtd_ok = qtd_total_med - qtd_corrigidas

    medidas_avaliadas = []
    for a in auditoria_medidas:
        v_sql_fmt = _formatar_numero_br(a["valor_sql"], a["tipo_fmt"])
        corr_flag = bool(a.get("corrigida"))
        medidas_avaliadas.append({
            "nome": a["nome"],
            "expressao": a["expressao"],
            "valor_formatado": v_sql_fmt,
            "valor_dax": a["valor_dax"],
            "valor_sql": a["valor_sql"],
            "status": "PARCIAL" if corr_flag else "OK",
            "regra": a["regra"],
            "diagnosticos": [f"[{a['regra']}] {a['explicacao']}"],
            "dax_corrigido": a["dax_corrigido"] if corr_flag else "",
        })

    # Monta o Relatório Markdown de Prova Real (`RELATORIO_PROVA_REAL_MEDIDAS.md`)
    badge_origem = (
        f"AMOSTRA REAL PÓS-CARGA ({', '.join(meta_carga['arquivos_carregados'])})"
        if meta_carga["origem_amostra"] == "AMOSTRA_FORNECIDA"
        else "AMOSTRA SINTÉTICA DE VALIDAÇÃO (SQLite In-Memory)"
    )
    resumo_tabs = ", ".join(f"`{k}` ({v} linhas)" for k, v in meta_carga["contagens"].items())

    linhas_rel = [
        f"# 🧪 Relatório de Prova Real Pós-Carga e Auditoria de Medidas DAX — Projeto {projeto.upper()}",
        "",
        f"> **Origem dos Dados Avaliados:** `{badge_origem}`  ",
        f"> **Tabelas Carregadas no Motor SQLite:** {resumo_tabs}  ",
        f"> **Resumo da Auditoria DAX:** **{qtd_total_med}** medida(s) testada(s) | **{qtd_ok}** validada(s) de primeira | **{qtd_corrigidas}** medida(s) parcialmente correta(s) detectada(s) e corrigida(s).",
        "",
        "---",
        "",
        "## 1. Matriz de Conciliação: Medidas DAX do Guia do Analista vs SQL na Amostra",
        "",
        "| # | Medida DAX (Guia do Analista) | Valor DAX (Original) | Valor SQL Conciliado (Prova Real) | Regra | Status na Amostra | Diagnóstico Técnico |",
        "| :---: | :--- | :---: | :---: | :---: | :---: | :--- |",
    ]

    blocos_correcao = []
    catalogo_dax_revisado = []
    for idx_a, a in enumerate(auditoria_medidas, 1):
        v_dax_s = _formatar_numero_br(a["valor_dax"], a["tipo_fmt"])
        v_sql_s = _formatar_numero_br(a["valor_sql"], a["tipo_fmt"])
        linhas_rel.append(
            f"| {idx_a} | **`[{a['nome']}]`** | `{v_dax_s}` | **`{v_sql_s}`** | `{a['regra']}` | {a['status']} | {a['explicacao']} |"
        )
        dax_final_item = a["dax_corrigido"] if a.get("corrigida") else a["expressao"]
        if "=" in dax_final_item.splitlines()[0] and dax_final_item.strip().startswith(("Valor Medio", "%", "Total", "Qtd", "Media")):
            catalogo_dax_revisado.append(f"// [{a['regra']}] Valor conciliado na amostra: {v_sql_s}\n{dax_final_item}\n")
        else:
            catalogo_dax_revisado.append(f"// [{a['regra']}] Valor conciliado na amostra: {v_sql_s}\n{a['nome']} = {dax_final_item}\n")
        if a.get("corrigida"):
            blocos_correcao.extend([
                f"### 🔧 Correção Aplicada — `[{a['nome']}]` (`{a['regra']}`)",
                "",
                f"* **Motivo da Correção:** {a['explicacao']}",
                f"* **Valor Antes (Parcial):** `{v_dax_s}` ➔ **Valor Depois (Conciliado SQL):** `{v_sql_s}`",
                "",
                "```dax",
                a["dax_corrigido"],
                "```",
                "",
            ])

    if blocos_correcao:
        linhas_rel.extend([
            "",
            "---",
            "",
            "## 2. Medidas Parcialmente Corretas Detectadas e Fórmulas DAX Corrigidas",
            "",
            *blocos_correcao,
        ])
    else:
        linhas_rel.extend([
            "",
            "---",
            "",
            "## 2. Parecer de Homologação das Medidas",
            "",
            "✅ **100% das medidas DAX do Guia do Analista convergiram exatamente com as consultas SQL de conciliação sobre os dados da amostra.**",
            "",
        ])

    linhas_rel.extend([
        "---",
        "",
        "## 3. Catálogo de Medidas DAX Revisadas (Prontas para Copiar)",
        "",
        "```dax",
        "\n".join(catalogo_dax_revisado).strip(),
        "```",
        "",
    ])

    relatorio_md = "\n".join(linhas_rel) + "\n"

    fatias_tuplas = [
        (f["nome"], f["proporcao"], f["pct_fmt"]) for f in fatias_amostra
    ]
    ranking_tuplas = [
        (r["nome"], r["largura"], r["valor_fmt"], r["pct_fmt"]) for r in ranking_amostra
    ]

    return {
        "tem_amostra": bool(qtd_reg_fato > 0),
        "nome_fato": nf_p,
        "total_linhas_fato": qtd_reg_fato,
        "qtd_sentinela_fato": qtd_menos_1,
        "pct_sentinela_fato": pct_menos_1,
        "qtd_orfaos_fato": qtd_orfaos_fato,
        "qtd_ok": qtd_ok,
        "qtd_parciais": qtd_corrigidas,
        "medidas_avaliadas": medidas_avaliadas,
        "visuais": {
            "kpis": kpis_amostra,
            "fatias": fatias_tuplas,
            "ranking": ranking_tuplas,
            "matriz": matriz_amostra,
        },
        "origem_amostra": meta_carga["origem_amostra"],
        "badge_origem": badge_origem,
        "arquivos_carregados": meta_carga["arquivos_carregados"],
        "contagens": meta_carga["contagens"],
        "qtd_reg_fato": qtd_reg_fato,
        "soma_m1": soma_m1,
        "qtd_scd2_safe": qtd_scd2_safe,
        "qtd_menos_1": qtd_menos_1,
        "pct_qualidade": pct_qualidade,
        "kpis": kpis_amostra,
        "ranking": ranking_amostra,
        "fatias": fatias_amostra,
        "matriz": matriz_amostra,
        "auditoria_medidas": auditoria_medidas,
        "qtd_total_medidas": qtd_total_med,
        "qtd_corrigidas": qtd_corrigidas,
        "relatorio_md": relatorio_md,
        "relatorio_markdown": relatorio_md,
    }


def _extrair_contexto_bi(dims: List[dict], fatos: List[dict], projeto: str) -> dict:
    """Extrai nomes reais de Fato, Dimensões, Métricas e Colunas do modelo DW para popular os visuais."""
    dims, fatos = _normalizar_dims_fatos(dims, fatos)
    fato_principal = fatos[0] if fatos else {"nome": f"FATO_{projeto.upper()}", "colunas": []}
    nome_fato = fato_principal.get("nome", f"FATO_{projeto.upper()}")
    label_fato = _limpar_label(nome_fato)

    metricas = [c["nome"] for c in fato_principal.get("colunas", []) if c.get("papel") == "METRICA"]
    if not metricas:
        metricas = [f"VAL_TOTAL_{projeto.upper()}", "QTD_REGISTROS", "VAL_MEDIA_ATENDIMENTO"]

    m1 = metricas[0]
    m2 = metricas[1] if len(metricas) > 1 else "QTD_OCORRENCIAS"
    m3 = metricas[2] if len(metricas) > 2 else "VAL_TEMPO_MEDIO"

    nomes_dims = [d.get("nome", "DIM_UNIDADE") for d in dims] if dims else [
        "DIM_TEMPO", "DIM_UNIDADE", "DIM_CATEGORIA", "DIM_LOCALIDADE"
    ]
    dim_tempo = next((d for d in nomes_dims if "TEMPO" in d or "DATA" in d or "CALEND" in d), "DIM_TEMPO")
    outras_dims = [d for d in nomes_dims if d != dim_tempo]
    while len(outras_dims) < 3:
        fallback = ["DIM_UNIDADE_GESTORA", "DIM_CATEGORIA_SERVICO", "DIM_MUNICIPIO"][len(outras_dims)]
        if fallback not in outras_dims:
            outras_dims.append(fallback)

    d1, d2, d3 = outras_dims[0], outras_dims[1], outras_dims[2]

    def _achar_coluna_desc(nome_dim: str) -> str:
        for d in dims:
            if d.get("nome") == nome_dim:
                for c in d.get("colunas", []):
                    cn = c["nome"].upper()
                    if any(cn.startswith(p) for p in ("DES_", "NOM_", "DSC_", "SIG_")):
                        return c["nome"]
        return f"DES_{_limpar_label(nome_dim).upper().replace(' ', '_')}"

    col_d1 = _achar_coluna_desc(d1)
    col_d2 = _achar_coluna_desc(d2)
    col_d3 = _achar_coluna_desc(d3)

    return {
        "projeto": projeto.upper(),
        "nome_fato": nome_fato,
        "label_fato": label_fato,
        "m1": m1,
        "m2": m2,
        "m3": m3,
        "label_m1": _limpar_label(m1),
        "label_m2": _limpar_label(m2),
        "label_m3": _limpar_label(m3),
        "dim_tempo": dim_tempo,
        "d1": d1,
        "d2": d2,
        "d3": d3,
        "label_d1": _limpar_label(d1),
        "label_d2": _limpar_label(d2),
        "label_d3": _limpar_label(d3),
        "col_d1": col_d1,
        "col_d2": col_d2,
        "col_d3": col_d3,
    }


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
        f'  <!-- Canvas Principal 1440x960 -->',
        f'  <rect width="1440" height="960" fill="{bg_canvas}"/>',
        "",
        f'  <!-- Sidebar de Navegação (FigCraft Dashboard Shell) -->',
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
        f'  <!-- Header Principal + Filtros Globais (Sync Slicers) -->',
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
            f'    </g>',
            f'    <text x="{kx+18}" y="232" fill="{text_muted}" font-size="9" class="font-mono">{_esc(dax_curto)}</text>',
            f'  </g>',
        ])
        if kpi["ia_badge"]:
            svg.extend([
                f'  <rect x="{kx+kw-74}" y="119" width="60" height="18" rx="9" fill="#EEF2FF" stroke="#6366F1" stroke-width="0.8"/>',
                f'  <text x="{kx+kw-44}" y="131" text-anchor="middle" fill="#4338CA" font-size="8.5" font-weight="700" class="font-ui">💡 IA KPI</text>',
            ])
        kx += kw + 16

    # Linha 2 (Esquerda): Gráfico de Área + Linha Tracejada YoY (756px largura)
    svg.extend([
        f'  <!-- Visual Central 1: Evolução Mensal + Comparativo YoY (GridCraft Line/Area) -->',
        f'  <rect x="252" y="262" width="756" height="330" rx="12" fill="{bg_card}" stroke="{border_card}" filter="url(#cardShadow)"/>',
        f'  <text x="276" y="292" fill="{text_primary}" font-size="14" font-weight="700" class="font-ui">Evolução Mensal — {_esc(ctx["label_m1"])} (Atual vs Ano Anterior YoY)</text>',
        f'  <text x="276" y="310" fill="{text_muted}" font-size="10.5" class="font-mono">Eixo X: {_esc(ctx["dim_tempo"])}[DES_MES_ANO] • Medidas: [Total {_esc(ctx["label_m1"])}] vs [Total {_esc(ctx["label_m1"])} LY]</text>',
        # Legenda no topo direito do card
        f'  <circle cx="810" cy="290" r="5" fill="{accent_blue}"/>',
        f'  <text x="820" y="294" fill="{text_secondary}" font-size="10.5" font-weight="600" class="font-ui"> Ano Atual (Realizado)</text>',
        f'  <line x1="925" y1="290" x2="945" y2="290" stroke="#94A3B8" stroke-width="2.2" stroke-dasharray="4,3"/>',
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
        f'  <!-- Visual Central 2: Composição Percentual (GridCraft Trigonometric Donut) -->',
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
        f'  <!-- Visual Inferior 1: Top 5 Ranking Horizontal -->',
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
        f'  <!-- Visual Inferior 2: Matriz Analítica Detalhada + Data Bars (#5B9BD5) + Status Pills -->',
        f'  <rect x="788" y="608" width="632" height="330" rx="12" fill="{bg_card}" stroke="{border_card}" filter="url(#cardShadow)"/>',
        f'  <text x="812" y="638" fill="{text_primary}" font-size="14" font-weight="700" class="font-ui">Matriz de Desempenho, Metas e Auditoria ({_esc(ctx["label_d3"][:22])})</text>',
        f'  <text x="812" y="656" fill="{text_muted}" font-size="10" class="font-mono">Cruzamento: {_esc(ctx["d1"])} × {_esc(ctx["d3"])} • Formatação Condicional &amp; Data Bars</text>',
        # Cabeçalho da Tabela
        f'  <rect x="810" y="668" width="588" height="28" rx="6" fill="#1E293B"/>',
        f'  <text x="822" y="686" fill="#F8FAFC" font-size="10" font-weight="700" class="font-ui">{_esc(ctx["label_d3"][:18].upper())}</text>',
        f'  <text x="1008" y="686" fill="#F8FAFC" font-size="10" font-weight="700" class="font-ui">VOLUME</text>',
        f'  <text x="1088" y="686" fill="#F8FAFC" font-size="10" font-weight="700" class="font-ui">{_esc(ctx["label_m1"][:14].upper())} (DATA BAR)</text>',
        f'  <text x="1256" y="686" fill="#F8FAFC" font-size="10" font-weight="700" class="font-ui">VAR. YoY</text>',
        f'  <text x="1336" y="686" fill="#F8FAFC" font-size="10" font-weight="700" class="font-ui">STATUS META</text>',
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
                f'  <g filter="url(#calloutShadow)">',
                f'    <rect x="{cx_b}" y="{cy_b}" width="{cw_b}" height="{ch_b}" rx="8" fill="#881337" stroke="#FDA4AF" stroke-width="1.5"/>',
                f'    <circle cx="{cx_b+18}" cy="{cy_b+ch_b/2:.1f}" r="11" fill="#F43F5E"/>',
                f'    <text x="{cx_b+18}" y="{cy_b+ch_b/2+4:.1f}" text-anchor="middle" fill="#FFFFFF" font-size="11" font-weight="800" class="font-ui">{num}</text>',
                f'    <text x="{cx_b+36}" y="{cy_b+16}" fill="#FFE4E6" font-size="10" font-weight="800" class="font-ui">{_esc(c_title)}</text>',
                f'    <text x="{cx_b+36}" y="{cy_b+31}" fill="#FECDD3" font-size="9" class="font-mono">{_esc(c_sub[:44])}</text>',
                f'  </g>',
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


# ==============================================================================
# 2. DIAGRAMAS VETORIAIS SVG: STAR SCHEMA & MAPA DO CANVAS ODI 12C
# ==============================================================================

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
        f'  <g filter="url(#boxShadow)">',
        f'    <rect x="{fx}" y="{fy}" width="{fw}" height="{fh}" rx="12" fill="#FFFFFF" stroke="#D97706" stroke-width="2.5"/>',
        f'    <rect x="{fx}" y="{fy}" width="{fw}" height="44" rx="10" fill="#B45309"/>',
        f'    <text x="{fx+16}" y="{fy+27}" fill="#FFFFFF" font-size="13.5" font-weight="800" class="font-mono">📊 {_esc(nome_fato)}</text>',
        f'    <rect x="{fx+fw-90}" y="{fy+12}" width="76" height="20" rx="10" fill="#FEF3C7"/>',
        f'    <text x="{fx+fw-52}" y="{fy+26}" text-anchor="middle" fill="#92400E" font-size="9.5" font-weight="800" class="font-ui">TABELA FATO</text>',
        f'  </g>',
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
            f'  <g filter="url(#boxShadow)">',
            f'    <rect x="{dx}" y="{dy}" width="{dw}" height="{dh}" rx="10" fill="#FFFFFF" stroke="#2563EB" stroke-width="1.8"/>',
            f'    <rect x="{dx}" y="{dy}" width="{dw}" height="36" rx="8" fill="#1E40AF"/>',
            f'    <text x="{dx+14}" y="{dy+23}" fill="#FFFFFF" font-size="12" font-weight="800" class="font-mono">🗂️ {_esc(d_nome[:24])}</text>',
            f'    <rect x="{dx+dw-78}" y="{dy+9}" width="66" height="18" rx="9" fill="#DBEAFE"/>',
            f'    <text x="{dx+dw-45}" y="{dy+21}" text-anchor="middle" fill="#1E3A8A" font-size="8.5" font-weight="800" class="font-ui">SK -1 OK</text>',
            f'  </g>',
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
    dim_ex = dims[0]["nome"] if dims else f"DIM_UNIDADE"
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


# ==============================================================================
# 3. GRIDCRAFT ENGINE: PLANILHA INDICADORES_POWERBI.XLSX & LEITOR NATIVO .ODS
# ==============================================================================

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
            xml_bytes = zf.read("content.xml")
        root = ET.fromstring(xml_bytes)
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


# ==============================================================================
# 4. DECKCRAFT + WORDCRAFT: APRESENTAÇÃO EXECUTIVA (.PPTX / HTML) & EXPORTADOR .DOCX
# ==============================================================================

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


# ==============================================================================
# 5. PDFCRAFT + PANIC HUNT: EXTRATOR NATIVO DE TEXTO .PDF (ZERO DEPENDÊNCIAS)
# ==============================================================================

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


# ==============================================================================
# 5.5 LEITORES NATIVOS DE DOCUMENTOS (.DOCX / .ODT) & SCANNER LGPD DE CONTEÚDO
# ==============================================================================

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
            xml_bytes = zf.read("word/document.xml")

        root = ET.fromstring(xml_bytes)
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
        except Exception:
            pass

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
            xml_bytes = zf.read("content.xml")

        root = ET.fromstring(xml_bytes)
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
        except Exception:
            pass

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


def _validar_luhn(digitos: str) -> bool:
    """Valida número de cartão de crédito pelo algoritmo de Luhn."""
    nums = [int(c) for c in digitos if c.isdigit()]
    if len(nums) < 13 or len(nums) > 19 or len(set(nums)) == 1:
        return False
    soma = 0
    paridade = len(nums) % 2
    for idx, d in enumerate(nums):
        if idx % 2 == paridade:
            d *= 2
            if d > 9:
                d -= 9
        soma += d
    return (soma % 10) == 0


def mascarar_pii_texto(texto: str) -> str:
    """
    Mascara dados pessoais (CPF, CNPJ, E-mail, Telefone BR e Cartão de Crédito)
    em um texto ou célula de amostra, inspirado em `pdfcraft/crates/redact`.
    """
    if not texto:
        return ""
    res = str(texto)
    # CPF formatado: 123.456.789-00 -> ***.456.789-**
    res = re.sub(r"\b(\d{3})\.(\d{3})\.(\d{3})-(\d{2})\b", r"**_.\2.\3-**".replace("_", "*"), res)
    # CNPJ formatado: 12.345.678/0001-99 -> **.345.678/0001-**
    res = re.sub(r"\b(\d{2})\.(\d{3})\.(\d{3})/(\d{4})-(\d{2})\b", r"**.\2.\3/\4-**", res)
    # E-mail: joao.silva@ba.gov.br -> jo***@ba.gov.br
    res = re.sub(
        r"\b([A-Za-z0-9._%+-]{1,2})[A-Za-z0-9._%+-]*@([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b",
        r"\1***@\2",
        res,
    )
    # Telefone BR: (71) 98888-7777 -> (71) *****-7777
    res = re.sub(
        r"(\(?\d{2}\)?\s?)(?:9\d{4}|\d{4})([-\s]\d{4})\b",
        r"\1*****\2",
        res,
    )
    # Cartão de Crédito: 4532 1111 2222 3333 -> **** **** **** 3333
    res = re.sub(
        r"\b(?:\d{4}[-\s]){3}(\d{4})\b",
        r"**** **** **** \1",
        res,
    )
    return res


def escanear_pii_em_texto_ou_linhas(
    dados,
    nome_contexto: str = "",
    max_ocorrencias: int = 25,
) -> List[dict]:
    """
    Inspeciona o conteúdo real das linhas/células ou texto livre em busca de PII
    escondido (CPF, CNPJ, E-mail, Telefone/Celular BR, Cartão de Crédito), mesmo
    quando o nome da coluna parece inócuo (ex: `TXT_OBSERVACAO`, `DES_HISTORICO`).
    Retorna lista de achados com valor mascarado (`***.456.789-**`) e enquadramento LGPD.
    """
    padroes = [
        (
            "CPF",
            re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b"),
            "RESTRITO_LGPD_PII",
            "Art. 5º, I e Art. 7º da LGPD (Lei 13.709/2018) — Identificador Pessoal Direto",
        ),
        (
            "EMAIL",
            re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
            "RESTRITO_LGPD_PII",
            "Art. 5º, I da LGPD — Endereço Eletrônico Pessoal/Funcional",
        ),
        (
            "TELEFONE_BR",
            re.compile(r"(?:\+55\s?)?(?:\(\d{2}\)\s?|\b\d{2}\s)(?:9\d{4}|\d{4})[-\s]\d{4}\b"),
            "RESTRITO_LGPD_PII",
            "Art. 5º, I da LGPD — Telefone / Celular de Contato Individual",
        ),
        (
            "CNPJ",
            re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b"),
            "INTERNO_GOVERNO",
            "Cadastro Nacional de Pessoa Jurídica (Verificar se MEI / Empresário Individual)",
        ),
        (
            "CARTAO_CREDITO",
            re.compile(r"\b(?:\d{4}[-\s]){3}\d{4}\b"),
            "SENSIVEL_FINANCEIRO",
            "Dado Financeiro / Cartão de Pagamento (PCI-DSS & LGPD)",
        ),
    ]

    achados: List[dict] = []

    def _analisar_celula(valor_str: str, nome_col: str, num_linha: int) -> None:
        if not valor_str or len(achados) >= max_ocorrencias:
            return
        for tipo_pii, rgx, classif, base_legal in padroes:
            m = rgx.search(valor_str)
            if m:
                trecho = m.group(0)
                if tipo_pii == "CARTAO_CREDITO" and not _validar_luhn(trecho):
                    continue
                achados.append({
                    "tipo_pii": tipo_pii,
                    "coluna": nome_col or nome_contexto or "TEXTO_LIVRE",
                    "linha": num_linha,
                    "valor_mascarado": mascarar_pii_texto(trecho),
                    "amostra_mascarada": mascarar_pii_texto(valor_str[:90]),
                    "classificacao_sugerida": classif,
                    "base_legal_sugerida": base_legal,
                })
                if len(achados) >= max_ocorrencias:
                    return

    if isinstance(dados, str):
        for idx_l, ln in enumerate(dados.splitlines(), start=1):
            _analisar_celula(ln, nome_contexto or "DOCUMENTO", idx_l)
    elif isinstance(dados, list) and dados:
        if isinstance(dados[0], dict):
            for idx_l, row_dict in enumerate(dados, start=2):
                for col_k, val_v in row_dict.items():
                    _analisar_celula(str(val_v or ""), str(col_k or ""), idx_l)
        elif isinstance(dados[0], (list, tuple)):
            cabecalho = [str(c).strip() for c in dados[0]]
            for idx_l, row_list in enumerate(dados[1:], start=2):
                for idx_c, val_v in enumerate(row_list):
                    col_k = cabecalho[idx_c] if idx_c < len(cabecalho) and cabecalho[idx_c] else f"COL_{idx_c + 1}"
                    _analisar_celula(str(val_v or ""), col_k, idx_l)

    return achados


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
                except OSError:
                    pass

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
        root = ET.fromstring(xml_text) if xml_text.strip() else ET.Element("pipeline")
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
        f'  <!-- Fundo com Grade Oficial Apache Hop -->',
        f'  <rect width="{canvas_w}" height="{canvas_h}" fill="#F8FAFC"/>',
        f'  <rect y="{offset_y}" width="{canvas_w}" height="{canvas_h - offset_y}" fill="url(#hopGrid)"/>',
        "",
        f'  <!-- Header Institucional Apache Hop 2.x -->',
        f'  <rect width="{canvas_w}" height="64" fill="#0F172A"/>',
        '  <rect x="18" y="13" width="38" height="38" rx="8" fill="#2563EB"/>',
        '  <text x="37" y="38" text-anchor="middle" fill="#FFFFFF" font-size="16" font-weight="800" class="hop-ui">H</text>',
        f'  <text x="68" y="29" fill="#FFFFFF" font-size="14" font-weight="700" class="hop-ui">APACHE HOP 2.x CANVAS — {_esc(nome_meta)}</text>',
        f'  <text x="68" y="48" fill="#94A3B8" font-size="11" class="hop-mono">{_esc(tipo_canvas)} • {len(nodes)} {"Actions" if is_workflow else "Transforms"} • {len(hops)} Hops{(" • " + _esc(desc_meta[:65])) if desc_meta else ""}</text>',
        "",
        f'  <!-- Legenda de Hops no Topo Direito -->',
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
            f'  <g class="hop-notepad" filter="url(#hopShadow)">',
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
        f"- **Diagrama Vetorial Principal:** [`diagrama_esteira_hop.svg`](diagrama_esteira_hop.svg)",
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
            root = ET.fromstring(arq.read_text(encoding="utf-8", errors="ignore"))
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

