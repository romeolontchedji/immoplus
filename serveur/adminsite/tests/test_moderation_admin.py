"""Administration de la modération : relecture des annonces, file de signalements, décisions, lecture journalisée."""

import datetime
import uuid

import pytest
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone

from adminsite.tests.test_administration import REGLAGES, personnel, se_connecter
from apps.accounts.tests.fabriques import AdminFactory, ClientFactory, PersonnelFactory
from apps.audit.models import AuditLog
from apps.chat import services as chat
from apps.listings.models import Listing
from apps.listings.tests.fabriques import ListingFactory, gerant_verifie, medias_prets
from apps.moderation import services
from apps.moderation.models import ModerationAction, Report

pytestmark = [pytest.mark.integration, pytest.mark.pg, pytest.mark.django_db, pytest.mark.securite]


@pytest.fixture(autouse=True)
def reglages_admin():
    with override_settings(**REGLAGES):
        yield


@pytest.fixture
def mod():
    u = personnel(PersonnelFactory)
    c = Client()
    se_connecter(u, client=c)
    return u, c


def lancer(c, nom_modele, action, ids):
    return c.post(
        reverse(f"admin:{nom_modele}_changelist"),
        {"action": action, "_selected_action": [str(i) for i in ids]},
        follow=True,
    )


class TestRelectureDesAnnonces:
    def test_approuver_la_premiere_annonce(self, mod):
        _, c = mod
        a = ListingFactory(gerant=gerant_verifie(), status="processing", published_at=None)
        medias_prets(a)
        r = lancer(c, "listings_listing", "approuver", [a.pk])
        assert r.status_code == 200
        a.refresh_from_db()
        assert a.status == "published"
        assert AuditLog.objects.filter(action="listing.status_changed", target_id=a.pk).exists()

    def test_refuser(self, mod):
        _, c = mod
        a = ListingFactory(status="processing", published_at=None)
        lancer(c, "listings_listing", "refuser", [a.pk])
        a.refresh_from_db()
        assert (a.status, a.hidden_reason) == ("hidden", "moderation")

    def test_une_annonce_incomplete_n_est_pas_publiee_et_le_motif_est_affiche(self, mod):
        _, c = mod
        a = ListingFactory(status="processing", published_at=None)
        r = lancer(c, "listings_listing", "approuver", [a.pk])
        a.refresh_from_db()
        assert a.status == "processing" and "pas publiable" in r.content.decode()

    def test_la_fiche_admin_n_expose_pas_l_adresse_privee(self, mod):
        _, c = mod
        a = ListingFactory(address_private="Rue 12 maison bleue")
        r = c.get(reverse("admin:listings_listing_change", args=[a.pk]))
        assert r.status_code == 200 and "Rue 12" not in r.content.decode()

    def test_pas_d_ajout_ni_de_suppression(self, mod):
        _, c = mod
        assert c.get(reverse("admin:listings_listing_add")).status_code == 403


class TestSignalements:
    def test_file_prise_en_charge_et_classement(self, mod):
        u, c = mod
        a = ListingFactory()
        r1, _ = services.signaler(ClientFactory(), "listing", a.pk, "scam")
        r2, _ = services.signaler(ClientFactory(), "listing", a.pk, "fake_listing")
        page = c.get(reverse("admin:moderation_report_changelist"))
        assert page.status_code == 200 and "Dossiers ouverts : 2" in page.content.decode()
        lancer(c, "moderation_report", "prendre", [r1.pk])
        lancer(c, "moderation_report", "classer", [r2.pk])
        r1.refresh_from_db()
        r2.refresh_from_db()
        assert r1.status == "in_review" and r1.assigned_to_id == u.pk
        assert r2.status == "resolved_dismissed"

    def test_lecture_de_conversation_exige_le_motif_et_se_journalise(self, mod):
        u, c = mod
        gerant = gerant_verifie()
        annonce = ListingFactory(gerant=gerant)
        locataire = ClientFactory()
        conversation, message, *_ = chat.ouvrir(
            locataire, annonce.pk, "Bonjour, le loyer ?", str(uuid.uuid4())
        )
        rapport, _ = services.signaler(gerant.user, "conversation", conversation.pk, "harassment")
        url = reverse("admin:moderation_report_conversation", args=[rapport.pk])
        assert "Motif de la lecture" in c.get(url).content.decode()
        refus = c.post(url, {"reason": "x"})
        assert "Bonjour, le loyer" not in refus.content.decode()
        assert not AuditLog.objects.filter(action="conversation.lue_par_personnel").exists()
        ok = c.post(url, {"reason": "Vérification d'un signalement de harcèlement"})
        assert "Bonjour, le loyer" in ok.content.decode()
        assert (
            AuditLog.objects.filter(action="conversation.lue_par_personnel", actor=u).count() == 1
        )

    def test_un_signalement_d_annonce_n_ouvre_pas_de_conversation(self, mod):
        _, c = mod
        r, _ = services.signaler(ClientFactory(), "listing", ListingFactory().pk, "scam")
        assert (
            c.get(reverse("admin:moderation_report_conversation", args=[r.pk])).status_code == 403
        )


class TestDecisions:
    def test_avertissement_par_le_formulaire(self, mod):
        u, c = mod
        cible = ClientFactory()
        r = c.post(
            reverse("admin:moderation_moderationaction_add"),
            {
                "action": "warning",
                "target_user": cible.pk,
                "reason": "Évite de partager tes coordonnées.",
            },
            follow=True,
        )
        assert r.status_code == 200
        a = ModerationAction.objects.get(action="warning")
        assert a.actor_id == u.pk and a.target_user_id == cible.pk

    def test_masquage_d_annonce_par_le_formulaire(self, mod):
        _, c = mod
        a = ListingFactory()
        c.post(
            reverse("admin:moderation_moderationaction_add"),
            {"action": "listing_hidden", "target_listing": a.pk, "reason": "Photos non conformes."},
            follow=True,
        )
        a.refresh_from_db()
        assert a.status == "hidden" and a.hidden_reason == "moderation"

    def test_une_decision_refusee_ne_cree_rien_et_explique_pourquoi(self, mod):
        _, c = mod
        cible = ClientFactory()
        trop_long = timezone.localtime(timezone.now() + datetime.timedelta(days=45))
        r = c.post(
            reverse("admin:moderation_moderationaction_add"),
            {
                "action": "suspension",
                "target_user": cible.pk,
                "ends_at_0": trop_long.strftime("%Y-%m-%d"),
                "ends_at_1": trop_long.strftime("%H:%M:%S"),
                "reason": "Suspension trop longue.",
            },
            follow=True,
        )
        assert not ModerationAction.objects.exists()
        assert "30 jours au plus" in r.content.decode()
        cible.refresh_from_db()
        assert cible.status == "active"

    def test_un_moderateur_ne_peut_pas_bannir_mais_un_administrateur_oui(self, mod):
        _, c = mod
        cible = ClientFactory()
        donnees = {"action": "ban", "target_user": cible.pk, "reason": "Fraude avérée et répétée."}
        c.post(reverse("admin:moderation_moderationaction_add"), donnees, follow=True)
        cible.refresh_from_db()
        assert cible.status == "active"
        admin_user = personnel(AdminFactory)
        c2 = Client()
        se_connecter(admin_user, client=c2)
        c2.post(reverse("admin:moderation_moderationaction_add"), donnees, follow=True)
        cible.refresh_from_db()
        assert cible.status == "banned"

    def test_les_decisions_ne_se_modifient_ni_ne_se_suppriment(self, mod):
        _, c = mod
        a = services.appliquer(
            PersonnelFactory(),
            "warning",
            motif="Avertissement de test",
            utilisateur=ClientFactory(),
        )
        assert (
            c.get(reverse("admin:moderation_moderationaction_delete", args=[a.pk])).status_code
            == 403
        )
        assert Listing.objects.count() == 0 and Report.objects.count() == 0


class TestTypesDeLogement:
    """Décision V1 : valider une proposition, ou la rattacher à un type validé."""

    def test_valider(self, mod):
        from apps.listings.models import RoomType
        from apps.listings.services import types

        _, c = mod
        t = types.proposer(gerant_verifie(), "Villa")
        lancer(c, "listings_roomtype", "valider", [t.pk])
        t.refresh_from_db()
        assert t.status == "approved"
        assert AuditLog.objects.filter(action="room_type.valide").exists()
        assert RoomType.objects.filter(slug="villa", status="approved").exists()

    def test_rattacher(self, mod):
        from apps.listings.models import RoomType
        from apps.listings.services import types

        _, c = mod
        t = types.proposer(gerant_verifie(), "Studette")
        a = ListingFactory(room_type=t.slug)
        url = reverse("admin:listings_roomtype_rattacher", args=[t.pk])
        page = c.get(url)
        assert page.status_code == 200 and "1 annonce(s)" in page.content.decode()
        cible = RoomType.objects.get(slug="studio")
        r = c.post(url, {"cible": cible.pk})
        assert r.status_code == 302
        a.refresh_from_db()
        assert a.room_type == "studio" and not RoomType.objects.filter(pk=t.pk).exists()

    def test_pas_de_suppression_ni_d_ajout(self, mod):
        _, c = mod
        assert c.get(reverse("admin:listings_roomtype_add")).status_code == 403
