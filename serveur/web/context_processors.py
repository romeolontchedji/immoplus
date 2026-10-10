"""Compteurs de la barre de navigation (messages et notifications non lus) pour l'utilisateur connecté."""

from apps.chat import selectors as chat_selectors
from apps.notifications import selectors as notifications


def navigation(request):
    utilisateur = getattr(request, "user", None)
    if (
        utilisateur is None
        or not utilisateur.is_authenticated
        or utilisateur.role not in ("client", "gerant")
    ):
        return {}
    return {
        "non_lus_messages": chat_selectors.total_non_lus(utilisateur.pk, utilisateur.role),
        "non_lues_notifications": notifications.non_lues(utilisateur.pk),
    }
