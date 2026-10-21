"""Intitulés français des relations dans l'administration (aucune instruction SQL)."""


import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0005_intitules_des_champs"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="appsetting",
            name="updated_by",
            field=models.ForeignKey(
                blank=True,
                db_column="updated_by",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to=settings.AUTH_USER_MODEL,
                verbose_name="modifié par",
            ),
        ),
    ]
