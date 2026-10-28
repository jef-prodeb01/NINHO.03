"""Catálogo de perguntas de negócio (META_CONSULTA_NEGOCIO): mínimo de 30 da IA + perguntas do cliente."""

import re
from collections import Counter

from inspecionar_ddl_origem import parse_ddl_text
from modular_semantica import construir_catalogo_meta, construir_perguntas_negocio
from ninho_core.perguntas_semanticas import MINIMO_PERGUNTAS_IA, ler_perguntas_cliente
from simular_projeto import _converter_oltp_para_dw_se_necessario
from testar_ninho import DDL_ORIGEM_TESTE

INTAKE = """
### 5.1 Lista de Perguntas Solicitadas pelo Cliente
1. `[Ex: Qual o percentual de cumprimento de SLA por módulo no último ciclo?]`
2. Qual o valor total de contratos assinados por órgão público no ano?
3. Quais fornecedores tiveram mais contratos nos últimos 12 meses?
4. `...`

---
"""


def _tabelas():
    return _converter_oltp_para_dw_se_necessario(parse_ddl_text(DDL_ORIGEM_TESTE, "x.sql"))


def test_ia_gera_no_minimo_30_perguntas_nos_3_horizontes(tmp_path):
    ia, _ = construir_perguntas_negocio(_tabelas(), "DW", "GLD", fontes_cliente=[])
    assert len(ia) >= MINIMO_PERGUNTAS_IA
    horizontes = Counter(p.horizonte for p in ia)
    assert set(horizontes) == {"EXECUTIVA", "TATICA", "AUDITORIA"}
    assert len({p.pergunta for p in ia}) == len(ia), "perguntas duplicadas"
    assert all(p.origem == "IA" and p.sql for p in ia)


def test_sql_usa_so_views_semanticas_e_sem_select_estrela():
    ia, _ = construir_perguntas_negocio(_tabelas(), "DW", "GLD", fontes_cliente=[])
    for p in ia:
        assert "SELECT *" not in p.sql.upper(), p.id_consulta
        tabelas_lidas = set(re.findall(r"(?:FROM|JOIN)\s+DW\.(\w+)", p.sql))
        assert tabelas_lidas and all(t.startswith("VW_GLD_") for t in tabelas_lidas), (p.id_consulta, tabelas_lidas)
        assert p.sql.count("(") == p.sql.count(")"), p.id_consulta


def test_perguntas_do_modelo_usam_nomes_reais():
    ia, _ = construir_perguntas_negocio(_tabelas(), "DW", "GLD", fontes_cliente=[])
    textos = " ".join(p.pergunta for p in ia)
    assert "valor contrato" in textos and "Orgao Publico" in textos.replace("Órgão", "Orgao").replace("Público", "Publico")
    assert any("DTC_ASSINATURA" in p.sql or "DIM_TEMPO" in p.sql for p in ia), "eixo temporal real não usado"


def test_perguntas_do_cliente_sao_lidas_sem_exemplos(tmp_path):
    intake = tmp_path / "INTAKE_SEMANTICA.md"
    intake.write_text(INTAKE, encoding="utf-8")
    assert ler_perguntas_cliente(intake) == [
        "Qual o valor total de contratos assinados por órgão público no ano?",
        "Quais fornecedores tiveram mais contratos nos últimos 12 meses?",
    ]
    _, cliente = construir_perguntas_negocio(_tabelas(), "DW", "GLD", fontes_cliente=[intake])
    assert [p.id_consulta for p in cliente] == ["PN_GLD_CLI_001", "PN_GLD_CLI_002"]
    assert all("Ponto de partida sugerido: PN_GLD_IA_" in p.observacao for p in cliente)


def test_catalogo_meta_inclui_ia_e_cliente(tmp_path, monkeypatch):
    import modular_semantica

    intake = tmp_path / "INTAKE_SEMANTICA.md"
    intake.write_text(INTAKE, encoding="utf-8")
    original = modular_semantica.construir_perguntas_negocio
    monkeypatch.setattr(
        modular_semantica, "construir_perguntas_negocio",
        lambda t, s, p, e=None, fontes_cliente=None: original(t, s, p, e, fontes_cliente=[intake]),
    )
    sql = construir_catalogo_meta(_tabelas(), "DW", "GLD")["06_meta_consulta_negocio.sql"]
    assert sql.count("MERGE INTO DW.META_CONSULTA_NEGOCIO") >= MINIMO_PERGUNTAS_IA + 2
    assert "PN_GLD_CLI_002" in sql and "NULL AS SQL_VALIDADO_INTERPRETACAO" in sql
