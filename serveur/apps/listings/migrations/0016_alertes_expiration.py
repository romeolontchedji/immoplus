"""Alertes : date de la dernière activité du locataire (une alerte sans nouvelle depuis 14 jours est mise en pause)."""

import django.db.models.functions.datetime
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("listings", "0015_loyer_prepaye"),
    ]

    operations = [
        migrations.AddField(
            model_name="alert",
            name="last_engaged_at",
            field=models.DateTimeField(
                db_default=django.db.models.functions.datetime.Now(),
                default=django.utils.timezone.now,
                verbose_name="dernière activité",
            ),
        ),
    ]
