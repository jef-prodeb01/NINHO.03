"""Testes dos utilitários compartilhados (ninho_core)."""

import xml.etree.ElementTree as ET

import pytest

from ninho_core import paths, xml_seguro

XML_BOMBA = b"""<?xml version="1.0"?>
<!DOCTYPE lolz [<!ENTITY lol "lol"><!ENTITY lol2 "&lol;&lol;&lol;">]>
<raiz>&lol2;</raiz>"""


def test_xml_valido_e_lido_normalmente():
    raiz = xml_seguro.fromstring("<pipeline><nome>ppl_carga</nome></pipeline>")
    assert raiz.find("nome").text == "ppl_carga"


def test_xml_com_entidades_e_bloqueado():
    with pytest.raises(ET.ParseError):
        xml_seguro.fromstring(XML_BOMBA)


def test_parse_de_arquivo_retorna_element_tree(tmp_path):
    arq = tmp_path / "mapa.xml"
    arq.write_text("<Mapping><Name>MAP_CARGA</Name></Mapping>", encoding="utf-8")
    assert xml_seguro.parse(arq).getroot().find("Name").text == "MAP_CARGA"


def test_zip_bomb_e_barrada(tmp_path):
    import zipfile

    from ninho_core.zip_seguro import ArquivoCompactadoSuspeito, ler_membro

    arq = tmp_path / "bomba.xlsx"
    with zipfile.ZipFile(arq, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("xl/sharedStrings.xml", b"0" * (2 * 1024 * 1024))  # ~2 KB compactado
    with zipfile.ZipFile(arq) as zf:
        assert len(ler_membro(zf, "xl/sharedStrings.xml")) == 2 * 1024 * 1024
        with pytest.raises(ArquivoCompactadoSuspeito):
            ler_membro(zf, "xl/sharedStrings.xml", limite=1024 * 1024)


def test_fichas_do_projeto_sao_restauradas_e_nao_apagadas(tmp_path):
    from ninho_core.catalogo import restaurar_fichas_projeto

    (tmp_path / "modelos").mkdir()
    for nome in ("PROJETO_RESUMO.md", "PROJETO_VERSION.md"):
        (tmp_path / "modelos" / nome).write_text("modelo em branco", encoding="utf-8")
        (tmp_path / nome).write_text("dados do projeto X", encoding="utf-8")
    assert restaurar_fichas_projeto(tmp_path) == 2
    assert (tmp_path / "PROJETO_RESUMO.md").read_text(encoding="utf-8") == "modelo em branco"
    assert restaurar_fichas_projeto(tmp_path) == 0


def test_raiz_do_projeto_contem_ninho_py():
    assert (paths.BASE_DIR / "ninho.py").exists()
    assert paths.ENTREGA_DIR.name == "entrega" and paths.SAIDA_DIR.name == "saida"
