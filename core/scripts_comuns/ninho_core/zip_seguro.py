"""
Leitura segura de membros de arquivos ZIP enviados por clientes (.xlsx, .ods, .docx, .odt, .pbix).

Protege contra "zip bombs": o tamanho descompactado é verificado pelo cabeçalho E durante a
leitura (em blocos), então um cabeçalho falsificado também é barrado.
"""

import zipfile

LIMITE_MEMBRO_BYTES = 256 * 1024 * 1024  # 256 MB por membro (layouts de .pbix grandes cabem com folga)
_BLOCO = 1024 * 1024


class ArquivoCompactadoSuspeito(ValueError):
    """Membro do ZIP maior que o limite permitido (possível zip bomb)."""


def ler_membro(zf: zipfile.ZipFile, nome: str, limite: int = LIMITE_MEMBRO_BYTES) -> bytes:
    """Equivalente seguro de `zf.read(nome)`."""
    info = zf.getinfo(nome)
    if info.file_size > limite:
        raise ArquivoCompactadoSuspeito(f"'{nome}' declara {info.file_size} bytes descompactados (limite {limite}).")
    partes, total = [], 0
    with zf.open(info) as membro:
        while True:
            bloco = membro.read(_BLOCO)
            if not bloco:
                break
            total += len(bloco)
            if total > limite:
                raise ArquivoCompactadoSuspeito(f"'{nome}' excede {limite} bytes ao descompactar.")
            partes.append(bloco)
    return b"".join(partes)
