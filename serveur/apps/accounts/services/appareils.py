"""Appareils connectés : ouverture, liste, révocation, jeton de notification (CDC EF-AUT-11)."""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Device, FournisseurPush, Plateforme, User
from apps.core.errors import ErreurMetier

from . import jetons


def ouvrir(
    utilisateur: User,
    *,
    installation_id: str,
    platform: str,
    app_version: str | None = None,
    label: str | None = None,
    ip: str | None = None,
) -> tuple[Device, str]:
    """Crée (ou réactive) l'appareil d'une installation et retourne (appareil, jeton de rafraîchissement)."""
    if platform not in Plateforme.values:
        raise ErreurMetier(
            "validation_error", "Plateforme inconnue.", champs={"platform": ["Valeur inconnue"]}
        )
    maintenant = timezone.now()
    brut, hache = jetons.nouveau_refresh()
    with transaction.atomic():
        appareil, _ = Device.objects.select_for_update().get_or_create(
            user=utilisateur,
            installation_id=installation_id,
            defaults={
                "platform": platform,
                "refresh_expires_at": maintenant + jetons.DUREE_REFRESH,
            },
        )
        appareil.platform = platform
        appareil.app_version = (app_version or "")[:20] or None
        appareil.label = (label or "")[:120] or None
        appareil.refresh_hash = hache
        appareil.prev_refresh_hash = None
        appareil.rotated_at = None
        appareil.refresh_expires_at = maintenant + jetons.DUREE_REFRESH
        appareil.revoked_at = None
        appareil.last_seen_at = maintenant
        appareil.last_ip = ip or None
        appareil.save()
    jetons.marquer_appareil_actif(appareil.pk)
    return appareil, brut


def lister(utilisateur: User) -> list[Device]:
    return list(
        Device.objects.filter(user=utilisateur, revoked_at__isnull=True).order_by(
            "-last_seen_at", "-created_at"
        )
    )


def revoquer(utilisateur: User, appareil_id) -> None:
    """Déconnecte un appareil du compte. 404 si l'appareil n'appartient pas à l'appelant (ou n'existe pas)."""
    try:
        appareil = Device.objects.select_related("user").get(
            pk=appareil_id, user=utilisateur, revoked_at__isnull=True
        )
    except (Device.DoesNotExist, ValueError, TypeError, DjangoValidationError) as erreur:
        raise ErreurMetier("not_found", "Appareil introuvable.", statut=404) from erreur
    jetons.revoquer_appareil(appareil, raison="demande_utilisateur")


def revoquer_autres(utilisateur: User, garder_id=None, *, raison: str = "autres_appareils") -> int:
    """Révoque tous les appareils sauf `garder_id`. Retourne le nombre d'appareils déconnectés."""
    requete = Device.objects.select_related("user").filter(
        user=utilisateur, revoked_at__isnull=True
    )
    if garder_id is not None:
        requete = requete.exclude(pk=garder_id)
    appareils = list(requete)
    for appareil in appareils:
        jetons.revoquer_appareil(appareil, raison=raison)
    return len(appareils)


def enregistrer_push(appareil: Device, fournisseur: str, jeton: str) -> None:
    if fournisseur not in FournisseurPush.values:
        raise ErreurMetier(
            "validation_error", "Fournisseur inconnu.", champs={"provider": ["Valeur inconnue"]}
        )
    if not jeton or len(jeton) > 4096:
        raise ErreurMetier(
            "validation_error", "Jeton invalide.", champs={"token": ["Valeur invalide"]}
        )
    appareil.push_provider = fournisseur
    appareil.push_token = jeton
    appareil.push_invalid_at = None
    appareil.save(update_fields=["push_provider", "push_token", "push_invalid_at"])


def marquer_vu(appareil_id, ip: str | None = None) -> None:
    Device.objects.filter(pk=appareil_id).update(last_seen_at=timezone.now(), last_ip=ip or None)
