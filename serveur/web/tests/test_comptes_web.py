import pytest
from django.conf import settings
from django.core.cache import cache
from django.test import Client

from apps.accounts.models import User
from apps.accounts.services import administration as service_administration
from apps.accounts.services import compte as service_compte
from apps.accounts.tests.fabriques import (
    MOT_DE_PASSE,
    AdminFactory,
    ClientFactory,
    DeviceFactory,
)
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


def test_preferences_notifications():
    u = ClientFactory(phone_e164="+2290197343434")
    c = Client()
    c.post("/connexion", {"phone": "97343434", "password": MOT_DE_PASSE})
    assert c.get("/compte/preferences").status_code == 200
    r = c.post(
        "/compte/preferences",
        {"messages_push": "", "messages_apercu": "on", "alertes_push": "on", "rappels_push": "on"},
    )
    assert r.status_code == 200 and "enregistr" in r.content.decode()
    u.refresh_from_db()
    reglages = service_compte.preferences(u)
    assert reglages["messages"] == {"push": False, "apercu": True}
    assert reglages["rappels"]["push"] is True


def test_preferences_exigent_la_connexion():
    assert Client().get("/compte/preferences")["Location"].startswith("/connexion")


def test_appareils_listes_et_revoques():
    u = ClientFactory(phone_e164="+2290197343434")
    appareil = DeviceFactory(user=u, label="Tecno")
    c = Client()
    c.post("/connexion", {"phone": "97343434", "password": MOT_DE_PASSE})
    page = c.get("/compte/appareils").content.decode()
    assert "Tecno" in page
    r = c.post(f"/compte/appareils/{appareil.pk}/revoquer")
    assert r["Location"] == "/compte/appareils"
    appareil.refresh_from_db()
    assert appareil.revoked_at is not None


def test_revoquer_un_appareil_d_autrui_repond_sans_fuite():
    ClientFactory(phone_e164="+2290197343434")
    autre = DeviceFactory()
    c = Client()
    c.post("/connexion", {"phone": "97343434", "password": MOT_DE_PASSE})
    r = c.post(f"/compte/appareils/{autre.pk}/revoquer")
    assert r.status_code == 302
    autre.refresh_from_db()
    assert autre.revoked_at is None


def test_changement_de_numero(django_capture_on_commit_callbacks):
    u = ClientFactory(phone_e164="+2290197343434")
    c = Client()
    c.post("/connexion", {"phone": "97343434", "password": MOT_DE_PASSE})
    with django_capture_on_commit_callbacks(execute=True):
        r = c.post("/compte/numero", {"phone": "97565656", "captcha": "captcha-ok"})
    assert r.status_code == 302 and r["Location"] == "/compte/numero/code"
    r = c.post("/compte/numero/code", {"code": "424242", "password": MOT_DE_PASSE})
    assert r["Location"].startswith("/compte")
    u.refresh_from_db()
    assert u.phone_e164 == "+2290197565656"
    assert c.get("/compte").status_code == 200


def test_changement_de_numero_mauvais_mot_de_passe():
    ClientFactory(phone_e164="+2290197343434")
    c = Client()
    c.post("/connexion", {"phone": "97343434", "password": MOT_DE_PASSE})
    c.post("/compte/numero", {"phone": "97565656", "captcha": "captcha-ok"})
    r = c.post("/compte/numero/code", {"code": "424242", "password": "faux"})
    assert r.status_code == 200
    assert User.objects.get(phone_e164="+2290197343434")


def test_gerant_cree_par_l_administration_se_connecte_puis_change_de_mot_de_passe():
    service_administration.creer_gerant(
        acteur=AdminFactory(),
        telephone="97565656",
        nom="Idris Adam",
        zone="Banikanni",
        mot_de_passe=FORT,
    )
    c = Client()
    assert c.post("/connexion", {"phone": "97565656", "password": FORT}).status_code == 302
    assert c.get("/pro/dashboard").status_code == 200
    r = c.post(
        "/compte",
        {"action": "mot-de-passe", "current_password": FORT, "new_password": "un-Autre-solide-99"},
    )
    assert r.status_code == 200 and "mot de passe a été changé" in r.content.decode()
    c2 = Client()
    assert (
        c2.post("/connexion", {"phone": "97565656", "password": "un-Autre-solide-99"}).status_code
        == 302
    )
    assert c2.get("/pro/dashboard").status_code == 200


# --------------------------------------------------------------- « Se souvenir de moi » (ADR 0005)
def test_connexion_sans_se_souvenir_session_de_navigateur():
    ClientFactory(phone_e164="+2290197626262")
    c = Client()
    page = c.get("/connexion").content.decode()
    assert "Se souvenir de moi" in page and 'name="se_souvenir"' in page and "checked" not in page
    c.post("/connexion", {"phone": "97626262", "password": MOT_DE_PASSE})
    assert c.session.get_expire_at_browser_close()
    assert (
        c.cookies[settings.SESSION_COOKIE_NAME]["expires"] == ""
        and c.cookies[settings.SESSION_COOKIE_NAME]["max-age"] == ""
    )


def test_connexion_avec_se_souvenir_trente_jours():
    ClientFactory(phone_e164="+2290197636363")
    c = Client()
    c.post("/connexion", {"phone": "97636363", "password": MOT_DE_PASSE, "se_souvenir": "on"})
    assert not c.session.get_expire_at_browser_close()
    assert c.session.get_expiry_age() == 30 * 24 * 60 * 60
    assert c.cookies[settings.SESSION_COOKIE_NAME]["max-age"] == 30 * 24 * 60 * 60


# --------------------------------------------------------------- appareils (plan v2, W7)
def test_appareils_montre_la_session_en_cours_et_explique():
    ClientFactory(phone_e164="+2290197646464")
    c = Client(
        HTTP_USER_AGENT="Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36"
    )
    c.post("/connexion", {"phone": "97646464", "password": MOT_DE_PASSE})
    page = c.get("/compte/appareils").content.decode()
    assert "Chrome sur Android" in page and "Session en cours" in page and "Un appareil, c" in page


def test_deconnecter_partout_garde_cette_session():
    u = ClientFactory(phone_e164="+2290197656565")
    DeviceFactory(user=u)
    ici, ailleurs = Client(), Client()
    for c in (ici, ailleurs):
        c.post("/connexion", {"phone": "97656565", "password": MOT_DE_PASSE})
    r = ici.post("/compte/appareils", {"action": "partout"})
    assert "1 appareil et toutes les autres sessions" in r.content.decode()
    assert ici.get("/compte").status_code == 200
    assert ailleurs.get("/compte").status_code == 302
    assert not u.devices.filter(revoked_at__isnull=True).exists()
