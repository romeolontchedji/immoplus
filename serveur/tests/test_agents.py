"""AGENTS.md est la mémoire permanente du projet : il doit rester cohérent avec le dépôt."""

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unitaire
RACINE = Path(__file__).resolve().parents[2]
AGENTS = (RACINE / "AGENTS.md").read_text(encoding="utf-8")


def test_existe_court_et_mentionne_serveur():
    assert len(AGENTS.splitlines()) < 400
    assert "serveur/" in AGENTS


def test_claude_md_renvoie_vers_agents():
    assert (RACINE / "CLAUDE.md").read_text(encoding="utf-8").strip().startswith("Lis AGENTS.md")


def test_backend_seulement_dans_la_regle_qui_l_interdit():
    for numero, ligne in enumerate(AGENTS.splitlines(), 1):
        if re.search(r"backend/", ligne, re.IGNORECASE):
            assert (
                "interdit" in ligne.lower()
                or "jamais" in ligne.lower()
                or "créer un dossier" in ligne
            ), f"ligne {numero}"


def test_chaque_cible_make_citee_existe():
    makefile = (RACINE / "Makefile").read_text(encoding="utf-8")
    cibles = set(re.findall(r"^([a-z0-9-]+):", makefile, re.MULTILINE))
    citees = set(re.findall(r"`make ([a-z0-9-]+)`", AGENTS))
    tolerees = {"vendor"}
    citees_eff = citees - tolerees
    assert citees_eff, "aucune cible citée"
    assert citees_eff <= cibles, f"cibles absentes du Makefile : {sorted(citees_eff - cibles)}"


def test_les_cibles_obligatoires_sont_citees():
    obligatoires = {"up", "migrate", "seed", "css", "test", "lint", "test-unitaires", "test-integration",
                    "test-securite", "couverture", "verifier", "hooks", "openapi", "docs"}  # fmt: skip
    citees = set(re.findall(r"`make ([a-z0-9-]+)`", AGENTS))
    assert obligatoires <= citees, sorted(obligatoires - citees)


def test_regex_de_branche_identique_au_script():
    script = (RACINE / "outils" / "verifier_branche.py").read_text(encoding="utf-8")
    assert (
        "(main|(feat|fix|refactor|perf|test|docs|style|build|ci|chore|sec)/[a-z0-9]+(-[a-z0-9]+)*)"
        in script
    )
