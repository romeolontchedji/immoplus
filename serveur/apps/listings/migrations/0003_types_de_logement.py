"""Types de logement en table (décision V1, docs/plan-actions-v2.md) : les 4 officiels, et les propositions des gérants.

Le rôle `app` (site et API) ne peut qu'ajouter une proposition en attente : le déclencheur force `pending` et
l'ordre par défaut, et les droits de modification et de suppression lui sont retirés (validation et rattachement
passent par l'administration, rôle `admin_app`).
"""

import django.contrib.postgres.fields
import django.db.models.deletion
import django.db.models.functions.datetime
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

OFFICIELS = [
    ("single", "Chambre simple", 1),
    ("entree_coucher", "Entrée-coucher", 2),
    ("chambre_salon", "Chambre-salon", 3),
    ("studio", "Studio", 4),
]

GARDE = r"""
CREATE OR REPLACE FUNCTION room_types_garde() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF current_user = 'app' THEN
    NEW.status := 'pending';
    NEW.sort_order := 100;
    NEW.reviewed_by := NULL;
    NEW.reviewed_at := NULL;
  END IF;
  RETURN NEW;
END;
$$;
CREATE TRIGGER room_types_garde BEFORE INSERT ON room_types
  FOR EACH ROW EXECUTE FUNCTION room_types_garde();
DO $droits$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app') THEN
    REVOKE UPDATE, DELETE ON room_types FROM app;
  END IF;
END
$droits$;
"""

ANNULER_GARDE = r"""
DROP TRIGGER IF EXISTS room_types_garde ON room_types;
DROP FUNCTION IF EXISTS room_types_garde();
"""


def creer_officiels(apps, schema_editor):
    RoomType = apps.get_model("listings", "RoomType")
    for slug, label, ordre in OFFICIELS:
        RoomType.objects.update_or_create(
            slug=slug, defaults={"label": label, "status": "approved", "sort_order": ordre}
        )


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0005_occupation_utilisateur"),
        ("listings", "0002_fil_favoris_alertes"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="RoomType",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("slug", models.CharField(max_length=40, unique=True)),
                ("label", models.CharField(max_length=40)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("approved", "Validé"),
                            ("pending", "Proposé, à valider"),
                        ],
                        db_default="pending",
                        default="pending",
                        max_length=10,
                    ),
                ),
                ("sort_order", models.SmallIntegerField(db_default=100, default=100)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "created_at",
                    models.DateTimeField(
                        db_default=django.db.models.functions.datetime.Now(),
                        default=django.utils.timezone.now,
                    ),
                ),
            ],
            options={
                "verbose_name": "type de logement",
                "verbose_name_plural": "types de logement",
                "db_table": "room_types",
                "ordering": ["sort_order", "label"],
            },
        ),
        migrations.RemoveConstraint(
            model_name="listing",
            name="listings_type_valide",
        ),
        migrations.AlterField(
            model_name="alert",
            name="room_types",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(max_length=40),
                db_default=[],
                default=list,
                size=None,
            ),
        ),
        migrations.AlterField(
            model_name="listing",
            name="room_type",
            field=models.CharField(max_length=40),
        ),
        migrations.AddField(
            model_name="roomtype",
            name="proposed_by",
            field=models.ForeignKey(
                blank=True,
                db_column="proposed_by",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="accounts.gerantprofile",
            ),
        ),
        migrations.AddField(
            model_name="roomtype",
            name="reviewed_by",
            field=models.ForeignKey(
                blank=True,
                db_column="reviewed_by",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddConstraint(
            model_name="roomtype",
            constraint=models.CheckConstraint(
                condition=models.Q(("status__in", ["approved", "pending"])),
                name="room_types_statut_valide",
            ),
        ),
        migrations.AddConstraint(
            model_name="roomtype",
            constraint=models.CheckConstraint(
                condition=models.Q(("slug__regex", "^[a-z0-9_]{2,40}$")),
                name="room_types_slug_valide",
            ),
        ),
        migrations.RunPython(creer_officiels, migrations.RunPython.noop),
        migrations.RunSQL(GARDE, reverse_sql=ANNULER_GARDE),
    ]
