"""Erreur métier unique et format de réponse d'erreur de l'API (CDC §10.1)."""

from django.http import Http404
from rest_framework import exceptions
from rest_framework.response import Response

from . import requete


class ErreurMetier(Exception):
    """Refus d'une règle métier : porte le code stable, le message français et le statut HTTP."""

    def __init__(self, code: str, message: str, *, statut: int = 400, champs=None, entetes=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.statut = statut
        self.champs = champs or {}
        self.entetes = entetes or {}


def corps_erreur(code: str, message: str, champs=None) -> dict:
    return {
        "error": {
            "code": code,
            "message": message,
            "fields": champs or {},
            "request_id": requete.courant(),
        }
    }


def reponse_erreur(erreur: ErreurMetier) -> Response:
    return Response(
        corps_erreur(erreur.code, erreur.message, erreur.champs),
        status=erreur.statut,
        headers=erreur.entetes,
    )


def _champs(detail) -> dict:
    """Aplatit le détail d'une `ValidationError` DRF en {champ: [messages]}."""
    if isinstance(detail, dict):
        return {k: [str(m) for m in (v if isinstance(v, list) else [v])] for k, v in detail.items()}
    return {
        "non_field_errors": [str(m) for m in (detail if isinstance(detail, list) else [detail])]
    }


def gestionnaire_exceptions(exc, contexte):
    """Convertit toute exception en `{"error": {code, message, fields, request_id}}`."""
    if isinstance(exc, ErreurMetier):
        return reponse_erreur(exc)
    from rest_framework.views import (
        exception_handler as gestionnaire_drf,
    )  # import tardif : évite un cycle

    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    reponse = gestionnaire_drf(exc, contexte)
    if reponse is None:
        return None
    if isinstance(exc, exceptions.ValidationError):
        corps = corps_erreur(
            "validation_error", "Les données envoyées sont invalides.", _champs(exc.detail)
        )
    elif isinstance(exc, exceptions.NotAuthenticated):
        corps = corps_erreur("not_authenticated", "Connexion requise.")
    elif isinstance(exc, exceptions.AuthenticationFailed):
        corps = corps_erreur("invalid_token", "Session invalide ou expirée. Reconnecte-toi.")
    elif isinstance(exc, exceptions.PermissionDenied):
        corps = corps_erreur("forbidden", "Tu n'as pas accès à cette ressource.")
    elif isinstance(exc, exceptions.NotFound):
        corps = corps_erreur("not_found", "Ressource introuvable.")
    elif isinstance(exc, exceptions.Throttled):
        corps = corps_erreur("rate_limited", "Trop de demandes. Réessaie un peu plus tard.")
    elif isinstance(exc, exceptions.ParseError):
        corps = corps_erreur("parse_error", "Requête illisible.")
    elif isinstance(exc, exceptions.MethodNotAllowed):
        corps = corps_erreur("method_not_allowed", "Méthode non autorisée.")
    elif isinstance(exc, exceptions.UnsupportedMediaType):
        corps = corps_erreur("unsupported_media_type", "Format de requête non pris en charge.")
    else:
        corps = corps_erreur("error", "Une erreur est survenue.")
    reponse.data = corps
    return reponse
