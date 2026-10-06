"""Lecture des variables d'environnement (un fichier d'environnement par service)."""

import os

_VRAI = {"1", "true", "vrai", "oui", "yes", "on"}


def texte(nom: str, defaut: str = "") -> str:
    return os.environ.get(nom, defaut)


def booleen(nom: str, defaut: bool = False) -> bool:
    valeur = os.environ.get(nom)
    if valeur is None:
        return defaut
    return valeur.strip().lower() in _VRAI


def entier(nom: str, defaut: int = 0) -> int:
    valeur = os.environ.get(nom)
    return int(valeur) if valeur not in (None, "") else defaut


def liste(nom: str, defaut: str = "") -> list[str]:
    return [x.strip() for x in os.environ.get(nom, defaut).split(",") if x.strip()]
