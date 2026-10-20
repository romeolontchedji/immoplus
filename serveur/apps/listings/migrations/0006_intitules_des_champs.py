"""Intitulés français des champs dans l'administration (aucune instruction SQL)."""

import django.db.models.deletion
import django.db.models.functions.datetime
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("listings", "0005_libelles_francais"),
    ]

    operations = [
        migrations.AlterField(
            model_name="district",
            name="is_active",
            field=models.BooleanField(db_default=True, default=True, verbose_name="actif"),
        ),
        migrations.AlterField(
            model_name="district",
            name="name",
            field=models.CharField(max_length=80, verbose_name="nom"),
        ),
        migrations.AlterField(
            model_name="district",
            name="slug",
            field=models.CharField(max_length=80, unique=True, verbose_name="identifiant d'URL"),
        ),
        migrations.AlterField(
            model_name="district",
            name="sort_order",
            field=models.SmallIntegerField(db_default=0, default=0, verbose_name="ordre"),
        ),
        migrations.AlterField(
            model_name="listing",
            name="address_private",
            field=models.CharField(
                blank=True, default="", max_length=255, verbose_name="adresse privée"
            ),
        ),
        migrations.AlterField(
            model_name="listing",
            name="advance_months",
            field=models.SmallIntegerField(verbose_name="avance (mois)"),
        ),
        migrations.AlterField(
            model_name="listing",
            name="agent_fee_amount",
            field=models.IntegerField(
                db_default=0, default=0, verbose_name="frais de démarcheur (F)"
            ),
        ),
        migrations.AlterField(
            model_name="listing",
            name="available_from",
            field=models.DateField(verbose_name="disponible le"),
        ),
        migrations.AlterField(
            model_name="listing",
            name="created_at",
            field=models.DateTimeField(
                db_default=django.db.models.functions.datetime.Now(),
                default=django.utils.timezone.now,
                verbose_name="créé le",
            ),
        ),
        migrations.AlterField(
            model_name="listing",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="supprimé le"),
        ),
        migrations.AlterField(
            model_name="listing",
            name="deposit_months",
            field=models.SmallIntegerField(verbose_name="caution (mois)"),
        ),
        migrations.AlterField(
            model_name="listing",
            name="description_md",
            field=models.TextField(db_default="", default="", verbose_name="description"),
        ),
        migrations.AlterField(
            model_name="listing",
            name="distance_to_campus_m",
            field=models.IntegerField(verbose_name="distance à l'UP (m)"),
        ),
        migrations.AlterField(
            model_name="listing",
            name="district",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="listings",
                to="listings.district",
                verbose_name="quartier",
            ),
        ),
        migrations.AlterField(
            model_name="listing",
            name="electricity_meter",
            field=models.CharField(
                choices=[("individual", "Individuel"), ("shared", "Partagé")],
                max_length=10,
                verbose_name="compteur",
            ),
        ),
        migrations.AlterField(
            model_name="listing",
            name="has_private_bathroom",
            field=models.BooleanField(verbose_name="douche interne"),
        ),
        migrations.AlterField(
            model_name="listing",
            name="hidden_reason",
            field=models.CharField(
                blank=True,
                choices=[
                    ("stale", "Sans confirmation"),
                    ("moderation", "Modération"),
                    ("owner", "Gérant"),
                    ("gerant_suspended", "Gérant suspendu"),
                ],
                max_length=16,
                null=True,
                verbose_name="raison du masquage",
            ),
        ),
        migrations.AlterField(
            model_name="listing",
            name="is_fenced",
            field=models.BooleanField(verbose_name="clôturée"),
        ),
        migrations.AlterField(
            model_name="listing",
            name="landmark_text",
            field=models.CharField(max_length=160, verbose_name="repère"),
        ),
        migrations.AlterField(
            model_name="listing",
            name="last_confirmed_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="confirmée le"),
        ),
        migrations.AlterField(
            model_name="listing",
            name="published_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="publiée le"),
        ),
        migrations.AlterField(
            model_name="listing",
            name="rent_amount",
            field=models.IntegerField(verbose_name="loyer (F)"),
        ),
        migrations.AlterField(
            model_name="listing",
            name="rented_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="louée le"),
        ),
        migrations.AlterField(
            model_name="listing",
            name="slug",
            field=models.CharField(max_length=160, unique=True, verbose_name="identifiant d'URL"),
        ),
        migrations.AlterField(
            model_name="listing",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Brouillon"),
                    ("processing", "En traitement"),
                    ("published", "Publiée"),
                    ("hidden", "Masquée"),
                    ("rented", "Louée"),
                    ("archived", "Archivée"),
                    ("removed", "Retirée"),
                ],
                db_default="draft",
                default="draft",
                max_length=12,
                verbose_name="statut",
            ),
        ),
        migrations.AlterField(
            model_name="listing",
            name="title",
            field=models.CharField(max_length=120, verbose_name="titre"),
        ),
        migrations.AlterField(
            model_name="listing",
            name="updated_at",
            field=models.DateTimeField(
                auto_now=True,
                db_default=django.db.models.functions.datetime.Now(),
                verbose_name="modifié le",
            ),
        ),
        migrations.AlterField(
            model_name="listing",
            name="water_source",
            field=models.CharField(
                choices=[
                    ("running", "Eau courante"),
                    ("well", "Puits"),
                    ("borehole", "Forage"),
                ],
                max_length=10,
                verbose_name="eau",
            ),
        ),
        migrations.AlterField(
            model_name="roomtype",
            name="created_at",
            field=models.DateTimeField(
                db_default=django.db.models.functions.datetime.Now(),
                default=django.utils.timezone.now,
                verbose_name="créé le",
            ),
        ),
        migrations.AlterField(
            model_name="roomtype",
            name="label",
            field=models.CharField(max_length=40, verbose_name="libellé"),
        ),
        migrations.AlterField(
            model_name="roomtype",
            name="reviewed_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="examiné le"),
        ),
        migrations.AlterField(
            model_name="roomtype",
            name="slug",
            field=models.CharField(max_length=40, unique=True, verbose_name="identifiant d'URL"),
        ),
        migrations.AlterField(
            model_name="roomtype",
            name="sort_order",
            field=models.SmallIntegerField(db_default=100, default=100, verbose_name="ordre"),
        ),
        migrations.AlterField(
            model_name="roomtype",
            name="status",
            field=models.CharField(
                choices=[("approved", "Validé"), ("pending", "Proposé, à valider")],
                db_default="pending",
                default="pending",
                max_length=10,
                verbose_name="statut",
            ),
        ),
    ]
