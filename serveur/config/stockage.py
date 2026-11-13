"""Fichiers statiques versionnés : `/static/js/x.js?v=<empreinte>`.

Caddy sert `/static/` avec `Cache-Control: immutable` pour un an : sans version dans l'adresse, un navigateur qui a déjà
chargé un script ne voit jamais sa mise à jour. L'empreinte (contenu du fichier) change à chaque modification, donc
l'adresse aussi ; le fichier lui-même n'est pas renommé (rien à régénérer, les URL internes des CSS restent valables)."""

import hashlib
from functools import lru_cache

from django.contrib.staticfiles import finders
from django.contrib.staticfiles.storage import StaticFilesStorage


@lru_cache(maxsize=None)
def _empreinte(nom: str) -> str:
    chemin = finders.find(nom)
    if not chemin or not isinstance(chemin, str):
        return ""
    try:
        with open(chemin, "rb") as fichier:
            return hashlib.md5(fichier.read(), usedforsecurity=False).hexdigest()[:10]
    except OSError:
        return ""


class StatiquesVersionnes(StaticFilesStorage):
    def url(self, name):
        adresse = super().url(name)
        empreinte = _empreinte(name)
        return f"{adresse}?v={empreinte}" if empreinte else adresse
