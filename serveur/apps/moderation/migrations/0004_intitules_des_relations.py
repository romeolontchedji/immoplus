"""Intitulés français des relations dans l'administration (aucune instruction SQL)."""


import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("chat", "0001_initial"),
        ("listings", "0007_intitules_des_relations"),
        ("moderation", "0003_intitules_des_champs"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="moderationaction",
            name="actor",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to=settings.AUTH_USER_MODEL,
                verbose_name="auteur",
            ),
        ),
        migrations.AlterField(
            model_name="moderationaction",
            name="target_listing",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="listings.listing",
                verbose_name="annonce visée",
            ),
        ),
        migrations.AlterField(
            model_name="moderationaction",
            name="target_message",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="chat.message",
                verbose_name="message visé",
            ),
        ),
        migrations.AlterField(
            model_name="moderationaction",
            name="target_user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to=settings.AUTH_USER_MODEL,
                verbose_name="compte visé",
            ),
        ),
        migrations.AlterField(
            model_name="report",
            name="assigned_to",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to=settings.AUTH_USER_MODEL,
                verbose_name="assigné à",
            ),
        ),
        migrations.AlterField(
            model_name="report",
            name="listing",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="listings.listing",
                verbose_name="annonce",
            ),
        ),
        migrations.AlterField(
            model_name="report",
            name="reporter",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to=settings.AUTH_USER_MODEL,
                verbose_name="signalé par",
            ),
        ),
        migrations.AlterField(
            model_name="report",
            name="resolved_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to=settings.AUTH_USER_MODEL,
                verbose_name="traité par",
            ),
        ),
    ]
