"""« Tu es » (décision V2) : facultatif à l'inscription, modifiable depuis le profil, refusé s'il est inconnu."""

from contextlib import contextmanager

import pytest
from django.db import connection
from django.test import Client

from apps.accounts.models import User
from apps.accounts.services import compte
from apps.accounts.tests.fabriques import MOT_DE_PASSE, ClientFactory

from .test_api_comptes import FORT, api, avec_jeton, corps_inscription

pytestmark = [pytest.mark.api, pytest.mark.pg, pytest.mark.django_db]


def _inscrire(client, capture=None, **extra):
    corps = corps_inscription(username="koffi.adjovi", first_name="Koffi", last_name="Adjovi")
    return client.post("/v1/auth/register", {**corps, **extra}, format="json")


class TestInscription:
    def test_occupation_enregistree(self, django_capture_on_commit_callbacks):
        r = _inscrire(api(), django_capture_on_commit_callbacks, occupation="employee")
        assert r.status_code == 201, r.content
        assert r.json()["user"]["occupation"] == "employee"
        assert User.objects.get(username="koffi.adjovi").occupation == "employee"

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
        assert not User.objects.filter(username="koffi.adjovi").exists()


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
        r = c.patch("/v1/me", {"last_name": "A."}, format="json")
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
    page = c.get("/inscription").content.decode()
    assert "Tu es" in page and "Je préfère ne pas répondre" in page
    r = c.post(
        "/inscription",
        {
            "first_name": "Awa", "last_name": "Bio", "username": "awa.bio",
            "occupation": "student_other", "password": FORT, "terms_accepted": "on", "captcha": "captcha-ok",
        },
    )  # fmt: skip
    assert r["Location"] == "/compte/cle-de-secours"
    u = User.objects.get(username="awa.bio")
    assert u.occupation == "student_other"
    c.post(
        "/compte/profil",
        {"action": "nom", "first_name": "Awa", "last_name": "Bio", "occupation": ""},
    )
    u.refresh_from_db()
    assert u.occupation is None


def test_site_compte_existant_sans_occupation():
    ClientFactory(username="sans.occupation")
    c = Client()
    c.post("/connexion", {"username": "sans.occupation", "password": MOT_DE_PASSE})
    assert c.get("/compte").status_code == 200
