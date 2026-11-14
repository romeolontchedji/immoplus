"""Frais de visite : montant demandé pour faire visiter la chambre (0 = aucun)."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("listings", "0017_adresse_privee_retiree")]

    operations = [
        migrations.AddField(
            model_name="listing",
            name="visit_fee_amount",
            field=models.IntegerField(db_default=0, default=0, verbose_name="frais de visite (F)"),
        ),
        migrations.AddConstraint(
            model_name="listing",
            constraint=models.CheckConstraint(
                condition=models.Q(("visit_fee_amount__gte", 0)),
                name="listings_frais_visite_positifs",
            ),
        ),
    ]
