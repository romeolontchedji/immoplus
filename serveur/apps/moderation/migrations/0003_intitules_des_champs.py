"""Intitulés français des champs dans l'administration (aucune instruction SQL)."""


import django.db.models.deletion
import django.db.models.functions.datetime
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("moderation", "0002_libelles_francais"),
    ]

    operations = [
        migrations.AlterField(
            model_name="moderationaction",
            name="action",
            field=models.CharField(max_length=20, verbose_name="action"),
        ),
        migrations.AlterField(
            model_name="moderationaction",
            name="created_at",
            field=models.DateTimeField(
                db_default=django.db.models.functions.datetime.Now(),
                default=django.utils.timezone.now,
                verbose_name="créé le",
            ),
        ),
        migrations.AlterField(
            model_name="moderationaction",
            name="ends_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="jusqu'au"),
        ),
        migrations.AlterField(
            model_name="moderationaction",
            name="reason",
            field=models.TextField(verbose_name="motif"),
        ),
        migrations.AlterField(
            model_name="moderationaction",
            name="report",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="actions",
                to="moderation.report",
                verbose_name="signalement",
            ),
        ),
        migrations.AlterField(
            model_name="moderationaction",
            name="revoked_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="levée le"),
        ),
        migrations.AlterField(
            model_name="report",
            name="created_at",
            field=models.DateTimeField(
                db_default=django.db.models.functions.datetime.Now(),
                default=django.utils.timezone.now,
                verbose_name="créé le",
            ),
        ),
        migrations.AlterField(
            model_name="report",
            name="details",
            field=models.CharField(
                blank=True, default="", max_length=500, verbose_name="détails"
            ),
        ),
        migrations.AlterField(
            model_name="report",
            name="reason_code",
            field=models.CharField(max_length=24, verbose_name="motif"),
        ),
        migrations.AlterField(
            model_name="report",
            name="resolution_note",
            field=models.CharField(
                blank=True,
                default="",
                max_length=500,
                verbose_name="note de traitement",
            ),
        ),
        migrations.AlterField(
            model_name="report",
            name="resolved_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="traité le"),
        ),
        migrations.AlterField(
            model_name="report",
            name="source",
            field=models.CharField(
                db_default="user", default="user", max_length=10, verbose_name="origine"
            ),
        ),
        migrations.AlterField(
            model_name="report",
            name="status",
            field=models.CharField(
                db_default="open", default="open", max_length=18, verbose_name="statut"
            ),
        ),
        migrations.AlterField(
            model_name="report",
            name="target_id",
            field=models.UUIDField(verbose_name="cible"),
        ),
        migrations.AlterField(
            model_name="report",
            name="target_type",
            field=models.CharField(max_length=12, verbose_name="type de cible"),
        ),
    ]
