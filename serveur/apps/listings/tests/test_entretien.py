"""Entretien planifié : fraîcheur, vidéos louées, archivage, comptes sanctionnés ou supprimés, planning beat."""

import datetime
import uuid

import pytest
from django.utils import timezone

from apps.accounts.models import OtpCode, User
from apps.accounts.services import administration
from apps.accounts.tests.fabriques import AdminFactory, ClientFactory
from apps.audit import services as audit
from apps.audit.models import AuditLog
from apps.chat import services as chat
from apps.chat.models import Conversation
from apps.core import parametres
from apps.listings.models import Listing, ListingMedia
from apps.listings.services import annonces, entretien
from apps.notifications.models import Notification

from .fabriques import ListingFactory, gerant_verifie, medias_prets

pytestmark = [pytest.mark.integration, pytest.mark.pg, pytest.mark.django_db]


def vieillir(annonce, jours):
    Listing.objects.filter(pk=annonce.pk).update(
        last_confirmed_at=timezone.now() - datetime.timedelta(days=jours)
    )


def test_masquage_automatique_coupe_par_defaut():
    assert parametres.lire("STALE_HIDE_DAYS") == 0


class TestFraicheur:
    @pytest.fixture(autouse=True)
    def masquage_actif(self):
        """Masquage automatique coupé par défaut depuis le 19/10/2026 : ces tests l'activent (14 jours)."""
        parametres.definir("STALE_HIDE_DAYS", 14)

    def test_desactive_par_defaut_ni_relance_ni_masquage(self):
        parametres.definir("STALE_HIDE_DAYS", 0)
        a = ListingFactory()
        vieillir(a, 60)
        assert entretien.relances_de_fraicheur() == {"relances": 0, "masquees": 0}
        a.refresh_from_db()
        assert a.status == "published"

    def test_rien_avant_sept_jours(self):
        a = ListingFactory(last_confirmed_at=timezone.now() - datetime.timedelta(days=6))
        assert entretien.relances_de_fraicheur() == {"relances": 0, "masquees": 0}
        a.refresh_from_db()
        assert a.status == "published" and a.reminder_stage == 0

    def test_relances_a_sept_et_dix_jours_une_seule_fois_chacune(self):
        a = ListingFactory()
        vieillir(a, 7)
        assert entretien.relances_de_fraicheur()["relances"] == 1
        assert entretien.relances_de_fraicheur()["relances"] == 0
        vieillir(a, 10)
        assert entretien.relances_de_fraicheur()["relances"] == 1
        a.refresh_from_db()
        assert a.reminder_stage == 2 and a.status == "published"
        n = Notification.objects.filter(kind="listing.reminder", user=a.gerant.user)
        assert n.count() == 2 and "4 jour" in n.order_by("-created_at").first().body

    def test_masquage_a_quatorze_jours_avec_notification(self, django_capture_on_commit_callbacks):
        a = ListingFactory()
        vieillir(a, 14)
        with django_capture_on_commit_callbacks(execute=True):
            assert entretien.relances_de_fraicheur()["masquees"] == 1
        a.refresh_from_db()
        assert (a.status, a.hidden_reason) == ("hidden", "stale")
        assert Notification.objects.filter(kind="listing.hidden", user=a.gerant.user).exists()

    def test_les_seuils_sont_des_parametres(self):
        parametres.definir("STALE_HIDE_DAYS", 5)
        a = ListingFactory()
        vieillir(a, 5)
        assert entretien.relances_de_fraicheur()["masquees"] == 1
        a.refresh_from_db()
        assert a.hidden_reason == "stale"

    def test_confirmer_remet_les_etapes_a_zero_et_remet_en_ligne(self):
        p = gerant_verifie()
        a = ListingFactory(gerant=p)
        medias_prets(a)
        vieillir(a, 14)
        entretien.relances_de_fraicheur()
        annonces.confirmer(p, a.pk)
        a.refresh_from_db()
        assert a.status == "published" and a.reminder_stage == 0

    def test_les_annonces_non_publiees_sont_ignorees(self):
        for statut in ("hidden", "rented", "draft"):
            vieillir(ListingFactory(status=statut), 30)
        assert entretien.relances_de_fraicheur() == {"relances": 0, "masquees": 0}


class TestMedias:
    def test_video_d_une_annonce_louee_supprimee_apres_sept_jours(self):
        p = gerant_verifie()
        a = ListingFactory(gerant=p)
        medias_prets(a, photos=2, video=True)
        annonces.marquer_louee(p, a.pk)
        video = ListingMedia.objects.get(listing=a, kind="video")
        assert video.delete_after is not None
        assert entretien.purger_medias()["videos"] == 0
        ListingMedia.objects.filter(pk=video.pk).update(
            delete_after=timezone.now() - datetime.timedelta(minutes=1)
        )
        assert entretien.purger_medias()["videos"] == 1
        video.refresh_from_db()
        assert video.deleted_at is not None
        assert entretien.purger_medias()["videos"] == 0
        assert (
            ListingMedia.objects.filter(listing=a, kind="photo", deleted_at__isnull=True).count()
            == 2
        )

    def test_originaux_supprimes_vingt_quatre_heures_apres_le_traitement(self):
        a = ListingFactory()
        m = ListingMedia.objects.create(
            listing=a,
            kind="photo",
            status="ready",
            declared_size_bytes=1,
            original_path="media_tmp/x",
        )
        assert entretien.purger_medias()["originaux"] == 0
        ListingMedia.objects.filter(pk=m.pk).update(
            updated_at=timezone.now() - datetime.timedelta(hours=25)
        )
        assert entretien.purger_medias()["originaux"] == 1
        m.refresh_from_db()
        assert m.original_path is None


class TestLoueeEtArchivage:
    def test_archivage_apres_nonante_jours(self):
        recente = ListingFactory(
            status="rented", rented_at=timezone.now() - datetime.timedelta(days=60)
        )
        vieille = ListingFactory(
            status="rented", rented_at=timezone.now() - datetime.timedelta(days=91)
        )
        assert entretien.archiver_louees() == 1
        recente.refresh_from_db()
        vieille.refresh_from_db()
        assert recente.status == "rented" and vieille.status == "archived"

    def test_conversations_en_lecture_seule_apres_trente_jours(self):
        p = gerant_verifie()
        a = ListingFactory(gerant=p)
        locataire = ClientFactory()
        c, *_ = chat.ouvrir(locataire, a.pk, "Bonjour", str(uuid.uuid4()))
        annonces.marquer_louee(p, a.pk)
        assert chat.passer_en_lecture_seule_apres_location() == 0
        Listing.objects.filter(pk=a.pk).update(
            rented_at=timezone.now() - datetime.timedelta(days=31)
        )
        assert chat.passer_en_lecture_seule_apres_location() == 1
        assert Conversation.objects.get(pk=c.pk).status == "read_only"
        assert chat.passer_en_lecture_seule_apres_location() == 0


class TestComptes:
    def test_suspension_depuis_l_administration_masque_les_annonces_puis_les_remet(self):
        p = gerant_verifie()
        a = ListingFactory(gerant=p, last_confirmed_at=timezone.now())
        medias_prets(a)
        admin = AdminFactory()
        administration.changer_statut(
            acteur=admin,
            cible=p.user,
            statut="suspended",
            jusqu_a=timezone.now() + datetime.timedelta(days=3),
        )
        a.refresh_from_db()
        assert (a.status, a.hidden_reason) == ("hidden", "gerant_suspended")
        administration.changer_statut(acteur=admin, cible=p.user, statut="active")
        a.refresh_from_db()
        assert a.status == "published"

    def test_bannissement_masque_et_un_client_ne_touche_a_rien(self):
        p = gerant_verifie()
        a = ListingFactory(gerant=p)
        administration.changer_statut(acteur=AdminFactory(), cible=ClientFactory(), statut="banned")
        a.refresh_from_db()
        assert a.status == "published"
        administration.changer_statut(acteur=AdminFactory(), cible=p.user, statut="banned")
        a.refresh_from_db()
        assert a.status == "hidden"

    def test_suppression_du_compte_archive_les_annonces_et_supprime_les_brouillons(self):
        p = gerant_verifie()
        publiee = ListingFactory(gerant=p)
        brouillon = ListingFactory(gerant=p, status="draft", published_at=None)
        masquee = ListingFactory(gerant=p, status="hidden")
        assert annonces.archiver_du_gerant(p.user_id) == 2
        for x in (publiee, masquee, brouillon):
            x.refresh_from_db()
        assert (publiee.status, masquee.status) == (
            "archived",
            "archived",
        ) and brouillon.deleted_at is not None

    def test_le_signal_de_suppression_declenche_l_archivage(self, monkeypatch):
        from apps.accounts import signals

        p = gerant_verifie()
        a = ListingFactory(gerant=p)
        signals.compte_supprime.send(sender=User, utilisateur_id=p.user_id, role="gerant")
        a.refresh_from_db()
        assert a.status == "archived"
        autre = ListingFactory()
        signals.compte_supprime.send(
            sender=User, utilisateur_id=autre.gerant.user_id, role="client"
        )
        autre.refresh_from_db()
        assert autre.status == "published"


class TestIndicateursEtPurges:
    def test_taux_et_delai_de_reponse(self):
        p = gerant_verifie()
        sans, avec = ListingFactory(gerant=p), ListingFactory(gerant=p)
        c1, *_ = chat.ouvrir(ClientFactory(), sans.pk, "Bonjour", str(uuid.uuid4()))
        c2, *_ = chat.ouvrir(ClientFactory(), avec.pk, "Bonjour", str(uuid.uuid4()))
        chat.envoyer(p.user, c2.pk, "Oui", str(uuid.uuid4()))
        Conversation.objects.filter(pk=c2.pk).update(
            first_reply_at=timezone.now() + datetime.timedelta(minutes=20),
            created_at=timezone.now(),
        )
        resultat = chat.calculer_indicateurs_gerants()
        taux, delai = resultat[p.user_id]
        assert float(taux) == 50.0 and 19 <= delai <= 21 and c1
        assert administration.maj_indicateurs_gerants(resultat) == 1
        p.refresh_from_db()
        assert float(p.response_rate_30d) == 50.0 and p.median_response_min == delai

    def test_purge_des_codes_otp(self):
        ancien = OtpCode.objects.create(
            phone_e164="+22901000000",
            purpose="signup",
            code_hmac="a" * 64,
            expires_at=timezone.now() - datetime.timedelta(days=8),
        )
        recent = OtpCode.objects.create(
            phone_e164="+22901000001",
            purpose="signup",
            code_hmac="b" * 64,
            expires_at=timezone.now() - datetime.timedelta(days=1),
        )
        assert administration.purger_otp() == 1
        assert (
            not OtpCode.objects.filter(pk=ancien.pk).exists()
            and OtpCode.objects.filter(pk=recent.pk).exists()
        )

    def test_retention_de_l_audit_sans_role_ne_fait_rien_de_dangereux(self):
        audit.enregistrer("test.action", cible_type="test")
        bilan = audit.purger_selon_retention()
        assert AuditLog.objects.filter(action="test.action").exists()
        assert bilan["ignore"] in (True, False)


def test_toutes_les_taches_planifiees_existent():
    from config.celery import app

    app.loader.import_default_modules()
    manquantes = [c["task"] for c in app.conf.beat_schedule.values() if c["task"] not in app.tasks]
    assert manquantes == []


def test_toutes_les_files_sont_connues():
    from config.celery import app

    app.loader.import_default_modules()
    for nom in (
        "apps.notifications.message",
        "apps.notifications.envoyer_push",
        "apps.media.purger",
    ):
        assert nom in app.tasks
