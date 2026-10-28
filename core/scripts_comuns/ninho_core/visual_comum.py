"""
Helpers visuais compartilhados: escape SVG/HTML, largura de texto, arcos de donut,
normalização de tabelas DIM/FATO, formatação numérica pt-BR e relacionamentos do Star Schema.

Extraído de gerador_artefatos_visuais.py (que mantém uma fachada de reimportação).
"""

import html
import math
import re
from typing import Any, Dict, List, Optional, Tuple


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
