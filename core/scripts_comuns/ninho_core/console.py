"""
Saída de console padronizada dos motores do NINHO.

As cores ANSI só são usadas quando a saída é um terminal interativo. Em pipes,
arquivos de log e no chat das IDEs agênticas (que capturam a saída do comando)
os códigos de escape viram ruído como "[93m[AVISO][0m", então ficam desligados.
Também respeitam as convenções NO_COLOR (desliga) e FORCE_COLOR (liga).
"""

import os
import sys


def _cores_habilitadas() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def configurar_saida_utf8() -> None:
    """Garante UTF-8 no stdout/stderr (consoles Windows usam cp1252 por padrão)."""
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, "reconfigure"):
            try:
                fluxo.reconfigure(encoding="utf-8", errors="replace")
            except Exception:  # fluxo já fechado ou substituído (ex.: pytest capture)
                pass


CORES_ATIVAS = _cores_habilitadas()

VERDE = "\033[92m" if CORES_ATIVAS else ""
AMARELO = "\033[93m" if CORES_ATIVAS else ""
VERMELHO = "\033[91m" if CORES_ATIVAS else ""
AZUL = "\033[94m" if CORES_ATIVAS else ""
CIANO = "\033[96m" if CORES_ATIVAS else ""
NEGRITO = "\033[1m" if CORES_ATIVAS else ""
RESET = "\033[0m" if CORES_ATIVAS else ""


def print_ok(msg: str) -> None:
    print(f"  {VERDE}[OK]{RESET} {msg}")


def print_warn(msg: str) -> None:
    print(f"  {AMARELO}[AVISO]{RESET} {msg}")


def print_err(msg: str) -> None:
    print(f"  {VERMELHO}[ERRO]{RESET} {msg}")
