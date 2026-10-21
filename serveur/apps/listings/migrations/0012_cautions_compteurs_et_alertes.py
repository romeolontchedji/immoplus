"""Demandes du 2026-10-20 : cautions eau et électricité distinctes de la caution du loyer, équipements dans les
alertes, et type de chambre ajouté à la recherche par mot-clé (« sanitaire », « entrée-couché »…).
"""

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0008_domaine_demo_immoplus"),
        ("listings", "0011_eau_plusieurs_sources"),
    ]

    operations = [
        migrations.AddField(
            model_name="alert",
            name="electricity_meters",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(max_length=10),
                db_default=[],
                default=list,
                size=None,
                verbose_name="électricité",
            ),
        ),
        migrations.AddField(
            model_name="alert",
            name="fenced_required",
            field=models.BooleanField(
                db_default=False, default=False, verbose_name="cour clôturée"
            ),
        ),
        migrations.AddField(
            model_name="alert",
            name="kitchens",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(max_length=10),
                db_default=[],
                default=list,
                size=None,
                verbose_name="cuisine",
            ),
        ),
        migrations.AddField(
            model_name="alert",
            name="water_sources",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(max_length=10),
                db_default=[],
                default=list,
                size=None,
                verbose_name="eau",
            ),
        ),
        migrations.AddField(
            model_name="listing",
            name="electricity_deposit_amount",
            field=models.IntegerField(
                db_default=0, default=0, verbose_name="caution électricité (F)"
            ),
        ),
        migrations.AddField(
            model_name="listing",
            name="water_deposit_amount",
            field=models.IntegerField(db_default=0, default=0, verbose_name="caution eau (F)"),
        ),
        migrations.AlterField(
            model_name="listing",
            name="deposit_months",
            field=models.SmallIntegerField(verbose_name="caution du loyer (mois)"),
        ),
        migrations.AddConstraint(
            model_name="listing",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("electricity_deposit_amount__gte", 0),
                    ("water_deposit_amount__gte", 0),
                ),
                name="listings_cautions_compteurs_positives",
            ),
        ),
        migrations.RunSQL(
            "UPDATE listings SET search_vector = coalesce(search_vector, ''::tsvector)"
            " || to_tsvector('french', unaccent(room_types.label))"
            " FROM room_types WHERE room_types.slug = listings.room_type",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
