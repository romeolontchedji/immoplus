"""Administration : isolation, connexion par mot de passe, verrouillage, liste blanche, actions journalisées."""

import pytest
from django.test import Client, override_settings
from django.urls import reverse

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
from apps.listings.tests.fabriques import ListingFactory
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
    return fabrique()


def dernier_code(adresse: str) -> str | None:
    """Code à 6 chiffres du dernier courriel envoyé à `adresse` (tâches exécutées sur place en test)."""
    import re

    from django.core import mail

    for message in reversed(mail.outbox):
        if adresse in message.to:
            trouve = re.search(r"\b(\d{6})\b", message.subject)
            return trouve.group(1) if trouve else None
    return None


def se_connecter(u, mdp=MOT_DE_PASSE, client=None, *, double_auth=True):
    """Mot de passe, puis (si accepté) le code reçu par courriel, comme un vrai membre de l'équipe."""
    c = client or Client()
    r = c.post("/login/", {"username": u.email, "password": mdp, "next": "/"})
    if double_auth and r.status_code == 302 and (code := dernier_code(u.email)):
        c.post("/verification/", {"code": code, "next": "/"})
    return c, r


class TestConnexion:
    def test_page_de_connexion(self):
        r = Client().get("/login/")
        assert r.status_code == 200 and "Adresse e-mail" in r.content.decode()

    def test_connexion_avec_mot_de_passe(self):
        u = personnel()
        c, r = se_connecter(u)
        assert r.status_code == 302
        assert c.get("/").status_code == 200

    def test_mauvais_mot_de_passe(self):
        u = personnel()
        c, r = se_connecter(u, mdp="faux")
        assert r.status_code == 200 and c.get("/").status_code == 302

    @pytest.mark.parametrize("fabrique", [ClientFactory, GerantFactory])
    def test_un_locataire_ou_un_gerant_ne_peut_pas_entrer(self, fabrique):
        u = fabrique(email="client@immoplus.test")
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

    def test_l_echec_est_garde_dans_l_historique_avec_un_message_clair(self):
        from axes.models import AccessFailureLog

        u = personnel()
        _, r = se_connecter(u, mdp="faux")
        assert "Adresse e-mail ou mot de passe incorrect." in r.content.decode()
        assert AccessFailureLog.objects.filter(username=u.email).count() == 1

    def test_les_connexions_affichent_le_compte_et_non_son_identifiant(self):
        u = personnel()
        c, _ = se_connecter(u)
        page = c.get("/axes/accesslog/").content.decode()
        assert u.email in page

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
        c, r = se_connecter(u)  # bon mot de passe : refusé quand même
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
                "password": "Un-Mot-De-Passe-42",
            },
        )
        assert r.status_code == 302
        g = User.objects.get(phone_e164="+2290197343434")
        assert g.role == "gerant" and g.has_usable_password()
        assert g.check_password("Un-Mot-De-Passe-42")
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


class TestTableauDeBord:
    def test_la_vue_d_ensemble_s_affiche_avec_des_donnees_reelles(self):
        from apps.core import stats
        from apps.moderation.models import Report

        admin_ = personnel()
        c, _ = se_connecter(admin_)
        annonce = ListingFactory(status="published")
        Report.objects.create(
            reporter=ClientFactory(),
            source="user",
            target_type="listing",
            target_id=annonce.pk,
            listing=annonce,
            reason_code="fake_listing",
            details="Fausse annonce",
        )
        stats.incrementer("messages", 4)
        r = c.get("/")
        assert r.status_code == 200
        html = r.content.decode()
        assert "À traiter" in html
        assert "Signalements ouverts" in html and ">1<" in html
        assert ">4<" in html  # compteur messages du jour
        assert reverse("admin:moderation_report_changelist") in html

    def test_le_moderateur_ne_voit_pas_le_journal_ni_le_lien_admin(self):
        c, _ = se_connecter(personnel(PersonnelFactory))
        html = c.get("/").content.decode()
        assert "À traiter" in html
        assert "Journal d'activité" not in html and "Paramètres" not in html


def test_les_controles_systeme_de_django_sont_sans_erreur():
    """`manage.py check` : une configuration d'administration invalide doit faire échouer les tests."""
    from django.core import checks

    erreurs = [e for e in checks.run_checks() if e.level >= checks.ERROR]
    assert erreurs == [], erreurs


class TestParametresParTheme:
    """Page « Paramètres » : réglages rangés par thème, champs typés, journalisés avec l'avant et l'après."""

    def test_modifier_la_maintenance(self):
        from apps.audit.models import AuditLog
        from apps.core import parametres

        c, _ = se_connecter(personnel())
        page = c.get(reverse("admin:core_appsetting_changelist")).content.decode()
        assert "Application et maintenance" in page and "Contact et identité légale" in page
        r = c.post(
            reverse("admin:core_appsetting_changelist"),
            {"section": "application", "application-MAINTENANCE_ENABLED": "on", "application-MAINTENANCE_MESSAGE": "Travaux",
             "application-APP_NOTICE": "", "application-MIN_SUPPORTED_VERSION": "1.2.0"},
        )  # fmt: skip
        assert r.status_code == 302
        assert (
            parametres.lire("MAINTENANCE_ENABLED") is True
            and parametres.lire("MIN_SUPPORTED_VERSION") == "1.2.0"
        )
        ligne = AuditLog.objects.filter(
            action="parametre.modifie", metadata__cle="MAINTENANCE_ENABLED"
        ).get()
        assert ligne.metadata["avant"] is False and ligne.metadata["apres"] is True
        parametres.definir("MAINTENANCE_ENABLED", False)

    def test_json_invalide_refuse(self):
        from apps.core import parametres

        c, _ = se_connecter(personnel())
        avant = parametres.lire("PLANS")
        r = c.post(
            reverse("admin:core_appsetting_changelist"),
            {
                "section": "abonnement",
                "abonnement-SUBSCRIPTION_GRACE_DAYS": "7",
                "abonnement-PLANS": "[pas du json",
            },
        )
        assert r.status_code == 200 and parametres.lire("PLANS") == avant

    def test_un_moderateur_ne_voit_pas_les_parametres(self):
        c, _ = se_connecter(personnel(PersonnelFactory))
        assert c.get(reverse("admin:core_appsetting_changelist")).status_code in (302, 403)


def test_quartiers_geres_sans_suppression():
    from apps.listings.models import District

    c, _ = se_connecter(personnel())
    r = c.post(
        reverse("admin:listings_district_add"),
        {"name": "Kpébié Nord", "slug": "kpebie-nord", "latitude": "9.35", "longitude": "2.62", "sort_order": "40", "is_active": "on"},
    )  # fmt: skip
    assert r.status_code == 302 and District.objects.filter(slug="kpebie-nord").exists()
    d = District.objects.get(slug="kpebie-nord")
    assert c.get(reverse("admin:listings_district_delete", args=[d.pk])).status_code == 403


class TestAudienceEtMenu:
    def test_audience_sans_file_des_gerants_et_menu_ordonne(self):
        from apps.core import stats

        stats.incrementer("views", 4, sujet="canal:web")
        stats.incrementer("views", 2, sujet="canal:app")
        c, _ = se_connecter(personnel())
        page = c.get("/").content.decode()
        assert (
            "Audience" in page and "Vues sur le site" in page and "Gérants à vérifier" not in page
        )
        menu = page[page.index('id="nav-sidebar"') :]
        # Rubriques par usage : la modération d'abord, l'abonnement (désactivé) en dernier
        assert menu.index("Modération") < menu.index("Comptes") < menu.index("Abonnement")


class TestDoubleAuthentification:
    def test_sans_le_code_aucune_page_n_est_accessible(self):
        u = personnel()
        c, r = se_connecter(u, double_auth=False)
        assert r.status_code == 302
        page = c.get("/")
        assert page.status_code == 302 and page["Location"].startswith("/verification/")
        code = dernier_code(u.email)
        assert code and len(code) == 6
        from django.core import mail

        assert "valable 10 minutes" in mail.outbox[-1].body

    def test_le_bon_code_ouvre_l_administration_et_se_journalise(self):
        u = personnel()
        c, _ = se_connecter(u, double_auth=False)
        r = c.post("/verification/", {"code": dernier_code(u.email), "next": "/"})
        assert r.status_code == 302 and c.get("/").status_code == 200
        assert AuditLog.objects.filter(action="admin.2fa_reussie", actor_id=u.pk).exists()

    def test_cinq_codes_faux_deconnectent(self):
        u = personnel()
        c, _ = se_connecter(u, double_auth=False)
        bon = dernier_code(u.email)
        faux = "000000" if bon != "000000" else "111111"
        for _ in range(4):
            assert "Code incorrect" in c.post("/verification/", {"code": faux}).content.decode()
        r = c.post("/verification/", {"code": faux})
        assert r.status_code == 302 and "double_auth=bloque" in r["Location"]
        assert c.get("/").status_code == 302  # plus connecté
        assert (
            c.post("/verification/", {"code": bon}).status_code == 302
        )  # l'ancien code ne vaut plus rien
        assert c.get("/").status_code == 302

    def test_renvoi_limite_a_une_minute(self):
        u = personnel()
        c, _ = se_connecter(u, double_auth=False)
        page = c.post("/verification/", {"renvoyer": "1"}).content.decode()
        assert "Patiente une minute" in page

    def test_code_expire(self):
        from apps.core import redis_file

        u = personnel()
        c, _ = se_connecter(u, double_auth=False)
        for cle in redis_file.client().scan_iter("admin:2fa:*"):
            redis_file.client().delete(cle)
        r = c.post("/verification/", {"code": dernier_code(u.email)})
        assert "double_auth=expire" in r["Location"]


class TestPageErreurs:
    def test_l_administrateur_voit_et_corrige_les_erreurs(self):
        import logging

        from apps.core import erreurs

        try:
            raise KeyError("absent")
        except KeyError:
            logging.getLogger("apps.essai").exception("Échec de test")
        c, _ = se_connecter(personnel())
        assert "KeyError" in c.get("/").content.decode()
        page = c.get("/erreurs/").content.decode()
        assert "KeyError" in page and "Corrigée" in page
        c.post("/erreurs/", {"resoudre": erreurs.liste()[0]["id"]})
        assert erreurs.liste() == []

    def test_un_moderateur_n_y_a_pas_acces(self):
        c, _ = se_connecter(personnel(PersonnelFactory))
        assert c.get("/erreurs/").status_code == 403


class TestPlanV3Administration:
    def test_chaque_parametre_a_une_note(self):
        from adminsite.parametres_page import NOTES
        from apps.core import parametres

        assert set(parametres.DEFAUTS) <= set(NOTES)
        c, _ = se_connecter(personnel())
        page = c.get("/core/appsetting/").content.decode()
        assert 'class="lg-champ__note"' in page and "recommandé : le gérant marque lui-même" in page

    def test_echecs_du_site_visibles_dans_l_administration(self):
        from apps.accounts.services import authentification
        from apps.core.errors import ErreurMetier

        ClientFactory(phone_e164="+2290197343434")
        with pytest.raises(ErreurMetier):
            authentification.authentifier("97343434", "faux", "192.168.1.10")
        ligne = AuditLog.objects.get(action="auth.connexion_echouee")
        assert (
            ligne.metadata["numero"] == "+229 01 ** ** 34 34"
            and ligne.metadata["surface"] == "site"
        )
        c, _ = se_connecter(personnel())
        page = c.get("/connexions-echouees/").content.decode()
        assert "+229 01 ** ** 34 34" in page and "192.168.1.10" in page

    def test_les_pages_de_securite_expliquent_ce_qu_elles_montrent(self):
        c, _ = se_connecter(personnel())
        page = c.get("/axes/accessattempt/").content.decode()
        assert "une page vide est donc normale" in page

    def test_moderateur_masque_un_avis(self):
        import uuid

        from apps.chat import services as chat
        from apps.listings.models import Review
        from apps.listings.services import avis

        a = ListingFactory()
        loc = ClientFactory()
        conversation = chat.demarrer(loc, a.pk)
        chat.envoyer(loc, conversation.pk, "Bonjour", uuid.uuid4())
        chat.envoyer(a.gerant.user, conversation.pk, "Oui", uuid.uuid4())
        r = avis.donner(loc, a.pk, 1, "Commentaire déplacé")
        c, _ = se_connecter(personnel(PersonnelFactory))
        assert c.get("/listings/review/").status_code == 200
        c.post("/listings/review/", {"action": "masquer", "_selected_action": [str(r.pk)]})
        assert Review.objects.get(pk=r.pk).is_hidden
