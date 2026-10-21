"""Intitulés français dans l'administration (options seulement, aucune modification de table)."""


from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0005_occupation_utilisateur"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="gerantprofile",
            options={
                "base_manager_name": "objects",
                "verbose_name": "gérant",
                "verbose_name_plural": "gérants",
            },
        ),
        migrations.AlterModelOptions(
            name="user",
            options={"verbose_name": "compte", "verbose_name_plural": "comptes"},
        ),
    ]
