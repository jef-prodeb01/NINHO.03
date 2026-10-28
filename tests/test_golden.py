"""
Golden files: o SQL gerado para um DDL de referência é congelado em tests/golden/.

Qualquer mudança no texto gerado (DW, ODI, Camada Semântica, RLS, META_*) quebra este teste e
aparece como diff. Se a mudança for intencional, regenere e revise o diff no commit:

    NINHO_ATUALIZAR_GOLDEN=1 pytest tests/test_golden.py      (Linux/macOS)
    $env:NINHO_ATUALIZAR_GOLDEN=1; pytest tests/test_golden.py (PowerShell)
"""

import os
import re
from pathlib import Path

import pytest

import simular_projeto
from inspecionar_ddl_origem import parse_ddl_text
from melhorar_dw_existente import construir_scripts_odi
from modular_semantica import (
    construir_catalogo_meta,
    construir_script_rls,
    construir_script_validacoes_semantica,
    construir_views_dim_atuais,
    construir_views_eventos,
    construir_views_kpis,
)
from testar_ninho import DDL_ORIGEM_TESTE

PASTA_GOLDEN = Path(__file__).parent / "golden"
ATUALIZAR = os.environ.get("NINHO_ATUALIZAR_GOLDEN") == "1"
_DATAS = [
    (re.compile(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(:\d{2})?"), "<DATA_HORA>"),
    (re.compile(r"\d{2}/\d{2}/\d{4}( \d{2}:\d{2}(:\d{2})?)?"), "<DATA_HORA>"),
    (re.compile(r"\b\d{4}-\d{2}-\d{2}\b"), "<DATA>"),
]


def _normalizar(texto: str) -> str:
    for padrao, marcador in _DATAS:
        texto = padrao.sub(marcador, texto)
    return texto.replace("\r\n", "\n")


def _artefatos(tmp_path, monkeypatch) -> dict:
    tabelas = simular_projeto._converter_oltp_para_dw_se_necessario(parse_ddl_text(DDL_ORIGEM_TESTE, "golden.sql"))
    monkeypatch.setattr(simular_projeto, "SAIDA_DW_DIR", tmp_path)
    arquivos = simular_projeto._gerar_scripts_ddl_completos_dw(
        tabelas, schema_dw="DW_GLD", schema_stg="STG_GLD", projeto="GLD", ts_dat="GLD_DATA", ts_idx="GLD_INDEX",
        entregaveis={"01_tablespaces", "02_staging", "03_dimensoes_ddl", "04_fatos_ddl", "05_sequences"},
    )
    saida = {f"dw__{p.relative_to(tmp_path).as_posix().replace('/', '__')}": p.read_text(encoding="utf-8") for p in arquivos}

    dims = [t for t in tabelas if t["nome_tabela"].startswith("DIM_")]
    fatos = [t for t in tabelas if t["nome_tabela"].startswith("FATO_")]
    odi_ddl, odi_dims, odi_fato = construir_scripts_odi(dims, fatos, [], schema="DW_GLD", projeto="GLD", estrategia="A", schema_stg="STG_GLD")
    saida.update({"odi__ddl.sql": odi_ddl, "odi__dims.sql": odi_dims, "odi__fato.sql": odi_fato})

    saida["sem__01_vw_dim.sql"] = construir_views_dim_atuais(tabelas, "DW_GLD", "GLD")
    saida["sem__02_vw_evento.sql"] = construir_views_eventos(tabelas, "DW_GLD", "GLD")
    saida["sem__03_vw_kpi.sql"] = construir_views_kpis(tabelas, "DW_GLD", "GLD")
    saida["sem__02_rls.sql"] = construir_script_rls(tabelas, "DW_GLD", "GLD")
    saida["sem__09_validacoes.sql"] = construir_script_validacoes_semantica(tabelas, "DW_GLD", "GLD")
    for nome, conteudo in construir_catalogo_meta(tabelas, "DW_GLD", "GLD").items():
        saida[f"meta__{nome}"] = conteudo
    return {nome: _normalizar(texto) for nome, texto in saida.items()}


def test_sql_gerado_igual_ao_golden(tmp_path, monkeypatch):
    artefatos = _artefatos(tmp_path, monkeypatch)
    assert len(artefatos) >= 15

    if ATUALIZAR:
        PASTA_GOLDEN.mkdir(exist_ok=True)
        for antigo in PASTA_GOLDEN.glob("*"):
            antigo.unlink()
        for nome, texto in artefatos.items():
            (PASTA_GOLDEN / nome).write_text(texto, encoding="utf-8", newline="\n")
        pytest.skip(f"Golden files regenerados ({len(artefatos)}). Revise o diff antes do commit.")

    esperados = {p.name for p in PASTA_GOLDEN.glob("*")}
    assert esperados == set(artefatos), (
        f"Conjunto de artefatos mudou. Novos: {sorted(set(artefatos) - esperados)}; "
        f"removidos: {sorted(esperados - set(artefatos))}"
    )
    divergentes = [
        nome for nome, texto in artefatos.items()
        if (PASTA_GOLDEN / nome).read_text(encoding="utf-8") != texto
    ]
    assert not divergentes, f"SQL gerado mudou em: {divergentes}. Se for intencional, regenere com NINHO_ATUALIZAR_GOLDEN=1."
