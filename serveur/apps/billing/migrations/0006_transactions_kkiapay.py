"""Transactions payées par la fenêtre KKiaPay (abonnement des gérants, alertes des locataires)."""

import django.db.models.deletion
import django.utils.timezone
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0011_suppression_du_numero"),
        ("listings", "0012_cautions_compteurs_et_alertes"),
        ("billing", "0005_intitules_des_relations"),
    ]

    operations = [
        migrations.CreateModel(
            name="Transaction",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("objet", models.CharField(choices=[("abonnement", "Abonnement de gérant"), ("alerte", "Alerte de locataire")], max_length=12, verbose_name="objet")),
                ("plan_code", models.CharField(blank=True, default="", max_length=32, verbose_name="formule")),
                ("amount", models.IntegerField(verbose_name="montant (F)")),
                ("status", models.CharField(choices=[("pending", "En attente"), ("succeeded", "Réussi"), ("failed", "Échoué"), ("refunded", "Remboursé")], default="pending", max_length=10, verbose_name="statut")),
                ("provider_ref", models.CharField(blank=True, max_length=120, null=True, unique=True, verbose_name="référence KKiaPay")),
                ("used_at", models.DateTimeField(blank=True, null=True, verbose_name="utilisée le")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, verbose_name="créé le")),
                ("paid_at", models.DateTimeField(blank=True, null=True, verbose_name="payé le")),
                ("alert", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="listings.alert", verbose_name="alerte créée")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="+", to="accounts.user", verbose_name="payeur")),
            ],
            options={
                "verbose_name": "transaction KKiaPay",
                "verbose_name_plural": "transactions KKiaPay",
                "db_table": "transactions",
            },
        ),
    ]
