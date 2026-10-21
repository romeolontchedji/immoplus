"""Masquage automatique « sans confirmation » coupé par défaut (plan d'actions v3, 19/10/2026).

Le bouton « Confirmer la disponibilité » a disparu : une annonce ne doit plus être masquée faute de confirmation.
Les bases déjà initialisées gardaient 14 jours (valeur écrite par `seed`) : on passe à 0 (= jamais). Une autre
valeur, choisie volontairement dans l'administration, est conservée. Aucun changement de schéma.
"""

from django.db import migrations


def couper_le_masquage(apps, schema_editor):
    AppSetting = apps.get_model("core", "AppSetting")
    AppSetting.objects.filter(key="STALE_HIDE_DAYS", value=14).update(value=0)


class Migration(migrations.Migration):
    dependencies = [("core", "0007_messagerie_sans_filtrage")]

    operations = [migrations.RunPython(couper_le_masquage, migrations.RunPython.noop)]
