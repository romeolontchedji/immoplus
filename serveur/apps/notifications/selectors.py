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
