"""Compteurs de la barre de navigation (messages et notifications non lus) pour l'utilisateur connecté."""

from django.utils.functional import SimpleLazyObject

from apps.chat import selectors as chat_selectors
from apps.core import configuration
from apps.notifications import selectors as notifications

# Pages sans barre latérale même connecté : l'accueil (menus inchangés) et les pages de connexion.
SANS_BARRE = (
    "/connexion",
    "/inscription",
    "/mot-de-passe-oublie",
    "/dev/",
    "/styleguide",
    "/deconnexion",
)


def _recentes(utilisateur_id) -> list:
    """Les 5 dernières notifications, chacune avec son lien profond (bouton « Consulter » de la cloche)."""
    from web.views_public import _lien_notification

    lignes = notifications.liste(utilisateur_id, limite=5)[0]
    for n in lignes:
        n.lien = _lien_notification({"data": n.data})
    return lignes


def navigation(request):
    utilisateur = getattr(request, "user", None)
    if (
        utilisateur is None
        or not utilisateur.is_authenticated
        or utilisateur.role not in ("client", "gerant")
    ):
        return {}
    chemin = getattr(request, "path", "/")
    abonnement_requis = False
    if utilisateur.role == "gerant":
        from apps.accounts import selectors as comptes
        from apps.billing import services as abonnements

        if abonnements.actif():  # paiements éteints : aucune requête de plus
            abonnement_requis = not abonnements.can_publish(comptes.profil_gerant(utilisateur).pk)
    return {
        "abonnement_requis": abonnement_requis,
        "non_lus_messages": chat_selectors.total_non_lus(utilisateur.pk, utilisateur.role),
        "non_lues_notifications": notifications.non_lues(utilisateur.pk),
        # Les 5 dernières, pour la fenêtre de la cloche (lues seulement si elle est affichée).
        "notifications_recentes": SimpleLazyObject(lambda: _recentes(utilisateur.pk)),
        # Barre latérale fixe sur toutes les pages des comptes connectés, sauf l'accueil (plan v3, E2).
        "barre_laterale": chemin != "/" and not chemin.startswith(SANS_BARRE),
    }


def contact(request):
    """Numéro de l'équipe (paramètre `TEAM_PHONE`) : appel, WhatsApp et affichage, partout le même."""
    # Paresseux : le paramètre n'est lu (cache de 30 s) que si le gabarit affiche le contact.
    return {"contact_equipe": SimpleLazyObject(configuration.contact_equipe)}
