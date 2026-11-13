"""Loyer pré-payé : nombre de mois de loyer à régler avant d'entrer dans la chambre (0 = aucun)."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("listings", "0014_reponse_du_gerant_aux_avis"),
    ]

    operations = [
        migrations.AddField(
            model_name="listing",
            name="prepaid_months",
            field=models.SmallIntegerField(
                db_default=0, default=0, verbose_name="pré-payé (mois)"
            ),
        ),
        migrations.AddConstraint(
            model_name="listing",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("prepaid_months__gte", 0),
                    ("prepaid_months__lte", 12),
                ),
                name="listings_prepaye_borne",
            ),
        ),
    ]
