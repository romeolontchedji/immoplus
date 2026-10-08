"""Le rôle PostgreSQL `app` (site et API) ne lit ni ne modifie rien de ce qui sert l'administration (CDC §8.2).

Tables concernées : sessions d'administration, appareils TOTP et codes de secours (2FA), verrouillages `axes`,
journal des actions de l'administration. Les droits ne sont posés que si le rôle existe (absent en test).
"""

from django.db import migrations

TABLES = (
    "admin_sessions",
    "django_admin_log",
    "otp_totp_totpdevice",
    "otp_static_staticdevice",
    "otp_static_statictoken",
    "axes_accessattempt",
    "axes_accessfailurelog",
    "axes_accesslog",
)

_MODELE_DROITS = """
DO $droits$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app') THEN
    REVOKE ALL ON __TABLES__ FROM app;
  END IF;
END
$droits$;
"""
_MODELE_ANNULER = """
DO $droits$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app') THEN
    GRANT SELECT, INSERT, UPDATE, DELETE ON __TABLES__ TO app;
  END IF;
END
$droits$;
"""

# Les noms de tables sont des constantes du module : aucune entrée externe n'entre dans ces requêtes.
DROITS = _MODELE_DROITS.replace("__TABLES__", ", ".join(TABLES))
ANNULER = _MODELE_ANNULER.replace("__TABLES__", ", ".join(TABLES))


class Migration(migrations.Migration):
    dependencies = [
        ("adminsite", "0001_sessions"),
        ("admin", "0003_logentry_add_action_flag_choices"),
        ("otp_totp", "0003_add_timestamps"),
        ("otp_static", "0003_add_timestamps"),
        ("axes", "0010_accessattemptexpiration"),
    ]
    operations = [migrations.RunSQL(DROITS, reverse_sql=ANNULER)]
