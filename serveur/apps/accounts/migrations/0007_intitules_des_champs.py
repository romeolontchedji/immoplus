"""Intitulés français des champs dans l'administration (aucune instruction SQL)."""


import django.db.models.deletion
import django.db.models.functions.datetime
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0006_libelles_francais"),
    ]

    operations = [
        migrations.AlterField(
            model_name="gerantprofile",
            name="created_at",
            field=models.DateTimeField(
                db_default=django.db.models.functions.datetime.Now(),
                default=django.utils.timezone.now,
                verbose_name="créé le",
            ),
        ),
        migrations.AlterField(
            model_name="gerantprofile",
            name="created_by",
            field=models.ForeignKey(
                db_column="created_by",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to=settings.AUTH_USER_MODEL,
                verbose_name="créé par",
            ),
        ),
        migrations.AlterField(
            model_name="gerantprofile",
            name="display_name",
            field=models.CharField(
                blank=True, max_length=120, null=True, verbose_name="nom affiché"
            ),
        ),
        migrations.AlterField(
            model_name="gerantprofile",
            name="median_response_min",
            field=models.IntegerField(
                blank=True, null=True, verbose_name="délai médian de réponse (min)"
            ),
        ),
        migrations.AlterField(
            model_name="gerantprofile",
            name="response_rate_30d",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=5,
                null=True,
                verbose_name="taux de réponse (30 j)",
            ),
        ),
        migrations.AlterField(
            model_name="gerantprofile",
            name="updated_at",
            field=models.DateTimeField(
                auto_now=True,
                db_default=django.db.models.functions.datetime.Now(),
                verbose_name="modifié le",
            ),
        ),
        migrations.AlterField(
            model_name="gerantprofile",
            name="user",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                primary_key=True,
                related_name="gerant_profile",
                serialize=False,
                to=settings.AUTH_USER_MODEL,
                verbose_name="compte",
            ),
        ),
        migrations.AlterField(
            model_name="gerantprofile",
            name="verification_status",
            field=models.CharField(
                choices=[
                    ("pending", "En attente"),
                    ("interview", "Entretien"),
                    ("verified", "Vérifié"),
                    ("rejected", "Refusé"),
                ],
                db_default="pending",
                default="pending",
                max_length=12,
                verbose_name="vérification",
            ),
        ),
        migrations.AlterField(
            model_name="gerantprofile",
            name="verified_at",
            field=models.DateTimeField(
                blank=True, null=True, verbose_name="vérifié le"
            ),
        ),
        migrations.AlterField(
            model_name="gerantprofile",
            name="verified_by",
            field=models.ForeignKey(
                blank=True,
                db_column="verified_by",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to=settings.AUTH_USER_MODEL,
                verbose_name="vérifié par",
            ),
        ),
        migrations.AlterField(
            model_name="gerantprofile",
            name="zone",
            field=models.CharField(max_length=160, verbose_name="zone"),
        ),
        migrations.AlterField(
            model_name="user",
            name="avatar_path",
            field=models.CharField(
                blank=True, max_length=255, null=True, verbose_name="photo"
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="created_at",
            field=models.DateTimeField(
                db_default=django.db.models.functions.datetime.Now(),
                default=django.utils.timezone.now,
                verbose_name="créé le",
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="deleted_at",
            field=models.DateTimeField(
                blank=True, null=True, verbose_name="supprimé le"
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="email",
            field=models.EmailField(
                blank=True,
                max_length=254,
                null=True,
                unique=True,
                verbose_name="e-mail",
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="full_name",
            field=models.CharField(max_length=120, verbose_name="nom complet"),
        ),
        migrations.AlterField(
            model_name="user",
            name="last_seen_at",
            field=models.DateTimeField(
                blank=True, null=True, verbose_name="dernière activité"
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="occupation",
            field=models.CharField(
                blank=True,
                choices=[
                    ("student_up", "Étudiant(e) à l'UP"),
                    ("student_other", "Étudiant(e) ailleurs"),
                    ("employee", "Salarié(e)"),
                    ("self_employed", "Indépendant(e)"),
                    ("other", "Autre"),
                ],
                max_length=16,
                null=True,
                verbose_name="tu es",
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="phone_e164",
            field=models.CharField(
                blank=True,
                max_length=16,
                null=True,
                unique=True,
                verbose_name="téléphone",
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="phone_verified_at",
            field=models.DateTimeField(
                blank=True, null=True, verbose_name="numéro vérifié le"
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[
                    ("client", "Locataire"),
                    ("gerant", "Gérant"),
                    ("moderator", "Modérateur"),
                    ("admin", "Administrateur"),
                ],
                max_length=12,
                verbose_name="rôle",
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="status",
            field=models.CharField(
                choices=[
                    ("active", "Actif"),
                    ("suspended", "Suspendu"),
                    ("banned", "Banni"),
                    ("deleted", "Supprimé"),
                ],
                db_default="active",
                default="active",
                max_length=12,
                verbose_name="statut",
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="suspended_until",
            field=models.DateTimeField(
                blank=True, null=True, verbose_name="suspendu jusqu'au"
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="terms_accepted_at",
            field=models.DateTimeField(
                blank=True, null=True, verbose_name="conditions acceptées le"
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="terms_version",
            field=models.CharField(
                blank=True,
                max_length=16,
                null=True,
                verbose_name="version des conditions",
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="token_version",
            field=models.IntegerField(
                db_default=0, default=0, verbose_name="version de sécurité"
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="updated_at",
            field=models.DateTimeField(
                auto_now=True,
                db_default=django.db.models.functions.datetime.Now(),
                verbose_name="modifié le",
            ),
        ),
    ]
