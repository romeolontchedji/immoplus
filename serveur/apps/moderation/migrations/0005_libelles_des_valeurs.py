"""Libellés français des valeurs de modération (aucune instruction SQL)."""


from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("moderation", "0004_intitules_des_relations"),
    ]

    operations = [
        migrations.AlterField(
            model_name="moderationaction",
            name="action",
            field=models.CharField(
                choices=[
                    ("message_masked", "Message masqué"),
                    ("message_deleted", "Message supprimé"),
                    ("listing_hidden", "Annonce masquée"),
                    ("listing_removed", "Annonce retirée"),
                    ("warning", "Avertissement"),
                    ("suspension", "Suspension"),
                    ("ban", "Bannissement"),
                    ("reinstatement", "Réhabilitation"),
                ],
                max_length=20,
                verbose_name="action",
            ),
        ),
        migrations.AlterField(
            model_name="report",
            name="reason_code",
            field=models.CharField(
                choices=[
                    ("fake_listing", "Fausse annonce"),
                    ("already_rented", "Déjà louée"),
                    ("price_mismatch", "Prix différent"),
                    ("contact_leak", "Coordonnées partagées"),
                    ("harassment", "Harcèlement"),
                    ("scam", "Arnaque"),
                    ("other", "Autre"),
                ],
                max_length=24,
                verbose_name="motif",
            ),
        ),
        migrations.AlterField(
            model_name="report",
            name="source",
            field=models.CharField(
                choices=[("user", "Utilisateur"), ("system", "Détection automatique")],
                db_default="user",
                default="user",
                max_length=10,
                verbose_name="origine",
            ),
        ),
        migrations.AlterField(
            model_name="report",
            name="status",
            field=models.CharField(
                choices=[
                    ("open", "Ouvert"),
                    ("in_review", "En cours d'examen"),
                    ("resolved_actioned", "Traité : sanction"),
                    ("resolved_dismissed", "Classé sans suite"),
                ],
                db_default="open",
                default="open",
                max_length=18,
                verbose_name="statut",
            ),
        ),
        migrations.AlterField(
            model_name="report",
            name="target_type",
            field=models.CharField(
                choices=[
                    ("listing", "Annonce"),
                    ("message", "Message"),
                    ("user", "Compte"),
                    ("conversation", "Conversation"),
                ],
                max_length=12,
                verbose_name="type de cible",
            ),
        ),
    ]
