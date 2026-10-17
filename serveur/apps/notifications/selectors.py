"""Lectures du centre de notifications."""

import datetime

from .models import Notification

PLAFOND_COMPTEUR = 100


def non_lues(utilisateur_id) -> int:
    """Compteur borné à 100 (« 99+ » côté interface)."""
    return Notification.objects.filter(user_id=utilisateur_id, read_at__isnull=True)[
        :PLAFOND_COMPTEUR
    ].count()


def liste(utilisateur_id, *, avant=None, limite: int = 30) -> tuple[list[Notification], str | None]:
    """Notifications, plus récentes d'abord ; curseur = date de création de la dernière ligne rendue."""
    requete = Notification.objects.filter(user_id=utilisateur_id)
    if avant is not None:
        requete = requete.filter(created_at__lt=avant)
    lignes = list(requete.order_by("-created_at", "-id")[: limite + 1])
    suivant = None
    if len(lignes) > limite:
        lignes = lignes[:limite]
        suivant = lignes[-1].created_at.astimezone(datetime.UTC).isoformat()
    return lignes, suivant


def nombre_du_jour(utilisateur_id, kind: str, cle: str, valeur: str) -> int:
    """Notifications de ce type reçues aujourd'hui (fuseau de l'application) pour une même valeur de `data[cle]`."""
    from django.utils import timezone

    debut = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
    return Notification.objects.filter(
        user_id=utilisateur_id, kind=kind, created_at__gte=debut, **{f"data__{cle}": valeur}
    ).count()


def donnees_par_cle(dedupe_key: str) -> dict | None:
    """Données d'une notification identifiée par sa clé d'unicité, ou None si elle n'existe pas."""
    return Notification.objects.filter(dedupe_key=dedupe_key).values_list("data", flat=True).first()
