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
        "accounts.GerantProfile", on_delete=models.CASCADE, related_name="+", db_column="gerant_id"
    )
    plan_code = models.CharField(max_length=32)  # code d'un plan de app_settings.PLANS
    status = models.CharField(max_length=10, choices=StatutAbonnement.choices)
    current_period_start = models.DateTimeField()
    current_period_end = models.DateTimeField()
    cancel_at_period_end = models.BooleanField(default=False, db_default=False)
    canceled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_default=Now())
    updated_at = models.DateTimeField(auto_now=True, db_default=Now())

    class Meta:
        db_table = "subscriptions"
        verbose_name = "abonnement"
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
        "accounts.GerantProfile", on_delete=models.CASCADE, related_name="+", db_column="gerant_id"
    )
    plan_code = models.CharField(max_length=32)
    amount = models.IntegerField()
    currency = models.CharField(max_length=3, default="XOF", db_default="XOF")
    provider = models.CharField(max_length=10, choices=Fournisseur.choices)
    provider_ref = models.CharField(max_length=120, unique=True, null=True, blank=True)
    method = models.CharField(max_length=12, choices=Methode.choices)
    payer_phone_e164 = models.CharField(max_length=16)
    status = models.CharField(
        max_length=10,
        choices=StatutPaiement.choices,
        default=StatutPaiement.PENDING,
        db_default="pending",
    )
    idempotency_key = models.CharField(max_length=64, unique=True)
    webhook_events = models.JSONField(default=list, db_default=[])
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_default=Now())

    class Meta:
        db_table = "payments"
        verbose_name = "paiement"
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
