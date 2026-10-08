"""Intergiciels de l'administration : liste blanche d'adresses et durée de session."""

import ipaddress

from django.conf import settings
from django.contrib.auth import logout
from django.http import Http404
from django.utils import timezone

from apps.core import parametres
from apps.core.http import ip_client

CHEMINS_LIBRES = ("/healthz",)


class ListeBlancheIpMiddleware:
    """Seconde barrière derrière Caddy : une adresse hors liste obtient un 404, comme si l'hôte n'existait pas.

    `ADMIN_ALLOWED_IPS` vide = tout refuser ; `None` = contrôle désactivé (développement et tests).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        autorisees = getattr(settings, "ADMIN_ALLOWED_IPS", None)
        if (
            autorisees is not None
            and request.path not in CHEMINS_LIBRES
            and not self._autorise(request, autorisees)
        ):
            raise Http404
        return self.get_response(request)

    @staticmethod
    def _autorise(request, autorisees) -> bool:
        brute = ip_client(request)
        try:
            adresse = ipaddress.ip_address(brute or "")
        except ValueError:
            return False
        for entree in autorisees:
            try:
                if adresse in ipaddress.ip_network(entree, strict=False):
                    return True
            except ValueError:
                continue
        return False


class DureeDeSessionMiddleware:
    """Inactivité de 30 minutes (session glissante) et durée absolue de 8 heures."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        session = request.session
        if request.user.is_authenticated:
            maintenant = int(timezone.now().timestamp())
            debut = session.setdefault("debut", maintenant)
            if maintenant - debut > int(parametres.lire("ADMIN_SESSION_MAX_H")) * 3600:
                logout(request)  # vide la session ET retire l'utilisateur de la requête en cours
            else:
                session.set_expiry(int(parametres.lire("ADMIN_SESSION_IDLE_MIN")) * 60)
        return self.get_response(request)
