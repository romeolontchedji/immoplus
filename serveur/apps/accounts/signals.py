"""Signaux émis par les services de comptes ; les autres applications s'y abonnent (aucun import croisé)."""

from django.dispatch import Signal

# Émis après la suppression (anonymisation) d'un compte, avec `utilisateur_id` et `role`.
compte_supprime = Signal()

# Émis après un changement de statut (suspension, bannissement, réactivation) : `utilisateur`, `ancien`, `nouveau`.
statut_compte_change = Signal()
