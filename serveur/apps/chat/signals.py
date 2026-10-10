"""Signaux émis par la messagerie ; la modération s'y abonne (aucun import croisé)."""

from django.dispatch import Signal

# Coordonnées détectées dans un message : `conversation_id`, `message_id`, `expediteur_id`, `motifs`.
contact_detecte = Signal()
