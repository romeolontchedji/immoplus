"""Inactivité de l'administration portée de 30 à 60 minutes : une valeur restée à l'ancien défaut suit le nouveau."""

from django.db import migrations


def porter(apps, schema_editor):
    apps.get_model("core", "AppSetting").objects.filter(key="ADMIN_SESSION_IDLE_MIN", value=30).update(value=60)


def revenir(apps, schema_editor):
    apps.get_model("core", "AppSetting").objects.filter(key="ADMIN_SESSION_IDLE_MIN", value=60).update(value=30)


class Migration(migrations.Migration):
    dependencies = [("core", "0010_parametres_sms_retires")]

    operations = [migrations.RunPython(porter, revenir)]
