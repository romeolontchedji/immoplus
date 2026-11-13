"""Administration : isolation, connexion par mot de passe, verrouillage, liste blanche, actions journalisées."""

import datetime

import pytest
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone

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
from apps.listings.tests.fabriques import ListingFactory, gerant_verifie, medias_prets
from config.settings import admin_base

pytestmark = [pytest.mark.integration, pytest.mark.pg, pytest.mark.django_db, pytest.mark.securite]

MDP_PERSONNEL = "un-Mot-de-passe-solide-42"

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
            trouve = re.search(
                r"\b(\d{6})\b", message.body
            )  # le code est dans le corps, jamais dans l'objet
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

    def test_inactivite_d_une_heure(self):
        u = personnel()
        c, _ = se_connecter(u)
        assert c.get("/").status_code == 200
        import time_machine
        from django.utils import timezone

        from adminsite.models import AdminSession

        with time_machine.travel(timezone.now() + timezone.timedelta(minutes=50), tick=False):
            assert c.get("/").status_code == 200  # 50 min d'inactivité : encore ouverte
        with time_machine.travel(timezone.now() + timezone.timedelta(minutes=50 + 61), tick=False):
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

    def test_creation_d_un_gerant_puis_lien_d_activation(self):
        c, admin_ = self.connecte()
        r = c.post(
            reverse("admin:accounts_user_nouveau_gerant"),
            {"first_name": "Koffi", "last_name": "Gérant", "display_name": "Koffi",
             "zone": "Banikanni"},
        )  # fmt: skip
        page = r.content.decode()
        assert r.status_code == 200 and "/activer/" in page and "wa.me/?text=" in page
        g = User.objects.get(role="gerant")
        assert g.full_name == "Koffi Gérant" and not g.has_usable_password() and g.username is None
        assert GerantProfile.complets.get(user=g).created_by == admin_
        assert AuditLog.objects.filter(action="gerant.cree", actor=admin_).exists()
        assert AuditLog.objects.filter(action="gerant.lien_activation", actor=admin_).exists()

    def test_lien_de_reinitialisation_depuis_la_fiche_du_compte(self):
        c, admin_ = self.connecte()
        locataire = ClientFactory()
        fiche = c.get(reverse("admin:accounts_user_change", args=[locataire.pk])).content.decode()
        assert "Générer un lien de réinitialisation" in fiche
        r = c.get(reverse("admin:accounts_user_lien", args=[locataire.pk, "reinitialisation"]))
        assert r.status_code == 200 and "/mot-de-passe/nouveau/" in r.content.decode()
        assert AuditLog.objects.filter(
            action="auth.lien_reinitialisation_equipe", actor=admin_
        ).exists()

    def test_un_moderateur_ne_cree_pas_de_gerant(self):
        c, _ = self.connecte(PersonnelFactory)
        r = c.post(
            reverse("admin:accounts_user_nouveau_gerant"),
            {"first_name": "X", "last_name": "Y", "zone": "Z"},
        )
        assert r.status_code in (302, 403) and not User.objects.filter(role="gerant").exists()

    def test_un_administrateur_cree_un_moderateur_puis_un_administrateur(self):
        c, admin_ = self.connecte()
        for role in ("moderator", "admin"):
            r = c.post(
                reverse("admin:accounts_user_nouveau_personnel"),
                {"full_name": "Awa Bio", "email": f"{role}@immoplus.test", "role": role,
                 "password": MDP_PERSONNEL, "password2": MDP_PERSONNEL},
            )  # fmt: skip
            assert r.status_code == 302, r.content.decode()[:400]
            u = User.objects.get(email=f"{role}@immoplus.test")
            assert u.role == role and u.is_staff and u.check_password(MDP_PERSONNEL)
        assert AuditLog.objects.filter(action="admin.personnel_cree", actor=admin_).count() == 2

    def test_le_nouveau_personnel_peut_se_connecter(self):
        c, _ = self.connecte()
        c.post(
            reverse("admin:accounts_user_nouveau_personnel"),
            {"full_name": "Awa Bio", "email": "nouveau@immoplus.test", "role": "moderator",
             "password": MDP_PERSONNEL, "password2": MDP_PERSONNEL},
        )  # fmt: skip
        nouveau = User.objects.get(email="nouveau@immoplus.test")
        connecte, _ = se_connecter(nouveau, MDP_PERSONNEL)
        assert connecte.get("/").status_code == 200

    def test_un_moderateur_ne_cree_pas_de_personnel(self):
        c, _ = self.connecte(PersonnelFactory)
        r = c.post(
            reverse("admin:accounts_user_nouveau_personnel"),
            {"full_name": "X Y", "email": "intrus@immoplus.test", "role": "admin",
             "password": MDP_PERSONNEL, "password2": MDP_PERSONNEL},
        )  # fmt: skip
        assert r.status_code in (302, 403)
        assert not User.objects.filter(email="intrus@immoplus.test").exists()

    @pytest.mark.parametrize(
        "changement",
        [
            {"password2": "autre-Mot-de-passe-42"},  # confirmation différente
            {"password": "12345678", "password2": "12345678"},  # mot de passe trop faible
            {"role": "client"},  # rôle qui n'est pas du personnel
        ],
    )
    def test_creation_de_personnel_refusee(self, changement):
        c, _ = self.connecte()
        champs = {"full_name": "Awa Bio", "email": "refuse@immoplus.test", "role": "moderator",
                  "password": MDP_PERSONNEL, "password2": MDP_PERSONNEL}  # fmt: skip
        r = c.post(reverse("admin:accounts_user_nouveau_personnel"), {**champs, **changement})
        assert r.status_code == 200
        assert not User.objects.filter(email="refuse@immoplus.test").exists()

    def test_creation_de_personnel_avec_une_adresse_deja_prise(self):
        c, admin_ = self.connecte()
        avant = User.objects.count()
        r = c.post(
            reverse("admin:accounts_user_nouveau_personnel"),
            {"full_name": "Doublon", "email": admin_.email.upper(), "role": "moderator",
             "password": MDP_PERSONNEL, "password2": MDP_PERSONNEL},
        )  # fmt: skip
        assert r.status_code == 200 and "existe déjà" in r.content.decode()
        assert User.objects.count() == avant

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

    def test_suppression_de_comptes_avec_confirmation(self):
        c, admin_ = self.connecte()
        from django.utils import timezone

        confirme = ClientFactory(email="confirme@exemple.bj", email_verified_at=timezone.now())
        non_confirme = ClientFactory(email="attente@exemple.bj", email_verified_at=None)
        ids = [str(confirme.pk), str(non_confirme.pk)]
        liste = reverse("admin:accounts_user_changelist")
        # 1re étape : page de confirmation, rien n'est encore supprimé.
        r = c.post(liste, {"action": "supprimer_comptes", "_selected_action": ids})
        assert r.status_code == 200 and "Oui, supprimer" in r.content.decode()
        confirme.refresh_from_db()
        assert confirme.deleted_at is None
        # 2e étape : confirmation.
        r = c.post(
            liste, {"action": "supprimer_comptes", "_selected_action": ids, "confirmer": "oui"}
        )
        assert r.status_code == 302
        for compte in (confirme, non_confirme):
            compte.refresh_from_db()
            assert compte.deleted_at is not None and compte.email is None
            assert compte.status == "deleted"
        ligne = AuditLog.objects.filter(action="compte.supprime", actor=admin_).first()
        assert ligne is not None and ligne.metadata["par_equipe"] is True

    def test_on_ne_supprime_ni_un_administrateur_ni_soi_meme(self):
        c, admin_ = self.connecte()
        autre_admin = AdminFactory()
        c.post(
            reverse("admin:accounts_user_changelist"),
            {
                "action": "supprimer_comptes",
                "_selected_action": [str(autre_admin.pk), str(admin_.pk)],
                "confirmer": "oui",
            },
        )
        for compte in (autre_admin, admin_):
            compte.refresh_from_db()
            assert compte.deleted_at is None

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
        parametres.definir("LOGIN_LOCK_THRESHOLD", 3)
        from apps.core.models import AppSetting

        ligne = AppSetting.objects.get(key="LOGIN_LOCK_THRESHOLD")
        r = c.post(reverse("admin:core_appsetting_change", args=[ligne.pk]), {"value": "5"})
        assert r.status_code == 302
        assert parametres.lire("LOGIN_LOCK_THRESHOLD") == 5
        assert AuditLog.objects.filter(action="parametre.modifie").exists()


class TestMasquerOuRetirerUneAnnonce:
    """Administrateurs et modérateurs masquent ou retirent une annonce déjà en ligne, avec un motif vu du gérant."""

    @staticmethod
    def _poster(client, action, annonce, motif="Photos qui ne correspondent pas à la chambre"):
        return client.post(
            reverse("admin:listings_listing_changelist"),
            {
                "action": action,
                "_selected_action": [str(annonce.pk)],
                "confirmer": "oui",
                "motif": motif,
            },
        )

    @pytest.mark.parametrize("fabrique", ["moderateur", "admin"])
    def test_masquer_puis_remettre_en_ligne(self, fabrique):
        from apps.listings.models import Listing
        from apps.notifications.models import Notification

        annonce = ListingFactory(
            gerant=gerant_verifie()
        )  # gérant vérifié et photos : l'annonce est publiable
        medias_prets(annonce)
        c, _ = se_connecter(
            personnel(PersonnelFactory if fabrique == "moderateur" else AdminFactory)
        )
        self._poster(c, "masquer_annonces", annonce)
        annonce = Listing.objects.get(pk=annonce.pk)
        assert annonce.status == "hidden" and annonce.hidden_reason == "moderation"
        assert Notification.objects.filter(
            kind="account.sanction", user=annonce.gerant.user
        ).exists()
        self._poster(c, "remettre_en_ligne", annonce)
        assert Listing.objects.get(pk=annonce.pk).status == "published"

    def test_retirer_est_definitif_pour_le_gerant(self):
        from apps.listings.models import Listing

        annonce = ListingFactory()
        c, _ = se_connecter(personnel(AdminFactory))
        self._poster(c, "retirer_annonces", annonce)
        assert Listing.objects.get(pk=annonce.pk).status == "removed"

    def test_la_page_de_confirmation_demande_un_motif(self):
        from apps.listings.models import Listing

        annonce = ListingFactory()
        c, _ = se_connecter(personnel(AdminFactory))
        page = c.post(
            reverse("admin:listings_listing_changelist"),
            {"action": "masquer_annonces", "_selected_action": [str(annonce.pk)]},
        )
        assert page.status_code == 200 and "Motif" in page.content.decode()
        self._poster(c, "masquer_annonces", annonce, motif="court")  # trop court : refusé
        assert Listing.objects.get(pk=annonce.pk).status == "published"


class TestPouvoirsDeLAdministrateur:
    """L'administrateur a la main sur tout ce qui peut s'écrire (le journal et l'anonymisation des comptes restent intacts)."""

    @staticmethod
    def _action(client, modele, action, objets, **extra):
        return client.post(
            reverse(f"admin:{modele}_changelist"),
            {
                "action": action,
                "_selected_action": [str(o.pk) for o in objets],
                "confirmer": "oui",
                **extra,
            },
        )

    def test_ajouter_un_type_de_logement(self):
        from apps.listings.models import RoomType

        c, _ = se_connecter(personnel(AdminFactory))
        r = c.post(
            reverse("admin:listings_roomtype_add"),
            {"label": "Colocation étudiante", "sort_order": 50},
        )
        assert r.status_code == 302
        t = RoomType.objects.get(label="Colocation étudiante")
        assert t.status == "approved" and t.slug == "colocation_etudiante" and t.sort_order == 50
        # un nom déjà pris (même sans accents ni majuscules) est refusé
        r = c.post(
            reverse("admin:listings_roomtype_add"),
            {"label": "COLOCATION ETUDIANTE", "sort_order": 1},
        )
        assert (
            r.status_code == 200
            and RoomType.objects.filter(slug__startswith="colocation_etudiante").count() == 1
        )

    def test_un_moderateur_n_ajoute_pas_de_type(self):
        c, _ = se_connecter(personnel(PersonnelFactory))
        assert c.get(reverse("admin:listings_roomtype_add")).status_code == 403

    def test_supprimer_un_type_inutilise_seulement(self):
        from apps.listings.models import RoomType
        from apps.listings.services import types as types_chambre

        admin_ = personnel(AdminFactory)
        c, _ = se_connecter(admin_)
        libre = types_chambre.creer_officiel("Type libre", acteur=admin_)
        utilise = types_chambre.creer_officiel("Type utilise", acteur=admin_)
        ListingFactory(room_type=utilise.slug)
        c.post(reverse("admin:listings_roomtype_delete", args=[libre.pk]), {"post": "yes"})
        c.post(reverse("admin:listings_roomtype_delete", args=[utilise.pk]), {"post": "yes"})
        assert not RoomType.objects.filter(pk=libre.pk).exists()
        assert RoomType.objects.filter(
            pk=utilise.pk
        ).exists()  # des annonces l'utilisent : à rattacher

    def test_corriger_une_annonce_est_reserve_aux_administrateurs(self):
        from apps.listings.models import Listing

        annonce = ListingFactory(title="Ancien titre")
        champs = {
            "title": "Nouveau titre", "rent_amount": annonce.rent_amount, "landmark_text": annonce.landmark_text,
            "available_from": annonce.available_from or "2026-12-01", "district": annonce.district_id,
        }  # fmt: skip
        url = reverse("admin:listings_listing_change", args=[annonce.pk])
        modo, _ = se_connecter(personnel(PersonnelFactory))
        assert modo.post(url, champs).status_code == 403
        c, _ = se_connecter(personnel(AdminFactory))
        c.post(url, champs)
        assert Listing.objects.get(pk=annonce.pk).title == "Nouveau titre"
        refus = c.post(
            url, {**champs, "title": "Appelle 97 12 34 56 vite"}
        )  # coordonnées : refusées
        assert (
            refus.status_code == 200 and Listing.objects.get(pk=annonce.pk).title == "Nouveau titre"
        )

    def test_retablir_une_annonce_retiree_et_la_supprimer(self):
        from apps.listings.models import Listing

        retiree = ListingFactory(status="removed")
        c, _ = se_connecter(personnel(AdminFactory))
        self._action(c, "listings_listing", "retablir_retiree", [retiree])
        assert Listing.objects.get(pk=retiree.pk).status == "hidden"
        self._action(c, "listings_listing", "supprimer_annonces", [retiree])
        assert Listing.objects.get(pk=retiree.pk).deleted_at is not None

    def test_deconnecter_et_changer_le_role_du_personnel(self):
        cible = personnel(PersonnelFactory)
        avant = cible.token_version
        c, _ = se_connecter(personnel(AdminFactory))
        self._action(c, "accounts_user", "deconnecter_comptes", [cible])
        cible.refresh_from_db()
        assert cible.token_version > avant
        self._action(c, "accounts_user", "passer_administrateur", [cible])
        cible.refresh_from_db()
        assert cible.role == "admin"
        self._action(c, "accounts_user", "passer_moderateur", [cible])
        cible.refresh_from_db()
        assert cible.role == "moderator"

    def test_abonnement_prolonger_puis_mettre_fin_et_marquer_rembourse(self):
        from apps.billing import services
        from apps.billing.models import Subscription, Transaction
        from apps.core import parametres
        from apps.listings.tests.fabriques import gerant_verifie

        parametres.definir("PLANS", [
            {"code": "free_v1", "label": "Gratuit", "price": 0, "period_months": 1, "active": True},
            {"code": "standard", "label": "Standard", "price": 500, "period_months": 1, "active": True},
        ])  # fmt: skip
        g, admin_ = gerant_verifie(), personnel(AdminFactory)
        services.activer_en_especes(acteur=admin_, gerant_id=g.pk, plan_code="standard")
        abo = Subscription.objects.get(gerant_id=g.pk, plan_code="standard")
        fin = abo.current_period_end
        c, _ = se_connecter(admin_)
        self._action(c, "billing_subscription", "prolonger", [abo])
        abo.refresh_from_db()
        assert abo.current_period_end > fin
        self._action(c, "billing_subscription", "mettre_fin", [abo])
        abo.refresh_from_db()
        assert abo.status == "expired"
        ligne = Transaction.objects.filter(user=g.user, status="succeeded").first()
        self._action(c, "billing_transaction", "marquer_rembourse", [ligne])
        ligne.refresh_from_db()
        assert ligne.status == "refunded"

    def test_supprimer_un_avis(self):
        from apps.listings.models import Review

        annonce = ListingFactory()
        avis = Review.objects.create(
            listing=annonce, author=ClientFactory(), rating=1, comment="Nul"
        )
        c, _ = se_connecter(personnel(AdminFactory))
        c.post(reverse("admin:listings_review_delete", args=[avis.pk]), {"post": "yes"})
        assert not Review.objects.filter(pk=avis.pk).exists()


class TestMessagesEquipe:
    def test_un_moderateur_ecrit_depuis_l_administration(self):
        from apps.moderation.models import MessageEquipe

        locataire = ClientFactory(username="awa.msg")
        c, _ = se_connecter(personnel(PersonnelFactory))
        url = reverse("admin:moderation_messageequipe_ecrire", args=[locataire.pk])
        assert c.get(url).status_code == 200
        r = c.post(
            url,
            {
                "corps": "Bonjour Awa, voici notre réponse.",
                "objet": "Ta question",
                "contexte": "question",
            },
        )
        assert r.status_code == 302
        m = MessageEquipe.objects.get(utilisateur=locataire)
        assert m.vers_utilisateur and m.objet == "Ta question" and m.contexte_type == "question"

    def test_on_n_ecrit_pas_a_un_membre_du_personnel(self):
        c, _ = se_connecter(personnel(PersonnelFactory))
        autre = personnel(AdminFactory)
        assert (
            c.get(reverse("admin:moderation_messageequipe_ecrire", args=[autre.pk])).status_code
            == 404
        )

    def test_depuis_un_avis_on_ecrit_a_son_auteur_avec_l_objet_pre_rempli(self):
        from apps.listings.models import Review

        annonce = ListingFactory(title="Chambre Zongo")
        auteur = ClientFactory()
        avis = Review.objects.create(listing=annonce, author=auteur, rating=2, comment="Bof")
        c, _ = se_connecter(personnel(PersonnelFactory))
        r = c.post(
            reverse("admin:listings_review_changelist"),
            {"action": "ecrire_a_l_auteur", "_selected_action": [str(avis.pk)]},
        )
        assert r.status_code == 302
        assert (
            str(auteur.pk) in r["Location"]
            and "avis%3A" in r["Location"]
            and "Chambre+Zongo" in r["Location"]
        )

    def test_la_tuile_compte_les_messages_a_traiter(self):
        from apps.moderation import messages_equipe as equipe

        equipe.ecrire_a_l_equipe(ClientFactory(), "J'ai une question")
        c, _ = se_connecter(personnel(AdminFactory))
        page = c.get(reverse("admin:index")).content.decode()
        assert "Messages à traiter" in page


class TestPageDeRubrique:
    def test_la_page_d_une_rubrique_renvoie_a_l_accueil_sans_erreur(self):
        c, _ = se_connecter(personnel(AdminFactory))
        for rubrique in ("listings", "accounts"):
            r = c.get(f"/{rubrique}/")
            assert r.status_code == 302 and r["Location"] == reverse("admin:index")


class TestCarteNouvellesAnnonces:
    def test_la_carte_compte_les_annonces_des_sept_derniers_jours_et_mene_a_la_liste(self):
        from apps.listings.tests.fabriques import ListingFactory

        ListingFactory(title="Chambre toute neuve")  # publiée à l'instant
        ListingFactory(
            title="Chambre ancienne",
            published_at=timezone.now() - datetime.timedelta(days=30),
        )
        c, _ = se_connecter(personnel(AdminFactory))
        page = c.get(reverse("admin:index")).content.decode()
        assert "Nouvelles annonces" in page and "mises en ligne ces 7 jours" in page
        depuis = (timezone.localdate() - datetime.timedelta(days=7)).isoformat()
        liste = c.get(reverse("admin:listings_listing_changelist") + f"?published_at__gte={depuis}")
        corps = liste.content.decode()
        assert liste.status_code == 200 and "Chambre toute neuve" in corps
        assert "Chambre ancienne" not in corps


class TestPageStatistiques:
    def test_page_dediee_avec_gerants_et_locataires(self):
        from apps.accounts.tests.fabriques import ClientFactory
        from apps.listings.tests.fabriques import gerant_verifie

        gerant_verifie()
        ClientFactory(full_name="Awa Locataire")
        c, _ = se_connecter(personnel(AdminFactory))
        r = c.get(reverse("admin:statistiques"))
        corps = r.content.decode()
        assert r.status_code == 200
        assert "Chiffres clés" in corps and "Awa Locataire" in corps and "Gérants" in corps

    def test_la_fiche_d_un_gerant_affiche_ses_statistiques(self):
        from apps.listings.tests.fabriques import gerant_verifie

        g = gerant_verifie()
        c, _ = se_connecter(personnel(AdminFactory))
        corps = c.get(reverse("admin:accounts_user_change", args=[g.user.pk])).content.decode()
        assert "Statistiques" in corps and "Audience" in corps


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

    def test_cloudinary_s_active_depuis_les_parametres_seulement_s_il_est_configure(self):
        from apps.core import parametres

        c, _ = se_connecter(personnel())
        envoi = {"section": "medias", "medias-MEDIA_STORAGE": "cloudinary"}
        with override_settings(CLOUDINARY_CLOUD_NAME=""):
            page = c.post("/core/appsetting/", envoi).content.decode()
        assert "Cloudinary n&#x27;est pas configuré" in page
        assert parametres.lire("MEDIA_STORAGE") == "local"
        with override_settings(CLOUDINARY_CLOUD_NAME="immoplus-test"):
            c.post("/core/appsetting/", envoi)
        assert parametres.lire("MEDIA_STORAGE") == "cloudinary"

    def test_inactivite_de_l_administration_d_une_heure(self):
        from apps.core import parametres

        assert parametres.lire("ADMIN_SESSION_IDLE_MIN") == 60

    def test_echecs_du_site_visibles_dans_l_administration(self):
        from apps.accounts.services import authentification
        from apps.core.errors import ErreurMetier

        ClientFactory(username="kofi.zongo")
        with pytest.raises(ErreurMetier):
            authentification.authentifier("kofi.zongo", "faux", "192.168.1.10")
        ligne = AuditLog.objects.get(action="auth.connexion_echouee")
        assert ligne.metadata["identifiant"] == "kofi.zongo" and ligne.metadata["surface"] == "site"
        c, _ = se_connecter(personnel())
        page = c.get("/connexions-echouees/").content.decode()
        assert "kofi.zongo" in page and "192.168.1.10" in page

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
