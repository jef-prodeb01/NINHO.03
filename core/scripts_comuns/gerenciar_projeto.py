#!/usr/bin/env python3
"""
Utilitário de Ciclo de Vida do Projeto NINHO (Empacotamento e Reset de Workspace).

Resolve o problema de reutilização do repositório template:
1. --status:   Lista todos os artefatos gerados atualmente em `saida/` e `entrega/`.
2. --exportar: Empacota todos os artefatos gerados (`saida/`, `entrega/`, `INTAKE_*.md`,
               `PROJETO_*.md` e `documentacao/catalogo_projetos/`) em uma pasta dedicada
               e gera um arquivo `.zip` pronto para entrega/versionamento do cliente.
3. --resetar:  Limpa os arquivos gerados em `saida/` e `entrega/` preservando intacta a
               estrutura de pastas (`.gitkeep` e `README.md`), deixando o template limpo
               para o próximo projeto.

Uso:
    python core/scripts_comuns/gerenciar_projeto.py --status
    python core/scripts_comuns/gerenciar_projeto.py --exportar ../entregas_clientes --projeto SEIBAHIA
    python core/scripts_comuns/gerenciar_projeto.py --resetar --confirmar
"""

import argparse
import datetime
import os
import shutil
import sys
import zipfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent.parent.parent

PRESERVED_FILENAMES = {".gitkeep", "README.md"}

TARGET_DIRS = [
    BASE_DIR / "saida",
    BASE_DIR / "entrega",
]

MODULE_FORM_FILES = [
    BASE_DIR / "modulos" / "planejador_dw" / "INTAKE_DW.md",
    BASE_DIR / "modulos" / "planejador_dw" / "PROJETO_DW.md",
    BASE_DIR / "modulos" / "camada_semantica" / "INTAKE_SEMANTICA.md",
    BASE_DIR / "modulos" / "camada_semantica" / "PROJETO_SEMANTICA.md",
    BASE_DIR / "modulos" / "governanca_dados" / "INTAKE_GOVERNANCA.md",
    BASE_DIR / "modulos" / "governanca_dados" / "PROJETO_GOVERNANCA.md",
]


def listar_arquivos_gerados() -> dict[str, list[Path]]:
    """Retorna os arquivos de projeto presentes em `saida/` e `entrega/` (exceto .gitkeep e README.md)."""
    resultado: dict[str, list[Path]] = {"saida": [], "entrega": []}
    for chave, pasta_raiz in [("saida", BASE_DIR / "saida"), ("entrega", BASE_DIR / "entrega")]:
        if not pasta_raiz.exists():
            continue
        for root, _, files in os.walk(pasta_raiz):
            for f in sorted(files):
                if f in PRESERVED_FILENAMES:
                    continue
                resultado[chave].append(Path(root) / f)
    return resultado


def exibir_status() -> int:
    """Exibe o inventário atual do workspace."""
    gerados = listar_arquivos_gerados()
    total_saida = len(gerados["saida"])
    total_entrega = len(gerados["entrega"])

    print("=" * 72)
    print("📦 STATUS DO WORKSPACE — CICLO DE VIDA DO PROJETO (NINHO)")
    print("=" * 72)
    print(f"  • Artefatos gerados em `saida/`  : {total_saida} arquivo(s)")
    for p in gerados["saida"][:25]:
        print(f"      - {p.relative_to(BASE_DIR).as_posix()}")
    if total_saida > 25:
        print(f"      ... e mais {total_saida - 25} arquivo(s).")

    print(f"\n  • Insumos presentes em `entrega/`: {total_entrega} arquivo(s)")
    for p in gerados["entrega"][:25]:
        print(f"      - {p.relative_to(BASE_DIR).as_posix()}")
    if total_entrega > 25:
        print(f"      ... e mais {total_entrega - 25} arquivo(s).")

    print("=" * 72)
    if total_saida == 0 and total_entrega == 0:
        print("✅ O workspace está limpo (modo Template pronto para novo projeto).")
    else:
        print("💡 Dica: Use `--exportar <destino> --projeto <SIGLA>` para empacotar a entrega")
        print("         ou `--resetar --confirmar` para limpar `saida/` e `entrega/`.")
    return 0


def exportar_projeto(destino_base: str, sigla_projeto: str) -> int:
    """Exporta todos os artefatos de `saida/`, `entrega/` e formulários para uma pasta e arquivo .zip."""
    gerados = listar_arquivos_gerados()
    total_arquivos = len(gerados["saida"]) + len(gerados["entrega"])

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    sigla_limpa = "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in sigla_projeto.upper())
    nome_pacote = f"PACOTE_{sigla_limpa}_{timestamp}"

    pasta_destino_raiz = Path(destino_base).resolve()
    pasta_pacote = pasta_destino_raiz / nome_pacote
    pasta_pacote.mkdir(parents=True, exist_ok=True)

    copiados = 0

    # 1. Copiar arquivos gerados em saida/ e entrega/
    for chave in ("saida", "entrega"):
        for caminho_origem in gerados[chave]:
            rel = caminho_origem.relative_to(BASE_DIR)
            caminho_dest = pasta_pacote / rel
            caminho_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(caminho_origem, caminho_dest)
            copiados += 1

    # 2. Copiar formulários INTAKE e PROJETO preenchidos
    for form in MODULE_FORM_FILES:
        if form.exists():
            rel = form.relative_to(BASE_DIR)
            caminho_dest = pasta_pacote / rel
            caminho_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(form, caminho_dest)
            copiados += 1

    # 3. Copiar fichas do catálogo de projetos (exceto template base)
    pasta_catalogo = BASE_DIR / "documentacao" / "catalogo_projetos"
    if pasta_catalogo.exists():
        for arq in pasta_catalogo.glob("*.md"):
            if arq.name in ("README.md", "TEMPLATE_FICHA_PROJETO.md"):
                continue
            rel = arq.relative_to(BASE_DIR)
            caminho_dest = pasta_pacote / rel
            caminho_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(arq, caminho_dest)
            copiados += 1

    # 4. Compactar em .zip
    arquivo_zip = pasta_destino_raiz / f"{nome_pacote}.zip"
    with zipfile.ZipFile(arquivo_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(pasta_pacote):
            for f in files:
                abs_path = Path(root) / f
                rel_path = abs_path.relative_to(pasta_pacote)
                zf.write(abs_path, rel_path.as_posix())

    print("=" * 72)
    print(f"✅ PROJETO '{sigla_limpa}' EXPORTADO COM SUCESSO!")
    print("=" * 72)
    print(f"  📂 Pasta do Pacote : {pasta_pacote}")
    print(f"  🗜️  Arquivo ZIP     : {arquivo_zip}")
    print(f"  📄 Total Copiado   : {copiados} arquivo(s) ({total_arquivos} de saida/entrega + formulários)")
    print("=" * 72)
    return 0


def resetar_workspace(confirmar: bool, manter_entrega: bool = False) -> int:
    """Remove os arquivos gerados em `saida/` (e opcionalmente `entrega/`), preservando .gitkeep e README.md."""
    gerados = listar_arquivos_gerados()
    alvos = list(gerados["saida"])
    if not manter_entrega:
        alvos.extend(gerados["entrega"])

    if not alvos:
        print("✅ Nenhum arquivo gerado para remover. O workspace já está limpo.")
        return 0

    if not confirmar:
        print("⚠️  MODO SIMULAÇÃO (Dry-Run) — Nenhum arquivo foi apagado.")
        print(f"   Seriam removidos {len(alvos)} arquivo(s):")
        for p in alvos[:30]:
            print(f"     - {p.relative_to(BASE_DIR).as_posix()}")
        if len(alvos) > 30:
            print(f"     ... e mais {len(alvos) - 30} arquivo(s).")
        print("\n👉 Para executar a limpeza de fato, adicione a flag `--confirmar`.")
        return 0

    removidos = 0
    for caminho in alvos:
        try:
            caminho.unlink()
            removidos += 1
        except OSError as exc:
            print(f"❌ Erro ao remover {caminho}: {exc}")

    # Remover eventuais subpastas vazias não-canônicas que não contenham .gitkeep ou README.md
    for pasta_raiz in TARGET_DIRS:
        if manter_entrega and pasta_raiz.name == "entrega":
            continue
        for root, dirs, files in os.walk(pasta_raiz, topdown=False):
            caminho_dir = Path(root)
            if caminho_dir == pasta_raiz:
                continue
            if not any(caminho_dir.iterdir()):
                try:
                    caminho_dir.rmdir()
                except OSError:
                    pass

    print("=" * 72)
    print(f"🧹 WORKSPACE RESETADO COM SUCESSO! ({removidos} arquivo(s) removido(s))")
    print("   Estrutura de pastas (.gitkeep e README.md) preservada intacta.")
    print("=" * 72)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Gerenciador de Ciclo de Vida do Projeto NINHO (Status, Exportação e Reset)."
    )
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument(
        "--status",
        action="store_true",
        help="Exibe o inventário de arquivos gerados em saida/ e entrega/.",
    )
    grupo.add_argument(
        "--exportar",
        metavar="DESTINO",
        help="Diretório de destino onde o pacote do projeto e o .zip serão gerados.",
    )
    grupo.add_argument(
        "--resetar",
        action="store_true",
        help="Limpa os artefatos gerados em saida/ e entrega/ preservando .gitkeep e README.md.",
    )

    parser.add_argument(
        "--projeto",
        default="PROJETO_DW",
        help="Sigla do projeto ao usar --exportar (padrão: PROJETO_DW).",
    )
    parser.add_argument(
        "--confirmar",
        action="store_true",
        help="Confirma a exclusão física dos arquivos ao usar --resetar.",
    )
    parser.add_argument(
        "--manter-entrega",
        action="store_true",
        help="Ao usar --resetar, limpa apenas `saida/` e preserva os insumos de `entrega/`.",
    )

    args = parser.parse_args()

    if args.status:
        return exibir_status()
    if args.exportar:
        return exportar_projeto(args.exportar, args.projeto)
    if args.resetar:
        return resetar_workspace(args.confirmar, args.manter_entrega)
    return 0


if __name__ == "__main__":
    sys.exit(main())

