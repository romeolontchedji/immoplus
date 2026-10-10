"""Signaux émis par les services de notifications ; la messagerie s'y abonne (aucun import croisé)."""

from django.dispatch import Signal

# Émis quand le sort du push d'une notification est réglé : arguments `kind`, `data`, `motif`
# (« envoye » : accepté par le fournisseur ; « saute » : saut motivé — catégorie coupée, silence, aucun appareil).
push_regle = Signal()
