"""Intitulés français dans l'administration (options seulement, aucune modification de table)."""


from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("audit", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="auditlog",
            options={
                "verbose_name": "entrée du journal",
                "verbose_name_plural": "journal d'activité",
            },
        ),
    ]
