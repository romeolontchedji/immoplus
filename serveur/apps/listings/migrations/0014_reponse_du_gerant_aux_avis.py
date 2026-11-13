"""Réponse publique du gérant à un avis."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("listings", "0013_avis_lies_au_gerant"),
    ]

    operations = [
        migrations.AddField(
            model_name="review",
            name="owner_reply",
            field=models.TextField(blank=True, db_default="", default="", verbose_name="réponse du gérant"),
        ),
        migrations.AddField(
            model_name="review",
            name="owner_replied_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="réponse du gérant le"),
        ),
    ]
