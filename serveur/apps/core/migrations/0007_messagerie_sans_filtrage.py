"""Messagerie sans filtrage des coordonnées (décision du porteur, 2026-10-18).

Les bases déjà initialisées gardaient « mask » (écrit par `seed`) : on le passe à « off ». Une valeur choisie
volontairement (« flag », « block ») est conservée. Aucun changement de schéma.
"""

from django.db import migrations


def couper_le_filtrage(apps, schema_editor):
    AppSetting = apps.get_model("core", "AppSetting")
    AppSetting.objects.filter(key="CONTACT_LEAK_MODE", value="mask").update(value="off")


class Migration(migrations.Migration):
    dependencies = [("core", "0006_intitules_des_relations")]

    operations = [migrations.RunPython(couper_le_filtrage, migrations.RunPython.noop)]
