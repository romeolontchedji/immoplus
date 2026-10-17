"""Intitulés français des relations dans l'administration (aucune instruction SQL)."""


import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0007_intitules_des_champs"),
        ("billing", "0004_intitules_des_champs"),
    ]

    operations = [
        migrations.AlterField(
            model_name="payment",
            name="gerant",
            field=models.ForeignKey(
                db_column="gerant_id",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to="accounts.gerantprofile",
                verbose_name="gérant",
            ),
        ),
        migrations.AlterField(
            model_name="subscription",
            name="gerant",
            field=models.ForeignKey(
                db_column="gerant_id",
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to="accounts.gerantprofile",
                verbose_name="gérant",
            ),
        ),
    ]
