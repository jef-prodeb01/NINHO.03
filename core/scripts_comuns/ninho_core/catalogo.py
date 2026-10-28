"""
Ficha do projeto ativo em `documentacao/catalogo_projetos/` (PROJETO_RESUMO.md e PROJETO_VERSION.md).

Esses dois arquivos são versionados no estado "projeto não inicializado" e reescritos durante um
projeto. Limpezas (/limpar-demo, --resetar, suíte de testes) devem RESTAURAR o modelo em branco de
`catalogo_projetos/modelos/`, nunca apagar os arquivos.
"""

import shutil
from pathlib import Path

from ninho_core.paths import DOCUMENTACAO_DIR

CATALOGO_DIR = DOCUMENTACAO_DIR / "catalogo_projetos"
MODELOS_DIR = CATALOGO_DIR / "modelos"
ARQUIVOS_FICHA = ("PROJETO_RESUMO.md", "PROJETO_VERSION.md")


def fichas_modificadas(catalogo_dir: Path = CATALOGO_DIR) -> list:
    """Fichas que diferem do modelo em branco (ou seja, contêm dados de um projeto)."""
    alterados = []
    for nome in ARQUIVOS_FICHA:
        atual, modelo = catalogo_dir / nome, catalogo_dir / "modelos" / nome
        if modelo.exists() and (not atual.exists() or atual.read_bytes() != modelo.read_bytes()):
            alterados.append(atual)
    return alterados


def restaurar_fichas_projeto(catalogo_dir: Path = CATALOGO_DIR) -> int:
    """Restaura as fichas do modelo em branco. Retorna quantas foram restauradas."""
    alterados = fichas_modificadas(catalogo_dir)
    for atual in alterados:
        shutil.copyfile(catalogo_dir / "modelos" / atual.name, atual)
    return len(alterados)
