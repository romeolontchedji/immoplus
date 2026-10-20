"""Limitation de débit par catégorie (fenêtre fixe, compteurs dans redis-queue). CDC §10.1.

Un compte connecté a son propre compteur : au Bénin, des centaines d'abonnés mobiles ou d'étudiants sur le Wi-Fi du
campus sortent par la même adresse IP (CGNAT), et un plafond par adresse les bloquerait tous ensemble. Les requêtes
anonymes restent comptées par adresse, avec des plafonds réglables dans l'administration (`RATE_IP_FACTOR`,
`AUTH_RATE_PER_MIN_IP`).
"""

from rest_framework.exceptions import Throttled
from rest_framework.throttling import BaseThrottle

from apps.core import parametres, redis_file
from apps.core.http import ip_client


class LimiteParIp(BaseThrottle):
    """Sous-classer en fixant `categorie`, `limite` et `fenetre_s`."""

    categorie = "defaut"
    limite = 60
    fenetre_s = 60

    def plafond_par_adresse(self) -> int:
        """Plafond d'une adresse IP pour les requêtes anonymes (partagée par de nombreux abonnés)."""
        return self.limite * int(parametres.lire("RATE_IP_FACTOR"))

    def allow_request(self, request, view) -> bool:
        utilisateur = getattr(request, "user", None)
        if utilisateur is not None and utilisateur.is_authenticated:
            cle, plafond = f"debit:{self.categorie}:u:{utilisateur.pk}", self.limite
        else:
            cle = f"debit:{self.categorie}:{ip_client(request) or 'inconnue'}"
            plafond = self.plafond_par_adresse()
        r = redis_file.client()
        compte = r.incr(cle)
        if compte == 1:
            r.expire(cle, self.fenetre_s)
        self._attente = max(1, r.ttl(cle))
        return compte <= plafond

    def wait(self):
        return getattr(self, "_attente", self.fenetre_s)

    def throttle_failure(self):  # pragma: no cover - DRF appelle wait()
        raise Throttled(wait=self.wait())


class LimiteAuth(LimiteParIp):
    """Connexion, inscription, rafraîchissement, mot de passe oublié : `AUTH_RATE_PER_MIN_IP` par minute et par
    adresse (60 par défaut). Chaque compte reste en plus protégé par son propre verrouillage."""

    categorie = "auth"
    limite = 30

    def plafond_par_adresse(self) -> int:
        return int(parametres.lire("AUTH_RATE_PER_MIN_IP"))


class LimiteCompte(LimiteParIp):
    """Actions du compte connecté (écritures) : 60 par minute et par compte."""

    categorie = "compte"
    limite = 60


class LimiteLecture(LimiteParIp):
    """Lectures (fil, listes, comptes, interrogation de rattrapage) : 240 par minute et par compte."""

    categorie = "lecture"
    limite = 240
