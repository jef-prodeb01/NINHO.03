"""Regras de arquitetura da Fase 2 (desmembramento dos arquivos gigantes)."""

import ast
import importlib

import pytest

from ninho_core.paths import BASE_DIR

PASTA_CORE = BASE_DIR / "core" / "scripts_comuns" / "ninho_core"
SCRIPTS = {p.stem for p in (BASE_DIR / "core" / "scripts_comuns").glob("*.py")}


@pytest.mark.parametrize("modulo", sorted(p.name for p in PASTA_CORE.glob("*.py")))
def test_ninho_core_nao_depende_dos_scripts(modulo):
    """ninho_core é a base: nunca importa os scripts de core/scripts_comuns (evita ciclos)."""
    arvore = ast.parse((PASTA_CORE / modulo).read_text(encoding="utf-8"))
    importados = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            importados.update(a.name.split(".")[0] for a in no.names)
        elif isinstance(no, ast.ImportFrom) and no.module and no.level == 0:
            importados.add(no.module.split(".")[0])
    assert not (importados & SCRIPTS), f"{modulo} importa script(s) de nível superior: {importados & SCRIPTS}"


@pytest.mark.parametrize(
    "fachada,nomes",
    [
        ("gerador_artefatos_visuais", ["gerar_mockup_painel_bi_svg", "exportar_markdown_para_pdf", "gerar_planilha_indicadores_xlsx",
                                       "avaliar_medidas_guia_bi_amostra", "gerar_svg_canvas_hop", "mascarar_pii_texto", "ler_planilha_ods"]),
        ("melhorar_dw_existente", ["construir_scripts_odi", "construir_guia_bi_rapido", "construir_dicionario_html",
                                   "identificar_fks_fato", "abreviar_identificador_odi"]),
        ("auditar_esteira_hop", ["gerar_pacote_hop_completo", "migrar_kettle_para_hop", "audit_hop_directory"]),
    ],
)
def test_fachadas_mantem_nomes_antigos(fachada, nomes):
    modulo = importlib.import_module(fachada)
    faltando = [n for n in nomes if not hasattr(modulo, n)]
    assert not faltando, f"{fachada} perdeu: {faltando}"


@pytest.mark.parametrize("arquivo,limite", [
    ("gerador_artefatos_visuais.py", 400),
    ("melhorar_dw_existente.py", 700),
])
def test_arquivos_desmembrados_nao_voltam_a_crescer(arquivo, limite):
    linhas = (BASE_DIR / "core" / "scripts_comuns" / arquivo).read_text(encoding="utf-8").count("\n")
    assert linhas <= limite, f"{arquivo} tem {linhas} linhas (limite {limite}): coloque código novo em ninho_core/"
