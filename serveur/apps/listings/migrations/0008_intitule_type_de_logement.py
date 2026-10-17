"""Intitulé français du type de logement (aucune instruction SQL)."""


from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("listings", "0007_intitules_des_relations"),
    ]

    operations = [
        migrations.AlterField(
            model_name="listing",
            name="room_type",
            field=models.CharField(max_length=40, verbose_name="type de logement"),
        ),
    ]
