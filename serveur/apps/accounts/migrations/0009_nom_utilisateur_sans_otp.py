"""Identification par nom d'utilisateur, sans code SMS (ADR 0009).

Les comptes existants reçoivent un nom d'utilisateur tiré de leur nom (« aicha.zongo », « aicha.zongo2 »…) et leur
nom complet est découpé en prénom et nom. Le numéro n'est plus unique. Le rôle `app` peut modifier les nouvelles
colonnes (nom d'utilisateur, prénom, nom, e-mail confirmé depuis le profil, clé de secours).
"""

import re
import unicodedata

import django.db.models.functions.text
from django.db import migrations, models


def _base(texte: str) -> str:
    sans_accents = (
        unicodedata.normalize("NFKD", texte or "").encode("ascii", "ignore").decode().lower()
    )
    base = re.sub(r"[^a-z0-9]+", ".", sans_accents).strip(".")
    base = re.sub(r"\.{2,}", ".", base)[:26].strip(".")
    return base if len(base) >= 3 else (base + "immo")[:26].strip(".") or "immo"


def remplir(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    pris = set()
    for u in User.objects.order_by("created_at"):
        parties = (u.full_name or "").split()
        u.first_name = (parties[0] if parties else "")[:60]
        u.last_name = " ".join(parties[1:])[:60]
        if u.role in ("client", "gerant") and not u.username:
            base, n = _base(u.full_name), 1
            candidat = base
            while candidat in pris:
                n += 1
                candidat = f"{base}{n}"
            u.username = candidat
        if u.username:
            pris.add(u.username)
        u.save(update_fields=["first_name", "last_name", "username"])


DROITS = """
DO $droits$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app') THEN
    GRANT UPDATE (username, first_name, last_name, email, email_verified_at, recovery_key_hash,
                  recovery_key_created_at) ON users TO app;
  END IF;
END $droits$;
"""
RETIRER_DROITS = """
DO $droits$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app') THEN
    REVOKE UPDATE (username, first_name, last_name, email, email_verified_at, recovery_key_hash,
                   recovery_key_created_at) ON users FROM app;
  END IF;
END $droits$;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0008_domaine_demo_immoplus"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="email_verified_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="e-mail confirmé le"),
        ),
        migrations.AddField(
            model_name="user",
            name="first_name",
            field=models.CharField(db_default="", default="", max_length=60, verbose_name="prénom"),
        ),
        migrations.AddField(
            model_name="user",
            name="last_name",
            field=models.CharField(db_default="", default="", max_length=60, verbose_name="nom"),
        ),
        migrations.AddField(
            model_name="user",
            name="recovery_key_created_at",
            field=models.DateTimeField(
                blank=True, null=True, verbose_name="clé de secours créée le"
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="recovery_key_hash",
            field=models.CharField(
                blank=True,
                max_length=255,
                null=True,
                verbose_name="empreinte de la clé de secours",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="username",
            field=models.CharField(
                blank=True, max_length=30, null=True, verbose_name="nom d'utilisateur"
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="phone_e164",
            field=models.CharField(blank=True, max_length=16, null=True, verbose_name="téléphone"),
        ),
        migrations.AddIndex(
            model_name="user",
            index=models.Index(fields=["phone_e164"], name="users_telephone_idx"),
        ),
        migrations.RunPython(remplir, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="user",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(("role", "client"), _negated=True),
                    ("username__isnull", False),
                    _connector="OR",
                ),
                name="users_locataire_a_un_nom_utilisateur",
            ),
        ),
        migrations.AddConstraint(
            model_name="user",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("username__isnull", True),
                    ("username__regex", "^[a-z0-9][a-z0-9._]{1,28}[a-z0-9]$"),
                    _connector="OR",
                ),
                name="users_nom_utilisateur_valide",
            ),
        ),
        migrations.AddConstraint(
            model_name="user",
            constraint=models.UniqueConstraint(
                django.db.models.functions.text.Lower("username"),
                name="users_nom_utilisateur_unique",
            ),
        ),
        migrations.RunSQL(DROITS, reverse_sql=RETIRER_DROITS),
    ]
