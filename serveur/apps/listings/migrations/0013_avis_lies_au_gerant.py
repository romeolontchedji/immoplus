"""L'avis est lié au gérant en plus de la chambre : sa réputation survit à l'archivage des annonces louées."""

import django.db.models.deletion
from django.db import migrations, models
from django.db.models import OuterRef, Subquery


def renseigner_le_gerant(apps, schema_editor):
    Review, Listing = apps.get_model("listings", "Review"), apps.get_model("listings", "Listing")
    Review.objects.filter(gerant__isnull=True).update(
        gerant_id=Subquery(Listing.objects.filter(pk=OuterRef("listing_id")).values("gerant_id")[:1])
    )


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0011_suppression_du_numero"),
        ("listings", "0012_cautions_compteurs_et_alertes"),
    ]

    operations = [
        migrations.AddField(
            model_name="review",
            name="gerant",
            field=models.ForeignKey(
                db_column="gerant_id",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="accounts.gerantprofile",
                verbose_name="gérant",
            ),
        ),
        migrations.RunPython(renseigner_le_gerant, migrations.RunPython.noop),
        migrations.AddIndex(
            model_name="review",
            index=models.Index(fields=["gerant", "is_hidden", "-created_at"], name="avis_gerant_idx"),
        ),
    ]
