"""La suspension, le bannissement et la suppression d'un compte gérant agissent sur ses annonces."""

from django.dispatch import receiver

from apps.accounts.enums import Statut
from apps.accounts.signals import compte_supprime, statut_compte_change


@receiver(statut_compte_change, dispatch_uid="listings-statut-compte")
def compte_change(sender, utilisateur, ancien, nouveau, **kwargs):
    from .services import annonces

    if utilisateur.role != "gerant":
        return
    if ancien == Statut.ACTIVE and nouveau in (Statut.SUSPENDED, Statut.BANNED):
        annonces.masquer_pour_gerant_suspendu(utilisateur.pk, acteur=None)
    elif ancien in (Statut.SUSPENDED, Statut.BANNED) and nouveau == Statut.ACTIVE:
        annonces.remettre_apres_suspension(utilisateur.pk, acteur=None)


@receiver(compte_supprime, dispatch_uid="listings-compte-supprime")
def compte_supprime_recu(sender, utilisateur_id, role, **kwargs):
    from .services import annonces

    if role == "gerant":
        annonces.archiver_du_gerant(utilisateur_id)
