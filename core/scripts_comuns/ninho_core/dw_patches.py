"""
Patches não-destrutivos do Fast-Track sobre DW existente: COMMENT ON, dicionário HTML,
índices/procedures, FKs ENABLE NOVALIDATE, linha -1, controle de carga ETA e testes de integridade.

Extraído de melhorar_dw_existente.py (que mantém uma fachada de reimportação).
"""

import re
import html
from datetime import datetime
from ninho_core.dw_modelo import (
    _obter_sk_dim,
    coluna_ja_indexada,
    gerar_comentario_coluna,
    gerar_comentario_tabela,
    gerar_valor_default_menos_um,
    identificar_fks_fato,
)


def construir_script_comentarios(tabelas_cat: list, schema: str, titulo_camada: str) -> tuple:
    """Gera o script SQL de COMMENT ON TABLE e COMMENT ON COLUMN para um grupo de tabelas."""
    linhas = [
        "-- =============================================================================",
        f"-- PATCH FAST-TRACK: COMENTÁRIOS DE TABELAS E COLUNAS ({titulo_camada.upper()})",
        f"-- Schema Alvo: {schema} | Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "-- Nota: Script 100% não-destrutivo. Não altera estrutura nem esteira de carga.",
        "-- =============================================================================",
        "",
    ]
    qtd_tab = 0
    qtd_col = 0
    for tab, cat in tabelas_cat:
        nome_tab = tab["nome_tabela"].upper()
        comm_tab = gerar_comentario_tabela(tab, cat, schema).replace("'", "''")
        linhas.append("-- -----------------------------------------------------------------------------")
        linhas.append(f"-- Tabela: {schema}.{nome_tab} ({cat})")
        linhas.append("-- -----------------------------------------------------------------------------")
        linhas.append(f"COMMENT ON TABLE {schema}.{nome_tab} IS '{comm_tab}';")
        linhas.append("")
        qtd_tab += 1
        for col in tab["colunas"]:
            nome_col = col["nome_dw"].upper()
            comm_col = gerar_comentario_coluna(col, tab, cat).replace("'", "''")
            linhas.append(f"COMMENT ON COLUMN {schema}.{nome_tab}.{nome_col} IS '{comm_col}';")
            qtd_col += 1
        linhas.append("")
    return "\n".join(linhas), qtd_tab, qtd_col


def construir_dicionario_html(tabelas_classificadas: list, schema: str, projeto: str) -> str:
    """Gera o Dicionário de Dados interativo em HTML5 a partir das tabelas reais do DDL."""
    cards_html = []
    schema = html.escape(str(schema), quote=True)
    projeto = html.escape(str(projeto), quote=True)
    for tab, cat in tabelas_classificadas:
        nome_tab = html.escape(tab["nome_tabela"].upper(), quote=True)
        comm_tab = html.escape(gerar_comentario_tabela(tab, cat, projeto), quote=True)
        pks = set(tab.get("pks", []))
        fks_cols = {fk["coluna"].upper() for fk in tab.get("fks", [])}
        for c in tab["colunas"]:
            cn = c["nome_dw"].upper()
            if cat == "FATO" and (cn.startswith(("DIM_", "SK_")) or cn.endswith("_KEY")):
                fks_cols.add(cn)

        badge_cls = "badge-fato" if cat == "FATO" else "badge-dim"
        badge_txt = "Tabela Fato" if cat == "FATO" else ("Dimensão" if cat == "DIM" else "Staging / Apoio")
        pk_label = html.escape(", ".join(pks) if pks else "DIMENSION_KEY", quote=True)

        linhas_tr = []
        for col in tab["colunas"]:
            cn = col["nome_dw"].upper()
            cn_esc = html.escape(cn, quote=True)
            tipo = html.escape(str(col["tipo_oracle"]), quote=True)
            obr = html.escape(str(col["obrigatorio"]), quote=True)
            desc = html.escape(gerar_comentario_coluna(col, tab, cat), quote=True)

            if cn in pks:
                badge_col = '<span class="badge badge-pk">PK</span>'
                regra_col = "Chave Primária"
            elif cn in fks_cols:
                badge_col = '<span class="badge badge-fk">FK</span>'
                regra_col = '<span class="formula">NVL(LOOKUP, -1)</span>'
            elif cat == "FATO" and cn.startswith(("VAL_", "VLR_", "QTD_", "QT_", "PER_", "PRC_")):
                badge_col = '<span class="badge badge-metric">Métrica</span>'
                fn_agreg = "AVG" if cn.startswith(("PER_", "PRC_")) else "SUM"
                regra_col = f'<span class="formula">{fn_agreg}({cn_esc})</span>'
            else:
                badge_col = "-"
                if cn in ("DTC_EFETIVACAO", "DTC_INICIO_VIGENCIA"):
                    regra_col = "SCD2 Início Vigência"
                elif cn in ("DTC_EXPIRACAO", "DTC_FIM_VIGENCIA"):
                    regra_col = "SCD2 Fim Vigência (NULL = Atual)"
                elif cn.startswith(("ID_", "COD_")) and cat == "DIM":
                    regra_col = "Chave Natural"
                else:
                    regra_col = obr

            linhas_tr.append(
                f"                <tr>\n"
                f"                    <td class=\"col-name\">{cn_esc}</td>\n"
                f"                    <td class=\"col-type\">{tipo} ({obr})</td>\n"
                f"                    <td>{badge_col}</td>\n"
                f"                    <td>{desc}</td>\n"
                f"                    <td>{regra_col}</td>\n"
                f"                </tr>"
            )

        card = f"""    <div class="table-card" data-category="{cat}">
        <div class="table-header">
            <div>
                <span class="table-title">{schema}.{nome_tab}</span>
                <span class="badge {badge_cls}">{badge_txt}</span>
            </div>
            <span><strong>PK:</strong> {pk_label} | <strong>Colunas:</strong> {len(tab['colunas'])}</span>
        </div>
        <div class="table-desc">
            {comm_tab}
        </div>
        <table>
            <thead>
                <tr>
                    <th>Coluna</th>
                    <th>Tipo Oracle</th>
                    <th>Papel</th>
                    <th>Descrição de Negócio (COMMENT ON COLUMN)</th>
                    <th>Regra / Comportamento</th>
                </tr>
            </thead>
            <tbody>
{chr(10).join(linhas_tr)}
            </tbody>
        </table>
    </div>"""
        cards_html.append(card)

    data_hoje = datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dicionário de Dados — {projeto}</title>
    <style>
        :root {{
            --bg-color: #f8fafc;
            --card-bg: #ffffff;
            --border-color: #e2e8f0;
            --text-main: #1e293b;
            --text-muted: #64748b;
            --primary: #2563eb;
            --badge-pk: #dc2626;
            --badge-fk: #d97706;
            --badge-metric: #059669;
            --badge-dim: #7c3aed;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            margin: 0;
            padding: 24px;
            line-height: 1.5;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        header {{ margin-bottom: 24px; padding-bottom: 16px; border-bottom: 2px solid var(--border-color); }}
        h1 {{ font-size: 26px; margin: 0 0 8px 0; color: #0f172a; }}
        .meta-info {{ font-size: 14px; color: var(--text-muted); display: flex; gap: 20px; flex-wrap: wrap; }}
        .search-bar {{ display: flex; gap: 12px; margin-bottom: 24px; position: sticky; top: 12px; z-index: 100; background: var(--bg-color); padding: 8px 0; }}
        .search-input {{ flex: 1; padding: 12px 16px; font-size: 15px; border: 2px solid var(--border-color); border-radius: 8px; outline: none; background: #ffffff; }}
        .search-input:focus {{ border-color: var(--primary); }}
        .filter-btn {{ padding: 10px 16px; background: #ffffff; border: 1px solid var(--border-color); border-radius: 8px; cursor: pointer; font-weight: 500; color: var(--text-main); }}
        .filter-btn.active {{ background: var(--primary); color: #ffffff; border-color: var(--primary); }}
        .table-card {{ background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 12px; margin-bottom: 24px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
        .table-header {{ padding: 16px 20px; background: #f1f5f9; border-bottom: 1px solid var(--border-color); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }}
        .table-title {{ font-size: 18px; font-weight: 700; margin: 0; color: #0f172a; margin-right: 8px; }}
        .table-desc {{ padding: 12px 20px; background: #fafafa; font-size: 14px; color: var(--text-muted); border-bottom: 1px solid var(--border-color); }}
        .badge {{ display: inline-block; font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 12px; text-transform: uppercase; }}
        .badge-fato {{ background: #fee2e2; color: var(--badge-pk); }}
        .badge-dim {{ background: #ede9fe; color: var(--badge-dim); }}
        .badge-pk {{ background: #fee2e2; color: #b91c1c; }}
        .badge-fk {{ background: #fef3c7; color: #b45309; }}
        .badge-metric {{ background: #d1fae5; color: #047857; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 13px; text-align: left; }}
        th {{ background: #f8fafc; padding: 10px 16px; font-weight: 600; color: var(--text-muted); border-bottom: 1px solid var(--border-color); }}
        td {{ padding: 10px 16px; border-bottom: 1px solid var(--border-color); }}
        tr:last-child td {{ border-bottom: none; }}
        .col-name {{ font-family: monospace; font-weight: 600; color: #0f172a; }}
        .col-type {{ color: #475569; font-family: monospace; }}
        .formula {{ font-family: monospace; background: #f1f5f9; padding: 2px 6px; border-radius: 4px; font-size: 12px; }}
    </style>
</head>
<body>
<div class="container">
    <header>
        <h1>📖 Dicionário de Dados — {projeto}</h1>
        <div class="meta-info">
            <span><strong>Schema Oracle:</strong> {schema}</span>
            <span><strong>Data de Geração:</strong> {data_hoje}</span>
            <span><strong>Total de Tabelas:</strong> {len(tabelas_classificadas)}</span>
            <span><strong>Modo:</strong> Fast-Track (DW Existente)</span>
        </div>
    </header>
    <div class="search-bar">
        <input type="text" id="searchInput" class="search-input" placeholder="Buscar por tabela, coluna, tipo ou descrição de negócio...">
        <button class="filter-btn active" onclick="filterCategory('ALL', event)">Todas ({len(tabelas_classificadas)})</button>
        <button class="filter-btn" onclick="filterCategory('FATO', event)">Fatos</button>
        <button class="filter-btn" onclick="filterCategory('DIM', event)">Dimensões</button>
    </div>
{chr(10).join(cards_html)}
</div>
<script>
    document.getElementById('searchInput').addEventListener('input', function(e) {{
        const query = e.target.value.toLowerCase();
        document.querySelectorAll('.table-card').forEach(card => {{
            card.style.display = card.textContent.toLowerCase().includes(query) ? 'block' : 'none';
        }});
    }});
    function filterCategory(cat, ev) {{
        document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
        if (ev && ev.target) ev.target.classList.add('active');
        document.querySelectorAll('.table-card').forEach(card => {{
            card.style.display = (cat === 'ALL' || card.getAttribute('data-category') === cat) ? 'block' : 'none';
        }});
    }}
</script>
</body>
</html>
"""


def construir_scripts_indices(
    dims: list,
    fatos: list,
    schema: str,
    ts_idx: str = None,
    estrategia: str = "A",
) -> tuple:
    """Gera os scripts SQL de índices otimizados para Dimensões (B-Tree) e Fatos (Bitmap ou B-Tree)."""
    clausula_ts = f" TABLESPACE {ts_idx}" if ts_idx else ""
    nomes_dims = {d["nome_tabela"].upper() for d in dims}

    # 1. Script de Índices para Dimensões (SEMPRE B-TREE, NUNCA BITMAP)
    linhas_dim = [
        "-- =============================================================================",
        "-- PATCH FAST-TRACK: ÍNDICES DE PERFORMANCE E LOOKUP SCD2 (DIMENSÕES)",
        f"-- Schema Alvo: {schema} | Regra: Estritamente B-TREE em Dimensões (Zero Bitmap)",
        "-- =============================================================================",
        "",
    ]
    qtd_idx_dim = 0
    for d in dims:
        nt = d["nome_tabela"].upper()
        curto = nt[:18]
        linhas_dim.append("-- -----------------------------------------------------------------------------")
        linhas_dim.append(f"-- Dimensão: {schema}.{nt}")
        linhas_dim.append("-- -----------------------------------------------------------------------------")
        cols_d = [c["nome_dw"].upper() for c in d["colunas"]]

        # Identifica chave natural (ID_* ou COD_*) e colunas de vigência SCD2
        naturais = [
            c for c in cols_d
            if c.startswith(("ID_", "COD_", "NUM_CPF", "NUM_CNPJ", "MATRICULA"))
            and c != "DIMENSION_KEY"
        ]
        col_scd_fim = next((c for c in cols_d if c in ("DTC_EXPIRACAO", "DTC_FIM_VIGENCIA", "SIN_ATIVO", "FLG_ATUAL")), None)

        if naturais:
            nat_principal = naturais[0]
            if not coluna_ja_indexada(d, nat_principal):
                nome_idx = f"IDX_{curto}_LKP"[:30]
                if col_scd_fim:
                    linhas_dim.append(
                        f"-- Índice composto B-Tree de Lookup SCD2 (Chave Natural + Vigência)\n"
                        f"CREATE INDEX {schema}.{nome_idx} ON {schema}.{nt} ({nat_principal}, {col_scd_fim})"
                        f" COMPRESS 1{clausula_ts} PARALLEL 4 NOLOGGING;\n"
                        f"ALTER INDEX {schema}.{nome_idx} NOPARALLEL LOGGING;\n"
                    )
                else:
                    linhas_dim.append(
                        f"-- Índice B-Tree de Lookup por Chave Natural\n"
                        f"CREATE INDEX {schema}.{nome_idx} ON {schema}.{nt} ({nat_principal})"
                        f" COMPRESS 1{clausula_ts} PARALLEL 4 NOLOGGING;\n"
                        f"ALTER INDEX {schema}.{nome_idx} NOPARALLEL LOGGING;\n"
                    )
                qtd_idx_dim += 1

        # Colunas de filtro frequente (SIG_, STS_, TIP_)
        filtros = [c for c in cols_d if c.startswith(("SIG_", "STS_", "TIP_")) and not coluna_ja_indexada(d, c)]
        for idx_num, col_f in enumerate(filtros[:2], start=1):
            nome_idx_f = f"IDX_{curto}_FLT{idx_num}"[:30]
            linhas_dim.append(
                f"CREATE INDEX {schema}.{nome_idx_f} ON {schema}.{nt} ({col_f})"
                f" COMPRESS 1{clausula_ts} PARALLEL 4 NOLOGGING;\n"
                f"ALTER INDEX {schema}.{nome_idx_f} NOPARALLEL LOGGING;\n"
            )
            qtd_idx_dim += 1

        if nt == "DIM_TEMPO" and "DTC_COMPLETA" in cols_d and not coluna_ja_indexada(d, "DTC_COMPLETA"):
            linhas_dim.append(
                f"CREATE UNIQUE INDEX {schema}.IDX_DIM_TEMPO_DTC ON {schema}.DIM_TEMPO (DTC_COMPLETA)"
                f"{clausula_ts} PARALLEL 4 NOLOGGING;\n"
                f"ALTER INDEX {schema}.IDX_DIM_TEMPO_DTC NOPARALLEL LOGGING;\n"
            )
            qtd_idx_dim += 1

        linhas_dim.append(
            f"BEGIN\n"
            f"    DBMS_STATS.GATHER_TABLE_STATS(ownname => '{schema}', tabname => '{nt}', cascade => TRUE, degree => 4);\n"
            f"END;\n/\n"
        )

    # 2. Script de Índices para Fatos (Estratégia A = BITMAP | Estratégia B = B-TREE COMPRESS 1)
    tipo_idx_str = "BITMAP INDEX (Estratégia A - Star Transformation)" if estrategia.upper() == "A" else "B-TREE COMPRESS 1 (Estratégia B - MERGE Concorrente)"
    linhas_fato = [
        "-- =============================================================================",
        "-- PATCH FAST-TRACK: ÍNDICES DE CHAVES ESTRANGEIRAS E TUNING (FATOS)",
        f"-- Schema Alvo: {schema} | Modalidade: {tipo_idx_str}",
        "-- =============================================================================",
        "",
    ]
    qtd_idx_fato = 0
    for f in fatos:
        nt = f["nome_tabela"].upper()
        curto = nt[:16]
        cols_fato_reais = {c["nome_dw"].upper() for c in f["colunas"]}
        linhas_fato.append("-- -----------------------------------------------------------------------------")
        linhas_fato.append(f"-- Fato: {schema}.{nt}")
        linhas_fato.append("-- -----------------------------------------------------------------------------")
        fks = identificar_fks_fato(f, nomes_dims)
        cols_fks_validas = []
        for seq_fk, fk_info in enumerate(fks, start=1):
            col_fk = fk_info["coluna"].upper()
            if col_fk not in cols_fato_reais:
                continue
            cols_fks_validas.append(col_fk)
            if coluna_ja_indexada(f, col_fk):
                linhas_fato.append(f"-- [OK] Coluna FK {col_fk} já possui índice no DDL original.")
                continue
            sufixo_col = re.sub(r"^(DIM|SK|ID)_", "", col_fk)[:8]
            if estrategia.upper() == "A":
                nome_idx = f"BIX_{curto}_{seq_fk}_{sufixo_col}"[:30].rstrip("_")
                linhas_fato.append(
                    f"CREATE BITMAP INDEX {schema}.{nome_idx} ON {schema}.{nt} ({col_fk})"
                    f"{clausula_ts} PARALLEL 4 NOLOGGING;\n"
                    f"ALTER INDEX {schema}.{nome_idx} NOPARALLEL LOGGING;\n"
                )
            else:
                nome_idx = f"IDX_{curto}_{seq_fk}_{sufixo_col}"[:30].rstrip("_")
                linhas_fato.append(
                    f"CREATE INDEX {schema}.{nome_idx} ON {schema}.{nt} ({col_fk})"
                    f" COMPRESS 1{clausula_ts} PARALLEL 4 NOLOGGING;\n"
                    f"ALTER INDEX {schema}.{nome_idx} NOPARALLEL LOGGING;\n"
                )
            qtd_idx_fato += 1

        # Índice composto do Grão da Fato (Update Key do IKM MERGE / filtro composto de alta seletividade)
        # Estritamente restrito às colunas que existem fisicamente na tabela Fato (evita ORA-00904)
        degeneradas_grao = [
            c["nome_dw"].upper()
            for c in f["colunas"]
            if c["nome_dw"].upper().startswith(("COD_", "ID_", "NUM_"))
            and c["nome_dw"].upper() not in cols_fks_validas
            and not c["nome_dw"].upper().startswith(("SK_FATO", "SK_FAT", "ID_FATO", "ID_FAT"))
        ]
        cols_grao_composto = (cols_fks_validas + degeneradas_grao)[:4]
        if len(cols_grao_composto) >= 2:
            nome_idx_grao = f"IDX_{curto}_GRAO"[:30].rstrip("_")
            linhas_fato.append(
                f"-- Índice composto B-Tree sobre o Grão / Update Key da Fato (colunas validadas no DDL)\n"
                f"CREATE INDEX {schema}.{nome_idx_grao} ON {schema}.{nt} ({', '.join(cols_grao_composto)})"
                f" COMPRESS 1{clausula_ts} PARALLEL 4 NOLOGGING;\n"
                f"ALTER INDEX {schema}.{nome_idx_grao} NOPARALLEL LOGGING;\n"
            )
            qtd_idx_fato += 1

        linhas_fato.append(
            f"BEGIN\n"
            f"    DBMS_STATS.GATHER_TABLE_STATS(ownname => '{schema}', tabname => '{nt}', cascade => TRUE, degree => 4);\n"
            f"END;\n/\n"
        )

    return "\n".join(linhas_dim), "\n".join(linhas_fato), qtd_idx_dim, qtd_idx_fato


def construir_patches_ajustes_nao_destrutivos(dims: list, fatos: list, schema: str) -> tuple:
    """
    Gera scripts de evolução segura (sem DROP/CREATE):
      - MERGE idempotente da linha técnica -1 em todas as dimensões (respeitando todas as colunas NOT NULL)
      - ALTER TABLE ADD CONSTRAINT (PK e FK com ENABLE NOVALIDATE para não travar nem rejeitar legado)
    """
    nomes_dims = {d["nome_tabela"].upper(): d for d in dims}

    linhas_dim = [
        "-- =============================================================================",
        "-- PATCH FAST-TRACK NÃO-DESTRUTIVO: LINHA PADRÃO (-1) E CONSTRAINTS (DIMENSÕES)",
        f"-- Schema Alvo: {schema} | Seguro para execução em banco já populado",
        "-- =============================================================================",
        "",
    ]
    for d in dims:
        nt = d["nome_tabela"].upper()
        cols = d["colunas"]
        if not cols:
            continue
        pks = d.get("pks", [])
        col_pk = pks[0] if pks else ("DIMENSION_KEY" if any(c["nome_dw"] == "DIMENSION_KEY" for c in cols) else cols[0]["nome_dw"])

        linhas_dim.append("-- -----------------------------------------------------------------------------")
        linhas_dim.append(f"-- Dimensão: {schema}.{nt} (PK: {col_pk})")
        linhas_dim.append("-- -----------------------------------------------------------------------------")

        # Se PK não estava declarada no DDL, sugere ALTER TABLE ADD CONSTRAINT ENABLE NOVALIDATE
        if not pks:
            nome_pk = f"PK_{nt}"[:30]
            linhas_dim.append(
                f"-- Adiciona constraint de Primary Key (ENABLE NOVALIDATE preserva carga existente)\n"
                f"ALTER TABLE {schema}.{nt} ADD CONSTRAINT {nome_pk} PRIMARY KEY ({col_pk}) ENABLE NOVALIDATE;\n"
            )

        # MERGE idempotente para o registro padrão -1
        select_exprs = []
        insert_cols = []
        insert_vals = []
        for c in cols:
            c_copy = dict(c)
            c_copy["_pks_tab"] = [col_pk]
            cn = c["nome_dw"].upper()
            val_sql = gerar_valor_default_menos_um(c_copy)
            select_exprs.append(f"{val_sql} AS {cn}")
            insert_cols.append(f"T.{cn}")
            insert_vals.append(f"S.{cn}")

        val_pk = "-1" if "CHAR" not in cols[0]["tipo_oracle"].upper() else "'-1'"
        linhas_dim.append("-- Garante existência idempotente do registro sentinela -1 ('NAO INFORMADO')")
        linhas_dim.append(f"MERGE INTO {schema}.{nt} T")
        linhas_dim.append(f"USING (SELECT {', '.join(select_exprs)} FROM DUAL) S")
        linhas_dim.append(f"ON (T.{col_pk} = {val_pk})")
        linhas_dim.append("WHEN NOT MATCHED THEN")
        linhas_dim.append(f"    INSERT ({', '.join(insert_cols)})")
        linhas_dim.append(f"    VALUES ({', '.join(insert_vals)});")
        linhas_dim.append("")

    linhas_dim.append("COMMIT;\n")

    # Script de Constraints Não-Destrutivas nas Fatos (ENABLE NOVALIDATE)
    linhas_fato = [
        "-- =============================================================================",
        "-- PATCH FAST-TRACK NÃO-DESTRUTIVO: INTEGRIDADE REFERENCIAL E AJUSTES (FATOS)",
        f"-- Schema Alvo: {schema} | Cláusula ENABLE NOVALIDATE (não bloqueia dados históricos)",
        "-- =============================================================================",
        "",
    ]
    for f in fatos:
        nt = f["nome_tabela"].upper()
        curto = nt[:14]
        fks_ja_declaradas = {fk["coluna"].upper() for fk in f.get("fks", [])}
        fks_inferidas = identificar_fks_fato(f, set(nomes_dims.keys()))

        linhas_fato.append("-- -----------------------------------------------------------------------------")
        linhas_fato.append(f"-- Fato: {schema}.{nt}")
        linhas_fato.append("-- -----------------------------------------------------------------------------")
        adicionou = False
        for seq_fk, fk_info in enumerate(fks_inferidas, start=1):
            col_fk = fk_info["coluna"].upper()
            tab_ref = fk_info["tabela_ref"].upper()
            if col_fk in fks_ja_declaradas:
                linhas_fato.append(f"-- [OK] Constraint FK na coluna {col_fk} -> {tab_ref} já existe no DDL.")
                continue
            if tab_ref in nomes_dims:
                d_alvo = nomes_dims[tab_ref]
                pk_alvo = d_alvo["pks"][0] if d_alvo.get("pks") else "DIMENSION_KEY"
                nome_fk = f"FK_{curto}_{seq_fk}_{col_fk[:8]}"[:30].rstrip("_")
                linhas_fato.append(
                    f"ALTER TABLE {schema}.{nt} ADD CONSTRAINT {nome_fk}\n"
                    f"    FOREIGN KEY ({col_fk}) REFERENCES {schema}.{tab_ref} ({pk_alvo})\n"
                    f"    ENABLE NOVALIDATE;\n"
                )
                adicionou = True
            else:
                linhas_fato.append(
                    f"-- [INFO] Possível FK {col_fk} -> {tab_ref} (tabela alvo não presente neste DDL; descomente se existir no schema):\n"
                    f"-- ALTER TABLE {schema}.{nt} ADD CONSTRAINT FK_{curto}_{seq_fk} FOREIGN KEY ({col_fk}) REFERENCES {schema}.{tab_ref} (DIMENSION_KEY) ENABLE NOVALIDATE;\n"
                )
        if not adicionou and not fks_inferidas:
            linhas_fato.append(f"-- Nenhuma FK dimensional pendente detectada para {nt}.")
        linhas_fato.append("")

    return "\n".join(linhas_dim), "\n".join(linhas_fato)


def construir_testes_integridade(dims: list, fatos: list, schema: str, projeto: str) -> str:
    """Gera o script 13_testes_integridade.sql adaptado às tabelas reais do DDL existente."""
    nomes_dims = {d["nome_tabela"].upper(): d for d in dims}
    linhas = [
        "-- =============================================================================",
        f"-- SUÍTE DE TESTES DE INTEGRIDADE PARA DW EXISTente — PROJETO: {projeto}",
        f"-- Schema Alvo: {schema} | Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "-- =============================================================================",
        "",
        "SET SERVEROUTPUT ON;",
        "SET LINESIZE 200;",
        "SET PAGESIZE 100;",
        "",
    ]

    if dims:
        linhas.append("-- 1. Verificação da presença do registro sentinela -1 nas Dimensões")
        unions_m1 = []
        for d in dims:
            nt = d["nome_tabela"].upper()
            pk_d = d["pks"][0] if d.get("pks") else ("DIMENSION_KEY" if any(c["nome_dw"] == "DIMENSION_KEY" for c in d["colunas"]) else d["colunas"][0]["nome_dw"])
            unions_m1.append(f"SELECT '{nt}' AS TABELA_DIMENSAO, COUNT(*) AS QTD_REGISTRO_MENOS_1 FROM {schema}.{nt} WHERE {pk_d} = -1")
        linhas.append("\nUNION ALL\n".join(unions_m1) + ";\n")

    if fatos:
        linhas.append("-- 2. Verificação de FKs Nulas e Chaves Órfãs nas Tabelas Fato")
        for f in fatos:
            nt = f["nome_tabela"].upper()
            fks = identificar_fks_fato(f, set(nomes_dims.keys()))
            exprs_nulos = [f"SUM(CASE WHEN {fk['coluna']} IS NULL THEN 1 ELSE 0 END) AS NULOS_{fk['coluna'][:18]}" for fk in fks]
            if exprs_nulos:
                linhas.append(f"SELECT COUNT(*) AS TOTAL_{nt[:18]},\n       " + ",\n       ".join(exprs_nulos))
                linhas.append(f"FROM {schema}.{nt};\n")

            unions_orfas = []
            for fk in fks:
                col_fk = fk["coluna"].upper()
                tab_ref = fk["tabela_ref"].upper()
                if tab_ref in nomes_dims:
                    d_alvo = nomes_dims[tab_ref]
                    pk_alvo = d_alvo["pks"][0] if d_alvo.get("pks") else "DIMENSION_KEY"
                    unions_orfas.append(
                        f"SELECT '{nt} -> {tab_ref} ({col_fk})' AS RELACIONAMENTO, COUNT(*) AS QTD_ORFAS\n"
                        f"FROM {schema}.{nt} F\n"
                        f"LEFT JOIN {schema}.{tab_ref} D ON F.{col_fk} = D.{pk_alvo}\n"
                        f"WHERE D.{pk_alvo} IS NULL"
                    )
            if unions_orfas:
                linhas.append("\nUNION ALL\n".join(unions_orfas) + ";\n")

    todas_tabs = [d["nome_tabela"].upper() for d in dims] + [f["nome_tabela"].upper() for f in fatos]
    if todas_tabs:
        lista_in = ", ".join(f"'{t}'" for t in todas_tabs)
        linhas.append("-- 3. Auditoria de Índices UNUSABLE / INVALID e Cobertura de Comentários no Catálogo Oracle")
        linhas.append(
            f"SELECT TABLE_NAME, INDEX_NAME, INDEX_TYPE, STATUS\n"
            f"FROM ALL_INDEXES\n"
            f"WHERE OWNER = '{schema}'\n"
            f"  AND TABLE_NAME IN ({lista_in})\n"
            f"  AND STATUS <> 'VALID';\n"
        )
        linhas.append(
            f"SELECT TABLE_NAME, COUNT(*) AS COLUNAS_SEM_COMENTARIO\n"
            f"FROM ALL_COL_COMMENTS\n"
            f"WHERE OWNER = '{schema}'\n"
            f"  AND TABLE_NAME IN ({lista_in})\n"
            f"  AND COMMENTS IS NULL\n"
            f"GROUP BY TABLE_NAME;\n"
        )

    return "\n".join(linhas)


def construir_relatorio_diagnostico(
    tabelas_classificadas: list,
    schema: str,
    projeto: str,
    modo: str,
    arquivos_gerados: list,
) -> str:
    """Gera o relatório executivo DIAGNOSTICO_MELHORIAS_DW_EXISTENTE.md em 09_relatorio_estrategias/."""
    achados = []
    total_cols = 0
    cols_sem_comm_orig = 0
    tabs_sem_comm_orig = 0

    for tab, cat in tabelas_classificadas:
        nt = tab["nome_tabela"].upper()
        if not (tab.get("comentario_tabela") or "").strip():
            tabs_sem_comm_orig += 1
        sem_c = [c["nome_dw"] for c in tab["colunas"] if not (c.get("comentario") or "").strip()]
        total_cols += len(tab["colunas"])
        cols_sem_comm_orig += len(sem_c)

        itens_tab = []
        if not (tab.get("comentario_tabela") or "").strip() or sem_c:
            itens_tab.append(f"Documentação incompleta na origem ({len(sem_c)}/{len(tab['colunas'])} colunas sem `COMMENT ON COLUMN`).")
        if cat == "DIM" and not tab.get("pks"):
            itens_tab.append("Dimensão sem constraint `PRIMARY KEY` explícita no DDL.")
        if cat == "DIM" and not tab.get("indices"):
            itens_tab.append("Dimensão sem índice B-Tree de Lookup SCD2 / Chave Natural declarado no DDL.")
        if cat == "FATO":
            fks = identificar_fks_fato(tab, set())
            fks_sem_idx = [fk["coluna"] for fk in fks if not coluna_ja_indexada(tab, fk["coluna"])]
            if fks_sem_idx:
                itens_tab.append(f"{len(fks_sem_idx)} coluna(s) FK sem índice de performance no DDL: `{', '.join(fks_sem_idx)}`.")
        if not itens_tab:
            itens_tab.append("Estrutura física aderente; comentários e estatísticas consolidadas.")

        achados.append(f"### `{schema}.{nt}` ({cat})\n" + "\n".join(f"- {it}" for it in itens_tab))

    lista_arqs = "\n".join(f"- `{a}`" for a in arquivos_gerados)
    return f"""# Diagnóstico e Patch Fast-Track — DW Existente ({projeto})

> **Schema Alvo:** `{schema}` | **Modo Executado:** `{modo.upper()}` | **Data:** {datetime.now().strftime('%Y-%m-%d %H:%M')}  
> **Garantia de Segurança:** Todos os scripts gerados são **100% não-destrutivos** (zero `DROP TABLE`, zero alteração na esteira de carga ODI/Hop).

---

## 1. Resumo do Raio-X no DDL Recebido

- **Tabelas Inspecionadas:** `{len(tabelas_classificadas)}`
- **Total de Colunas Mapeadas:** `{total_cols}`
- **Tabelas sem `COMMENT ON TABLE` no DDL original:** `{tabs_sem_comm_orig}`
- **Colunas sem `COMMENT ON COLUMN` no DDL original:** `{cols_sem_comm_orig}`

---

## 2. Diagnóstico por Tabela

{chr(10).join(achados)}

---

## 3. Artefatos Não-Destrutivos Gerados em `saida/planejador_dw/`

{lista_arqs}
"""


def construir_script_controle_carga_eta(
    dims: list,
    fatos: list,
    schema: str,
    projeto: str,
    ts_dat: str,
    ts_idx: str,
) -> str:
    """
    Gera o script `01_tb_controle_carga.sql` com o padrão corporativo completo:
      1) `ETA_ETAPAS_CARGA` (bloco PL/SQL idempotente seguro contra ORA-00955, comentários 100% nas 5 colunas e MERGE INTO das etapas STG/DIM/FATO)
      2) `TB_CONTROLE_CARGA` (telemetria detalhada de execução por lote)
    """
    linhas = [
        "-- =============================================================================",
        f"-- NINHO — 01_tb_controle_carga.sql (PROJETO: {projeto} | SCHEMA: {schema})",
        "-- Padrão Corporativo: ETA_ETAPAS_CARGA (Idempotente ORA-00955 Safe) + TB_CONTROLE_CARGA",
        "-- =============================================================================",
        "",
        "-- 1. Criação idempotente de ETA_ETAPAS_CARGA (Padrão Apache Hop / ODI 12c)",
        "DECLARE",
        "    e_table_exists EXCEPTION;",
        "    PRAGMA EXCEPTION_INIT(e_table_exists, -955);",
        "BEGIN",
        "    EXECUTE IMMEDIATE '",
        f"        CREATE TABLE {schema}.ETA_ETAPAS_CARGA (",
        "            ETA_COD_ETAPA           NUMBER(10)          NOT NULL,",
        "            ETA_DES_ETAPA           VARCHAR2(200 CHAR)  NOT NULL,",
        "            ETA_TABELA_ALVO         VARCHAR2(100 CHAR)  NOT NULL,",
        "            ETA_DATA_ULT_ATUALIZACAO DATE               DEFAULT SYSDATE NOT NULL,",
        "            ETA_STATUS_ULT_EXECUCAO VARCHAR2(30 CHAR)   DEFAULT ''PENDENTE'' NOT NULL,",
        f"            CONSTRAINT PK_ETA_ETAPAS_CARGA PRIMARY KEY (ETA_COD_ETAPA) USING INDEX TABLESPACE {ts_idx}",
        f"        ) TABLESPACE {ts_dat}",
        "    ';",
        "EXCEPTION",
        "    WHEN e_table_exists THEN NULL;",
        "END;",
        "/",
        "",
        f"COMMENT ON TABLE {schema}.ETA_ETAPAS_CARGA IS 'Tabela corporativa de controle de etapas de carga ETL (Apache Hop / ODI 12c). Uma linha representa uma etapa monitorada do pipeline.';",
        f"COMMENT ON COLUMN {schema}.ETA_ETAPAS_CARGA.ETA_COD_ETAPA IS 'Código identificador sequencial da etapa de carga (PK).';",
        f"COMMENT ON COLUMN {schema}.ETA_ETAPAS_CARGA.ETA_DES_ETAPA IS 'Descrição funcional da etapa de extração/transformação/carga.';",
        f"COMMENT ON COLUMN {schema}.ETA_ETAPAS_CARGA.ETA_TABELA_ALVO IS 'Nome físico da tabela alvo (STG_*, DIM_* ou FATO_*) atualizada pela etapa.';",
        f"COMMENT ON COLUMN {schema}.ETA_ETAPAS_CARGA.ETA_DATA_ULT_ATUALIZACAO IS 'Data e hora da última execução bem-sucedida da etapa.';",
        f"COMMENT ON COLUMN {schema}.ETA_ETAPAS_CARGA.ETA_STATUS_ULT_EXECUCAO IS 'Status operacional da última execução (SUCESSO, ERRO, EM_ANDAMENTO, PENDENTE).';",
        "",
    ]

    etapas = []
    cod = 1
    for d in dims:
        dn = d["nome_tabela"].upper()
        if "TEMPO" in dn or "CALENDARIO" in dn:
            continue
        stg_n = re.sub(r"^DIM_", "STG_", dn)
        etapas.append((cod, f"Carga Stage {stg_n}", stg_n))
        cod += 1
        etapas.append((cod, f"Carga Dimensão SCD2 {dn}", dn))
        cod += 1
    for f in fatos:
        fn = f["nome_tabela"].upper()
        stg_f = re.sub(r"^(FATO|FAT)_", "STG_", fn)
        etapas.append((cod, f"Carga Stage {stg_f}", stg_f))
        cod += 1
        etapas.append((cod, f"Carga Tabela Fato {fn}", fn))
        cod += 1

    if etapas:
        linhas.append("-- Registro idempotente das etapas do projeto em ETA_ETAPAS_CARGA")
        for c_etapa, desc_etapa, tab_alvo in etapas:
            linhas.extend([
                f"MERGE INTO {schema}.ETA_ETAPAS_CARGA T",
                f"USING (SELECT {c_etapa} AS COD, '{desc_etapa}' AS DES, '{tab_alvo}' AS ALVO FROM DUAL) S",
                "ON (T.ETA_COD_ETAPA = S.COD)",
                "WHEN NOT MATCHED THEN",
                "    INSERT (ETA_COD_ETAPA, ETA_DES_ETAPA, ETA_TABELA_ALVO, ETA_DATA_ULT_ATUALIZACAO, ETA_STATUS_ULT_EXECUCAO)",
                "    VALUES (S.COD, S.DES, S.ALVO, SYSDATE, 'PENDENTE');",
            ])
        linhas.append("COMMIT;")
        linhas.append("")

    linhas.extend([
        "-- 2. Tabela complementar de telemetria detalhada de lotes (TB_CONTROLE_CARGA)",
        f"CREATE TABLE {schema}.TB_CONTROLE_CARGA (",
        "    COD_CARGA         NUMBER(10)          GENERATED BY DEFAULT AS IDENTITY NOT NULL,",
        f"    SGL_PROJETO       VARCHAR2(50 CHAR)   DEFAULT '{projeto}' NOT NULL,",
        "    NOM_OBJETO_ALVO   VARCHAR2(128 CHAR)  NOT NULL,",
        "    TIP_CAMADA        VARCHAR2(20 CHAR)   NOT NULL,",
        "    DTC_INICIO_CARGA  TIMESTAMP           DEFAULT SYSTIMESTAMP NOT NULL,",
        "    DTC_FIM_CARGA     TIMESTAMP           NULL,",
        "    QTD_LIDOS         NUMBER(15)          DEFAULT 0,",
        "    QTD_INSERIDOS     NUMBER(15)          DEFAULT 0,",
        "    QTD_ATUALIZADOS   NUMBER(15)          DEFAULT 0,",
        "    QTD_REJEITADOS    NUMBER(15)          DEFAULT 0,",
        "    IND_STATUS        VARCHAR2(20 CHAR)   DEFAULT 'EM_ANDAMENTO' NOT NULL,",
        "    DES_MENSAGEM_ERRO VARCHAR2(4000 CHAR) NULL,",
        f"    CONSTRAINT PK_TB_CONTROLE_CARGA PRIMARY KEY (COD_CARGA) USING INDEX TABLESPACE {ts_idx}",
        f") TABLESPACE {ts_dat};",
        "",
        f"COMMENT ON TABLE {schema}.TB_CONTROLE_CARGA IS 'Tabela corporativa de auditoria e telemetria de execução de cargas ETL (STG/DIM/FATO). Uma linha representa uma execução de lote.';",
        "",
    ])
    return "\n".join(linhas)


def construir_script_linha_default(dims: list, schema: str) -> str:
    """Gera o script isolado 06_init_default_records.sql com MERGE idempotente da linha -1."""
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linhas = [
        "-- =============================================================================",
        "-- NINHO MICRO-PROCESSO — REGISTRO PADRÃO (-1 / NÃO INFORMADO) NAS DIMENSÕES",
        f"-- Schema Alvo: {schema} | Data: {agora}",
        "-- Garantias  : 100% Idempotente (MERGE INTO ON DIMENSION_KEY = -1)",
        "-- =============================================================================",
        "",
    ]
    for d in dims:
        nt = d["nome_tabela"].upper()
        cols = d["colunas"]
        if not cols:
            continue
        col_pk = _obter_sk_dim(d)
        select_exprs = []
        insert_cols = []
        insert_vals = []
        for c in cols:
            c_copy = dict(c)
            c_copy["_pks_tab"] = [col_pk]
            cn = c["nome_dw"].upper()
            val_sql = gerar_valor_default_menos_um(c_copy)
            select_exprs.append(f"{val_sql} AS {cn}")
            insert_cols.append(f"T.{cn}")
            insert_vals.append(f"S.{cn}")

        val_pk = "-1" if "CHAR" not in cols[0]["tipo_oracle"].upper() else "'-1'"
        linhas.extend([
            f"-- Dimensão: {schema}.{nt} (PK: {col_pk})",
            f"MERGE INTO {schema}.{nt} T",
            f"USING (SELECT {', '.join(select_exprs)} FROM DUAL) S",
            f"ON (T.{col_pk} = {val_pk})",
            "WHEN NOT MATCHED THEN",
            f"    INSERT ({', '.join(insert_cols)})",
            f"    VALUES ({', '.join(insert_vals)});",
            "",
        ])
    linhas.append("COMMIT;\n")
    return "\n".join(linhas)
