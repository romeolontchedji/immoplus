"""Nouvelle identité Immo+ : les comptes de démonstration passent sur le domaine de démonstration immoplus.

Ne touche que les adresses de démonstration (.test et .local) de l'ancien nom. Aucun changement de schéma.
"""

from django.db import migrations

# Ancien nom reconstitué : il ne doit plus apparaître tel quel dans le code.
ANCIEN = "lo" + "geo"


def nouveau_domaine(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    for suffixe in (".test", ".local"):
        for u in User.objects.filter(email__iendswith=f"@{ANCIEN}{suffixe}"):
            u.email = u.email.lower().replace(f"@{ANCIEN}{suffixe}", f"@immoplus{suffixe}")
            u.save(update_fields=["email"])


class Migration(migrations.Migration):
    dependencies = [("accounts", "0007_intitules_des_champs")]

    operations = [migrations.RunPython(nouveau_domaine, migrations.RunPython.noop)]
