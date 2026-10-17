"""Intitulés français des champs dans l'administration (aucune instruction SQL)."""


import django.db.models.functions.datetime
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("billing", "0003_libelles_francais"),
    ]

    operations = [
        migrations.AlterField(
            model_name="payment",
            name="amount",
            field=models.IntegerField(verbose_name="montant (F)"),
        ),
        migrations.AlterField(
            model_name="payment",
            name="created_at",
            field=models.DateTimeField(
                db_default=django.db.models.functions.datetime.Now(),
                default=django.utils.timezone.now,
                verbose_name="créé le",
            ),
        ),
        migrations.AlterField(
            model_name="payment",
            name="method",
            field=models.CharField(
                choices=[
                    ("mtn_momo", "MTN Mobile Money"),
                    ("moov_money", "Moov Money"),
                ],
                max_length=12,
                verbose_name="moyen de paiement",
            ),
        ),
        migrations.AlterField(
            model_name="payment",
            name="paid_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="payé le"),
        ),
        migrations.AlterField(
            model_name="payment",
            name="plan_code",
            field=models.CharField(max_length=32, verbose_name="formule"),
        ),
        migrations.AlterField(
            model_name="payment",
            name="provider",
            field=models.CharField(
                choices=[
                    ("sandbox", "Factice"),
                    ("fedapay", "FedaPay"),
                    ("kkiapay", "KKiaPay"),
                ],
                max_length=10,
                verbose_name="fournisseur",
            ),
        ),
        migrations.AlterField(
            model_name="payment",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "En attente"),
                    ("succeeded", "Réussi"),
                    ("failed", "Échoué"),
                    ("refunded", "Remboursé"),
                ],
                db_default="pending",
                default="pending",
                max_length=10,
                verbose_name="statut",
            ),
        ),
        migrations.AlterField(
            model_name="subscription",
            name="cancel_at_period_end",
            field=models.BooleanField(
                db_default=False, default=False, verbose_name="annulé en fin de période"
            ),
        ),
        migrations.AlterField(
            model_name="subscription",
            name="canceled_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="annulé le"),
        ),
        migrations.AlterField(
            model_name="subscription",
            name="created_at",
            field=models.DateTimeField(
                db_default=django.db.models.functions.datetime.Now(),
                default=django.utils.timezone.now,
                verbose_name="créé le",
            ),
        ),
        migrations.AlterField(
            model_name="subscription",
            name="current_period_end",
            field=models.DateTimeField(verbose_name="fin de période"),
        ),
        migrations.AlterField(
            model_name="subscription",
            name="current_period_start",
            field=models.DateTimeField(verbose_name="début de période"),
        ),
        migrations.AlterField(
            model_name="subscription",
            name="plan_code",
            field=models.CharField(max_length=32, verbose_name="formule"),
        ),
        migrations.AlterField(
            model_name="subscription",
            name="status",
            field=models.CharField(
                choices=[
                    ("trialing", "Essai"),
                    ("active", "Actif"),
                    ("past_due", "Impayé (grâce)"),
                    ("canceled", "Annulé"),
                    ("expired", "Expiré"),
                ],
                max_length=10,
                verbose_name="statut",
            ),
        ),
        migrations.AlterField(
            model_name="subscription",
            name="updated_at",
            field=models.DateTimeField(
                auto_now=True,
                db_default=django.db.models.functions.datetime.Now(),
                verbose_name="modifié le",
            ),
        ),
    ]
