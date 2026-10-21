"""Intitulés français des relations dans l'administration (aucune instruction SQL)."""


import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0007_intitules_des_champs"),
        ("listings", "0006_intitules_des_champs"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="listing",
            name="gerant",
            field=models.ForeignKey(
                db_column="gerant_id",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="listings",
                to="accounts.gerantprofile",
                verbose_name="gérant",
            ),
        ),
        migrations.AlterField(
            model_name="roomtype",
            name="proposed_by",
            field=models.ForeignKey(
                blank=True,
                db_column="proposed_by",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="accounts.gerantprofile",
                verbose_name="proposé par",
            ),
        ),
        migrations.AlterField(
            model_name="roomtype",
            name="reviewed_by",
            field=models.ForeignKey(
                blank=True,
                db_column="reviewed_by",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to=settings.AUTH_USER_MODEL,
                verbose_name="examiné par",
            ),
        ),
    ]
