"""Paramètres des codes SMS et du SMS de repli retirés (ADR 0009) : leurs lignes enregistrées sont effacées."""

from django.db import migrations

OBSOLETES = [
    "OTP_ALLOWED_COUNTRIES",
    "OTP_DAILY_BUDGET",
    "OTP_PHONE_PER_HOUR",
    "OTP_INSTALLATION_PER_DAY",
    "OTP_IP24_PER_DAY",
    "OTP_RESEND_DELAY_S",
    "SMS_FALLBACK_ENABLED",
]


def effacer(apps, schema_editor):
    apps.get_model("core", "AppSetting").objects.filter(key__in=OBSOLETES).delete()


class Migration(migrations.Migration):
    dependencies = [("core", "0009_identite_immoplus")]

    operations = [migrations.RunPython(effacer, migrations.RunPython.noop)]
