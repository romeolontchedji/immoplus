"""Intitulés français dans l'administration (options seulement, aucune modification de table)."""


from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0003_statistiques_journalieres"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="appsetting",
            options={"verbose_name": "paramètre", "verbose_name_plural": "paramètres"},
        ),
    ]
