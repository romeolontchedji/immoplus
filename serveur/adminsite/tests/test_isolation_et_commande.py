"""Le rôle `app` ne voit rien de l'administration ; la commande de création du personnel."""

from io import StringIO

import pytest
from django.core.management import CommandError, call_command
from django_otp.plugins.otp_totp.models import TOTPDevice

from apps.accounts.models import User
from apps.accounts.tests.integration.test_contraintes_base import refuse
from apps.audit.models import AuditLog

pytestmark = [pytest.mark.integration, pytest.mark.pg, pytest.mark.django_db]

TABLES = [
    "admin_sessions", "django_admin_log", "otp_totp_totpdevice", "otp_static_staticdevice",
    "otp_static_statictoken", "axes_accessattempt", "axes_accessfailurelog", "axes_accesslog",
]  # fmt: skip


@pytest.mark.securite
@pytest.mark.parametrize("table", TABLES)
def test_le_role_app_ne_lit_aucune_table_d_administration(table):
    refuse(f"SELECT count(*) FROM {table}")
    refuse(f"DELETE FROM {table}")


@pytest.mark.securite
def test_le_role_app_garde_ses_tables_de_site():
    from apps.accounts.tests.integration.test_contraintes_base import execute

    assert execute("SELECT count(*) FROM django_session") == 1
    assert execute("SELECT count(*) FROM devices") == 1


@pytest.mark.securite
def test_le_role_admin_app_garde_acces_aux_tables_d_administration():
    from apps.accounts.tests.integration.test_contraintes_base import execute

    assert execute("SELECT count(*) FROM admin_sessions", role="admin_app") == 1


MDP = "un-Mot-de-passe-solide-42"


def creer(**options):
    sortie = StringIO()
    call_command("creer_personnel", stdout=sortie, **{"mot_de_passe": MDP, **options})
    return sortie.getvalue()


def test_creation_d_un_moderateur_avec_son_appareil_totp():
    texte = creer(email="Modo@Logeo.test", nom="Modo", role="moderator")
    u = User.objects.get(email="modo@logeo.test")
    assert u.role == "moderator" and u.check_password(MDP) and u.is_staff
    assert TOTPDevice.objects.get(user=u).confirmed
    assert "otpauth://totp/" in texte and "Logeo" in texte
    assert AuditLog.objects.filter(action="admin.personnel_cree").exists()


def test_creation_d_un_administrateur():
    creer(email="chef@logeo.test", nom="Chef", role="admin")
    assert User.objects.get(email="chef@logeo.test").is_superuser


def test_mot_de_passe_faible_refuse():
    with pytest.raises(CommandError):
        creer(email="x@logeo.test", nom="X", role="admin", mot_de_passe="1234")
    assert not User.objects.filter(email="x@logeo.test").exists()


def test_courriel_deja_utilise():
    creer(email="x@logeo.test", nom="X", role="admin")
    with pytest.raises(CommandError):
        creer(email="X@logeo.test", nom="Y", role="admin")


def test_roles_de_clientele_refuses():
    with pytest.raises(CommandError):
        creer(email="x@logeo.test", nom="X", role="client")
