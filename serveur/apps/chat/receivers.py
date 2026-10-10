"""Abonnements de la messagerie aux signaux des annonces et des notifications."""

from django.dispatch import receiver

from apps.listings.enums import StatutAnnonce
from apps.listings.signals import statut_annonce_change
from apps.notifications import signals as signaux_notifications


@receiver(statut_annonce_change, dispatch_uid="chat-statut-annonce")
def annonce_changee(sender, annonce_id, ancien, nouveau, raison, **kwargs):
    """Annonce louée, masquée ou retirée : les participants des conversations en sont informés (EF-MSG-08)."""
    from . import services

    if nouveau in (StatutAnnonce.RENTED, StatutAnnonce.HIDDEN, StatutAnnonce.REMOVED):
        services.prevenir_conversations(annonce_id, nouveau)


@receiver(signaux_notifications.push_regle, dispatch_uid="chat-push-regle")
def push_regle(sender, kind, data, motif, **kwargs):
    """Push parti ou saut motivé : le message est considéré comme notifié (`notified_at`, CDC §11.9)."""
    if kind == "message.received" and data.get("message_id"):
        from . import services

        services.marquer_notifie(data["message_id"])
