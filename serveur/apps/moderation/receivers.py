"""La messagerie signale les coordonnées détectées : la modération en fait un signalement automatique."""

from django.dispatch import receiver

from apps.chat.signals import contact_detecte


@receiver(contact_detecte, dispatch_uid="moderation-contact-detecte")
def coordonnees_detectees(sender, conversation_id, message_id, expediteur_id, motifs, **kwargs):
    from . import services

    services.signaler_automatiquement(
        "message", message_id, "contact_leak", f"Détection : {', '.join(motifs)}"[:500],
        annonce_id=_annonce_de(conversation_id),
    )  # fmt: skip


def _annonce_de(conversation_id):
    from apps.chat import selectors

    conversation = selectors.conversation_par_id(conversation_id)
    return conversation.listing_id if conversation else None
