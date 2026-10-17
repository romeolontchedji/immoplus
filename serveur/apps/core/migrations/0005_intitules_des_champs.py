"""Intitulés français des champs dans l'administration (aucune instruction SQL)."""


import django.db.models.functions.datetime
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0004_libelles_francais"),
    ]

    operations = [
        migrations.AlterField(
            model_name="appsetting",
            name="description",
            field=models.CharField(max_length=255, verbose_name="description"),
        ),
        migrations.AlterField(
            model_name="appsetting",
            name="key",
            field=models.CharField(
                max_length=64, primary_key=True, serialize=False, verbose_name="clé"
            ),
        ),
        migrations.AlterField(
            model_name="appsetting",
            name="updated_at",
            field=models.DateTimeField(
                db_default=django.db.models.functions.datetime.Now(),
                default=django.utils.timezone.now,
                verbose_name="modifié le",
            ),
        ),
        migrations.AlterField(
            model_name="appsetting",
            name="value",
            field=models.JSONField(verbose_name="valeur"),
        ),
    ]
