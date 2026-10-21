"""Intitulés français dans l'administration (options seulement, aucune modification de table)."""


from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("moderation", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="moderationaction",
            options={
                "verbose_name": "décision de modération",
                "verbose_name_plural": "décisions de modération",
            },
        ),
        migrations.AlterModelOptions(
            name="report",
            options={
                "verbose_name": "signalement",
                "verbose_name_plural": "signalements",
            },
        ),
    ]
