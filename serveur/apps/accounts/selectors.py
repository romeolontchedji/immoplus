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


def gerants_publics(identifiants) -> dict:
    """Informations publiques des gérants, par identifiant de compte : nom affiché, badge, délai de réponse."""
    from .models import GerantProfile

    lignes = GerantProfile.objects.filter(pk__in=list(identifiants)).values(
        "user_id",
        "display_name",
        "user__full_name",
        "verification_status",
        "median_response_min",
    )
    return {
        ligne["user_id"]: {
            "id": ligne["user_id"],
            "name": ligne["display_name"] or ligne["user__full_name"],
            "verified": ligne["verification_status"] == "verified",
            "median_response_min": ligne["median_response_min"],
        }
        for ligne in lignes
    }


def gerant_public(gerant_id) -> dict | None:
    """Profil public d'un gérant actif : nom, badge, délai et taux de réponse, ancienneté. Jamais de numéro."""
    from .models import GerantProfile

    ligne = (
        GerantProfile.objects.filter(pk=gerant_id, user__deleted_at__isnull=True)
        .values(
            "user_id", "display_name", "user__full_name", "verification_status",
            "median_response_min", "response_rate_30d", "created_at", "user__status",
        )
        .first()
    )  # fmt: skip
    if ligne is None or ligne["user__status"] != "active":
        return None
    return {
        "id": ligne["user_id"],
        "name": ligne["display_name"] or ligne["user__full_name"],
        "verified": ligne["verification_status"] == "verified",
        "median_response_min": ligne["median_response_min"],
        "response_rate_30d": (
            float(ligne["response_rate_30d"]) if ligne["response_rate_30d"] is not None else None
        ),
        "member_since": ligne["created_at"].date(),
    }


def noms_utilisateurs(identifiants) -> dict:
    """Nom affiché des comptes (messagerie, notifications), par identifiant."""
    return {
        u["id"]: u["full_name"]
        for u in User.objects.filter(pk__in=list(identifiants)).values("id", "full_name")
    }


def appareils_push(utilisateur_id) -> list[dict]:
    """Appareils actifs capables de recevoir un push (jeton présent et valide)."""
    return [
        {"id": d.pk, "provider": d.push_provider, "token": d.push_token}
        for d in Device.objects.filter(
            user_id=utilisateur_id,
            revoked_at__isnull=True,
            push_invalid_at__isnull=True,
            push_token__isnull=False,
        )
    ]


def preferences_notifications(utilisateur_id) -> dict:
    return (
        User.objects.filter(pk=utilisateur_id).values_list("notif_prefs", flat=True).first() or {}
    )


def utilisateur_actif(utilisateur_id) -> bool:
    ligne = (
        User.objects.filter(pk=utilisateur_id)
        .values("status", "suspended_until", "deleted_at")
        .first()
    )
    if ligne is None or ligne["deleted_at"] is not None:
        return False
    return User(**{k: v for k, v in ligne.items() if k != "deleted_at"}).is_active


def suspensions_echues() -> list:
    """Comptes dont la suspension est arrivée à son terme (la levée automatique les réactive)."""
    from django.utils import timezone

    return list(
        User.objects.filter(
            status="suspended", suspended_until__isnull=False, suspended_until__lte=timezone.now()
        )
    )


def utilisateur_ou_none(identifiant):
    """Compte par identifiant, ou None s'il n'existe pas (contrairement à `utilisateur_par_id`, qui lève 401)."""
    try:
        return User.objects.filter(pk=identifiant).first()
    except ValueError:
        return None


def taux_de_reponse(utilisateur_id) -> float | None:
    """Taux de réponse sur 30 jours (pourcentage), calculé chaque nuit ; None tant qu'il n'est pas connu."""
    from .models import GerantProfile

    valeur = (
        GerantProfile.objects.filter(pk=utilisateur_id)
        .values_list("response_rate_30d", flat=True)
        .first()
    )
    return float(valeur) if valeur is not None else None
