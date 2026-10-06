"""Fixtures racine : CSS construit, clients de test. Complétées à chaque phase (CDC §12 bis)."""

import sys
from pathlib import Path

import pytest

RACINE_DEPOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE_DEPOT / "outils"))


@pytest.fixture(scope="session", autouse=True)
def css_construit():
    """Le site exige le CSS empreinté : on le construit une fois par session de test."""
    import construire_css

    construire_css.construire()
    from web.templatetags import logeo

    logeo._manifeste.cache_clear()
