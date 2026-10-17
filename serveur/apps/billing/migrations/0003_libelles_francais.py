"""Intitulés français dans l'administration (options seulement, aucune modification de table)."""


from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("billing", "0002_plan_gratuit_des_gerants_verifies"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="payment",
            options={"verbose_name": "paiement", "verbose_name_plural": "paiements"},
        ),
        migrations.AlterModelOptions(
            name="subscription",
            options={
                "verbose_name": "abonnement",
                "verbose_name_plural": "abonnements",
            },
        ),
    ]
