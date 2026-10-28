"""
Templates com cópia na skill devem ser idênticos à fonte única em modulos/.
Para corrigir uma divergência, edite o arquivo de modulos/ e copie-o para a skill.
"""

import pytest

from ninho_core.paths import BASE_DIR

PARES = [
    ("modulos/camada_semantica/templates/02_rls_template.sql",
     ".agents/skills/seguranca-rls-oracle/templates/template_rls_vpd.sql"),
    ("modulos/planejador_dw/templates/10_python_api_extractor_template.py",
     ".agents/skills/extrator-api-python/templates/template_extrator_api.py"),
    ("modulos/camada_semantica/templates/09_validacoes.sql",
     ".agents/skills/camada-semantica-oracle/templates/template_09_validacoes.sql"),
]


@pytest.mark.parametrize("fonte,copia", PARES)
def test_copia_da_skill_igual_a_fonte_unica(fonte, copia):
    assert (BASE_DIR / fonte).read_bytes() == (BASE_DIR / copia).read_bytes(), (
        f"{copia} divergiu de {fonte}. Edite a fonte em modulos/ e copie para a skill."
    )
