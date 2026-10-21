"""Intitulés français des champs dans l'administration (aucune instruction SQL)."""


import django.db.models.functions.datetime
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("audit", "0002_libelles_francais"),
    ]

    operations = [
        migrations.AlterField(
            model_name="auditlog",
            name="action",
            field=models.CharField(max_length=64, verbose_name="action"),
        ),
        migrations.AlterField(
            model_name="auditlog",
            name="actor_role",
            field=models.CharField(
                blank=True, max_length=12, null=True, verbose_name="rôle de l'auteur"
            ),
        ),
        migrations.AlterField(
            model_name="auditlog",
            name="created_at",
            field=models.DateTimeField(
                db_default=django.db.models.functions.datetime.Now(),
                default=django.utils.timezone.now,
                verbose_name="créé le",
            ),
        ),
        migrations.AlterField(
            model_name="auditlog",
            name="ip",
            field=models.GenericIPAddressField(
                blank=True, null=True, verbose_name="adresse IP"
            ),
        ),
        migrations.AlterField(
            model_name="auditlog",
            name="metadata",
            field=models.JSONField(db_default={}, default=dict, verbose_name="détails"),
        ),
        migrations.AlterField(
            model_name="auditlog",
            name="target_id",
            field=models.UUIDField(blank=True, null=True, verbose_name="cible"),
        ),
        migrations.AlterField(
            model_name="auditlog",
            name="target_type",
            field=models.CharField(
                blank=True, max_length=32, null=True, verbose_name="type de cible"
            ),
        ),
        migrations.AlterField(
            model_name="auditlog",
            name="user_agent",
            field=models.CharField(
                blank=True, max_length=255, null=True, verbose_name="navigateur"
            ),
        ),
    ]
