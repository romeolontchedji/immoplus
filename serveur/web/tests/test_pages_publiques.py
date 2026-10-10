"""Pages publiques et espace locataire : fil, fiche, favoris, alertes, messages, notifications, référencement."""

import re
import uuid

import pytest
from django.test import Client

from apps.accounts.tests.fabriques import MOT_DE_PASSE, ClientFactory
from apps.chat import services as chat
from apps.listings.models import Alert, Favorite
from apps.listings.tests.fabriques import (
    DistrictFactory,
    ListingFactory,
    gerant_verifie,
    medias_prets,
)
from apps.moderation.models import Report
from apps.notifications import services as notifications

pytestmark = [pytest.mark.integration, pytest.mark.pg, pytest.mark.django_db]


def connecte(utilisateur) -> Client:
    c = Client()
    c.force_login(utilisateur, backend="django.contrib.auth.backends.ModelBackend")
    session = c.session
    session["tv"] = (
        utilisateur.token_version
    )  # version de sécurité vérifiée par le middleware du site
    session.save()
    return c


def html(reponse) -> str:
    return reponse.content.decode()


class TestFilEtFiche:
    def test_accueil_liste_les_annonces_publiees(self):
        a = ListingFactory(title="Chambre lumineuse à Banikanni")
        ListingFactory(title="Annonce masquée", status="hidden")
        page = html(Client().get("/"))
        assert "Chambre lumineuse à Banikanni" in page and "Annonce masquée" not in page
        assert f"/annonces/{a.slug}" in page

    def test_recherche_filtres_et_message_vide(self):
        ListingFactory(title="Studio moderne", rent_amount=40000)
        ListingFactory(title="Chambre simple", rent_amount=15000)
        page = html(Client().get("/annonces?rent_max=20000"))
        assert "Chambre simple" in page and "Studio moderne" not in page
        vide = html(Client().get("/annonces?q=introuvable&rent_max=1000"))
        assert "Aucune chambre" in vide and "Crée une alerte" in vide

    def test_parametre_invalide_affiche_une_erreur_sans_planter(self):
        r = Client().get("/annonces?sort=nimporte")
        assert r.status_code == 200 and "Tri inconnu" in html(r)

    def test_pagination_par_lien(self):
        ListingFactory.create_batch(12)
        page = html(Client().get("/annonces"))
        lien = re.search(r'href="\?([^"]*cursor=[^"]+)"', page)
        assert lien and "Voir plus" in page
        assert Client().get("/annonces?" + lien.group(1).replace("&amp;", "&")).status_code == 200

    def test_page_quartier(self):
        q = DistrictFactory(slug="titirou", name="Titirou")
        ListingFactory(district=q, title="Chambre à Titirou")
        ListingFactory(title="Ailleurs")
        page = html(Client().get("/quartiers/titirou"))
        assert (
            "Chambres à Titirou" in page and "Chambre à Titirou" in page and "Ailleurs" not in page
        )
        assert Client().get("/quartiers/inconnu").status_code == 404

    def test_fiche_sans_donnee_privee(self):
        p = gerant_verifie()
        a = ListingFactory(gerant=p, address_private="Rue 12 maison bleue", title="Belle chambre")
        medias_prets(a, photos=2, video=True)
        r = Client().get(f"/annonces/{a.slug}")
        page = html(r)
        assert r.status_code == 200 and "Belle chambre" in page and "<video" in page
        assert "Rue 12" not in page and p.user.phone_e164 not in page
        assert "Connecte-toi pour écrire" in page

    def test_fiche_inconnue_ou_masquee(self):
        assert Client().get("/annonces/inconnue").status_code == 404
        a = ListingFactory(status="hidden")
        assert Client().get(f"/annonces/{a.slug}").status_code == 404

    def test_fiche_d_une_annonce_louee(self):
        a = ListingFactory(status="rented")
        medias_prets(a, video=True)
        page = html(Client().get(f"/annonces/{a.slug}"))
        assert "déjà louée" in page and "<video" not in page

    def test_aucun_style_ni_script_en_ligne_sur_les_pages_publiques(self):
        a = ListingFactory()
        for url in ("/", "/annonces", f"/annonces/{a.slug}"):
            page = html(Client().get(url))
            assert " style=" not in page and "<style" not in page
            assert not re.search(r"<script(?![^>]*\bsrc=)", page) and not re.search(
                r"\son[a-z]+=", page
            )

    def test_la_vue_est_comptee_une_fois_par_visiteur(self):
        from apps.core import stats
        from apps.listings.services import vues

        a = ListingFactory()
        c = Client()
        c.get(f"/annonces/{a.slug}")
        c.get(f"/annonces/{a.slug}")
        assert vues.vider_compteurs() == 1 and stats.lire("views", sujet=str(a.pk)) == 1


class TestEspaceLocataire:
    def test_les_pages_du_compte_exigent_la_connexion(self):
        for url in (
            "/compte/favoris",
            "/compte/alertes",
            "/compte/messages",
            "/compte/notifications",
        ):
            r = Client().get(url)
            assert r.status_code == 302 and r["Location"].startswith("/connexion")

    def test_contact_favori_et_signalement_depuis_la_fiche(self):
        a, u = ListingFactory(), ClientFactory()
        c = connecte(u)
        page = html(c.get(f"/annonces/{a.slug}"))
        assert "Envoyer le message" in page and "Ajouter aux favoris" in page
        assert "Ajoutée" in html(c.post(f"/annonces/{a.slug}/favori"))
        assert Favorite.objects.filter(user=u, listing=a).exists()
        assert "Retirée" in html(c.post(f"/annonces/{a.slug}/favori"))
        assert not Favorite.objects.filter(user=u).exists()
        assert "transmis" in html(c.post(f"/annonces/{a.slug}/signaler", {"reason_code": "scam"}))
        assert Report.objects.filter(reporter=u, reason_code="scam").exists()
        r = c.post(f"/annonces/{a.slug}/contacter", {"body": "Bonjour, elle est libre ?"})
        assert r.status_code == 302 and r["Location"].startswith("/compte/messages/")

    def test_le_message_vide_est_refuse_avec_une_explication(self):
        a = ListingFactory()
        r = connecte(ClientFactory()).post(f"/annonces/{a.slug}/contacter", {"body": "   "})
        assert r.status_code == 200 and "vide" in html(r)

    def test_favoris_page(self):
        a, u = ListingFactory(title="Ma favorite"), ClientFactory()
        Favorite.objects.create(user=u, listing=a)
        assert "Ma favorite" in html(connecte(u).get("/compte/favoris"))

    def test_alertes_creation_proposee_depuis_une_recherche_et_suppression(self):
        q, u = DistrictFactory(slug="zongo"), ClientFactory()
        c = connecte(u)
        formulaire = html(c.get("/compte/alertes?district=zongo&rent_max=20000"))
        assert re.search(r'value="20000"', formulaire)
        assert re.search(rf'value="{q.pk}"\s+selected', formulaire)
        r = c.post(
            "/compte/alertes",
            {
                "action": "creer",
                "label": "Zongo pas cher",
                "district_ids": str(q.pk),
                "max_rent": "20000",
            },
        )
        assert "Alerte créée" in html(r) and Alert.objects.filter(user=u).count() == 1
        alerte = Alert.objects.get(user=u)
        assert "Alerte supprimée" in html(
            c.post("/compte/alertes", {"action": "supprimer", "alerte_id": str(alerte.pk)})
        )
        assert not Alert.objects.filter(user=u).exists()

    def test_limite_d_alertes_expliquee(self):
        u = ClientFactory()
        for _ in range(5):
            Alert.objects.create(user=u)
        r = connecte(u).post("/compte/alertes", {"action": "creer", "max_rent": "10000"})
        assert "alertes actives" in html(r)

    def test_un_gerant_n_a_pas_d_alertes(self):
        assert connecte(gerant_verifie().user).get("/compte/alertes").status_code == 404


class TestMessagesWeb:
    def mise_en_place(self):
        p = gerant_verifie()
        a = ListingFactory(gerant=p, address_private="Rue 12 maison bleue")
        locataire = ClientFactory()
        conversation, *_ = chat.ouvrir(
            locataire, a.pk, "Bonjour, la chambre est libre ?", str(uuid.uuid4())
        )
        return p, a, locataire, conversation

    def test_liste_et_conversation_des_deux_cotes_avec_lecture(self):
        p, a, locataire, conversation = self.mise_en_place()
        cote_gerant = connecte(p.user)
        assert "Bonjour, la chambre est libre" in html(cote_gerant.get("/compte/messages"))
        page = html(cote_gerant.get(f"/compte/messages/{conversation.pk}"))
        assert "Bonjour, la chambre est libre" in page and "Rue 12 maison bleue" in page
        conversation.refresh_from_db()
        assert conversation.gerant_read_seq == 1
        page_loc = html(connecte(locataire).get(f"/compte/messages/{conversation.pk}"))
        assert "Rue 12" not in page_loc

    def test_envoi_blocage_deblocage(self):
        p, a, locataire, conversation = self.mise_en_place()
        c = connecte(p.user)
        cle = str(uuid.uuid4())
        r = c.post(
            f"/compte/messages/{conversation.pk}",
            {"action": "envoyer", "body": "Oui, venez demain", "client_msg_id": cle},
        )
        assert "Oui, venez demain" in html(r)
        c.post(
            f"/compte/messages/{conversation.pk}",
            {"action": "envoyer", "body": "Oui, venez demain", "client_msg_id": cle},
        )
        assert conversation.messages.count() == 2  # idempotent
        assert "Tu ne peux plus écrire" not in html(
            connecte(locataire).get(f"/compte/messages/{conversation.pk}")
        )
        c.post(f"/compte/messages/{conversation.pk}", {"action": "bloquer"})
        page_bloque = html(connecte(locataire).get(f"/compte/messages/{conversation.pk}"))
        assert "Tu ne peux plus écrire" in page_bloque
        assert "Débloquer" in html(c.get(f"/compte/messages/{conversation.pk}"))
        c.post(f"/compte/messages/{conversation.pk}", {"action": "debloquer"})
        assert "Tu ne peux plus écrire" not in html(
            connecte(locataire).get(f"/compte/messages/{conversation.pk}")
        )

    def test_rappel_affiche_quand_une_coordonnee_est_masquee(self):
        p, a, locataire, conversation = self.mise_en_place()
        r = connecte(locataire).post(
            f"/compte/messages/{conversation.pk}",
            {
                "action": "envoyer",
                "body": "Appelle le 97 12 34 56",
                "client_msg_id": str(uuid.uuid4()),
            },
        )
        assert "garde les échanges dans Logeo" in html(r)
        assert "97 12 34 56" not in html(
            connecte(p.user).get(f"/compte/messages/{conversation.pk}")
        )

    def test_un_tiers_obtient_404(self):
        *_, conversation = self.mise_en_place()
        assert (
            connecte(ClientFactory()).get(f"/compte/messages/{conversation.pk}").status_code == 404
        )
        assert connecte(ClientFactory()).get("/compte/messages/nimporte").status_code == 404


class TestNotificationsEtReferencement:
    def test_notifications_et_tout_lire(self):
        u = ClientFactory()
        notifications.creer(u.pk, "alert.match", "Nouvelle chambre", "Corps")
        c = connecte(u)
        assert "Nouvelle chambre" in html(c.get("/compte/notifications"))
        assert "Notifications (1)" in html(c.get("/annonces"))
        assert c.post("/compte/notifications").status_code == 302
        assert "Notifications (1)" not in html(c.get("/annonces"))

    def test_robots_et_sitemap(self):
        a = ListingFactory()
        DistrictFactory(slug="albarika")
        robots = html(Client().get("/robots.txt"))
        assert "Disallow: /compte" in robots and "Disallow: /pro" in robots
        sitemap = html(Client().get("/sitemap.xml"))
        assert f"/annonces/{a.slug}" in sitemap and "/quartiers/albarika" in sitemap
        assert Client().get("/sitemap.xml")["Content-Type"].startswith("application/xml")
        assert MOT_DE_PASSE
