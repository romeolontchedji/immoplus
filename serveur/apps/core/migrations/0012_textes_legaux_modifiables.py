"""Textes légaux modifiables depuis l'administration (Markdown) ; lecture seule pour le rôle du site public."""

import django.db.models.deletion
import django.db.models.functions.datetime
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

DROITS = r"""
DO $droits$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app') THEN
    REVOKE INSERT, UPDATE, DELETE ON legal_documents FROM app;
  END IF;
END
$droits$;
"""

ANNULER_DROITS = r"""
DO $droits$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app') THEN
    GRANT INSERT, UPDATE, DELETE ON legal_documents TO app;
  END IF;
END
$droits$;
"""


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0011_session_admin_une_heure"),
    ]

    operations = [
        migrations.CreateModel(
            name="LegalDocument",
            fields=[
                (
                    "slug",
                    models.CharField(
                        max_length=20, primary_key=True, serialize=False, verbose_name="document"
                    ),
                ),
                ("body_md", models.TextField(verbose_name="texte")),
                (
                    "updated_at",
                    models.DateTimeField(
                        db_default=django.db.models.functions.datetime.Now(),
                        default=django.utils.timezone.now,
                        verbose_name="modifié le",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        db_column="updated_by",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="modifié par",
                    ),
                ),
            ],
            options={
                "verbose_name": "texte légal",
                "verbose_name_plural": "textes légaux",
                "db_table": "legal_documents",
            },
        ),
        migrations.RunSQL(DROITS, ANNULER_DROITS),
    ]
