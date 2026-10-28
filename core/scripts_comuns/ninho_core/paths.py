"""Caminhos canônicos do NINHO (raiz do projeto e pastas oficiais)."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]
ENTREGA_DIR = BASE_DIR / "entrega"
SAIDA_DIR = BASE_DIR / "saida"
MODULOS_DIR = BASE_DIR / "modulos"
DOCUMENTACAO_DIR = BASE_DIR / "documentacao"


def get_base_dir() -> Path:
    """Retorna o diretório raiz do projeto NINHO."""
    return BASE_DIR
