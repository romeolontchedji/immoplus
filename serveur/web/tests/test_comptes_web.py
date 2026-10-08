import pytest
from django.core.cache import cache
from django.test import Client

from apps.accounts.models import User
from apps.accounts.tests.fabriques import MOT_DE_PASSE, ClientFactory
from apps.core.providers.sms import CLE_BOITE_DEV

pytestmark = [pytest.mark.integration, pytest.mark.pg, pytest.mark.django_db]
FORT = "un-Mot-de-passe-solide-42"


@pytest.fixture(autouse=True)
def code_fixe(settings):
    settings.OTP_DEBUG_CODE = "424242"


def test_inscription_complete_puis_espace_compte(django_capture_on_commit_callbacks):
    c = Client()
    page = c.get("/inscription")
    assert page.status_code == 200 and "captcha" in page.content.decode()
    with django_capture_on_commit_callbacks(execute=True):
        r = c.post("/inscription", {"phone": "97121212", "captcha": "captcha-ok"})
    assert r.status_code == 302 and r["Location"] == "/inscription/code"
    assert cache.get(CLE_BOITE_DEV)
    assert c.post("/inscription/code", {"code": "424242"})["Location"] == "/inscription/profil"
    r = c.post(
        "/inscription/profil", {"full_name": "Awa Bio", "password": FORT, "terms_accepted": "on"}
    )
    assert r["Location"] == "/compte"
    u = User.objects.get(phone_e164="+2290197121212")
    assert u.role == "client" and u.terms_version == "1"
    assert "Awa Bio" in c.get("/compte").content.decode()


def test_inscription_sans_defi_refusee():
    r = Client().post("/inscription", {"phone": "97121212", "captcha": ""})
    assert r.status_code == 200 and "robot" in r.content.decode()


def test_inscription_mauvais_code():
    c = Client()
    c.post("/inscription", {"phone": "97121212", "captcha": "captcha-ok"})
    r = c.post("/inscription/code", {"code": "000000"})
    assert r.status_code == 200 and "incorrect" in r.content.decode()


def test_les_etapes_exigent_les_precedentes():
    assert Client().get("/inscription/code")["Location"] == "/inscription"
    assert Client().get("/inscription/profil")["Location"] == "/inscription"
    assert Client().get("/mot-de-passe-oublie/nouveau")["Location"] == "/mot-de-passe-oublie"


def test_cgu_obligatoires(django_capture_on_commit_callbacks):
    c = Client()
    with django_capture_on_commit_callbacks(execute=True):
        c.post("/inscription", {"phone": "97121212", "captcha": "captcha-ok"})
    c.post("/inscription/code", {"code": "424242"})
    r = c.post("/inscription/profil", {"full_name": "Awa Bio", "password": FORT})
    assert r.status_code == 200 and not User.objects.exists()


def test_connexion_et_deconnexion():
    ClientFactory(phone_e164="+2290197343434")
    c = Client()
    r = c.post("/connexion", {"phone": "97343434", "password": MOT_DE_PASSE})
    assert r["Location"] == "/compte" and c.get("/compte").status_code == 200
    assert c.post("/deconnexion")["Location"] == "/"
    assert c.get("/compte").status_code == 302


def test_connexion_mauvais_mot_de_passe():
    ClientFactory(phone_e164="+2290197343434")
    r = Client().post("/connexion", {"phone": "97343434", "password": "faux"})
    assert r.status_code == 200 and "incorrect" in r.content.decode()


def test_compte_exige_la_connexion():
    assert Client().get("/compte")["Location"].startswith("/connexion")


@pytest.mark.parametrize(
    "cible", ["https://pirate.example/", "//pirate.example/", "javascript:alert(1)"]
)
def test_redirection_apres_connexion_limitee_au_site(cible):
    ClientFactory(phone_e164="+2290197343434")
    r = Client().post("/connexion", {"phone": "97343434", "password": MOT_DE_PASSE, "next": cible})
    assert r["Location"] == "/compte"


def test_mot_de_passe_oublie(django_capture_on_commit_callbacks):
    ClientFactory(phone_e164="+2290197343434")
    c = Client()
    with django_capture_on_commit_callbacks(execute=True):
        c.post("/mot-de-passe-oublie", {"phone": "97343434", "captcha": "captcha-ok"})
    c.post("/mot-de-passe-oublie/code", {"code": "424242"})
    r = c.post("/mot-de-passe-oublie/nouveau", {"password": FORT})
    assert r["Location"].startswith("/connexion")
    assert (
        Client().post("/connexion", {"phone": "97343434", "password": FORT})["Location"]
        == "/compte"
    )


def test_changement_de_mot_de_passe_deconnecte_les_autres_sessions():
    ClientFactory(phone_e164="+2290197343434")
    a, b = Client(), Client()
    for c in (a, b):
        c.post("/connexion", {"phone": "97343434", "password": MOT_DE_PASSE})
    a.post(
        "/compte",
        {"action": "mot-de-passe", "current_password": MOT_DE_PASSE, "new_password": FORT},
    )
    assert a.get("/compte").status_code == 200
    assert b.get("/compte").status_code == 302


def test_suppression_du_compte():
    ClientFactory(phone_e164="+2290197343434")
    c = Client()
    c.post("/connexion", {"phone": "97343434", "password": MOT_DE_PASSE})
    assert c.post("/compte", {"action": "suppression", "password": "faux"}).status_code == 200
    r = c.post("/compte", {"action": "suppression", "password": MOT_DE_PASSE})
    assert (
        r.status_code == 302 and User.objects.get(phone_e164__startswith="del:").status == "deleted"
    )
