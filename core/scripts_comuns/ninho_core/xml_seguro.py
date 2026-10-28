"""
Leitura segura de XML enviado por clientes (ODI 12c, Apache Hop, PBIX, DOCX/XLSX/ODS).

Usa `defusedxml` quando instalado. Sem ele, bloqueia declarações `<!ENTITY`, que são
o vetor de ataques de expansão de entidades ("billion laughs") e XXE. Em ambos os
casos o erro é levantado como `xml.etree.ElementTree.ParseError`, que os motores já
tratam como "XML inválido".
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Union

try:
    import defusedxml.ElementTree as _defused
    from defusedxml import DefusedXmlException as _ErroDefused
except ImportError:  # dependência opcional
    _defused = None
    _ErroDefused = ()

_MARCADOR_ENTIDADE = b"<!ENTITY"


def _bloquear_entidades(dados: bytes) -> None:
    if _MARCADOR_ENTIDADE in dados.upper():
        raise ET.ParseError("XML com declaração <!ENTITY bloqueado por segurança (expansão de entidades/XXE).")


def fromstring(texto: Union[str, bytes]) -> ET.Element:
    """Equivalente seguro de `ET.fromstring`."""
    dados = texto.encode("utf-8") if isinstance(texto, str) else bytes(texto)
    if _defused is not None:
        try:
            return _defused.fromstring(dados)
        except _ErroDefused as exc:
            raise ET.ParseError(str(exc)) from exc
    _bloquear_entidades(dados)
    return ET.fromstring(dados)


def parse(origem: Union[str, Path]) -> ET.ElementTree:
    """Equivalente seguro de `ET.parse` para caminhos de arquivo."""
    return ET.ElementTree(fromstring(Path(origem).read_bytes()))
