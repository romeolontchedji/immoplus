"""Modération : signalements, actions, sanctions, lecture journalisée, fin de suspension, API."""

import datetime
import uuid

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.services import appareils, jetons
from apps.accounts.tests.fabriques import AdminFactory, ClientFactory, PersonnelFactory
from apps.audit.models import AuditLog
from apps.chat import services as chat
from apps.chat.models import Message
from apps.core import parametres, stats
from apps.core.errors import ErreurMetier
from apps.listings.models import Listing
from apps.listings.tests.fabriques import ListingFactory, gerant_verifie, medias_prets
from apps.moderation import services
from apps.moderation.models import ModerationAction, Report
from apps.notifications.models import Notification

pytestmark = [pytest.mark.integration, pytest.mark.pg, pytest.mark.django_db]


def client_de(utilisateur, installation="inst-mod") -> APIClient:
    d, _ = appareils.ouvrir(utilisateur, installation_id=installation, platform="android")
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {jetons.emettre_acces(utilisateur, d)}")
    return c


@pytest.fixture
def decor():
    gerant = gerant_verifie()
    annonce = ListingFactory(gerant=gerant, last_confirmed_at=timezone.now())
    medias_prets(annonce)
    locataire = ClientFactory()
    conversation, message, *_ = chat.ouvrir(locataire, annonce.pk, "Bonjour", str(uuid.uuid4()))
    reponse, *_ = chat.envoyer(gerant.user, conversation.pk, "Oui, venez voir", str(uuid.uuid4()))
    return type(
        "D",
        (),
        {
            "gerant": gerant,
            "annonce": annonce,
            "locataire": locataire,
            "conversation": conversation,
            "message": message,
            "reponse": reponse,
        },
    )


class TestSignaler:
    def test_signalement_d_une_annonce(self, decor):
        r, cree = services.signaler(
            decor.locataire, "listing", decor.annonce.pk, "fake_listing", "  Photos   volées "
        )
        assert (
            cree
            and r.status == "open"
            and r.listing_id == decor.annonce.pk
            and r.details == "Photos volées"
        )
        assert r.source == "user" and stats.lire("reports_created") == 1

    def test_idempotent_par_auteur_et_cible(self, decor):
        r1, _ = services.signaler(decor.locataire, "listing", decor.annonce.pk, "scam")
        r2, cree = services.signaler(decor.locataire, "listing", decor.annonce.pk, "fake_listing")
        assert r1.pk == r2.pk and not cree and Report.objects.count() == 1

    def test_un_nouveau_signalement_apres_cloture(self, decor):
        r1, _ = services.signaler(decor.locataire, "listing", decor.annonce.pk, "scam")
        services.classer_sans_suite(PersonnelFactory(), r1, "Rien d'anormal constaté")
        r2, cree = services.signaler(decor.locataire, "listing", decor.annonce.pk, "scam")
        assert cree and r2.pk != r1.pk

    def test_signalement_de_message_conversation_et_utilisateur(self, decor):
        r1, _ = services.signaler(decor.locataire, "message", decor.reponse.pk, "harassment")
        r2, _ = services.signaler(decor.locataire, "conversation", decor.conversation.pk, "scam")
        r3, _ = services.signaler(decor.locataire, "user", decor.gerant.user_id, "other")
        assert (r1.listing_id, r2.listing_id, r3.listing_id) == (
            decor.annonce.pk,
            decor.annonce.pk,
            None,
        )

    @pytest.mark.parametrize(
        ("construire", "code"),
        [
            (lambda d: ("listing", d.annonce.pk, "inconnu"), "validation_error"),
            (lambda d: ("listing", "pas-un-uuid", "scam"), "validation_error"),
            (lambda d: ("listing", uuid.uuid4(), "scam"), "not_found"),
            (lambda d: ("message", d.message.pk, "scam"), "forbidden"),  # son propre message
            (lambda d: ("message", uuid.uuid4(), "scam"), "not_found"),
            (lambda d: ("user", d.locataire.pk, "scam"), "forbidden"),
            (lambda d: ("user", uuid.uuid4(), "scam"), "not_found"),
            (lambda d: ("chose", uuid.uuid4(), "scam"), "validation_error"),
        ],
    )
    def test_refus(self, decor, construire, code):
        cible, ident, motif = construire(decor)
        with pytest.raises(ErreurMetier) as e:
            services.signaler(decor.locataire, cible, ident, motif)
        assert e.value.code == code

    def test_un_tiers_ne_signale_pas_une_conversation_ou_un_message_d_autrui(self, decor):
        intrus = ClientFactory()
        for cible, ident in [
            ("conversation", decor.conversation.pk),
            ("message", decor.reponse.pk),
        ]:
            with pytest.raises(ErreurMetier) as e:
                services.signaler(intrus, cible, ident, "scam")
            assert e.value.statut == 404

    def test_le_gerant_ne_signale_pas_sa_propre_annonce(self, decor):
        with pytest.raises(ErreurMetier) as e:
            services.signaler(decor.gerant.user, "listing", decor.annonce.pk, "scam")
        assert e.value.code == "forbidden"

    def test_vingt_signalements_par_jour(self, decor):
        for annonce in ListingFactory.create_batch(20):
            services.signaler(decor.locataire, "listing", annonce.pk, "scam")
        with pytest.raises(ErreurMetier) as e:
            services.signaler(decor.locataire, "listing", decor.annonce.pk, "scam")
        assert e.value.statut == 429


class TestAutomatique:
    def test_coordonnees_detectees_creent_un_signalement_systeme(
        self, decor, django_capture_on_commit_callbacks
    ):
        parametres.definir("CONTACT_LEAK_MODE", "mask")  # éteint par défaut (échange libre)
        with django_capture_on_commit_callbacks(execute=True):
            m, *_ = chat.envoyer(
                decor.locataire, decor.conversation.pk, "Appelle le 97 12 34 56", str(uuid.uuid4())
            )
        r = Report.objects.get(target_id=m.pk)
        assert r.source == "system" and r.reporter is None and r.reason_code == "contact_leak"
        assert (
            r.listing_id == decor.annonce.pk
            and "telephone" in r.details
            and stats.lire("contact_detected") == 1
        )

    def test_un_seul_dossier_ouvert_par_cible_et_motif(self, decor):
        a = services.signaler_automatiquement("message", decor.message.pk, "contact_leak", "x")
        assert (
            a is not None
            and services.signaler_automatiquement("message", decor.message.pk, "contact_leak", "x")
            is None
        )

    def test_deja_louee_trois_signalements_previennent_le_gerant_une_fois(self, decor):
        autres = ClientFactory.create_batch(3)
        for u in autres[:2]:
            services.signaler_deja_louee(u, decor.annonce.pk)
        assert not Notification.objects.filter(kind="listing.reported_rented").exists()
        services.signaler_deja_louee(autres[2], decor.annonce.pk)
        n = Notification.objects.get(kind="listing.reported_rented")
        assert n.user_id == decor.gerant.user_id
        services.signaler_deja_louee(ClientFactory(), decor.annonce.pk)
        assert Notification.objects.filter(kind="listing.reported_rented").count() == 1

    def test_deja_louee_meme_personne_ne_compte_qu_une_fois(self, decor):
        u = ClientFactory()
        for _ in range(4):
            services.signaler_deja_louee(u, decor.annonce.pk)
        assert not Notification.objects.filter(kind="listing.reported_rented").exists()


class TestFile:
    def test_prise_en_charge_et_classement(self, decor):
        mod = PersonnelFactory()
        r, _ = services.signaler(decor.locataire, "listing", decor.annonce.pk, "scam")
        services.prendre_en_charge(mod, r)
        assert r.status == "in_review" and r.assigned_to_id == mod.pk
        with pytest.raises(ErreurMetier):
            services.classer_sans_suite(mod, r, "court")
        services.classer_sans_suite(mod, r, "Annonce conforme après vérification")
        assert r.status == "resolved_dismissed" and r.resolved_at
        with pytest.raises(ErreurMetier) as e:
            services.prendre_en_charge(mod, r)
        assert e.value.code == "report_closed"
        assert AuditLog.objects.filter(action="signalement.classe").exists()

    def test_reserve_au_personnel(self, decor):
        r, _ = services.signaler(decor.locataire, "listing", decor.annonce.pk, "scam")
        with pytest.raises(ErreurMetier) as e:
            services.prendre_en_charge(decor.locataire, r)
        assert e.value.statut == 403

    def test_tableau_de_moderation(self, decor):
        mod = PersonnelFactory()
        r1, _ = services.signaler(decor.locataire, "listing", decor.annonce.pk, "scam")
        r2, _ = services.signaler(ClientFactory(), "listing", decor.annonce.pk, "scam")
        Report.objects.filter(pk=r2.pk).update(
            created_at=timezone.now() - datetime.timedelta(hours=30)
        )
        services.classer_sans_suite(mod, r1, "Annonce conforme après vérification")
        t = services.tableau()
        assert (
            t["ouverts"] == 1
            and t["hors_delai"] == 1
            and t["par_statut"]["resolved_dismissed"] == 1
        )
        assert t["delai_median_h"] is not None


class TestActions:
    def test_motif_obligatoire_et_personnel_seulement(self, decor):
        with pytest.raises(ErreurMetier) as e:
            services.appliquer(
                PersonnelFactory(), "warning", motif="court", utilisateur=decor.locataire
            )
        assert "reason" in e.value.champs
        with pytest.raises(ErreurMetier) as e:
            services.appliquer(
                decor.locataire,
                "warning",
                motif="Un motif suffisamment long",
                utilisateur=decor.gerant.user,
            )
        assert e.value.statut == 403

    def test_masquer_et_supprimer_un_message(self, decor):
        mod = PersonnelFactory()
        r, _ = services.signaler(decor.gerant.user, "message", decor.message.pk, "harassment")
        a = services.appliquer(
            mod,
            "message_masked",
            motif="Propos déplacés envers le gérant",
            rapport=r,
            message_id=decor.message.pk,
        )
        decor.message.refresh_from_db()
        assert (
            decor.message.moderation_status == "masked" and a.target_user_id == decor.locataire.pk
        )
        assert r.status == "resolved_actioned" and r.resolved_by_id == mod.pk
        n = Notification.objects.get(kind="account.sanction", user=decor.locataire)
        assert "masqué" in n.title and "Propos déplacés" in n.body
        services.appliquer(
            mod,
            "message_deleted",
            motif="Après réexamen : suppression",
            message_id=decor.message.pk,
        )
        decor.message.refresh_from_db()
        assert decor.message.moderation_status == "deleted"
        with pytest.raises(ErreurMetier):
            services.appliquer(
                mod, "message_masked", motif="Message inexistant ici", message_id=uuid.uuid4()
            )

    def test_masquer_puis_retirer_une_annonce(self, decor):
        mod = PersonnelFactory()
        services.appliquer(
            mod,
            "listing_hidden",
            motif="Photos qui ne correspondent pas",
            annonce_id=decor.annonce.pk,
        )
        decor.annonce.refresh_from_db()
        assert decor.annonce.status == "hidden" and decor.annonce.hidden_reason == "moderation"
        assert Notification.objects.filter(kind="account.sanction", user=decor.gerant.user).exists()
        services.appliquer(
            mod,
            "listing_removed",
            motif="Annonce frauduleuse confirmée",
            annonce_id=decor.annonce.pk,
        )
        decor.annonce.refresh_from_db()
        assert decor.annonce.status == "removed" and decor.annonce.hidden_reason is None

    def test_annonce_inconnue(self, decor):
        with pytest.raises(ErreurMetier) as e:
            services.appliquer(
                PersonnelFactory(),
                "listing_hidden",
                motif="Motif suffisamment long",
                annonce_id=uuid.uuid4(),
            )
        assert e.value.statut == 404

    def test_avertissement(self, decor):
        a = services.appliquer(
            PersonnelFactory(),
            "warning",
            motif="Évite de partager tes coordonnées",
            utilisateur=decor.locataire,
        )
        assert (
            a.action == "warning"
            and Notification.objects.filter(kind="account.sanction", user=decor.locataire).count()
            == 1
        )
        with pytest.raises(ErreurMetier):
            services.appliquer(PersonnelFactory(), "warning", motif="Sans destinataire précisé")

    def test_suspension_d_un_gerant_masque_ses_annonces_puis_retablissement(self, decor):
        mod = PersonnelFactory()
        autre = ListingFactory(gerant=decor.gerant, last_confirmed_at=timezone.now())
        medias_prets(autre)
        fin = timezone.now() + datetime.timedelta(days=10)
        a = services.appliquer(
            mod,
            "suspension",
            motif="Plusieurs arnaques signalées",
            utilisateur=decor.gerant.user,
            jusqua=fin,
        )
        decor.gerant.user.refresh_from_db()
        assert decor.gerant.user.status == "suspended" and a.ends_at == fin
        assert set(
            Listing.objects.filter(gerant=decor.gerant).values_list("status", "hidden_reason")
        ) == {("hidden", "gerant_suspended")}
        services.appliquer(
            mod,
            "reinstatement",
            motif="Sanction levée après échange",
            utilisateur=decor.gerant.user,
        )
        decor.gerant.user.refresh_from_db()
        assert decor.gerant.user.status == "active"
        assert set(
            Listing.objects.filter(gerant=decor.gerant).values_list("status", flat=True)
        ) == {"published"}
        a.refresh_from_db()
        assert a.revoked_at and a.revoked_by_id == mod.pk and autre.pk

    def test_annonce_perimee_pendant_la_suspension_reste_masquee_sans_confirmation(self, decor):
        parametres.definir("STALE_HIDE_DAYS", 14)  # masquage automatique coupé par défaut (plan v3)
        mod = PersonnelFactory()
        services.appliquer(
            mod,
            "suspension",
            motif="Suspension de test",
            utilisateur=decor.gerant.user,
            jusqua=timezone.now() + datetime.timedelta(days=5),
        )
        Listing.objects.filter(pk=decor.annonce.pk).update(
            last_confirmed_at=timezone.now() - datetime.timedelta(days=20)
        )
        services.appliquer(
            mod, "reinstatement", motif="Rétablissement de test", utilisateur=decor.gerant.user
        )
        decor.annonce.refresh_from_db()
        assert decor.annonce.status == "hidden" and decor.annonce.hidden_reason == "stale"

    def test_plafond_de_suspension_d_un_moderateur(self, decor):
        trop = timezone.now() + datetime.timedelta(days=31)
        with pytest.raises(ErreurMetier) as e:
            services.appliquer(
                PersonnelFactory(),
                "suspension",
                motif="Suspension trop longue",
                utilisateur=decor.locataire,
                jusqua=trop,
            )
        assert e.value.statut == 403
        services.appliquer(
            AdminFactory(),
            "suspension",
            motif="Suspension longue admin",
            utilisateur=decor.locataire,
            jusqua=trop,
        )
        decor.locataire.refresh_from_db()
        assert decor.locataire.status == "suspended"

    @pytest.mark.parametrize("fin", [None, "passee"])
    def test_suspension_exige_une_fin_future(self, decor, fin):
        jusqua = None if fin is None else timezone.now() - datetime.timedelta(days=1)
        with pytest.raises(ErreurMetier) as e:
            services.appliquer(
                PersonnelFactory(),
                "suspension",
                motif="Suspension sans fin",
                utilisateur=decor.locataire,
                jusqua=jusqua,
            )
        assert "ends_at" in e.value.champs

    def test_seul_un_administrateur_bannit(self, decor):
        with pytest.raises(ErreurMetier) as e:
            services.appliquer(
                PersonnelFactory(), "ban", motif="Bannissement demandé", utilisateur=decor.locataire
            )
        assert e.value.statut == 403
        services.appliquer(
            AdminFactory(), "ban", motif="Récidive de fraude avérée", utilisateur=decor.gerant.user
        )
        decor.gerant.user.refresh_from_db()
        assert decor.gerant.user.status == "banned"
        decor.annonce.refresh_from_db()
        assert decor.annonce.status == "hidden"
        assert ModerationAction.objects.filter(action="ban", target_user=decor.gerant.user).exists()
        assert AuditLog.objects.filter(action="moderation.ban").exists()

    def test_un_moderateur_ne_sanctionne_pas_un_autre_membre_du_personnel(self, decor):
        with pytest.raises(ErreurMetier) as e:
            services.appliquer(PersonnelFactory(), "suspension", motif="Tentative interdite",
                               utilisateur=AdminFactory(), jusqua=timezone.now() + datetime.timedelta(days=2))  # fmt: skip
        assert e.value.statut == 403

    def test_action_inconnue(self, decor):
        with pytest.raises(ErreurMetier):
            services.appliquer(
                PersonnelFactory(),
                "explosion",
                motif="Action qui n'existe pas",
                utilisateur=decor.locataire,
            )

    def test_le_compte_suspendu_ne_peut_plus_ecrire_ni_ouvrir_de_conversation(self, decor):
        services.appliquer(
            PersonnelFactory(),
            "suspension",
            motif="Suspension de test",
            utilisateur=decor.locataire,
            jusqua=timezone.now() + datetime.timedelta(days=2),
        )
        decor.locataire.refresh_from_db()
        with pytest.raises(ErreurMetier) as e:
            chat.envoyer(decor.locataire, decor.conversation.pk, "Bonjour ?", str(uuid.uuid4()))
        assert e.value.code == "account_suspended"


class TestFinDeSuspension:
    def test_les_suspensions_echues_sont_levees_et_les_annonces_remises(self, decor):
        services.appliquer(
            PersonnelFactory(),
            "suspension",
            motif="Suspension courte",
            utilisateur=decor.gerant.user,
            jusqua=timezone.now() + datetime.timedelta(days=1),
        )
        assert services.expirer_sanctions() == 0
        from apps.accounts.models import User

        User.objects.filter(pk=decor.gerant.user_id).update(
            suspended_until=timezone.now() - datetime.timedelta(minutes=1)
        )
        assert services.expirer_sanctions() == 1
        decor.gerant.user.refresh_from_db()
        decor.annonce.refresh_from_db()
        assert decor.gerant.user.status == "active" and decor.annonce.status == "published"
        assert ModerationAction.objects.get(action="suspension").revoked_at
        assert Notification.objects.filter(
            user=decor.gerant.user, title__contains="terminée"
        ).exists()
        assert services.expirer_sanctions() == 0

    def test_un_bannissement_n_expire_pas(self, decor):
        services.appliquer(
            AdminFactory(), "ban", motif="Bannissement définitif", utilisateur=decor.locataire
        )
        assert services.expirer_sanctions() == 0


class TestLectureJournalisee:
    def test_motif_obligatoire_avant_ouverture(self, decor):
        with pytest.raises(ErreurMetier) as e:
            services.lire_conversation(PersonnelFactory(), decor.conversation.pk, "x")
        assert "reason" in e.value.champs
        assert not AuditLog.objects.filter(action="conversation.lue_par_personnel").exists()

    def test_lecture_complete_et_journalisee(self, decor):
        mod = PersonnelFactory()
        Message.objects.filter(pk=decor.message.pk).update(moderation_status="deleted")
        res = services.lire_conversation(
            mod, decor.conversation.pk, "Vérification d'un signalement de harcèlement"
        )
        assert [m["seq"] for m in res["messages"]] == [1, 2] and res["messages"][0][
            "body"
        ] == "Bonjour"  # texte d'origine
        trace = AuditLog.objects.get(action="conversation.lue_par_personnel")
        assert (
            trace.actor_id == mod.pk
            and trace.target_id == decor.conversation.pk
            and "harcèlement" in trace.metadata["motif"]
        )

    def test_alerte_apres_le_seuil_quotidien(self, decor):
        parametres.definir("STAFF_READS_ALERT_THRESHOLD", 2)
        mod = PersonnelFactory()
        for _ in range(3):
            services.lire_conversation(
                mod, decor.conversation.pk, "Vérification de routine du dossier"
            )
        assert (
            AuditLog.objects.filter(action="conversation.lectures_excessives", actor=mod).count()
            == 1
        )

    def test_conversation_inconnue_et_acces_refuse_aux_non_membres(self, decor):
        with pytest.raises(ErreurMetier) as e:
            services.lire_conversation(PersonnelFactory(), uuid.uuid4(), "Motif suffisamment long")
        assert e.value.statut == 404
        with pytest.raises(ErreurMetier) as e:
            services.lire_conversation(
                decor.locataire, decor.conversation.pk, "Motif suffisamment long"
            )
        assert e.value.statut == 403


class TestDecisionsSurAnnonces:
    def test_approuver_la_premiere_annonce(self):
        from apps.listings.services import annonces
        from apps.listings.tests.fabriques import medias_prets

        p = gerant_verifie()
        a = ListingFactory(gerant=p, status="processing", published_at=None)
        medias_prets(a)
        annonces.approuver_premiere(a, acteur=PersonnelFactory())
        a.refresh_from_db()
        assert a.status == "published" and a.published_at is not None

    def test_approbation_refusee_si_pas_en_attente_ou_incomplete(self):
        from apps.listings.services import annonces

        a = ListingFactory()
        with pytest.raises(ErreurMetier) as e:
            annonces.approuver_premiere(a, acteur=PersonnelFactory())
        assert e.value.code == "listing_locked"
        b = ListingFactory(status="processing", published_at=None)
        with pytest.raises(ErreurMetier) as e:
            annonces.approuver_premiere(b, acteur=PersonnelFactory())  # aucun média prêt
        assert e.value.code == "listing_not_publishable"

    def test_refuser(self):
        from apps.listings.services import annonces

        a = ListingFactory(status="processing", published_at=None)
        annonces.refuser(a, acteur=PersonnelFactory())
        a.refresh_from_db()
        assert (a.status, a.hidden_reason) == ("hidden", "moderation")
        with pytest.raises(ErreurMetier):
            annonces.refuser(ListingFactory(status="rented"), acteur=PersonnelFactory())


class TestApi:
    def test_signaler(self, decor):
        c = client_de(decor.locataire)
        corps = {
            "target_type": "listing",
            "target_id": str(decor.annonce.pk),
            "reason_code": "fake_listing",
            "details": "Photos volées",
        }
        r = c.post("/v1/reports", corps, format="json")
        assert r.status_code == 201 and r.json()["status"] == "open" and r.json()["created"] is True
        assert c.post("/v1/reports", corps, format="json").status_code == 200

    def test_validation_et_authentification(self, decor):
        c = client_de(decor.locataire)
        assert (
            c.post(
                "/v1/reports",
                {
                    "target_type": "listing",
                    "target_id": str(decor.annonce.pk),
                    "reason_code": "nimporte",
                },
                format="json",
            ).status_code
            == 400
        )
        assert (
            c.post(
                "/v1/reports",
                {"target_type": "listing", "target_id": str(uuid.uuid4()), "reason_code": "scam"},
                format="json",
            ).status_code
            == 404
        )
        assert APIClient().post("/v1/reports", {}, format="json").status_code == 401

    def test_le_gerant_peut_signaler_un_message(self, decor):
        r = client_de(decor.gerant.user).post(
            "/v1/reports",
            {
                "target_type": "message",
                "target_id": str(decor.message.pk),
                "reason_code": "harassment",
            },
            format="json",
        )
        assert r.status_code == 201

    def test_deja_louee(self, decor):
        c = client_de(decor.locataire)
        assert c.post(f"/v1/listings/{decor.annonce.pk}/report-rented").status_code == 201
        assert c.post(f"/v1/listings/{decor.annonce.pk}/report-rented").status_code == 200
        assert (
            client_de(decor.gerant.user, "i-g")
            .post(f"/v1/listings/{decor.annonce.pk}/report-rented")
            .status_code
            == 403
        )
