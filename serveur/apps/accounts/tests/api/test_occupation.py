"""« Tu es » (décision V2) : facultatif à l'inscription, modifiable depuis le profil, refusé s'il est inconnu."""

from contextlib import contextmanager

import pytest
from django.db import connection
from django.test import Client

from apps.accounts.models import User
from apps.accounts.services import compte
from apps.accounts.tests.fabriques import MOT_DE_PASSE, ClientFactory

from .test_api_comptes import FORT, api, avec_jeton, obtenir_jeton_otp

pytestmark = [pytest.mark.api, pytest.mark.pg, pytest.mark.django_db]


@pytest.fixture(autouse=True)
def code_otp_fixe(settings):
    settings.OTP_DEBUG_CODE = "424242"


def _inscrire(client, capture, **extra):
    jeton = obtenir_jeton_otp(client, "signup", "97575757", capture)
    corps = {
        "otp_token": jeton,
        "full_name": "Koffi Adjovi",
        "password": FORT,
        "terms_accepted": True,
        "platform": "android",
        **extra,
    }
    return client.post("/v1/auth/register", corps, format="json")


class TestInscription:
    def test_occupation_enregistree(self, django_capture_on_commit_callbacks):
        r = _inscrire(api(), django_capture_on_commit_callbacks, occupation="employee")
        assert r.status_code == 201, r.content
        assert r.json()["user"]["occupation"] == "employee"
        assert User.objects.get(phone_e164="+2290197575757").occupation == "employee"

    def test_occupation_facultative(self, django_capture_on_commit_callbacks):
        r = _inscrire(api(), django_capture_on_commit_callbacks)
        assert r.status_code == 201, r.content
        assert r.json()["user"]["occupation"] is None

    def test_occupation_inconnue_refusee_sans_creer_de_compte(
        self, django_capture_on_commit_callbacks
    ):
        r = _inscrire(api(), django_capture_on_commit_callbacks, occupation="astronaute")
        assert r.status_code == 400
        assert "occupation" in r.json()["error"]["fields"]
        assert not User.objects.filter(phone_e164="+2290197575757").exists()


class TestProfil:
    def _session(self, capture):
        c = api()
        r = _inscrire(c, capture, occupation="student_up")
        return avec_jeton(c, r.json()["tokens"]["access"])

    def test_modifier_puis_effacer(self, django_capture_on_commit_callbacks):
        c = self._session(django_capture_on_commit_callbacks)
        r = c.patch("/v1/me", {"occupation": "self_employed"}, format="json")
        assert r.status_code == 200 and r.json()["occupation"] == "self_employed"
        r = c.patch("/v1/me", {"occupation": None}, format="json")
        assert r.status_code == 200 and r.json()["occupation"] is None

    def test_changer_le_nom_ne_touche_pas_a_l_occupation(self, django_capture_on_commit_callbacks):
        c = self._session(django_capture_on_commit_callbacks)
        r = c.patch("/v1/me", {"full_name": "Koffi A."}, format="json")
        assert r.json()["occupation"] == "student_up" and r.json()["full_name"] == "Koffi A."


@contextmanager
def _en_tant_que_app():
    with connection.cursor() as c:
        c.execute("SET LOCAL ROLE app")
    try:
        yield
    finally:
        with connection.cursor() as c:
            c.execute("RESET ROLE")


def test_le_role_app_peut_modifier_l_occupation():
    """Régression : les droits sur `users` sont accordés colonne par colonne (migration 0005)."""
    u = ClientFactory()
    with _en_tant_que_app():
        compte.modifier_profil(User.objects.get(pk=u.pk), occupation="other")
    assert User.objects.get(pk=u.pk).occupation == "other"


@pytest.mark.integration
def test_site_inscription_et_compte(django_capture_on_commit_callbacks):
    c = Client()
    with django_capture_on_commit_callbacks(execute=True):
        c.post("/inscription", {"phone": "97585858", "captcha": "captcha-ok"})
    c.post("/inscription/code", {"code": "424242"})
    page = c.get("/inscription/profil").content.decode()
    assert "Tu es" in page and "Je préfère ne pas répondre" in page
    r = c.post(
        "/inscription/profil",
        {
            "full_name": "Awa Bio",
            "occupation": "student_other",
            "password": FORT,
            "terms_accepted": "on",
        },
    )
    assert r["Location"] == "/compte"
    u = User.objects.get(phone_e164="+2290197585858")
    assert u.occupation == "student_other"
    c.post("/compte/profil", {"action": "nom", "full_name": "Awa Bio", "occupation": ""})
    u.refresh_from_db()
    assert u.occupation is None


def test_site_compte_existant_sans_occupation():
    ClientFactory(phone_e164="+2290197595959")
    c = Client()
    c.post("/connexion", {"phone": "97595959", "password": MOT_DE_PASSE})
    assert c.get("/compte").status_code == 200
