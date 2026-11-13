"""Messages entre l'équipe et les utilisateurs (réponses aux questions, aux avis, suites de modération)."""

import uuid

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("moderation", "0005_libelles_des_valeurs"),
    ]

    operations = [
        migrations.CreateModel(
            name="MessageEquipe",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("vers_utilisateur", models.BooleanField(verbose_name="écrit à la personne")),
                ("objet", models.CharField(blank=True, default="", max_length=120, verbose_name="objet")),
                ("corps", models.TextField(verbose_name="message")),
                ("contexte_type", models.CharField(blank=True, default="", max_length=12, verbose_name="à propos de")),
                ("contexte_id", models.UUIDField(blank=True, null=True, verbose_name="référence")),
                ("lu_le", models.DateTimeField(blank=True, null=True, verbose_name="lu le")),
                ("traite_le", models.DateTimeField(blank=True, null=True, verbose_name="traité le")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, verbose_name="envoyé le")),
                ("auteur", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL, verbose_name="auteur")),
                ("utilisateur", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="+", to=settings.AUTH_USER_MODEL, verbose_name="personne")),
            ],
            options={
                "verbose_name": "message de l'équipe",
                "verbose_name_plural": "messages de l'équipe",
                "db_table": "team_messages",
                "ordering": ["created_at"],
                "indexes": [models.Index(fields=["utilisateur", "created_at"], name="equipe_fil_idx")],
            },
        ),
    ]
