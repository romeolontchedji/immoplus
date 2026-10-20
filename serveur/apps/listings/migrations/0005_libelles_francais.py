"""Intitulés français dans l'administration (options seulement, aucune modification de table)."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("listings", "0004_types_de_logement_elargis"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="district",
            options={
                "ordering": ["sort_order", "name"],
                "verbose_name": "quartier",
                "verbose_name_plural": "quartiers",
            },
        ),
        migrations.AlterModelOptions(
            name="listing",
            options={"verbose_name": "annonce", "verbose_name_plural": "annonces"},
        ),
    ]
