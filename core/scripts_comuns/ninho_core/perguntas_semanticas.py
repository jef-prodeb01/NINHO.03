"""
Catálogo de perguntas de negócio (META_CONSULTA_NEGOCIO) com SQL de referência (golden queries).

Gera, a partir do modelo real do projeto (Fatos, dimensões, métricas, eixo temporal, situação e
chave degenerada), no mínimo `MINIMO_PERGUNTAS_IA` perguntas propostas pela IA em 3 horizontes:
  - EXECUTIVA  (estratégica): volume, tendência, YoY/MoM, ranking, Pareto, totais e YTD;
  - TATICA     (operacional): médias por dimensão, cruzamentos, cobertura, sazonalidade, outliers;
  - AUDITORIA  (qualidade)  : chaves -1, métricas inválidas, datas futuras, frescor, duplicidade,
                              conciliação KPI x Evento.
As perguntas do cliente (INTAKE_SEMANTICA.md Seção 5.1) entram à parte, com a pergunta da IA
mais parecida indicada para o engenheiro validar o SQL.

Todo SQL consulta apenas as views semânticas (VW_EVENTO, VW_KPI, VW_DIM), sem SELECT *.
"""

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

MINIMO_PERGUNTAS_IA = 30
MAX_METRICAS_COMBINADAS = 3


@dataclass
class DimensaoPergunta:
    fk: str           # coluna FK na view de evento
    vw_dim: str       # view VW_<PROJ>_DIM_<ENT>_ATUAL
    sk: str           # chave substituta da dimensão
    atributo: str     # coluna descritiva exibida no resultado
    nome: str         # nome legível (ex.: "Órgão Público")


@dataclass
class FatoPergunta:
    entidade: str                                   # nome legível do processo (ex.: "Licitação Contrato")
    vw_evento: str
    vw_kpi: str
    dims: List[DimensaoPergunta] = field(default_factory=list)
    metricas: List[Tuple[str, str]] = field(default_factory=list)   # (coluna, nome legível)
    data: Optional[Tuple[str, str]] = None                          # (coluna, nome legível)
    situacao: Optional[str] = None                                  # "FLAG" | "STATUS" | None
    chave_degenerada: Optional[str] = None


@dataclass
class PerguntaNegocio:
    id_consulta: str
    pergunta: str
    sql: str
    objetos: str
    horizonte: str      # EXECUTIVA | TATICA | AUDITORIA | CLIENTE
    origem: str         # IA | CLIENTE
    observacao: str = ""


def _perguntas_do_fato(f: FatoPergunta, schema: str) -> List[Tuple[str, str, str, str]]:
    """Lista de (horizonte, pergunta, sql, objetos) para uma Fato."""
    ev = f"{schema}.{f.vw_evento}"
    kpi = f"{schema}.{f.vw_kpi}"
    E = f.entidade
    out: List[Tuple[str, str, str, str]] = []

    def add(horiz, pergunta, sql, *objs):
        out.append((horiz, pergunta, re.sub(r"\s+", " ", sql).strip(), ", ".join(dict.fromkeys(objs or (f.vw_evento,)))))

    def join(d: DimensaoPergunta) -> str:
        return f"JOIN {schema}.{d.vw_dim} d ON d.{d.sk} = e.{d.fk}"

    metricas = f.metricas[:MAX_METRICAS_COMBINADAS]
    D = f.data[0] if f.data else None
    D_dt = (
        f"TO_DATE(TO_CHAR(NULLIF(e.{D}, -1)), 'YYYYMMDD')"
        if D and D.upper() in ("DIM_TEMPO", "SK_TEMPO")
        else (f"e.{D}" if D else None)
    )

    # ---------------- EXECUTIVA ----------------
    add("EXECUTIVA", f"Quantos eventos de {E} existem no total?", f"SELECT COUNT(1) AS QTD_EVENTOS FROM {ev} e")
    if D:
        add("EXECUTIVA", f"Como evoluiu o volume mensal de {E} nos últimos 12 meses?",
            f"SELECT TRUNC({D_dt}, 'MM') AS MES, COUNT(1) AS QTD_EVENTOS FROM {ev} e "
            f"WHERE {D_dt} >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -12) GROUP BY TRUNC({D_dt}, 'MM') ORDER BY MES")
        add("EXECUTIVA", f"Qual a variação percentual do volume de {E} de um mês para o outro?",
            f"WITH m AS (SELECT TRUNC({D_dt}, 'MM') AS MES, COUNT(1) AS QTD FROM {ev} e GROUP BY TRUNC({D_dt}, 'MM')) "
            f"SELECT MES, QTD, ROUND((QTD - LAG(QTD) OVER (ORDER BY MES)) * 100 / NULLIF(LAG(QTD) OVER (ORDER BY MES), 0), 2) "
            f"AS PCT_VARIACAO_MES FROM m ORDER BY MES")
        add("EXECUTIVA", f"Como o volume de {E} do ano corrente se compara ao do ano anterior, mês a mês?",
            f"SELECT EXTRACT(MONTH FROM {D_dt}) AS MES, "
            f"SUM(CASE WHEN EXTRACT(YEAR FROM {D_dt}) = EXTRACT(YEAR FROM SYSDATE) THEN 1 ELSE 0 END) AS QTD_ANO_ATUAL, "
            f"SUM(CASE WHEN EXTRACT(YEAR FROM {D_dt}) = EXTRACT(YEAR FROM SYSDATE) - 1 THEN 1 ELSE 0 END) AS QTD_ANO_ANTERIOR "
            f"FROM {ev} e GROUP BY EXTRACT(MONTH FROM {D_dt}) ORDER BY MES")
    for col, nome in metricas:
        add("EXECUTIVA", f"Qual o total de {nome} em {E}?", f"SELECT SUM(e.{col}) AS TOTAL_{col} FROM {ev} e")
        if D:
            add("EXECUTIVA", f"Qual o total acumulado de {nome} no ano corrente?",
                f"SELECT SUM(e.{col}) AS TOTAL_ANO_{col} FROM {ev} e WHERE {D_dt} >= TRUNC(SYSDATE, 'YYYY')")
            add("EXECUTIVA", f"Como {nome} evoluiu mês a mês?",
                f"SELECT TRUNC({D_dt}, 'MM') AS MES, SUM(e.{col}) AS TOTAL_{col} FROM {ev} e "
                f"GROUP BY TRUNC({D_dt}, 'MM') ORDER BY MES")
    for d in f.dims:
        add("EXECUTIVA", f"Quais são os 10 itens de {d.nome} com maior volume de {E}?",
            f"SELECT d.{d.atributo}, COUNT(1) AS QTD_EVENTOS FROM {ev} e {join(d)} "
            f"GROUP BY d.{d.atributo} ORDER BY QTD_EVENTOS DESC FETCH FIRST 10 ROWS ONLY", f.vw_evento, d.vw_dim)
        for col, nome in metricas[:2]:
            add("EXECUTIVA", f"Quais são os 10 itens de {d.nome} com maior {nome}?",
                f"SELECT d.{d.atributo}, SUM(e.{col}) AS TOTAL_{col} FROM {ev} e {join(d)} "
                f"GROUP BY d.{d.atributo} ORDER BY TOTAL_{col} DESC NULLS LAST FETCH FIRST 10 ROWS ONLY", f.vw_evento, d.vw_dim)
        add("EXECUTIVA", f"Quantos itens de {d.nome} concentram 80% do volume de {E} (curva ABC)?",
            f"WITH r AS (SELECT d.{d.atributo} AS ITEM, COUNT(1) AS QTD FROM {ev} e {join(d)} GROUP BY d.{d.atributo}), "
            f"a AS (SELECT ITEM, SUM(QTD) OVER (ORDER BY QTD DESC ROWS UNBOUNDED PRECEDING) * 100 / NULLIF(SUM(QTD) OVER (), 0) AS PCT_ACUMULADO FROM r) "
            f"SELECT COUNT(1) AS QTD_ITENS_80_PCT FROM a WHERE PCT_ACUMULADO <= 80", f.vw_evento, d.vw_dim)

    # ---------------- TÁTICA ----------------
    for d in f.dims:
        for col, nome in metricas[:2]:
            add("TATICA", f"Qual o valor médio de {nome} por {d.nome}?",
                f"SELECT d.{d.atributo}, ROUND(AVG(e.{col}), 2) AS MEDIA_{col}, COUNT(1) AS QTD_EVENTOS FROM {ev} e {join(d)} "
                f"GROUP BY d.{d.atributo} ORDER BY MEDIA_{col} DESC NULLS LAST", f.vw_evento, d.vw_dim)
        if D:
            add("TATICA", f"Como {E} se distribuiu por {d.nome} no último mês completo?",
                f"SELECT d.{d.atributo}, COUNT(1) AS QTD_EVENTOS FROM {ev} e {join(d)} "
                f"WHERE {D_dt} >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -1) AND {D_dt} < TRUNC(SYSDATE, 'MM') "
                f"GROUP BY d.{d.atributo} ORDER BY QTD_EVENTOS DESC", f.vw_evento, d.vw_dim)
        janela = f" AND {D_dt} >= TRUNC(SYSDATE) - 90" if D else ""
        periodo = "nos últimos 90 dias" if D else "em todo o histórico"
        add("TATICA", f"Quais itens de {d.nome} não tiveram nenhum evento de {E} {periodo}?",
            f"SELECT d.{d.atributo} FROM {schema}.{d.vw_dim} d WHERE NOT EXISTS "
            f"(SELECT 1 FROM {ev} e WHERE e.{d.fk} = d.{d.sk}{janela}) ORDER BY d.{d.atributo}", d.vw_dim, f.vw_evento)
    for i, d1 in enumerate(f.dims):
        for d2 in f.dims[i + 1:i + 3]:
            add("TATICA", f"Como {E} se distribui cruzando {d1.nome} e {d2.nome}?",
                f"SELECT d1.{d1.atributo} AS {d1.atributo[:26]}_1, d2.{d2.atributo} AS {d2.atributo[:26]}_2, COUNT(1) AS QTD_EVENTOS "
                f"FROM {ev} e JOIN {schema}.{d1.vw_dim} d1 ON d1.{d1.sk} = e.{d1.fk} JOIN {schema}.{d2.vw_dim} d2 ON d2.{d2.sk} = e.{d2.fk} "
                f"GROUP BY d1.{d1.atributo}, d2.{d2.atributo} ORDER BY QTD_EVENTOS DESC FETCH FIRST 20 ROWS ONLY",
                f.vw_evento, d1.vw_dim, d2.vw_dim)
    if f.situacao == "FLAG":
        add("TATICA", f"Qual o percentual de eventos ativos de {E}?",
            f"SELECT ROUND(SUM(CASE WHEN e.IND_SITUACAO_EVENTO = 'ATIVO' THEN 1 ELSE 0 END) * 100 / NULLIF(COUNT(1), 0), 2) AS PCT_ATIVOS FROM {ev} e")
    elif f.situacao == "STATUS":
        add("TATICA", f"Como os eventos de {E} se distribuem por situação?",
            f"SELECT e.IND_SITUACAO_EVENTO, COUNT(1) AS QTD_EVENTOS, ROUND(COUNT(1) * 100 / NULLIF(SUM(COUNT(1)) OVER (), 0), 2) AS PCT "
            f"FROM {ev} e GROUP BY e.IND_SITUACAO_EVENTO ORDER BY QTD_EVENTOS DESC")
    if f.situacao and D:
        add("TATICA", f"Como a situação dos eventos de {E} evoluiu mês a mês?",
            f"SELECT TRUNC({D_dt}, 'MM') AS MES, e.IND_SITUACAO_EVENTO, COUNT(1) AS QTD_EVENTOS FROM {ev} e "
            f"GROUP BY TRUNC({D_dt}, 'MM'), e.IND_SITUACAO_EVENTO ORDER BY MES, QTD_EVENTOS DESC")
    if D:
        add("TATICA", f"Existe sazonalidade em {E}? Qual a média de eventos por mês do ano?",
            f"SELECT EXTRACT(MONTH FROM {D_dt}) AS MES_DO_ANO, ROUND(COUNT(1) / NULLIF(COUNT(DISTINCT EXTRACT(YEAR FROM {D_dt})), 0), 2) "
            f"AS MEDIA_EVENTOS FROM {ev} e GROUP BY EXTRACT(MONTH FROM {D_dt}) ORDER BY MES_DO_ANO")
        add("TATICA", f"Em quais dias da semana {E} mais acontece?",
            f"SELECT TO_CHAR({D_dt}, 'DY', 'NLS_DATE_LANGUAGE=PORTUGUESE') AS DIA_SEMANA, COUNT(1) AS QTD_EVENTOS FROM {ev} e "
            f"GROUP BY TO_CHAR({D_dt}, 'DY', 'NLS_DATE_LANGUAGE=PORTUGUESE') ORDER BY QTD_EVENTOS DESC")
    identificador = f.chave_degenerada or (f.dims[0].fk if f.dims else None)
    for col, nome in metricas[:2]:
        if identificador:
            add("TATICA", f"Quais eventos de {E} têm {nome} atípico (acima de 3 desvios-padrão da média)?",
                f"WITH s AS (SELECT AVG(e.{col}) AS MEDIA, STDDEV(e.{col}) AS DESVIO FROM {ev} e) "
                f"SELECT e.{identificador}, e.{col} FROM {ev} e CROSS JOIN s WHERE e.{col} > s.MEDIA + 3 * s.DESVIO "
                f"ORDER BY e.{col} DESC FETCH FIRST 50 ROWS ONLY")
        if D:
            add("TATICA", f"Qual a média móvel de 3 meses de {nome}?",
                f"WITH m AS (SELECT TRUNC({D_dt}, 'MM') AS MES, SUM(e.{col}) AS TOTAL FROM {ev} e GROUP BY TRUNC({D_dt}, 'MM')) "
                f"SELECT MES, TOTAL, ROUND(AVG(TOTAL) OVER (ORDER BY MES ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2) AS MEDIA_MOVEL_3M "
                f"FROM m ORDER BY MES")

    # ---------------- AUDITORIA ----------------
    for d in f.dims:
        add("AUDITORIA", f"Qual o percentual de eventos de {E} sem {d.nome} identificado (chave -1)?",
            f"SELECT ROUND(SUM(CASE WHEN e.{d.fk} = -1 THEN 1 ELSE 0 END) * 100 / NULLIF(COUNT(1), 0), 2) AS PCT_NAO_INFORMADO FROM {ev} e")
    for col, nome in metricas:
        add("AUDITORIA", f"Quantos eventos de {E} têm {nome} nulo ou negativo?",
            f"SELECT COUNT(1) AS QTD_INVALIDOS FROM {ev} e WHERE e.{col} IS NULL OR e.{col} < 0")
    if D:
        add("AUDITORIA", f"Existem eventos de {E} com data no futuro?",
            f"SELECT COUNT(1) AS QTD_DATA_FUTURA FROM {ev} e WHERE {D_dt} > SYSDATE")
        add("AUDITORIA", f"Qual a data do evento mais recente de {E} e há quantos dias foi registrado?",
            f"SELECT MAX({D_dt}) AS DATA_MAIS_RECENTE, TRUNC(SYSDATE) - TRUNC(MAX({D_dt})) AS DIAS_DESDE_ULTIMO FROM {ev} e")
    if f.chave_degenerada:
        k = f.chave_degenerada
        add("AUDITORIA", f"Existe duplicidade de {k} em {E}?",
            f"SELECT e.{k}, COUNT(1) AS QTD FROM {ev} e GROUP BY e.{k} HAVING COUNT(1) > 1 ORDER BY QTD DESC")
    add("AUDITORIA", f"O total da view de KPI de {E} confere com a contagem da view de eventos?",
        f"SELECT (SELECT SUM(QTD_TOTAL_REGISTROS) FROM {kpi}) - (SELECT COUNT(1) FROM {ev}) AS DIFERENCA FROM DUAL",
        f.vw_kpi, f.vw_evento)
    return out


def gerar_perguntas_ia(fatos: List[FatoPergunta], schema: str, projeto: str) -> List[PerguntaNegocio]:
    """Perguntas propostas pela IA, ordenadas por horizonte (Executiva, Tática, Auditoria)."""
    brutas = []
    for f in fatos:
        brutas.extend(_perguntas_do_fato(f, schema))
    ordem = {"EXECUTIVA": 0, "TATICA": 1, "AUDITORIA": 2}
    brutas.sort(key=lambda p: ordem[p[0]])
    vistas, perguntas = set(), []
    rotulo = {"EXECUTIVA": "Executiva/Estratégica", "TATICA": "Tática/Operacional", "AUDITORIA": "Auditoria/Qualidade"}
    for horiz, texto, sql, objs in brutas:
        if texto in vistas:
            continue
        vistas.add(texto)
        perguntas.append(PerguntaNegocio(
            id_consulta=f"PN_{projeto}_IA_{len(perguntas) + 1:03d}"[:50], pergunta=texto, sql=sql, objetos=objs,
            horizonte=horiz, origem="IA", observacao=f"Sugerida pela IA (não solicitada pelo cliente) — horizonte {rotulo[horiz]}.",
        ))
    return perguntas


# ----------------------------------------------------------------------------
# Perguntas do cliente (requisitos)
# ----------------------------------------------------------------------------
def ler_perguntas_cliente(*fontes: Path) -> List[str]:
    """
    Lê perguntas do cliente da Seção 5.1 do INTAKE_SEMANTICA.md e de arquivos opcionais
    (ex.: entrega/camada_semantica/perguntas_cliente.md, uma pergunta por item de lista).
    Ignora exemplos `[Ex: ...]` e reticências.
    """
    perguntas: List[str] = []
    for fonte in fontes:
        if not fonte or not Path(fonte).exists():
            continue
        texto = Path(fonte).read_text(encoding="utf-8", errors="replace")
        m = re.search(r"### 5\.1[^\n]*\n(.*?)(?=\n#{2,3} |\n---|\Z)", texto, re.DOTALL)
        trecho = m.group(1) if m else texto
        for linha in trecho.splitlines():
            item = re.match(r"^\s*(?:\d+[.)]|[-*])\s+(.+)$", linha)
            if not item:
                continue
            pergunta = item.group(1).strip().strip("`").strip()
            if not pergunta or pergunta.startswith("[") or pergunta in ("...", "…") or len(pergunta) < 8:
                continue
            if pergunta not in perguntas:
                perguntas.append(pergunta)
    return perguntas


def _palavras(texto: str) -> set:
    sem_acento = "".join(c for c in unicodedata.normalize("NFKD", texto.lower()) if not unicodedata.combining(c))
    return {p for p in re.findall(r"[a-z0-9]{4,}", sem_acento)}


def montar_perguntas_cliente(perguntas: List[str], perguntas_ia: List[PerguntaNegocio], projeto: str) -> List[PerguntaNegocio]:
    """Perguntas do cliente com a pergunta da IA mais parecida indicada como ponto de partida do SQL."""
    resultado = []
    for i, texto in enumerate(perguntas, start=1):
        alvo = _palavras(texto)
        melhor, nota = None, 0.0
        for p in perguntas_ia:
            cand = _palavras(p.pergunta)
            uniao = alvo | cand
            sim = len(alvo & cand) / len(uniao) if uniao else 0.0
            if sim > nota:
                melhor, nota = p, sim
        obs = "Pergunta do cliente (requisito). SQL a validar pelo engenheiro."
        if melhor and nota >= 0.15:
            obs += f" Ponto de partida sugerido: {melhor.id_consulta} ({melhor.pergunta})"
        resultado.append(PerguntaNegocio(
            id_consulta=f"PN_{projeto}_CLI_{i:03d}"[:50], pergunta=texto, sql="", objetos=melhor.objetos if melhor and nota >= 0.15 else "",
            horizonte="CLIENTE", origem="CLIENTE", observacao=obs,
        ))
    return resultado
