"""Administration : isolation, 2FA obligatoire, verrouillage, liste blanche, actions journalisées."""

import pytest
from django.test import Client, override_settings
from django.urls import reverse
from django_otp.plugins.otp_totp.models import TOTPDevice

from adminsite import middleware as mw
from apps.accounts.models import GerantProfile, User
from apps.accounts.tests.fabriques import (
    MOT_DE_PASSE,
    AdminFactory,
    ClientFactory,
    GerantFactory,
    PersonnelFactory,
)
from apps.audit.models import AuditLog
from config.settings import admin_base

pytestmark = [pytest.mark.integration, pytest.mark.pg, pytest.mark.django_db, pytest.mark.securite]

REGLAGES = {
    "ROOT_URLCONF": "config.urls_admin",
    "MIDDLEWARE": admin_base.MIDDLEWARE_ADMIN,
    "AUTHENTICATION_BACKENDS": admin_base.AUTHENTICATION_BACKENDS_ADMIN,
    "SESSION_ENGINE": admin_base.SESSION_ENGINE,
    "ADMIN_ALLOWED_IPS": None,
    "LOGIN_URL": "/login/",
    "ALLOWED_HOSTS": ["*"],
}


@pytest.fixture(autouse=True)
def reglages_admin():
    with override_settings(**REGLAGES):
        yield


def personnel(fabrique=AdminFactory):
    u = fabrique()
    TOTPDevice.objects.create(user=u, name="p", confirmed=True)
    return u


def code_totp(u) -> str:
    from django_otp.oath import totp

    appareil = TOTPDevice.objects.get(user=u)
    return (
        f"{totp(appareil.bin_key, step=appareil.step, t0=appareil.t0, digits=appareil.digits):06d}"
    )


def se_connecter(u, mdp=MOT_DE_PASSE, jeton=None, client=None):
    c = client or Client()
    r = c.post(
        "/login/",
        {
            "username": u.email,
            "password": mdp,
            "otp_token": jeton or code_totp(u),
            "otp_device": "",
            "next": "/",
        },
    )
    return c, r


class TestConnexion:
    def test_page_de_connexion(self):
        r = Client().get("/login/")
        assert r.status_code == 200 and "Adresse e-mail" in r.content.decode()

    def test_connexion_avec_mot_de_passe_et_code(self):
        u = personnel()
        c, r = se_connecter(u)
        assert r.status_code == 302
        assert c.get("/").status_code == 200

    def test_mot_de_passe_seul_ne_suffit_pas(self):
        u = personnel()
        c, r = se_connecter(u, jeton="000000")
        assert r.status_code == 200  # formulaire réaffiché
        assert c.get("/").status_code == 302  # redirigé vers la connexion

    def test_sans_code_la_connexion_est_refusee(self):
        u = personnel()
        c = Client()
        r = c.post(
            "/login/", {"username": u.email, "password": MOT_DE_PASSE, "otp_token": "", "next": "/"}
        )
        assert r.status_code == 200 and c.get("/").status_code == 302

    def test_mauvais_mot_de_passe(self):
        u = personnel()
        c, r = se_connecter(u, mdp="faux")
        assert r.status_code == 200 and c.get("/").status_code == 302

    def test_compte_sans_appareil_totp_ne_peut_pas_entrer(self):
        u = AdminFactory()
        c, r = se_connecter(u, jeton="123456")
        assert c.get("/").status_code == 302

    @pytest.mark.parametrize("fabrique", [ClientFactory, GerantFactory])
    def test_un_locataire_ou_un_gerant_ne_peut_pas_entrer(self, fabrique):
        u = fabrique(email="client@logeo.test")
        TOTPDevice.objects.create(user=u, name="p", confirmed=True)
        c, _ = se_connecter(u)
        assert c.get("/").status_code == 302

    def test_les_jetons_du_site_n_ouvrent_pas_l_administration(self):
        from apps.accounts.services import appareils, jetons

        u = ClientFactory()
        d, _ = appareils.ouvrir(u, installation_id="installation-1", platform="android")
        r = Client().get("/", HTTP_AUTHORIZATION=f"Bearer {jetons.emettre_acces(u, d)}")
        assert r.status_code == 302

    def test_la_connexion_est_journalisee(self):
        u = personnel()
        se_connecter(u)
        assert AuditLog.objects.filter(action="admin.connexion", actor=u).exists()

    def test_un_echec_est_journalise_sans_l_identifiant(self):
        u = personnel()
        se_connecter(u, mdp="faux")
        ligne = AuditLog.objects.get(action="admin.connexion_echec")
        assert u.email not in str(ligne.metadata) and ligne.actor_id is None

    def test_le_cookie_de_session_a_son_propre_nom(self, settings):
        u = personnel()
        c, _ = se_connecter(u)
        assert (
            "sessionid" in c.cookies
        )  # nom de test ; en production : __Host-lgadm (voir test_reglages)


class TestVerrouillage:
    def test_cinq_echecs_verrouillent_meme_avec_le_bon_mot_de_passe(self):
        u = personnel()
        for _ in range(5):
            se_connecter(u, mdp="faux")
        c, r = se_connecter(u)  # bon mot de passe et bon code : refusé quand même
        assert r.status_code == 429
        assert c.get("/").status_code == 302
        assert not AuditLog.objects.filter(action="admin.connexion").exists()

    def test_un_autre_compte_n_est_pas_touche_par_une_adresse_differente(self):
        a, b = personnel(), personnel(PersonnelFactory)
        for _ in range(5):
            se_connecter(a, mdp="faux")
        c, r = se_connecter(b, client=Client(REMOTE_ADDR="41.0.0.77"))
        assert r.status_code == 302


class TestSession:
    def test_session_dans_la_table_d_administration(self):
        from adminsite.models import AdminSession

        u = personnel()
        se_connecter(u)
        assert AdminSession.objects.count() == 1
        from django.contrib.sessions.models import Session

        assert Session.objects.count() == 0  # la table du site n'est pas touchée

    def test_inactivite_de_trente_minutes(self):
        u = personnel()
        c, _ = se_connecter(u)
        assert c.get("/").status_code == 200
        import time_machine
        from django.utils import timezone

        from adminsite.models import AdminSession

        with time_machine.travel(timezone.now() + timezone.timedelta(minutes=31), tick=False):
            assert c.get("/").status_code == 302
        assert AdminSession.objects.count() <= 1

    def test_duree_absolue_de_huit_heures(self):
        import time_machine
        from django.utils import timezone

        u = personnel()
        c, _ = se_connecter(u)
        maintenant = timezone.now()
        # une activité toutes les 20 minutes garde la session glissante vivante...
        for minutes in range(20, 8 * 60, 20):
            with time_machine.travel(maintenant + timezone.timedelta(minutes=minutes), tick=False):
                assert c.get("/").status_code == 200
        # ...mais elle s'éteint à 8 heures, quoi qu'il arrive
        with time_machine.travel(maintenant + timezone.timedelta(hours=8, minutes=5), tick=False):
            assert c.get("/").status_code == 302

    def test_la_deconnexion_est_journalisee(self):
        u = personnel()
        c, _ = se_connecter(u)
        c.post("/logout/")
        assert AuditLog.objects.filter(action="admin.deconnexion", actor=u).exists()


class TestListeBlanche:
    def test_adresse_hors_liste_obtient_404(self):
        with override_settings(ADMIN_ALLOWED_IPS=["10.0.0.0/8"]):
            assert Client(REMOTE_ADDR="41.0.0.1").get("/login/").status_code == 404

    def test_adresse_dans_la_liste(self):
        with override_settings(ADMIN_ALLOWED_IPS=["10.0.0.0/8"]):
            assert Client(REMOTE_ADDR="10.1.2.3").get("/login/").status_code == 200

    def test_liste_vide_refuse_tout(self):
        with override_settings(ADMIN_ALLOWED_IPS=[]):
            assert Client(REMOTE_ADDR="10.1.2.3").get("/login/").status_code == 404

    def test_sonde_de_vivacite_toujours_accessible(self):
        with override_settings(ADMIN_ALLOWED_IPS=[]):
            assert Client(REMOTE_ADDR="10.1.2.3").get("/healthz").status_code == 200

    def test_en_tete_forge_ignore_hors_proxy(self):
        with override_settings(ADMIN_ALLOWED_IPS=["10.0.0.0/8"], USE_X_FORWARDED_FOR=False):
            r = Client(REMOTE_ADDR="41.0.0.1").get("/login/", HTTP_X_FORWARDED_FOR="10.1.1.1")
            assert r.status_code == 404

    def test_derriere_caddy_la_derniere_valeur_fait_foi(self):
        with override_settings(ADMIN_ALLOWED_IPS=["10.0.0.0/8"], USE_X_FORWARDED_FOR=True):
            ok = Client().get("/login/", HTTP_X_FORWARDED_FOR="9.9.9.9, 10.1.1.1")
            refuse = Client().get("/login/", HTTP_X_FORWARDED_FOR="10.1.1.1, 9.9.9.9")
            assert (ok.status_code, refuse.status_code) == (200, 404)

    @pytest.mark.parametrize("entree", ["pas une ip", "", "999.1.1.1"])
    def test_adresses_illisibles_refusees(self, entree):
        assert (
            mw.ListeBlancheIpMiddleware._autorise(
                type("R", (), {"META": {"REMOTE_ADDR": entree}})(), ["10.0.0.0/8"]
            )
            is False
        )


class TestActions:
    def connecte(self, fabrique=AdminFactory):
        u = personnel(fabrique)
        c, _ = se_connecter(u)
        return c, u

    def test_le_site_public_n_a_pas_l_administration(self):
        with override_settings(ROOT_URLCONF="config.urls_public"):
            assert Client().get("/").status_code == 200  # accueil du site
            assert Client().get("/login/").status_code == 404

    def test_creation_d_un_gerant(self):
        c, admin_ = self.connecte()
        r = c.post(
            reverse("admin:accounts_user_nouveau_gerant"),
            {
                "phone": "97343434",
                "full_name": "Koffi Gérant",
                "display_name": "Koffi",
                "zone": "Banikanni",
            },
        )
        assert r.status_code == 302
        g = User.objects.get(phone_e164="+2290197343434")
        assert g.role == "gerant" and not g.has_usable_password()
        assert GerantProfile.complets.get(user=g).created_by == admin_
        assert AuditLog.objects.filter(action="gerant.cree", actor=admin_).exists()

    def test_creation_d_un_gerant_avec_un_numero_existant(self):
        ClientFactory(phone_e164="+2290197343434")
        c, _ = self.connecte()
        r = c.post(
            reverse("admin:accounts_user_nouveau_gerant"),
            {"phone": "97343434", "full_name": "X Y", "zone": "Z"},
        )
        assert r.status_code == 200 and User.objects.filter(role="gerant").count() == 0

    def test_un_moderateur_ne_cree_pas_de_gerant(self):
        c, _ = self.connecte(PersonnelFactory)
        r = c.post(
            reverse("admin:accounts_user_nouveau_gerant"),
            {"phone": "97343434", "full_name": "X Y", "zone": "Z"},
        )
        assert r.status_code in (302, 403) and not User.objects.filter(role="gerant").exists()

    def test_un_moderateur_ne_voit_pas_les_comptes_ni_le_journal(self):
        c, _ = self.connecte(PersonnelFactory)
        assert c.get(reverse("admin:accounts_user_changelist")).status_code == 403
        assert c.get(reverse("admin:audit_auditlog_changelist")).status_code == 403
        assert c.get(reverse("admin:core_appsetting_changelist")).status_code in (302, 403)

    def test_le_journal_est_en_lecture_seule(self):
        c, _ = self.connecte()
        assert c.get(reverse("admin:audit_auditlog_changelist")).status_code == 200
        assert c.get(reverse("admin:audit_auditlog_add")).status_code == 403

    def test_les_comptes_ne_se_suppriment_pas(self):
        c, _ = self.connecte()
        cible = ClientFactory()
        assert c.get(reverse("admin:accounts_user_delete", args=[cible.pk])).status_code == 403

    def test_les_pieces_d_identite_ne_s_affichent_pas_au_moderateur(self):
        from apps.accounts.tests.fabriques import GerantProfileFactory

        p = GerantProfileFactory(interview_notes="note confidentielle")
        GerantProfile.complets.filter(pk=p.pk).update(id_doc_path="chemin-secret")
        c, _ = self.connecte(PersonnelFactory)
        r = c.get(reverse("admin:accounts_gerantprofile_change", args=[p.pk]))
        assert r.status_code in (200, 403)
        if r.status_code == 200:
            assert (
                "chemin-secret" not in r.content.decode()
                and "note confidentielle" not in r.content.decode()
            )
        c2, _ = self.connecte()
        r2 = c2.get(reverse("admin:accounts_gerantprofile_change", args=[p.pk]))
        assert "note confidentielle" in r2.content.decode()

    def test_suspension_depuis_l_administration_coupe_les_sessions(self):
        from apps.accounts.services import appareils, jetons

        c, admin_ = self.connecte()
        cible = ClientFactory()
        d, _ = appareils.ouvrir(cible, installation_id="installation-2", platform="android")
        acces = jetons.emettre_acces(cible, d)
        r = c.post(
            reverse("admin:accounts_user_changelist"),
            {"action": "bannir", "_selected_action": [str(cible.pk)]},
        )
        assert r.status_code == 302
        cible.refresh_from_db()
        assert cible.status == "banned"
        with pytest.raises(Exception) as e:
            jetons.verifier_acces(acces)
        assert "invalid_token" in str(getattr(e.value, "code", e.value))
        assert AuditLog.objects.filter(action="compte.statut", actor=admin_).exists()

    def test_on_ne_se_banne_pas_soi_meme(self):
        c, admin_ = self.connecte()
        c.post(
            reverse("admin:accounts_user_changelist"),
            {"action": "bannir", "_selected_action": [str(admin_.pk)]},
        )
        admin_.refresh_from_db()
        assert admin_.status == "active"

    def test_modification_d_un_parametre(self):
        from apps.core import parametres

        c, _ = self.connecte()
        parametres.definir("OTP_PHONE_PER_HOUR", 3)
        from apps.core.models import AppSetting

        ligne = AppSetting.objects.get(key="OTP_PHONE_PER_HOUR")
        r = c.post(reverse("admin:core_appsetting_change", args=[ligne.pk]), {"value": "5"})
        assert r.status_code == 302
        assert parametres.lire("OTP_PHONE_PER_HOUR") == 5
        assert AuditLog.objects.filter(action="parametre.modifie").exists()


def test_totp_valide_une_seule_fois():
    u = personnel()
    jeton = code_totp(u)
    _, r1 = se_connecter(u, jeton=jeton)
    _, r2 = se_connecter(u, jeton=jeton)  # même code rejoué
    assert r1.status_code == 302 and r2.status_code == 200


def test_les_controles_systeme_de_django_sont_sans_erreur():
    """`manage.py check` : une configuration d'administration invalide doit faire échouer les tests."""
    from django.core import checks

    erreurs = [e for e in checks.run_checks() if e.level >= checks.ERROR]
    assert erreurs == [], erreurs
