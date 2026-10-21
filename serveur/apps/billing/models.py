"""Abonnements et paiements (CDC §9.20, §9.21) : livrés, testés, inactifs tant que `SUBSCRIPTION_ENABLED` est faux."""

import uuid

from django.db import models
from django.db.models.functions import Now
from django.utils import timezone

from .enums import Fournisseur, Methode, StatutAbonnement, StatutPaiement

NON_EXPIRES = [s.value for s in StatutAbonnement if s != StatutAbonnement.EXPIRED]


class Subscription(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gerant = models.ForeignKey(
        "accounts.GerantProfile",
        on_delete=models.CASCADE,
        related_name="+",
        db_column="gerant_id",
        verbose_name="gérant",
    )
    plan_code = models.CharField(
        max_length=32, verbose_name="formule"
    )  # code d'un plan de app_settings.PLANS
    status = models.CharField(
        max_length=10, choices=StatutAbonnement.choices, verbose_name="statut"
    )
    current_period_start = models.DateTimeField(verbose_name="début de période")
    current_period_end = models.DateTimeField(verbose_name="fin de période")
    cancel_at_period_end = models.BooleanField(
        default=False, db_default=False, verbose_name="annulé en fin de période"
    )
    canceled_at = models.DateTimeField(null=True, blank=True, verbose_name="annulé le")
    created_at = models.DateTimeField(
        default=timezone.now, db_default=Now(), verbose_name="créé le"
    )
    updated_at = models.DateTimeField(auto_now=True, db_default=Now(), verbose_name="modifié le")

    class Meta:
        db_table = "subscriptions"
        verbose_name = "abonnement"
        verbose_name_plural = "abonnements"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=[s.value for s in StatutAbonnement]),
                name="subscriptions_statut_valide",
            ),
            models.UniqueConstraint(
                fields=["gerant"],
                condition=models.Q(status__in=NON_EXPIRES),
                name="subscriptions_un_seul_non_expire",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.plan_code} ({self.get_status_display()})"


class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(
        Subscription, on_delete=models.SET_NULL, null=True, blank=True, related_name="payments"
    )
    gerant = models.ForeignKey(
        "accounts.GerantProfile",
        on_delete=models.CASCADE,
        related_name="+",
        db_column="gerant_id",
        verbose_name="gérant",
    )
    plan_code = models.CharField(max_length=32, verbose_name="formule")
    amount = models.IntegerField(verbose_name="montant (F)")
    currency = models.CharField(max_length=3, default="XOF", db_default="XOF")
    provider = models.CharField(
        max_length=10, choices=Fournisseur.choices, verbose_name="fournisseur"
    )
    provider_ref = models.CharField(max_length=120, unique=True, null=True, blank=True)
    method = models.CharField(
        max_length=12, choices=Methode.choices, verbose_name="moyen de paiement"
    )
    payer_phone_e164 = models.CharField(max_length=16)
    status = models.CharField(
        max_length=10,
        choices=StatutPaiement.choices,
        default=StatutPaiement.PENDING,
        db_default="pending",
        verbose_name="statut",
    )
    idempotency_key = models.CharField(max_length=64, unique=True)
    webhook_events = models.JSONField(default=list, db_default=[])
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name="payé le")
    created_at = models.DateTimeField(
        default=timezone.now, db_default=Now(), verbose_name="créé le"
    )

    class Meta:
        db_table = "payments"
        verbose_name = "paiement"
        verbose_name_plural = "paiements"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gte=0), name="payments_montant_positif"
            ),
            models.CheckConstraint(
                condition=models.Q(provider__in=[f.value for f in Fournisseur]),
                name="payments_fournisseur_valide",
            ),
            models.CheckConstraint(
                condition=models.Q(method__in=[m.value for m in Methode]),
                name="payments_methode_valide",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=[s.value for s in StatutPaiement]),
                name="payments_statut_valide",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.amount} F · {self.get_status_display()}"
