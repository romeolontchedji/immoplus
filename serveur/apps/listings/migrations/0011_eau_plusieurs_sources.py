"""Eau : plusieurs sources par chambre (demande du porteur, 2026-10-20) — forage, puits, compteur… à la fois.

Chaque annonce garde sa source actuelle, devenue la première de sa liste. Retour arrière : la première source.
"""

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0008_domaine_demo_immoplus"),
        ("listings", "0010_types_sanitaires"),
    ]

    operations = [
        migrations.AddField(
            model_name="listing",
            name="water_sources",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(
                    choices=[
                        ("individual", "Compteur d'eau personnel"),
                        ("sub_meter", "Décompteur"),
                        ("running", "Eau courante partagée"),
                        ("borehole", "Forage"),
                        ("well", "Puits"),
                    ],
                    max_length=10,
                ),
                default=list,
                size=None,
                verbose_name="eau",
            ),
        ),
        migrations.RunSQL(
            "UPDATE listings SET water_sources = ARRAY[water_source]::varchar(10)[]",
            reverse_sql="UPDATE listings SET water_source = COALESCE(water_sources[1], 'running')",
        ),
        migrations.RemoveConstraint(
            model_name="listing",
            name="listings_eau_valide",
        ),
        migrations.RemoveField(
            model_name="listing",
            name="water_source",
        ),
        migrations.AddConstraint(
            model_name="listing",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    (
                        "water_sources__contained_by",
                        ["individual", "sub_meter", "running", "borehole", "well"],
                    )
                ),
                name="listings_eau_valide",
            ),
        ),
        migrations.AddConstraint(
            model_name="listing",
            constraint=models.CheckConstraint(
                condition=models.Q(("water_sources__len__gte", 1)),
                name="listings_eau_renseignee",
            ),
        ),
    ]
