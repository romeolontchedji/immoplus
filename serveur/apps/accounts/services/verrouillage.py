"""Verrouillage progressif de la connexion (CDC §5.2, EF-AUT-05).

Les compteurs vivent dans `redis-queue` (jamais le cache à éviction). Le verrou porte sur le couple
(numéro saisi, appareil ou adresse IP), y compris pour un numéro inconnu : il ne révèle donc rien et personne
ne peut bloquer le compte d'autrui à distance. Un plafond horaire par numéro, tous appareils confondus,
ralentit les attaques réparties.
"""

import hashlib
import math

from apps.core import parametres, redis_file
from apps.core.errors import ErreurMetier

JOUR_S = 86400
SEMAINE_S = 7 * JOUR_S
DUREE_MAX_S = JOUR_S


def _h(valeur: str) -> str:
    return hashlib.sha256(valeur.encode()).hexdigest()[:32]


def _cles(telephone: str, client: str) -> dict[str, str]:
    couple = _h(f"{telephone}|{client}")
    return {
        "echecs": f"login:echecs:{couple}",
        "niveau": f"login:niveau:{couple}",
        "verrou": f"login:verrou:{couple}",
        "heure": f"login:heure:{_h(telephone)}",
    }


def refus_uniforme(attente_s: int) -> ErreurMetier:
    """La réponse 401 est identique pour un mauvais mot de passe, un numéro inconnu et un verrouillage."""
    return ErreurMetier(
        "invalid_credentials",
        "Numéro ou mot de passe incorrect.",
        statut=401,
        entetes={"Retry-After": str(max(1, math.ceil(attente_s)))},
    )


def controler(telephone: str, client: str) -> None:
    """Lève le refus uniforme si le couple est verrouillé ou si le plafond horaire du numéro est atteint."""
    r = redis_file.client()
    cles = _cles(telephone, client)
    attente = r.ttl(cles["verrou"])
    if attente and attente > 0:
        raise refus_uniforme(attente)
    plafond = int(parametres.lire("LOGIN_FAILS_PER_HOUR_PER_PHONE"))
    if int(r.get(cles["heure"]) or 0) >= plafond:
        raise refus_uniforme(max(1, r.ttl(cles["heure"])))


def enregistrer_echec(telephone: str, client: str) -> bool:
    """Compte un échec ; retourne vrai si cet échec déclenche le verrouillage."""
    r = redis_file.client()
    cles = _cles(telephone, client)
    seuil = int(parametres.lire("LOGIN_LOCK_THRESHOLD"))
    base_s = int(parametres.lire("LOGIN_LOCK_MINUTES")) * 60

    if r.incr(cles["heure"]) == 1:
        r.expire(cles["heure"], 3600)

    echecs = r.incr(cles["echecs"])
    r.expire(cles["echecs"], JOUR_S)
    if echecs >= seuil:
        niveau = r.incr(cles["niveau"])
        r.expire(cles["niveau"], SEMAINE_S)
        duree = min(base_s * 2 ** (niveau - 1), DUREE_MAX_S)
        r.set(cles["verrou"], 1, ex=duree)
        r.delete(cles["echecs"])
        return True
    return False


def enregistrer_succes(telephone: str, client: str) -> None:
    """Efface le compteur et le niveau de récidive du couple ; le plafond horaire du numéro reste."""
    cles = _cles(telephone, client)
    redis_file.client().delete(cles["echecs"], cles["niveau"], cles["verrou"])
