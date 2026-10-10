"""Limitation de débit par adresse et par catégorie (fenêtre fixe, compteurs dans redis-queue). CDC §10.1."""

from rest_framework.exceptions import Throttled
from rest_framework.throttling import BaseThrottle

from apps.core import redis_file
from apps.core.http import ip_client


class LimiteParIp(BaseThrottle):
    """Sous-classer en fixant `categorie`, `limite` et `fenetre_s`."""

    categorie = "defaut"
    limite = 60
    fenetre_s = 60

    def allow_request(self, request, view) -> bool:
        ip = ip_client(request) or "inconnue"
        cle = f"debit:{self.categorie}:{ip}"
        r = redis_file.client()
        compte = r.incr(cle)
        if compte == 1:
            r.expire(cle, self.fenetre_s)
        self._attente = max(1, r.ttl(cle))
        return compte <= self.limite

    def wait(self):
        return getattr(self, "_attente", self.fenetre_s)

    def throttle_failure(self):  # pragma: no cover - DRF appelle wait()
        raise Throttled(wait=self.wait())


class LimiteAuth(LimiteParIp):
    """Connexion, inscription, OTP, rafraîchissement : 30 requêtes par minute et par adresse."""

    categorie = "auth"
    limite = 30


class LimiteCompte(LimiteParIp):
    """Actions du compte connecté (écritures) : 60 par minute et par adresse."""

    categorie = "compte"
    limite = 60


class LimiteLecture(LimiteParIp):
    """Lectures du compte connecté (listes, comptes, interrogation de rattrapage) : 240 par minute et par adresse."""

    categorie = "lecture"
    limite = 240
