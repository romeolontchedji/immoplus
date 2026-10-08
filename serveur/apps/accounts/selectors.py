"""Lectures des comptes (aucune écriture ici)."""

from apps.core.errors import ErreurMetier

from .models import Device, User


def utilisateur_par_id(identifiant) -> User:
    try:
        return User.objects.get(pk=identifiant)
    except (User.DoesNotExist, ValueError) as erreur:
        raise ErreurMetier(
            "invalid_token", "Session invalide ou expirée. Reconnecte-toi.", statut=401
        ) from erreur


def appareil_par_id(identifiant) -> Device | None:
    return Device.objects.filter(pk=identifiant).first()


def profil_gerant(utilisateur):
    """Profil du gérant connecté (colonnes publiques seulement) ; 403 si le compte n'en a pas."""
    from .models import GerantProfile

    profil = GerantProfile.objects.select_related("user").filter(user=utilisateur).first()
    if profil is None:
        raise ErreurMetier("forbidden", "Espace réservé aux gérants.", statut=403)
    return profil
