"""Signaux émis par les services d'annonces ; la messagerie et les autres applications s'y abonnent."""

from django.dispatch import Signal

# Émis après chaque changement de statut : `annonce_id`, `ancien`, `nouveau`, `raison`.
statut_annonce_change = Signal()
