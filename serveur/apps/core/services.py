"""Services transverses : contrôle de disponibilité (base, Redis, disque)."""

import shutil

import redis
from django.conf import settings
from django.core.cache import cache
from django.db import connection


def _base() -> bool:
    with connection.cursor() as curseur:
        curseur.execute("SELECT 1")
        return curseur.fetchone() == (1,)


def _cache() -> bool:
    cache.set("readyz", "1", 5)
    return cache.get("readyz") == "1"


def _file() -> bool:
    return bool(redis.Redis.from_url(settings.REDIS_QUEUE_URL, socket_timeout=2).ping())


def _disque() -> bool:
    chemin = settings.MEDIA_ROOT
    chemin.mkdir(parents=True, exist_ok=True)
    usage = shutil.disk_usage(chemin)
    return usage.used / usage.total * 100 < settings.MEDIA_DISK_REFUS_POURCENT


CONTROLES = {"base": _base, "cache": _cache, "file": _file, "disque": _disque}


def verifier_disponibilite() -> dict[str, bool]:
    """Exécute chaque contrôle ; une exception vaut un échec (jamais de détail renvoyé)."""
    resultat = {}
    for nom, controle in CONTROLES.items():
        try:
            resultat[nom] = bool(controle())
        except Exception:  # noqa: BLE001 - tout échec = indisponible
            resultat[nom] = False
    return resultat
