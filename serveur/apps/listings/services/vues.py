"""Comptage des vues d'annonces (CDC §11.6, EF-DSH-04) : déduplication Redis (26 h) puis UPSERT toutes les 5 minutes."""

import re
import uuid

import redis

from apps.core import redis_file, stats

EXPIRATION_VISITEUR_S = 26 * 3600
_ROBOTS = re.compile(
    r"bot|crawl|spider|slurp|preview|facebookexternalhit|headless|curl|python-requests", re.I
)
PREFIXE_JOUR = "vues:jour:"
PREFIXE_VIDAGE = "vues:vidage:"


def est_robot(user_agent: str | None) -> bool:
    return bool(_ROBOTS.search(user_agent or ""))


def enregistrer(
    annonce_id, visiteur: str, *, user_agent: str | None = None, proprietaire: bool = False
) -> bool:
    """Compte une vue unique par visiteur, annonce et jour. Propriétaire et robots exclus. Retourne vrai si comptée."""
    if proprietaire or est_robot(user_agent) or not visiteur:
        return False
    r = redis_file.client()
    jour = stats.jour_courant().isoformat()
    if not r.set(f"vue:{jour}:{annonce_id}:{visiteur}", 1, nx=True, ex=EXPIRATION_VISITEUR_S):
        return False
    r.hincrby(f"{PREFIXE_JOUR}{jour}", str(annonce_id), 1)
    return True


def vider_compteurs() -> int:
    """Reporte les compteurs Redis dans `daily_stats` (idempotent : un compteur n'est reporté qu'une fois)."""
    r = redis_file.client()
    total = 0
    cles = list(r.scan_iter(match=f"{PREFIXE_JOUR}*", count=100)) + list(
        r.scan_iter(match=f"{PREFIXE_VIDAGE}*", count=100)
    )
    for cle in cles:
        if cle.startswith(PREFIXE_JOUR):
            jour = cle.removeprefix(PREFIXE_JOUR)
            en_cours = f"{PREFIXE_VIDAGE}{jour}:{uuid.uuid4().hex}"
            try:
                r.rename(
                    cle, en_cours
                )  # atomique : les nouvelles vues repartent d'un compteur neuf
            except redis.ResponseError:  # clé déjà reportée par un autre processus
                continue
        else:
            en_cours = cle
            jour = cle.removeprefix(PREFIXE_VIDAGE).split(":")[0]
        import datetime

        for annonce_id, valeur in r.hgetall(en_cours).items():
            stats.incrementer(
                "views", int(valeur), sujet=annonce_id, jour=datetime.date.fromisoformat(jour)
            )
            total += int(valeur)
        r.delete(en_cours)
    return total
