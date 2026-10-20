import re

import pytest
from django.conf import settings
from django.test import Client

from apps.accounts.models import User
from apps.accounts.services import administration as service_administration
from apps.accounts.services import compte as service_compte
from apps.accounts.services import identifiants
from apps.accounts.tests.fabriques import (
    MOT_DE_PASSE,
    AdminFactory,
    ClientFactory,
    DeviceFactory,
)

pytestmark = [pytest.mark.integration, pytest.mark.pg, pytest.mark.django_db]
FORT = "un-Mot-de-passe-solide-42"


INSCRIPTION = {
    "first_name": "Awa", "last_name": "Bio", "username": "awa.bio", "phone": "97121212", "password": FORT,
    "terms_accepted": "on", "captcha": "captcha-ok",
}  # fmt: skip


def gerant_active(nom_utilisateur="idris.adam"):
    """Gérant créé par l'administration puis activé par son lien (ADR 0009)."""
    gerant = service_administration.creer_gerant(
        acteur=AdminFactory(), telephone="97565656", prenom="Idris", nom="Adam", zone="Banikanni"
    )
    url = service_administration.lien_activation(acteur=AdminFactory(), gerant=gerant)
    c = Client()
    r = c.post(
        url.split("8080", 1)[-1].split(".bj", 1)[-1],
        {"username": nom_utilisateur, "password": FORT},
    )
    assert r["Location"] == "/compte/cle-de-secours", r.content.decode()[:500]
    return gerant, c


def test_inscription_sur_une_page_puis_cle_de_secours():
    c = Client()
    page = c.get("/inscription")
    assert page.status_code == 200 and "captcha" in page.content.decode()
    r = c.post("/inscription", INSCRIPTION)
    assert r.status_code == 302 and r["Location"] == "/compte/cle-de-secours"
    u = User.objects.get(username="awa.bio")
    assert u.phone_e164 == "+2290197121212" and u.full_name == "Awa Bio"
    page = c.get("/compte/cle-de-secours").content.decode()
    cle = re.search(r"data-cle>\s*([A-Z0-9-]{19})\s*<", page).group(1)
    assert identifiants.cle_correcte(u, cle)
    refus = c.post("/compte/cle-de-secours", {})
    assert refus.status_code == 200 and "Garde ta clé" in refus.content.decode()
    assert c.post("/compte/cle-de-secours", {"confirme": "on"})["Location"].startswith(
        "/compte/profil"
    )
    assert c.get("/compte/cle-de-secours")["Location"] == "/compte"  # plus jamais affichée
    assert "Awa Bio" in c.get("/compte").content.decode()


def test_inscription_sans_defi_refusee():
    r = Client().post("/inscription", {**INSCRIPTION, "captcha": ""})
    assert r.status_code == 200 and "robot" in r.content.decode() and not User.objects.exists()


def test_nom_d_utilisateur_deja_pris():
    ClientFactory(username="awa.bio")
    r = Client().post("/inscription", INSCRIPTION)
    assert r.status_code == 200 and "Déjà pris" in r.content.decode()


def test_cgu_obligatoires():
    r = Client().post("/inscription", {**INSCRIPTION, "terms_accepted": ""})
    assert r.status_code == 200 and not User.objects.exists()


def test_connexion_et_deconnexion():
    ClientFactory(username="kofi.web")
    c = Client()
    r = c.post("/connexion", {"username": "kofi.web", "password": MOT_DE_PASSE})
    assert r["Location"] == "/compte" and c.get("/compte").status_code == 200
    assert c.post("/deconnexion")["Location"] == "/"
    assert c.get("/compte").status_code == 302


def test_connexion_mauvais_mot_de_passe():
    ClientFactory(username="kofi.web")
    r = Client().post("/connexion", {"username": "kofi.web", "password": "faux"})
    assert r.status_code == 200 and "incorrect" in r.content.decode()


def test_compte_exige_la_connexion():
    assert Client().get("/compte")["Location"].startswith("/connexion")


@pytest.mark.parametrize(
    "cible", ["https://pirate.example/", "//pirate.example/", "javascript:alert(1)"]
)
def test_redirection_apres_connexion_limitee_au_site(cible):
    ClientFactory(username="kofi.web")
    r = Client().post(
        "/connexion", {"username": "kofi.web", "password": MOT_DE_PASSE, "next": cible}
    )
    assert r["Location"] == "/compte"


def test_mot_de_passe_oublie_presente_les_trois_portes():
    page = Client().get("/mot-de-passe-oublie").content.decode()
    assert "Par e-mail" in page and "/mot-de-passe-oublie/cle" in page and "WhatsApp" in page


def test_mot_de_passe_oublie_par_cle_de_secours():
    u = ClientFactory(username="kofi.web")
    cle = identifiants.nouvelle_cle_de_secours(u)
    u.save()
    c = Client()
    r = c.post(
        "/mot-de-passe-oublie/cle", {"username": "kofi.web", "recovery_key": cle, "password": FORT}
    )
    assert r["Location"] == "/compte/cle-de-secours"  # nouvelle clé, affichée une fois
    assert (
        Client().post("/connexion", {"username": "kofi.web", "password": FORT})["Location"]
        == "/compte"
    )


def test_mot_de_passe_oublie_par_lien():
    u = ClientFactory(username="kofi.web")
    jeton = identifiants.creer_jeton(u, "reinitialisation")
    r = Client().post(f"/mot-de-passe/nouveau/{jeton}", {"password": FORT})
    assert r["Location"] == "/connexion?reinitialise=1"
    assert "connecte-toi" in Client().get("/connexion?reinitialise=1").content.decode()
    deja = Client().post(f"/mot-de-passe/nouveau/{jeton}", {"password": "encore-un-Autre-8"})
    assert deja.status_code == 200 and "plus valable" in deja.content.decode()


def test_lien_par_email_sans_rien_reveler():
    r = Client().post("/mot-de-passe-oublie", {"identifier": "personne", "captcha": "captcha-ok"})
    assert r.status_code == 200 and "Si ce compte a un e-mail confirmé" in r.content.decode()


def test_changement_de_mot_de_passe_deconnecte_les_autres_sessions():
    ClientFactory(username="kofi.web")
    a, b = Client(), Client()
    for c in (a, b):
        c.post("/connexion", {"username": "kofi.web", "password": MOT_DE_PASSE})
    a.post(
        "/compte/profil",
        {
            "action": "mot-de-passe",
            "current_password": MOT_DE_PASSE,
            "new_password": FORT,
            "confirmation": FORT,
        },
    )
    assert a.get("/compte").status_code == 200
    assert b.get("/compte").status_code == 302


def test_le_nouveau_mot_de_passe_doit_etre_saisi_deux_fois_a_l_identique():
    ClientFactory(username="kofi.web")
    c = Client()
    c.post("/connexion", {"username": "kofi.web", "password": MOT_DE_PASSE})
    r = c.post(
        "/compte/profil",
        {
            "action": "mot-de-passe",
            "current_password": MOT_DE_PASSE,
            "new_password": FORT,
            "confirmation": FORT + "x",
        },
    )
    assert "Les deux mots de passe ne correspondent pas." in r.content.decode()
    c.post("/deconnexion")
    assert (
        c.post("/connexion", {"username": "kofi.web", "password": MOT_DE_PASSE}).status_code == 302
    )


def test_suppression_du_compte():
    ClientFactory(username="kofi.web")
    c = Client()
    c.post("/connexion", {"username": "kofi.web", "password": MOT_DE_PASSE})
    assert (
        c.post("/compte/profil", {"action": "suppression", "password": "faux"}).status_code == 200
    )
    r = c.post("/compte/profil", {"action": "suppression", "password": MOT_DE_PASSE})
    assert (
        r.status_code == 302 and User.objects.get(phone_e164__startswith="del:").status == "deleted"
    )


def test_preferences_notifications():
    u = ClientFactory(username="kofi.web")
    c = Client()
    c.post("/connexion", {"username": "kofi.web", "password": MOT_DE_PASSE})
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
    u = ClientFactory(username="kofi.web")
    appareil = DeviceFactory(user=u, label="Tecno")
    c = Client()
    c.post("/connexion", {"username": "kofi.web", "password": MOT_DE_PASSE})
    page = c.get("/compte/appareils").content.decode()
    assert "Tecno" in page
    r = c.post(f"/compte/appareils/{appareil.pk}/revoquer")
    assert r["Location"] == "/compte/appareils"
    appareil.refresh_from_db()
    assert appareil.revoked_at is not None


def test_revoquer_un_appareil_d_autrui_repond_sans_fuite():
    ClientFactory(username="kofi.web")
    autre = DeviceFactory()
    c = Client()
    c.post("/connexion", {"username": "kofi.web", "password": MOT_DE_PASSE})
    r = c.post(f"/compte/appareils/{autre.pk}/revoquer")
    assert r.status_code == 302
    autre.refresh_from_db()
    assert autre.revoked_at is None


def test_changement_de_numero_sans_code():
    u = ClientFactory(username="kofi.web")
    c = Client()
    c.post("/connexion", {"username": "kofi.web", "password": MOT_DE_PASSE})
    r = c.post("/compte/profil", {"action": "numero", "phone": "97565656", "password": "faux"})
    assert r.status_code == 200 and "incorrect" in r.content.decode()
    r = c.post(
        "/compte/profil", {"action": "numero", "phone": "97565656", "password": MOT_DE_PASSE}
    )
    assert "Ton numéro a été changé" in r.content.decode()
    u.refresh_from_db()
    assert u.phone_e164 == "+2290197565656"


def test_ajout_d_un_email_puis_confirmation():
    u = ClientFactory(username="kofi.web")
    c = Client()
    c.post("/connexion", {"username": "kofi.web", "password": MOT_DE_PASSE})
    r = c.post("/compte/profil", {"action": "email", "email": "kofi@exemple.bj"})
    assert "lien de confirmation" in r.content.decode()
    jeton = identifiants.creer_jeton(u, "email", a="kofi@exemple.bj")
    assert c.get(f"/compte/email/confirmer/{jeton}")["Location"].startswith(
        "/compte/profil?email=confirme"
    )
    assert "Confirmée" in c.get("/compte/profil").content.decode()


def test_nouvelle_cle_de_secours_depuis_le_profil():
    ClientFactory(username="kofi.web")
    c = Client()
    c.post("/connexion", {"username": "kofi.web", "password": MOT_DE_PASSE})
    assert c.post("/compte/profil", {"action": "cle", "password": "faux"}).status_code == 200
    assert (
        c.post("/compte/profil", {"action": "cle", "password": MOT_DE_PASSE})["Location"]
        == "/compte/cle-de-secours"
    )


def test_gerant_active_par_son_lien_se_connecte_puis_change_de_mot_de_passe():
    _, c = gerant_active()
    assert c.get("/pro/dashboard").status_code == 200
    r = c.post(
        "/compte/profil",
        {"action": "mot-de-passe", "current_password": FORT, "new_password": "un-Autre-solide-99",
         "confirmation": "un-Autre-solide-99"},
    )  # fmt: skip
    assert r.status_code == 200 and "mot de passe a été changé" in r.content.decode()
    c2 = Client()
    assert (
        c2.post(
            "/connexion", {"username": "idris.adam", "password": "un-Autre-solide-99"}
        ).status_code
        == 302
    )
    assert c2.get("/pro/dashboard").status_code == 200


# --------------------------------------------------------------- « Se souvenir de moi » (ADR 0005)
def test_connexion_sans_se_souvenir_session_de_navigateur():
    ClientFactory(username="compte62")
    c = Client()
    page = c.get("/connexion").content.decode()
    assert "Se souvenir de moi" in page and 'name="se_souvenir"' in page and "checked" not in page
    c.post("/connexion", {"username": "compte62", "password": MOT_DE_PASSE})
    assert c.session.get_expire_at_browser_close()
    assert (
        c.cookies[settings.SESSION_COOKIE_NAME]["expires"] == ""
        and c.cookies[settings.SESSION_COOKIE_NAME]["max-age"] == ""
    )


def test_connexion_avec_se_souvenir_trente_jours():
    ClientFactory(username="compte63")
    c = Client()
    c.post("/connexion", {"username": "compte63", "password": MOT_DE_PASSE, "se_souvenir": "on"})
    assert not c.session.get_expire_at_browser_close()
    assert c.session.get_expiry_age() == 30 * 24 * 60 * 60
    assert c.cookies[settings.SESSION_COOKIE_NAME]["max-age"] == 30 * 24 * 60 * 60


# --------------------------------------------------------------- appareils (plan v2, W7)
def test_appareils_montre_la_session_en_cours_et_explique():
    ClientFactory(username="compte64")
    c = Client(
        HTTP_USER_AGENT="Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36"
    )
    c.post("/connexion", {"username": "compte64", "password": MOT_DE_PASSE})
    page = c.get("/compte/appareils").content.decode()
    assert "Chrome sur Android" in page and "Session en cours" in page and "Un appareil, c" in page


def test_deconnecter_partout_garde_cette_session():
    u = ClientFactory(username="compte65")
    DeviceFactory(user=u)
    ici, ailleurs = Client(), Client()
    for c in (ici, ailleurs):
        c.post("/connexion", {"username": "compte65", "password": MOT_DE_PASSE})
    r = ici.post("/compte/appareils", {"action": "partout"})
    assert "1 appareil et toutes les autres sessions" in r.content.decode()
    assert ici.get("/compte").status_code == 200
    assert ailleurs.get("/compte").status_code == 302
    assert not u.devices.filter(revoked_at__isnull=True).exists()


def test_le_gerant_arrive_sur_son_profil_depuis_compte():
    _, c = gerant_active()
    assert c.get("/compte")["Location"] == "/compte/profil"
