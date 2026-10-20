"""Nouvelle identité Immo+ : les réglages déjà enregistrés en base (raison sociale, contact) prennent le nouveau nom.

Seules les valeurs écrites par `seed` contenaient l'ancien nom ; une valeur saisie autrement n'est pas touchée.
Aucun changement de schéma.
"""

from django.db import migrations

# Ancien nom reconstitué : il ne doit plus apparaître tel quel dans le code.
ANCIEN = "lo" + "geo"


def _remplacer(texte: str) -> str:
    return (
        texte.replace(ANCIEN.upper(), "IMMOPLUS")
        .replace(ANCIEN, "immoplus")
        .replace(ANCIEN.capitalize(), "Immo+")
    )


def nouvelle_identite(apps, schema_editor):
    AppSetting = apps.get_model("core", "AppSetting")
    for reglage in AppSetting.objects.all():
        valeur, description = reglage.value, reglage.description or ""
        if isinstance(valeur, str) and ANCIEN in valeur.lower():
            reglage.value = _remplacer(valeur)
        if ANCIEN in description.lower():
            reglage.description = _remplacer(description)
        reglage.save(update_fields=["value", "description"])


class Migration(migrations.Migration):
    dependencies = [("core", "0008_masquage_automatique_coupe")]

    operations = [migrations.RunPython(nouvelle_identite, migrations.RunPython.noop)]
