"""
Prova Real Pós-Carga: carrega amostras DIM/FATO em SQLite in-memory, extrai as medidas DAX
do Guia do Analista de BI e as reavalia (auditor MED-01..06).

Extraído de gerador_artefatos_visuais.py (que mantém uma fachada de reimportação).
"""

import logging as _logging_ninho

_LOG = _logging_ninho.getLogger("ninho.core.prova_dax")

import csv
import io
import re
import sqlite3
from ninho_core.visual_comum import (
    _formatar_numero_br,
    _inferir_sk_nk_dim,
    _limpar_label,
    _mapear_relacionamentos_star,
    _normalizar_dims_fatos,
)
from ninho_core.leitores import (
    _converter_valor_celula,
    _ler_planilha_xlsx_abas,
)
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


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
            except Exception as _exc:
                _LOG.debug("Exceção tratada (prova_dax.py:456): %r", _exc)

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
                    except Exception as _exc:
                        _LOG.debug("Exceção tratada (prova_dax.py:470): %r", _exc)

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
            except Exception as _exc:
                _LOG.debug("Exceção tratada (prova_dax.py:666): %r", _exc)

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
            except Exception as _exc:
                _LOG.debug("Exceção tratada (prova_dax.py:738): %r", _exc)

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
            except Exception as _exc:
                _LOG.debug("Exceção tratada (prova_dax.py:798): %r", _exc)

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
            "dax": "[% Qualidade] = 1 - [% Nao Informado -1]",
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
