"""Abonnements et paiements (CDC §9.20, §9.21) : tables livrées, inactives tant que SUBSCRIPTION_ENABLED est faux."""


import django.db.models.deletion
import django.db.models.functions.datetime
import django.utils.timezone
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("accounts", "0005_occupation_utilisateur"),
    ]

    operations = [
        migrations.CreateModel(
            name="Subscription",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("plan_code", models.CharField(max_length=32)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("trialing", "Essai"),
                            ("active", "Actif"),
                            ("past_due", "Impayé (grâce)"),
                            ("canceled", "Annulé"),
                            ("expired", "Expiré"),
                        ],
                        max_length=10,
                    ),
                ),
                ("current_period_start", models.DateTimeField()),
                ("current_period_end", models.DateTimeField()),
                (
                    "cancel_at_period_end",
                    models.BooleanField(db_default=False, default=False),
                ),
                ("canceled_at", models.DateTimeField(blank=True, null=True)),
                (
                    "created_at",
                    models.DateTimeField(
                        db_default=django.db.models.functions.datetime.Now(),
                        default=django.utils.timezone.now,
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        db_default=django.db.models.functions.datetime.Now(),
                    ),
                ),
                (
                    "gerant",
                    models.ForeignKey(
                        db_column="gerant_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="accounts.gerantprofile",
                    ),
                ),
            ],
            options={
                "verbose_name": "abonnement",
                "db_table": "subscriptions",
            },
        ),
        migrations.CreateModel(
            name="Payment",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("plan_code", models.CharField(max_length=32)),
                ("amount", models.IntegerField()),
                (
                    "currency",
                    models.CharField(db_default="XOF", default="XOF", max_length=3),
                ),
                (
                    "provider",
                    models.CharField(
                        choices=[
                            ("sandbox", "Factice"),
                            ("fedapay", "FedaPay"),
                            ("kkiapay", "KKiaPay"),
                        ],
                        max_length=10,
                    ),
                ),
                (
                    "provider_ref",
                    models.CharField(
                        blank=True, max_length=120, null=True, unique=True
                    ),
                ),
                (
                    "method",
                    models.CharField(
                        choices=[
                            ("mtn_momo", "MTN Mobile Money"),
                            ("moov_money", "Moov Money"),
                        ],
                        max_length=12,
                    ),
                ),
                ("payer_phone_e164", models.CharField(max_length=16)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "En attente"),
                            ("succeeded", "Réussi"),
                            ("failed", "Échoué"),
                            ("refunded", "Remboursé"),
                        ],
                        db_default="pending",
                        default="pending",
                        max_length=10,
                    ),
                ),
                ("idempotency_key", models.CharField(max_length=64, unique=True)),
                ("webhook_events", models.JSONField(db_default=[], default=list)),
                ("paid_at", models.DateTimeField(blank=True, null=True)),
                (
                    "created_at",
                    models.DateTimeField(
                        db_default=django.db.models.functions.datetime.Now(),
                        default=django.utils.timezone.now,
                    ),
                ),
                (
                    "gerant",
                    models.ForeignKey(
                        db_column="gerant_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="accounts.gerantprofile",
                    ),
                ),
                (
                    "subscription",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="payments",
                        to="billing.subscription",
                    ),
                ),
            ],
            options={
                "verbose_name": "paiement",
                "db_table": "payments",
            },
        ),
        migrations.AddConstraint(
            model_name="subscription",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    (
                        "status__in",
                        ["trialing", "active", "past_due", "canceled", "expired"],
                    )
                ),
                name="subscriptions_statut_valide",
            ),
        ),
        migrations.AddConstraint(
            model_name="subscription",
            constraint=models.UniqueConstraint(
                condition=models.Q(
                    ("status__in", ["trialing", "active", "past_due", "canceled"])
                ),
                fields=("gerant",),
                name="subscriptions_un_seul_non_expire",
            ),
        ),
        migrations.AddConstraint(
            model_name="payment",
            constraint=models.CheckConstraint(
                condition=models.Q(("amount__gte", 0)), name="payments_montant_positif"
            ),
        ),
        migrations.AddConstraint(
            model_name="payment",
            constraint=models.CheckConstraint(
                condition=models.Q(("provider__in", ["sandbox", "fedapay", "kkiapay"])),
                name="payments_fournisseur_valide",
            ),
        ),
        migrations.AddConstraint(
            model_name="payment",
            constraint=models.CheckConstraint(
                condition=models.Q(("method__in", ["mtn_momo", "moov_money"])),
                name="payments_methode_valide",
            ),
        ),
        migrations.AddConstraint(
            model_name="payment",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("status__in", ["pending", "succeeded", "failed", "refunded"])
                ),
                name="payments_statut_valide",
            ),
        ),
    ]
