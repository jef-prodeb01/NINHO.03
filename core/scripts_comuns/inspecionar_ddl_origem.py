#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Inspetor Determinístico de DDL de Origem (SQL Server / Postgres / MySQL / Oracle)
Plataforma NINHO — Prevenção de Alucinação Colunar & Pré-Diagnóstico de CDC/Tuning

Extrai 100% das tabelas, colunas, tipos mapeados para Oracle, PKs, FKs, Índices
e colunas candidatas de data/CDC a partir dos scripts DDL depositados em
'entrega/planejador_dw/ddl/', gerando a Matriz De/Para base do Blueprint.

Uso:
    python core/scripts_comuns/inspecionar_ddl_origem.py
    python core/scripts_comuns/inspecionar_ddl_origem.py --caminho entrega/planejador_dw/ddl/
    python core/scripts_comuns/inspecionar_ddl_origem.py --saida saida/planejador_dw/09_relatorio_estrategias/MATRIZ_DE_PARA_ORIGEM.md
"""

import sys
import re
import argparse
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

VERDE = "\033[92m"
AMARELO = "\033[93m"
VERMELHO = "\033[91m"
CIANO = "\033[96m"
NEGRITO = "\033[1m"
RESET = "\033[0m"


def get_base_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def mapear_tipo_oracle(tipo_origem: str) -> str:
    """Converte tipos SQL Server, Postgres ou MySQL para o padrão Oracle DW."""
    t = tipo_origem.strip().upper()
    t = re.sub(r"\s+COLLATE\s+\S+", "", t, flags=re.IGNORECASE).strip()

    if t.startswith("BIGINT"):
        return "NUMBER(19,0)"
    if t.startswith(("INT", "INTEGER", "SERIAL")):
        return "NUMBER(10,0)"
    if t.startswith(("SMALLINT", "TINYINT")):
        return "NUMBER(5,0)"
    if t.startswith("BIT") or t == "BOOLEAN" or t == "BOOL":
        return "CHAR(1 CHAR)"
    if t.startswith(("DATETIME", "DATETIME2", "SMALLDATETIME", "DATE", "TIMESTAMP")):
        return "DATE"
    m_char = re.match(r"N?CHAR\s*\(\s*(\d+)\s*\)", t)
    if m_char:
        return f"CHAR({m_char.group(1)} CHAR)"
    m_vchar = re.match(r"N?VARCHAR2?\s*\(\s*(\d+|MAX)\s*\)", t)
    if m_vchar:
        tam = m_vchar.group(1)
        if tam == "MAX" or (tam.isdigit() and int(tam) > 4000):
            return "CLOB"
        return f"VARCHAR2({tam} CHAR)"
    if t.startswith(("TEXT", "NTEXT", "CLOB")):
        return "CLOB"
    m_num = re.match(r"(?:DECIMAL|NUMERIC|NUMBER)\s*\(\s*(\d+)\s*(?:,\s*(\d+))?\s*\)", t)
    if m_num:
        p = m_num.group(1)
        s = m_num.group(2) or "0"
        return f"NUMBER({p},{s})"
    if t.startswith(("MONEY", "SMALLMONEY")):
        return "NUMBER(18,2)"
    if t.startswith(("FLOAT", "REAL", "DOUBLE")):
        return "NUMBER(18,4)"
    return t if t else "VARCHAR2(255 CHAR)"


def _extrair_blocos_create_table(sql_text: str) -> list:
    """Localiza instruções CREATE TABLE usando balanceamento de parênteses (suporta cláusulas TABLESPACE/STORAGE do Oracle)."""
    padrao_inicio = re.compile(
        r"CREATE\s+(?:GLOBAL\s+TEMPORARY\s+)?TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([^\(\s]+)\s*\(",
        re.IGNORECASE,
    )
    blocos = []
    pos = 0
    n = len(sql_text)
    while pos < n:
        m = padrao_inicio.search(sql_text, pos)
        if not m:
            break
        nome_bruto = m.group(1).strip()
        idx_abre = m.end() - 1  # posição do '('
        nivel = 0
        em_aspas = False
        idx_fecha = -1
        i = idx_abre
        while i < n:
            ch = sql_text[i]
            if ch == "'":
                if em_aspas and i + 1 < n and sql_text[i + 1] == "'":
                    i += 2
                    continue
                em_aspas = not em_aspas
            elif not em_aspas:
                if ch == "(":
                    nivel += 1
                elif ch == ")":
                    nivel -= 1
                    if nivel == 0:
                        idx_fecha = i
                        break
            i += 1
        if idx_fecha != -1:
            corpo = sql_text[idx_abre + 1 : idx_fecha]
            blocos.append((nome_bruto, corpo))
            pos = idx_fecha + 1
        else:
            pos = m.end()
    return blocos


def _dividir_definicoes_colunas(corpo: str) -> list:
    """Divide os itens internos do CREATE TABLE por vírgula no nível 0 de parênteses."""
    # Remove comentários de linha antes de dividir
    linhas_sem_coment = []
    for ln in corpo.splitlines():
        ln_s = ln.strip()
        if ln_s.startswith("--"):
            continue
        # Remove comentário inline '-- ...' fora de aspas simples
        idx_c = ln.find("--")
        if idx_c != -1 and "'" not in ln[:idx_c]:
            ln = ln[:idx_c]
        linhas_sem_coment.append(ln)
    texto = "\n".join(linhas_sem_coment)

    itens = []
    atual = []
    nivel = 0
    em_aspas = False
    i = 0
    n = len(texto)
    while i < n:
        ch = texto[i]
        if ch == "'":
            if em_aspas and i + 1 < n and texto[i + 1] == "'":
                atual.append("''")
                i += 2
                continue
            em_aspas = not em_aspas
            atual.append(ch)
        elif not em_aspas:
            if ch == "(":
                nivel += 1
                atual.append(ch)
            elif ch == ")":
                nivel = max(0, nivel - 1)
                atual.append(ch)
            elif ch == "," and nivel == 0:
                item_str = "".join(atual).strip()
                if item_str:
                    itens.append(item_str)
                atual = []
            else:
                atual.append(ch)
        else:
            atual.append(ch)
        i += 1

    ultimo = "".join(atual).strip()
    if ultimo:
        itens.append(ultimo)
    return itens


def parse_ddl_text(sql_text: str, arquivo_origem: str) -> list:
    """Extrai definições de tabelas, colunas, PKs, FKs, índices e comentários de um texto SQL."""
    tabelas = {}

    # 1. Localizar blocos CREATE TABLE com balanceamento de parênteses
    for nome_bruto_raw, corpo in _extrair_blocos_create_table(sql_text):
        partes_nome = [p.strip('`"[]') for p in nome_bruto_raw.split(".")]
        nome_bruto = ".".join(partes_nome)
        nome_curto = partes_nome[-1].upper()

        colunas = []
        pks = []
        fks = []

        for ln_clean in _dividir_definicoes_colunas(corpo):
            ln_clean = " ".join(ln_clean.split()).strip()
            if not ln_clean:
                continue

            # Constraint PK inline ou bloco
            m_pk = re.search(r"PRIMARY\s+KEY\s*(?:CLUSTERED|NONCLUSTERED)?\s*\(([^)]+)\)", ln_clean, re.IGNORECASE)
            if m_pk and ln_clean.upper().startswith(("CONSTRAINT", "PRIMARY KEY")):
                cols_pk = [c.strip().strip('`"[]').split()[0].upper() for c in m_pk.group(1).split(",")]
                for c_pk in cols_pk:
                    if c_pk not in pks:
                        pks.append(c_pk)
                continue

            # Constraint FK inline no CREATE TABLE
            m_fk = re.search(
                r"FOREIGN\s+KEY\s*\(([^)]+)\)\s*REFERENCES\s+([^\(\s]+)\s*\(([^)]+)\)",
                ln_clean,
                re.IGNORECASE,
            )
            if m_fk and ln_clean.upper().startswith(("CONSTRAINT", "FOREIGN KEY")):
                col_fk = m_fk.group(1).strip().strip('`"[]').upper()
                tab_ref = [p.strip('`"[]') for p in m_fk.group(2).strip().split(".")][-1].upper()
                col_ref = m_fk.group(3).strip().strip('`"[]').upper()
                fks.append({"coluna": col_fk, "tabela_ref": tab_ref, "coluna_ref": col_ref})
                continue

            if ln_clean.upper().startswith(("CONSTRAINT", "UNIQUE", "CHECK", "INDEX", "KEY", "SUPPLEMENTAL")):
                continue

            # Parse de coluna: nome + tipo + nulabilidade
            m_col = re.match(r'^[\["`]?([A-Za-z0-9_#$]+)[\]"`]?\s+(.+)$', ln_clean)
            if m_col:
                col_nome = m_col.group(1).upper()
                resto = m_col.group(2)

                not_null = bool(re.search(r"\bNOT\s+NULL\b", resto, re.IGNORECASE))
                if re.search(r"\bPRIMARY\s+KEY\b", resto, re.IGNORECASE) and col_nome not in pks:
                    pks.append(col_nome)

                # Extrair apenas a definição de tipo antes de COLLATE / NOT NULL / NULL / DEFAULT / CONSTRAINT / GENERATED / ENABLE
                tipo_raw = re.split(
                    r"\b(?:COLLATE|NOT\s+NULL|NULL|DEFAULT|CONSTRAINT|PRIMARY\s+KEY|GENERATED|IDENTITY|AUTO_INCREMENT|ENABLE|DISABLE)\b",
                    resto,
                    maxsplit=1,
                    flags=re.IGNORECASE,
                )[0].strip()

                colunas.append(
                    {
                        "nome_original": m_col.group(1),
                        "nome_dw": col_nome,
                        "tipo_origem": tipo_raw,
                        "tipo_oracle": mapear_tipo_oracle(tipo_raw),
                        "obrigatorio": "NOT NULL" if not_null else "NULL",
                        "comentario": "",
                    }
                )

        tabelas[nome_curto] = {
            "arquivo": arquivo_origem,
            "nome_completo_origem": nome_bruto,
            "nome_tabela": nome_curto,
            "comentario_tabela": "",
            "colunas": colunas,
            "pks": pks,
            "fks": fks,
            "indices": [],
        }

    # 2. Localizar ALTER TABLE ... ADD CONSTRAINT ... PRIMARY KEY
    padrao_alter_pk = re.compile(
        r"ALTER\s+TABLE\s+([^\s]+)\s+ADD\s+(?:CONSTRAINT\s+[^\s]+\s+)?PRIMARY\s+KEY\s*\(([^)]+)\)",
        re.IGNORECASE,
    )
    for m in padrao_alter_pk.finditer(sql_text):
        tab = [p.strip('`"[]') for p in m.group(1).strip().split(".")][-1].upper()
        if tab in tabelas:
            cols_pk = [c.strip().strip('`"[]').split()[0].upper() for c in m.group(2).split(",")]
            for c_pk in cols_pk:
                if c_pk not in tabelas[tab]["pks"]:
                    tabelas[tab]["pks"].append(c_pk)

    # 3. Localizar ALTER TABLE ... ADD CONSTRAINT ... FOREIGN KEY
    padrao_alter_fk = re.compile(
        r"ALTER\s+TABLE\s+([^\s]+)\s+ADD\s+(?:CONSTRAINT\s+[^\s]+\s+)?FOREIGN\s+KEY\s*\(([^)]+)\)\s*REFERENCES\s+([^\(\s]+)\s*\(([^)]+)\)",
        re.IGNORECASE,
    )
    for m in padrao_alter_fk.finditer(sql_text):
        tab = [p.strip('`"[]') for p in m.group(1).strip().split(".")][-1].upper()
        col_fk = m.group(2).strip().strip('`"[]').upper()
        tab_ref = [p.strip('`"[]') for p in m.group(3).strip().split(".")][-1].upper()
        col_ref = m.group(4).strip().strip('`"[]').upper()
        if tab in tabelas:
            tabelas[tab]["fks"].append({"coluna": col_fk, "tabela_ref": tab_ref, "coluna_ref": col_ref})

    # 4. Localizar CREATE [BITMAP|UNIQUE] INDEX
    padrao_idx = re.compile(
        r"CREATE\s+(?:UNIQUE\s+|BITMAP\s+)?(?:CLUSTERED\s+|NONCLUSTERED\s+)?INDEX\s+([^\s]+)\s+ON\s+([^\(\s]+)\s*\(([^)]+)\)(?:\s*INCLUDE\s*\(([^)]+)\))?",
        re.IGNORECASE,
    )
    for m in padrao_idx.finditer(sql_text):
        nome_idx = [p.strip('`"[]') for p in m.group(1).strip().split(".")][-1].upper()
        tab = [p.strip('`"[]') for p in m.group(2).strip().split(".")][-1].upper()
        cols_idx = [c.strip().strip('`"[]').split()[0].upper() for c in m.group(3).split(",")]
        cols_inc = [c.strip().strip('`"[]').split()[0].upper() for c in m.group(4).split(",")] if m.group(4) else []
        if tab in tabelas:
            tabelas[tab]["indices"].append(
                {"nome": nome_idx, "colunas": cols_idx, "include": cols_inc}
            )

    # 5. Localizar COMMENT ON TABLE e COMMENT ON COLUMN (essencial para Camada Semântica)
    padrao_comm_tab = re.compile(
        r"COMMENT\s+ON\s+TABLE\s+([^\s]+)\s+IS\s+'((?:[^']|'')*)'",
        re.IGNORECASE | re.DOTALL,
    )
    for m in padrao_comm_tab.finditer(sql_text):
        tab = [p.strip('`"[]') for p in m.group(1).strip().split(".")][-1].upper()
        if tab in tabelas:
            tabelas[tab]["comentario_tabela"] = m.group(2).replace("''", "'").strip()

    padrao_comm_col = re.compile(
        r"COMMENT\s+ON\s+COLUMN\s+([^\s]+)\s+IS\s+'((?:[^']|'')*)'",
        re.IGNORECASE | re.DOTALL,
    )
    for m in padrao_comm_col.finditer(sql_text):
        partes = [p.strip('`"[]').upper() for p in m.group(1).strip().split(".")]
        if len(partes) >= 2:
            tab = partes[-2]
            col = partes[-1]
            if tab in tabelas:
                for c_obj in tabelas[tab]["colunas"]:
                    if c_obj["nome_dw"] == col:
                        c_obj["comentario"] = m.group(2).replace("''", "'").strip()
                        break

    return list(tabelas.values())


def diagnosticar_cdc_e_tuning(tab: dict) -> dict:
    """Analisa colunas de data e índices para propor estratégia de CDC e perguntas ao engenheiro."""
    cols_data = [
        c["nome_dw"]
        for c in tab["colunas"]
        if c["tipo_oracle"].startswith(("DATE", "TIMESTAMP"))
        or c["nome_dw"].startswith(("DT_", "DTH_", "DTA_", "DAT_", "DTC_"))
        or (
            not c["nome_dw"].startswith(("ID_", "COD_", "SK_", "NUM_", "QTD_", "VLR_", "FLG_", "IND_", "SIN_", "TIPO_"))
            and any(k in c["nome_dw"] for k in ("CREATED_AT", "UPDATED_AT", "MODIFIED_AT", "DATA_"))
        )
    ]

    tem_audit_update = any(any(k in c for k in ("UPDATED", "MODIFIED", "ATUALIZACAO", "ALTERACAO")) for c in cols_data)
    cols_abertura = [c for c in cols_data if any(k in c for k in ("ABERTURA", "INICIO", "CRIACAO", "CREATED", "CADASTRO", "GERACAO"))]
    cols_conclusao = [c for c in cols_data if any(k in c for k in ("CONCLUSAO", "FIM", "FECHAMENTO", "ENCERRAMENTO", "BAIXA"))]

    if tem_audit_update:
        estrategia_cdc = "CDC Padrão por Coluna de Auditoria (Updated/Modified)"
        filtro_sugerido = f"WHERE {cols_data[0]} >= :V_DATA_CORTE"
    elif cols_abertura and cols_conclusao:
        ab = cols_abertura[0]
        conc = cols_conclusao[0]
        estrategia_cdc = f"CDC por Ciclo de Vida de Eventos ({ab} + {conc}) — Sem coluna UPDATED_AT explícita"
        filtro_sugerido = (
            f"WHERE ({ab} >= :V_DATA_CORTE OR {conc} >= :V_DATA_CORTE) "
            f"/* ou Snapshot de Abertos: {conc} IS NULL OR {conc} >= :V_DATA_CORTE */"
        )
    elif cols_data:
        estrategia_cdc = f"Incremental por Data de Evento ({', '.join(cols_data)})"
        filtro_sugerido = f"WHERE {cols_data[0]} >= :V_DATA_CORTE"
    else:
        estrategia_cdc = "Sem Coluna de Data Detectada (Carga Full / Comparação de PK ou Hash)"
        filtro_sugerido = "/* Avaliar carga Full para Dimensão ou CDC por ID incremental */"

    # Verificar se colunas de data estão indexadas na origem
    cols_indexadas = set()
    for idx in tab["indices"]:
        for c in idx["colunas"]:
            cols_indexadas.add(c)

    datas_indexadas = [c for c in cols_data if c in cols_indexadas]

    return {
        "colunas_data": cols_data,
        "estrategia_cdc": estrategia_cdc,
        "filtro_sugerido": filtro_sugerido,
        "datas_indexadas_origem": datas_indexadas,
    }


def sugerir_oportunidades_analiticas(tab: dict) -> dict:
    """
    Radar Consultivo da IA: Analisa os padrões de colunas do DDL de origem e sugere
    proativamente novos KPIs/Métricas, Regras de Negócio/Qualidade implícitas e
    Perguntas Executivas/Táticas/Auditoria que o cliente pode não ter previsto.
    """
    nomes_cols = [c["nome_dw"] for c in tab["colunas"]]
    cols_data = [
        c["nome_dw"]
        for c in tab["colunas"]
        if c["tipo_oracle"].startswith(("DATE", "TIMESTAMP"))
        or c["nome_dw"].startswith(("DT_", "DTH_", "DTA_", "DAT_", "DTC_"))
    ]

    kpis = []
    regras = []
    perguntas = []

    cols_abertura = [c for c in cols_data if any(k in c for k in ("ABERTURA", "INICIO", "CRIACAO", "CREATED", "CADASTRO", "ENTRADA"))]
    cols_conclusao = [c for c in cols_data if any(k in c for k in ("CONCLUSAO", "FIM", "FECHAMENTO", "ENCERRAMENTO", "BAIXA", "SAIDA"))]
    cols_prazo = [c for c in cols_data if any(k in c for k in ("PRAZO", "VENCIMENTO", "LIMITE", "SLA", "META", "PREVIST"))]
    cols_visualizacao = [c for c in cols_data if any(k in c for k in ("VISUALIZACAO", "LEITURA", "RECEBIMENTO", "ACEITE"))]
    cols_origem = [c for c in nomes_cols if "ORIGEM" in c and c not in cols_data]
    cols_atribuicao = [
        c
        for c in nomes_cols
        if c not in cols_data
        and any(k in c for k in ("ATRIBUICAO", "RESPONSAVEL", "EXECUTOR", "ANALISTA", "USUARIO_CONCLUSAO"))
    ]
    cols_valor = [
        c["nome_dw"]
        for c in tab["colunas"]
        if c["nome_dw"].startswith(("VAL_", "VLR_", "QTD_", "TOT_"))
        or any(k in c["nome_dw"] for k in ("VALOR", "CUSTO", "PRECO", "TAXA", "DESCONTO", "GLOSA", "SALDO", "MONTANTE"))
    ]

    # 1. Padrão Ciclo de Vida (Abertura x Conclusão)
    if cols_abertura and cols_conclusao:
        ab, conc = cols_abertura[0], cols_conclusao[0]
        kpis.extend(
            [
                {
                    "nome": "TEMPO_CICLO_DIAS (Lead Time)",
                    "formula": f"ROUND({conc} - {ab}, 2)",
                    "tipo": "NAO_ADITIVA (Média/Mediana)",
                    "beneficio": "Mede a velocidade real de resolução/tramitação ponta a ponta.",
                },
                {
                    "nome": "QTD_ESTOQUE_ABERTO (Backlog Ativo)",
                    "formula": f"SUM(CASE WHEN {conc} IS NULL THEN 1 ELSE 0 END)",
                    "tipo": "SEMI_ADITIVA (Snapshot de Passivo)",
                    "beneficio": "Quantifica a fila represada pendente de encerramento a qualquer momento.",
                },
                {
                    "nome": "IDADE_PASSIVO_DIAS (Aging de Backlog)",
                    "formula": f"CASE WHEN {conc} IS NULL THEN TRUNC(SYSDATE) - TRUNC({ab}) ELSE NULL END",
                    "tipo": "NAO_ADITIVA (Faixas: 0-15, 16-30, 31-60, >60d)",
                    "beneficio": "Revela demandas esquecidas ou paradas há muito tempo na fila.",
                },
                {
                    "nome": "TAXA_VAZAO_THROUGHPUT (%)",
                    "formula": f"ROUND(SUM(CASE WHEN {conc} IS NOT NULL THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0), 2)",
                    "tipo": "NAO_ADITIVA",
                    "beneficio": "Compara a capacidade de baixa contra o volume de entrada.",
                },
            ]
        )
        regras.extend(
            [
                f"**Sanitização de Datas Invertidas (`{conc} < {ab}`):** Caso existam registros com data de conclusão anterior à abertura por erro sistêmico na fonte, sinalizar `FLG_ERRO_CRONOLOGICO = 'S'` e expurgar do cálculo de `TEMPO_CICLO_DIAS` para não distorcer a média com tempos negativos.",
                f"**Segregação Estrita entre Fluxo Concluído e Estoque Aberto:** O cálculo de tempo médio de atendimento deve filtrar obrigatoriamente `{conc} IS NOT NULL`, enquanto painéis de fila/passivo devem filtrar `{conc} IS NULL`.",
            ]
        )
        perguntas.extend(
            [
                f"**[Executiva]** Qual é a evolução mensal do Lead Time médio (`{conc} - {ab}`) e da Taxa de Vazão (Throughput) por unidade?",
                f"**[Tática/Operacional]** Qual é o tamanho atual do Backlog em aberto (`{conc} IS NULL`) estratificado por faixa de envelhecimento (Aging: até 15 dias, 16-30 dias, 31-60 dias e acima de 60 dias)?",
                f"**[Auditoria/Qualidade]** Quantos registros apresentam inconsistência cronológica (`{conc} < {ab}`) na origem?",
            ]
        )

    # 2. Padrão de SLA / Prazo / Vencimento
    if cols_prazo:
        prz = cols_prazo[0]
        ref_fim = cols_conclusao[0] if cols_conclusao else "SYSDATE"
        kpis.extend(
            [
                {
                    "nome": "PCT_CUMPRIMENTO_SLA (%)",
                    "formula": f"ROUND(SUM(CASE WHEN NVL({ref_fim}, SYSDATE) <= {prz} THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT({prz}), 0), 2)",
                    "tipo": "NAO_ADITIVA",
                    "beneficio": "Indicador executivo chave de conformidade com prazos legais ou contratuais.",
                },
                {
                    "nome": "QTD_DIAS_ATRASO",
                    "formula": f"GREATEST(0, TRUNC(NVL({ref_fim}, SYSDATE)) - TRUNC({prz}))",
                    "tipo": "NAO_ADITIVA (Média/Máximo por Ofensor)",
                    "beneficio": "Dimensiona a severidade dos atrasos além do simples binário dentro/fora do prazo.",
                },
            ]
        )
        regras.append(
            f"**Classificação Preventiva de Risco de SLA (`{prz}`):** Categorizar registros abertos com prazo definido em 3 faixas: `'DENTRO DO PRAZO'`, `'EM RISCO (VENCE EM <= 3 DIAS)'` e `'PRAZO VENCIDO'`, permitindo atuação preventiva antes do estouro do SLA."
        )
        perguntas.extend(
            [
                f"**[Executiva]** Qual é o percentual de cumprimento de SLA (`{prz}`) por unidade e quais são as 10 unidades/categorias com maior volume de estouro de prazo?",
                f"**[Tática/Operacional]** Quais demandas ainda abertas já estão com `{prz}` vencido ou vencerão nas próximas 72 horas?",
            ]
        )

    # 3. Padrão de Fluxo / Tramitação (Origem vs Destino)
    if cols_origem:
        col_orig = cols_origem[0]
        par_atual = col_orig.replace("_ORIGEM", "")
        if par_atual in nomes_cols:
            kpis.extend(
                [
                    {
                        "nome": "TAXA_AUTO_TRAMITACAO_INTERNA (%)",
                        "formula": f"ROUND(SUM(CASE WHEN {par_atual} = {col_orig} THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0), 2)",
                        "tipo": "NAO_ADITIVA",
                        "beneficio": "Identifica retrabalho ou movimentações internas dentro da própria unidade sem avanço externo.",
                    }
                ]
            )
            regras.append(
                f"**Distinção entre Tramitação Externa e Movimentação Interna (`{col_orig}` vs `{par_atual}`):** Separar quando o registro muda efetivamente de setor (`{par_atual} <> {col_orig}`) de quando sofre apenas redistribuição interna na mesma unidade (`{par_atual} = {col_orig}`)."
            )
            perguntas.append(
                f"**[Executiva/Fluxo]** Quais são as principais rotas de tramitação (`{col_orig}` -> `{par_atual}`) que concentram 80% do volume e o maior tempo de retenção (gargalos)?"
            )

    # 4. Padrão de Fila, Visualização e Produtividade Humana
    if cols_atribuicao or cols_visualizacao:
        if cols_visualizacao and cols_abertura:
            vis, ab = cols_visualizacao[0], cols_abertura[0]
            kpis.append(
                {
                    "nome": "TEMPO_ESPERA_PRIMEIRA_LEITURA_HORAS",
                    "formula": f"ROUND(({vis} - {ab}) * 24, 2)",
                    "tipo": "NAO_ADITIVA",
                    "beneficio": "Separa o tempo em que a demanda ficou parada na fila esperando leitura do tempo efetivo de execução.",
                }
            )
        if cols_atribuicao:
            atr = cols_atribuicao[0]
            kpis.append(
                {
                    "nome": "QTD_FILA_SEM_RESPONSAVEL",
                    "formula": f"SUM(CASE WHEN {atr} IS NULL THEN 1 ELSE 0 END)",
                    "tipo": "SEMI_ADITIVA",
                    "beneficio": "Monitora demandas órfãs na fila geral que ainda não foram assumidas por nenhum responsável.",
                }
            )
            regras.append(
                f"**Preservação de Demandas Não Atribuídas (`{atr} IS NULL`):** Mapear chaves nulas de usuário/responsável para a Surrogate Key `-1` (`'NÃO ATRIBUÍDO / FILA GERAL'`), garantindo que itens sem responsável não desapareçam em consultas das views analíticas."
            )
            perguntas.append(
                f"**[Tática/Operacional]** Qual é o volume de demandas abertas sem responsável atribuído (`{atr}`) e qual a distribuição de produtividade por colaborador?"
            )

    # 5. Padrão Monetário / Quantitativo
    if cols_valor:
        v = cols_valor[0]
        kpis.extend(
            [
                {
                    "nome": f"TICKET_MEDIO_{v}",
                    "formula": f"ROUND(SUM(NVL({v}, 0)) / NULLIF(COUNT(*), 0), 2)",
                    "tipo": "NAO_ADITIVA",
                    "beneficio": "Avalia o valor médio por evento e detecta distorções ou outliers.",
                },
                {
                    "nome": f"VARIACAO_MENSAL_MOM_{v} (%)",
                    "formula": f"ROUND((SUM({v}) - LAG(SUM({v})) OVER (ORDER BY ANOMES)) * 100.0 / NULLIF(LAG(SUM({v})) OVER (ORDER BY ANOMES), 0), 2)",
                    "tipo": "NAO_ADITIVA",
                    "beneficio": "Permite acompanhar aceleração ou queda de tendência mês contra mês.",
                },
            ]
        )
        regras.append(
            f"**Proteção Aritmética em Métricas (`{v}`):** Aplicar `NVL({v}, 0)` em agregações aditivas e `NULLIF(denominador, 0)` em todos os cálculos percentuais para evitar `ORA-01476 (divisor is equal to zero)`."
        )
        perguntas.append(
            f"**[Executiva]** Qual é a evolução mensal (MoM) de `{v}` e quais dimensões concentram 80% do volume acumulado (Curva ABC / Pareto)?"
        )

    # Fallback caso a tabela seja puramente cadastral/dimensional
    if not kpis:
        kpis.append(
            {
                "nome": f"QTD_REGISTROS_{tab['nome_tabela']}",
                "formula": "COUNT(*)",
                "tipo": "ADITIVA",
                "beneficio": "Contagem base de ocorrências ou cadastros ativos.",
            }
        )
        regras.append(
            "**Integridade Referencial (Linha `-1`):** Garantir que códigos nulos na origem sejam mapeados para `DIMENSION_KEY = -1` ('NÃO INFORMADO')."
        )
        perguntas.append(
            f"**[Exploratória]** Qual é a distribuição de registros de `{tab['nome_tabela']}` por categoria/status?"
        )

    return {"kpis": kpis, "regras": regras, "perguntas": perguntas}


def gerar_relatorio_markdown(tabelas: list) -> str:
    linhas = [
        "# Matriz De/Para 100% Fiel à Origem & Pré-Diagnóstico de CDC/Tuning",
        "",
        f"> **Gerado automaticamente por `inspecionar_ddl_origem.py` em:** `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`  ",
        "> **Regra de Ouro 3 e 4:** Nenhuma coluna da origem foi omitida ou renomeada arbitrariamente. Utilize este diagnóstico para alinhar o modelo final com o Engenheiro de Dados antes da geração física.",
        "",
        "---",
        "",
    ]

    for tab in tabelas:
        diag = diagnosticar_cdc_e_tuning(tab)
        radar = sugerir_oportunidades_analiticas(tab)
        linhas.append(f"## Tabela de Origem: `{tab['nome_completo_origem']}` (`{tab['nome_tabela']}`)")
        linhas.append("")
        linhas.append(f"- **Arquivo Fonte:** `{tab['arquivo']}`")
        if tab.get("comentario_tabela"):
            linhas.append(f"- **Comentário da Tabela (`COMMENT ON TABLE`):** *{tab['comentario_tabela']}*")
        linhas.append(f"- **Total de Colunas:** `{len(tab['colunas'])}`")
        linhas.append(f"- **Chave Primária (PK):** `{', '.join(tab['pks']) if tab['pks'] else 'NÃO DECLARADA NO DDL'}`")
        linhas.append(f"- **Chaves Estrangeiras (FKs):** `{len(tab['fks'])}` relacionamento(s)")
        linhas.append(f"- **Índices na Origem:** `{len(tab['indices'])}` índice(s)")
        linhas.append("")
        linhas.append("### Diagnóstico Preditivo de CDC & Carga Incremental")
        linhas.append(f"- **Colunas de Data Identificadas:** `{', '.join(diag['colunas_data']) if diag['colunas_data'] else 'Nenhuma'}`")
        linhas.append(f"- **Colunas de Data com Índice na Origem:** `{', '.join(diag['datas_indexadas_origem']) if diag['datas_indexadas_origem'] else 'Nenhuma (Atenção a Full Table Scan na origem!)'}`")
        linhas.append(f"- **Estratégia CDC Recomendada:** **{diag['estrategia_cdc']}**")
        linhas.append(f"- **Filtro Incremental Sugerido:** `{diag['filtro_sugerido']}`")
        linhas.append("")
        linhas.append("### Matriz De/Para de Colunas (100% Fiel à Origem)")
        linhas.append("")
        linhas.append("| # | Coluna na Origem | Coluna no DW / Semântica | Tipo Origem | Tipo Oracle Sugerido | Nulabilidade | Papel Dimensional / Semântico | Comentário (`COMMENT ON COLUMN`) |")
        linhas.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")

        fks_map = {fk["coluna"]: fk["tabela_ref"] for fk in tab["fks"]}
        for idx, col in enumerate(tab["colunas"], 1):
            nm = col["nome_dw"]
            if nm in tab["pks"]:
                papel = "🔑 Chave Natural / Surrogate Key (PK)"
            elif nm in fks_map:
                papel = f"🔗 FK para Dimensão (`{fks_map[nm]}`)"
            elif nm in diag["colunas_data"]:
                papel = "📅 Marco Temporal / FK `DIM_TEMPO`"
            elif nm.startswith(("SIN_", "IND_", "FLG_", "STA_", "TIPO_")):
                papel = "🏷️ Flag / Atributo de Status ou Domínio"
            elif nm.startswith(("VAL_", "VLR_", "QTD_", "TOT_", "MED_", "PCT_")):
                papel = "📊 Métrica Quantitativa"
            else:
                papel = "📝 Atributo Descritivo"

            comm_col = col.get("comentario", "").replace("|", "/").replace("\n", " ") or "—"
            linhas.append(
                f"| {idx} | `{col['nome_original']}` | `{nm}` | `{col['tipo_origem']}` | `{col['tipo_oracle']}` | `{col['obrigatorio']}` | {papel} | {comm_col} |"
            )

        linhas.append("")
        if tab["fks"]:
            linhas.append("### Relacionamentos (Foreign Keys Detectadas)")
            linhas.append("")
            for fk in tab["fks"]:
                linhas.append(f"- `{fk['coluna']}` -> referencia `{fk['tabela_ref']}({fk['coluna_ref']})`")
            linhas.append("")

        linhas.append("### 💡 Radar Consultivo da IA (Sugestões Proativas para o Cliente/Engenheiro)")
        linhas.append("")
        linhas.append("> *Oportunidades analíticas detectadas automaticamente a partir da estrutura física de colunas (para complementar o escopo inicial solicitado pelo cliente):*")
        linhas.append("")
        linhas.append("#### 📊 Novos KPIs e Métricas Derivadas Sugeridas")
        linhas.append("")
        linhas.append("| KPI / Métrica Sugerida | Fórmula SQL Base (Oracle) | Tipo de Aditividade | Valor de Negócio para o Cliente |")
        linhas.append("| :--- | :--- | :--- | :--- |")
        for k in radar["kpis"]:
            linhas.append(f"| **`{k['nome']}`** | `{k['formula']}` | {k['tipo']} | {k['beneficio']} |")
        linhas.append("")
        linhas.append("#### 🛡️ Regras de Negócio e Qualidade de Dados Sugeridas")
        linhas.append("")
        for r in radar["regras"]:
            linhas.append(f"- {r}")
        linhas.append("")
        linhas.append("#### ❓ Novas Perguntas Estratégicas de Negócio Sugeridas (`META_CONSULTA_NEGOCIO`)")
        linhas.append("")
        for idx_p, p in enumerate(radar["perguntas"], 1):
            linhas.append(f"{idx_p}. {p}")
        linhas.append("")

        linhas.append("---")
        linhas.append("")

    return "\n".join(linhas)


def main():
    parser = argparse.ArgumentParser(
        description="Inspetor Determinístico de DDL de Origem (Extrai 100% das colunas, PKs, FKs, Índices, CDC e Radar Consultivo de KPIs)"
    )
    parser.add_argument(
        "--caminho",
        "--pasta",
        dest="caminho",
        type=str,
        default="",
        help="Pasta ou arquivo DDL (.sql) para inspecionar (padrão: entrega/planejador_dw/ddl/ e entrega/camada_semantica/ddl/)",
    )
    parser.add_argument(
        "--saida",
        type=str,
        default="",
        help="Caminho opcional para salvar o relatório Markdown completo com a Matriz De/Para",
    )
    args = parser.parse_args()

    base_dir = get_base_dir()
    alvos = []

    if args.caminho:
        p = Path(args.caminho)
        if not p.is_absolute():
            p = base_dir / p
        if p.is_file():
            alvos.append(p)
        elif p.is_dir():
            alvos.extend(sorted(p.glob("*.sql")) + sorted(p.glob("*.txt")))
    else:
        for d in [
            base_dir / "entrega" / "planejador_dw" / "ddl",
            base_dir / "entrega" / "planejador_dw" / "schemas_origem",
            base_dir / "entrega" / "camada_semantica" / "ddl",
            base_dir / "modulos" / "planejador_dw" / "entrada" / "ddl",
        ]:
            if d.exists():
                alvos.extend(
                    [f for f in sorted(d.iterdir()) if f.is_file() and f.suffix.lower() in [".sql", ".txt"] and f.name.lower() != "readme.md"]
                )

    print(f"\n{CIANO}{NEGRITO}{'=' * 75}{RESET}")
    print(f"{CIANO}{NEGRITO}  🔍 NINHO — INSPETOR DETERMINÍSTICO DE DDL DE ORIGEM & RADAR DE KPIs{RESET}")
    print(f"{CIANO}{NEGRITO}{'=' * 75}{RESET}\n")

    if not alvos:
        print(f"  {AMARELO}[AVISO]{RESET} Nenhum arquivo DDL (.sql/.txt) encontrado em 'entrega/planejador_dw/ddl/' ou 'entrega/camada_semantica/ddl/'.")
        print(f"  Deposite o DDL de origem ou informe '--caminho <arquivo.sql>'.\n")
        sys.exit(0)

    todas_tabelas = []
    for arq in alvos:
        sql_txt = arq.read_text(encoding="utf-8", errors="ignore")
        tabs = parse_ddl_text(sql_txt, arq.name)
        todas_tabelas.extend(tabs)

    if not todas_tabelas:
        print(f"  {VERMELHO}[ERRO]{RESET} Nenhuma instrução CREATE TABLE foi identificada nos arquivos analisados.\n")
        sys.exit(1)

    for tab in todas_tabelas:
        diag = diagnosticar_cdc_e_tuning(tab)
        radar = sugerir_oportunidades_analiticas(tab)
        cols_com_comentario = sum(1 for c in tab["colunas"] if c.get("comentario"))
        print(f"  {VERDE}[TABELA]{RESET} {NEGRITO}{tab['nome_completo_origem']}{RESET} ({len(tab['colunas'])} colunas)")
        print(f"    • PK: {', '.join(tab['pks']) if tab['pks'] else 'Nenhuma'} | FKs: {len(tab['fks'])} | Índices: {len(tab['indices'])} | Comentários: {cols_com_comentario}/{len(tab['colunas'])}")
        print(f"    • Colunas de Data: {', '.join(diag['colunas_data']) if diag['colunas_data'] else 'Nenhuma'}")
        print(f"    • Diagnóstico CDC: {diag['estrategia_cdc']}")
        print(f"    • Filtro Sugerido: {diag['filtro_sugerido']}")
        print(f"    • 💡 Radar Consultivo da IA: {len(radar['kpis'])} novos KPIs | {len(radar['regras'])} regras | {len(radar['perguntas'])} perguntas estratégicas sugeridas\n")

    if args.saida:
        out_path = Path(args.saida)
        if not out_path.is_absolute():
            out_path = base_dir / out_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(gerar_relatorio_markdown(todas_tabelas), encoding="utf-8")
        print(f"  {VERDE}[OK]{RESET} Matriz De/Para e Radar Consultivo salvos em: {out_path}\n")


if __name__ == "__main__":
    main()
