"""Énumérations de l'abonnement (CDC §9.20, §9.21)."""

from django.db import models


class StatutAbonnement(models.TextChoices):
    TRIALING = "trialing", "Essai"
    ACTIVE = "active", "Actif"
    PAST_DUE = "past_due", "Impayé (grâce)"
    CANCELED = "canceled", "Annulé"
    EXPIRED = "expired", "Expiré"


class StatutPaiement(models.TextChoices):
    PENDING = "pending", "En attente"
    SUCCEEDED = "succeeded", "Réussi"
    FAILED = "failed", "Échoué"
    REFUNDED = "refunded", "Remboursé"


class Fournisseur(models.TextChoices):
    SANDBOX = "sandbox", "Factice"
    FEDAPAY = "fedapay", "FedaPay"
    KKIAPAY = "kkiapay", "KKiaPay"


class Methode(models.TextChoices):
    MTN_MOMO = "mtn_momo", "MTN Mobile Money"
    MOOV_MONEY = "moov_money", "Moov Money"


# Machine à états (EF-ABO-08) : transitions permises ; toute autre est refusée.
TRANSITIONS = {
    StatutAbonnement.TRIALING: {
        StatutAbonnement.ACTIVE,
        StatutAbonnement.PAST_DUE,
        StatutAbonnement.CANCELED,
        StatutAbonnement.EXPIRED,
    },
    StatutAbonnement.ACTIVE: {
        StatutAbonnement.ACTIVE,
        StatutAbonnement.PAST_DUE,
        StatutAbonnement.CANCELED,
    },
    StatutAbonnement.PAST_DUE: {
        StatutAbonnement.ACTIVE,
        StatutAbonnement.EXPIRED,
        StatutAbonnement.CANCELED,
    },
    StatutAbonnement.CANCELED: {StatutAbonnement.EXPIRED},
    StatutAbonnement.EXPIRED: set(),
}
