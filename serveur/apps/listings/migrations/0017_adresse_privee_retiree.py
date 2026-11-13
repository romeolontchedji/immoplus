"""L'adresse précise d'une chambre n'est plus demandée ni conservée.

Première étape : le champ quitte le modèle et les adresses déjà saisies sont effacées. La colonne reste en base avec une
valeur par défaut vide, pour qu'une ancienne version du serveur encore en marche pendant le déploiement puisse écrire
sans erreur ; une migration suivante la supprimera (migration en deux temps)."""

from django.db import migrations

RETIRER = """
UPDATE listings SET address_private = '' WHERE address_private <> '';
ALTER TABLE listings ALTER COLUMN address_private SET DEFAULT '';
"""


class Migration(migrations.Migration):
    dependencies = [
        ("listings", "0016_alertes_expiration"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[migrations.RemoveField(model_name="listing", name="address_private")],
            database_operations=[migrations.RunSQL(RETIRER, reverse_sql=migrations.RunSQL.noop)],
        ),
    ]
