"""Chaque processus de production démarre avec son vrai modèle d'environnement (infra/compose/env/*.env.example).

Garde-fou de déploiement : un réglage exigé mais absent du modèle (clé, domaine) fait planter un conteneur au
démarrage, ce que ni les tests habituels (réglages de test) ni `docker compose config` ne voient.
"""

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

RACINE = Path(__file__).resolve().parents[5]
SERVEUR = RACINE / "serveur"
COMPOSE = RACINE / "infra" / "compose"
DOMAINE = "immoplus.exemple.bj"


def _outil_env():
    spec = importlib.util.spec_from_file_location("creer_env", RACINE / "outils" / "creer_env.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _services_django() -> list[tuple[str, str, str, dict]]:
    """(service, réglages, fichier d'environnement, variables du Compose) de chaque processus Django de production."""
    base = yaml.safe_load((COMPOSE / "docker-compose.yml").read_text(encoding="utf-8"))["services"]
    prod = yaml.load(
        (COMPOSE / "docker-compose.prod.yml").read_text(encoding="utf-8"), Loader=_ChargeurCompose
    )["services"]
    sortie = []
    for nom, svc in prod.items():
        environnement = svc.get("environment") or {}
        module = environnement.get("DJANGO_SETTINGS_MODULE")
        if module:
            fichier = base[nom]["env_file"][0]
            extra = {k: str(v) for k, v in environnement.items() if k != "DJANGO_SETTINGS_MODULE"}
            sortie.append((nom, module, fichier, extra))
    return sortie


class _ChargeurCompose(yaml.SafeLoader):
    """Accepte les étiquettes propres à Compose (`!override`, `!reset`)."""


_ChargeurCompose.add_multi_constructor(
    "!",
    lambda chargeur, _etiquette, noeud: (
        chargeur.construct_sequence(noeud)
        if isinstance(noeud, yaml.SequenceNode)
        else chargeur.construct_mapping(noeud)
        if isinstance(noeud, yaml.MappingNode)
        else chargeur.construct_scalar(noeud)
    ),
)


def _environnement(fichier: str) -> dict[str, str]:
    outil = _outil_env()
    valeurs = outil.generer(outil.lire_valeurs(RACINE / ".env.example"))
    valeurs.update(DOMAIN=DOMAINE, ADMIN_ALLOWED_IPS="203.0.113.7/32", SMS_PROVIDER="console")
    texte = outil.rendre((COMPOSE / f"{fichier}.example").read_text(encoding="utf-8"), valeurs)
    return dict(
        ligne.split("=", 1)
        for ligne in texte.splitlines()
        if ligne and not ligne.startswith("#") and "=" in ligne
    )


@pytest.mark.parametrize(
    "service,module,fichier,extra", _services_django(), ids=[s[0] for s in _services_django()]
)
def test_le_processus_demarre_avec_son_modele_d_environnement(service, module, fichier, extra):
    env = {
        "PATH": os.environ.get("PATH", ""),
        **_environnement(fichier),
        **extra,
        "DJANGO_SETTINGS_MODULE": module,
    }
    script = (
        "import django, json, sys; django.setup(); from django.conf import settings; "
        "sys.stdout.write(json.dumps({'hotes': settings.ALLOWED_HOSTS, 'debug': settings.DEBUG}))"
    )
    r = subprocess.run(
        [sys.executable, "-c", script],
        cwd=SERVEUR,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, f"{service} ({module}) ne démarre pas :\n{r.stderr[-1500:]}"
    reglages = json.loads(r.stdout.strip().splitlines()[-1])
    assert reglages["debug"] is False
    if module == "config.settings.public":
        assert {f"www.{DOMAINE}", f"api.{DOMAINE}"} <= set(reglages["hotes"])
    if module == "config.settings.admin":
        assert (
            f"pilotage.{DOMAINE}" in reglages["hotes"] and f"www.{DOMAINE}" not in reglages["hotes"]
        )
