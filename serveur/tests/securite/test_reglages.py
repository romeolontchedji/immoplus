"""Le démarrage échoue en production si DEBUG ou un secret de développement est présent."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.securite
SERVEUR = Path(__file__).resolve().parents[2]


def importer(module: str, **env) -> subprocess.CompletedProcess:
    propre = {
        k: v
        for k, v in os.environ.items()
        if k
        not in {
            "SECRET_KEY",
            "DEBUG",
            "JWT_SIGNING_KEY",
            "DOMAIN",
        }
    }
    return subprocess.run(
        [sys.executable, "-c", f"import {module}"],
        cwd=SERVEUR,
        env={**propre, "DOMAIN": "immoplus.exemple.bj", "CAPTCHA_PROVIDER": "turnstile", **env},
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize(
    "module", ["config.settings.public", "config.settings.admin", "config.settings.taches"]
)
class TestRefusEnProduction:
    def test_secret_absent(self, module):
        r = importer(module)
        assert r.returncode != 0 and "SECRET_KEY" in r.stderr

    def test_secret_de_developpement(self, module):
        r = importer(module, SECRET_KEY="dev-secret")
        assert r.returncode != 0 and "SECRET_KEY" in r.stderr

    def test_debug_actif(self, module):
        r = importer(module, SECRET_KEY="x" * 60, DEBUG="1")
        assert r.returncode != 0 and "DEBUG" in r.stderr

    def test_configuration_saine(self, module):
        r = importer(module, SECRET_KEY="x" * 60, JWT_SIGNING_KEY="y" * 60)
        assert r.returncode == 0, r.stderr


@pytest.mark.parametrize("module", ["config.settings.public", "config.settings.admin"])
@pytest.mark.parametrize("domaine", ["", "localhost"])
def test_domaine_de_production_obligatoire(module, domaine):
    r = importer(module, SECRET_KEY="x" * 60, JWT_SIGNING_KEY="y" * 60, DOMAIN=domaine)
    assert r.returncode != 0 and "DOMAIN" in r.stderr


def test_cookies_distincts_site_et_administration():
    site = importer(
        "config.settings.public",
        SECRET_KEY="a" * 60,
        JWT_SIGNING_KEY="b" * 60,
    )
    assert site.returncode == 0
    sortie = subprocess.run(
        [
            sys.executable,
            "-c",
            "import config.settings.public as p, config.settings.admin as a;"
            "import sys; sys.stdout.write(' '.join([p.SESSION_COOKIE_NAME, a.SESSION_COOKIE_NAME, p.SESSION_ENGINE, a.SESSION_ENGINE]))",
        ],
        cwd=SERVEUR,
        env={
            **os.environ,
            "DOMAIN": "immoplus.exemple.bj",
            "CAPTCHA_PROVIDER": "turnstile",
            "SECRET_KEY": "a" * 60,
            "JWT_SIGNING_KEY": "b" * 60,
        },
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    assert sortie[0] == "__Host-lgsid" and sortie[1] == "__Host-lgadm"
    assert sortie[2].endswith("cached_db")
    assert (
        sortie[3] == "adminsite.stockage_sessions"
    )  # table `admin_sessions`, jamais celle du site


CLES = {"SECRET_KEY": "a" * 60, "JWT_SIGNING_KEY": "b" * 60}


@pytest.mark.parametrize("cle", ["JWT_SIGNING_KEY"])
class TestClesDeSecurite:
    def test_absente(self, cle):
        r = importer("config.settings.public", **{k: v for k, v in CLES.items() if k != cle})
        assert r.returncode != 0 and cle in r.stderr

    def test_de_developpement(self, cle):
        r = importer("config.settings.public", **{**CLES, cle: "dev-quelque-chose"})
        assert r.returncode != 0 and cle in r.stderr

    def test_identique_a_une_autre_cle(self, cle):
        r = importer("config.settings.public", **{**CLES, cle: CLES["SECRET_KEY"]})
        assert r.returncode != 0 and "deux clés différentes" in r.stderr


def test_l_anti_robot_factice_est_refuse_en_production():
    r = importer(
        "config.settings.public",
        SECRET_KEY="x" * 60, JWT_SIGNING_KEY="y" * 60, CAPTCHA_PROVIDER="fake",
    )  # fmt: skip
    assert r.returncode != 0 and "CAPTCHA_PROVIDER" in r.stderr
