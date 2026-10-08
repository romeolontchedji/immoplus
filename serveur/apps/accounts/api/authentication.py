"""Authentification des requêtes d'API par jeton d'accès, et permissions par audience."""

from django.core.cache import cache
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.permissions import BasePermission

from apps.accounts import selectors
from apps.accounts.services import appareils, jetons
from apps.core.errors import ErreurMetier
from apps.core.http import ip_client


class AuthJwt(BaseAuthentication):
    """`Authorization: Bearer <jeton>` ; `request.user` est le compte, `request.auth` l'identité (appareil, rôle)."""

    def authenticate(self, request):
        en_tete = get_authorization_header(request).split()
        if not en_tete or en_tete[0].lower() != b"bearer":
            return None
        if len(en_tete) != 2:
            raise ErreurMetier(
                "invalid_token", "Session invalide ou expirée. Reconnecte-toi.", statut=401
            )
        identite = jetons.verifier_acces(en_tete[1].decode(errors="ignore"))
        utilisateur = selectors.utilisateur_par_id(identite.utilisateur_id)
        if cache.add(
            f"securite:vu:{identite.appareil_id}", 1, 300
        ):  # au plus une écriture toutes les 5 minutes
            appareils.marquer_vu(identite.appareil_id, ip_client(request))
        return utilisateur, identite

    def authenticate_header(self, request):
        return 'Bearer realm="logeo"'


class Connecte(BasePermission):
    def has_permission(self, request, view):
        return request.auth is not None and request.user is not None


class _Audience(BasePermission):
    role = ""

    def has_permission(self, request, view):
        # Jeton Bearer (application) ou session du site (même règle d'audience).
        role = (
            request.auth.role if request.auth is not None else getattr(request.user, "role", None)
        )
        if role is None:
            return False
        if role != self.role:
            raise ErreurMetier("wrong_audience", "Ce jeton n'ouvre pas cet espace.", statut=403)
        return True


class EstClient(_Audience):
    role = "client"


class EstGerant(_Audience):
    role = "gerant"
