"""EF-ABO-06 : chaque gérant déjà vérifié reçoit le plan Gratuit V1 (les suivants le reçoivent à la vérification)."""

import datetime

from django.db import migrations
from django.utils import timezone


def attribuer(apps, schema_editor):
    GerantProfile = apps.get_model("accounts", "GerantProfile")
    Subscription = apps.get_model("billing", "Subscription")
    maintenant = timezone.now()
    deja = set(Subscription.objects.exclude(status="expired").values_list("gerant_id", flat=True))
    Subscription.objects.bulk_create(
        [
            Subscription(
                gerant_id=g, plan_code="free_v1", status="active", current_period_start=maintenant,
                current_period_end=maintenant + datetime.timedelta(days=30 * 1200),
            )  # fmt: skip
            for g in GerantProfile.objects.filter(verification_status="verified").values_list("user_id", flat=True)
            if g not in deja
        ]
    )


class Migration(migrations.Migration):
    dependencies = [
        ("billing", "0001_abonnements_et_paiements"),
        ("accounts", "0005_occupation_utilisateur"),
    ]

    operations = [migrations.RunPython(attribuer, migrations.RunPython.noop)]
