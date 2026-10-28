"""Garante que o dispatcher ninho.py, os scripts e as skills de comando estejam coerentes."""

import subprocess
import sys

import ninho


def test_toda_rota_aponta_para_script_existente():
    for cmd, (script, _, _) in ninho.ROTAS_COMANDOS.items():
        if script.startswith("__"):
            continue
        assert (ninho.SCRIPTS_DIR / script).exists(), f"/{cmd} aponta para script inexistente: {script}"


def test_toda_skill_de_comando_tem_rota_no_dispatcher():
    for cmd in ninho.DESCRICOES_SKILLS_SLASH:
        assert cmd in ninho.ROTAS_COMANDOS, f"Skill /{cmd} sem rota em ROTAS_COMANDOS"


def test_skills_de_comando_instaladas_existem():
    for cmd in ninho.DESCRICOES_SKILLS_SLASH:
        if cmd in ninho.COMANDOS_RESERVADOS_IDE:
            continue
        assert (ninho.SKILLS_DIR / cmd / "SKILL.md").exists(), f"Skill /{cmd} não instalada; rode: python ninho.py instalar-comandos"


def test_skills_arquiteturais_existem():
    for skill in ninho.SKILLS_ARQUITETURAIS_PROTEGIDAS:
        assert (ninho.SKILLS_DIR / skill / "SKILL.md").exists(), f"Skill arquitetural ausente: {skill}"


def test_comando_desconhecido_retorna_erro_e_sugere_parecido():
    proc = subprocess.run(
        [sys.executable, str(ninho.ROOT_DIR / "ninho.py"), "simular-dww"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.returncode == 1
    assert "simular-dw" in proc.stdout
