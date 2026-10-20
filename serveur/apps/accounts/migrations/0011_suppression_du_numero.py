"""Le numéro de téléphone n'est plus conservé (demande du porteur, 2026-10-20 ; ADR 0009) : les colonnes sont
supprimées, avec les numéros déjà enregistrés. Seul le nom d'utilisateur identifie un compte.
"""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0010_suppression_codes_sms"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="user",
            name="users_clientele_a_un_numero",
        ),
        migrations.RemoveIndex(
            model_name="user",
            name="users_telephone_idx",
        ),
        migrations.RemoveField(
            model_name="user",
            name="phone_e164",
        ),
        migrations.RemoveField(
            model_name="user",
            name="phone_verified_at",
        ),
    ]
