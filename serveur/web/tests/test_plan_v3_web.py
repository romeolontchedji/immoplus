"""Site, plan d'actions v3 (19/10/2026) : fiche, contact direct, avis, profil du gérant, barre latérale."""

import uuid

import pytest
from django.test import Client

from apps.accounts.tests.fabriques import ClientFactory
from apps.chat import services as chat
from apps.chat.models import Conversation
from apps.listings.models import Review
from apps.listings.tests.fabriques import ListingFactory, gerant_verifie, medias_prets

from .test_pages_publiques import connecte, html

pytestmark = [pytest.mark.integration, pytest.mark.pg, pytest.mark.django_db]


class TestFiche:
    def test_quartier_galerie_equipements_et_autres_details(self):
        a = ListingFactory(
            kitchen="private", rent_negotiable=True, description_md="Près du marché",
            description_html="<p>Près du marché</p>",
        )  # fmt: skip
        medias_prets(a, photos=3, video=True)
        page = html(Client().get(f"/annonces/{a.slug}"))
        assert page.index("fiche-quartier") < page.index("fiche-titre")  # le quartier d'abord
        assert "data-galerie" in page and "1 / 4" in page
        assert "Cuisine interne" in page and "Prix à débattre" in page
        assert "Près du marché" in page  # les « Autres détails » s'affichent enfin

    def test_contacter_ouvre_la_discussion_sans_message_impose(self):
        a = ListingFactory()
        loc = ClientFactory()
        c = connecte(loc)
        page = html(c.get(f"/annonces/{a.slug}"))
        assert "toujours disponible ?" not in page and 'name="body"' not in page
        r = c.post(f"/annonces/{a.slug}/contacter")
        conversation = Conversation.objects.get(client=loc, listing=a)
        assert r["Location"] == f"/compte/messages/{conversation.pk}"
        assert conversation.last_seq == 0  # aucun message envoyé à la place du locataire
        assert c.post(f"/annonces/{a.slug}/contacter")["Location"] == r["Location"]

    def test_signalement_confirme(self):
        a = ListingFactory()
        page = html(
            connecte(ClientFactory()).post(f"/annonces/{a.slug}/signaler", {"reason_code": "scam"})
        )
        assert "Ton signalement a été pris en compte et sera traité" in page


class TestAvisSurLeSite:
    def test_formulaire_apres_echange_puis_publication(self):
        a = ListingFactory()
        loc = ClientFactory()
        c = connecte(loc)
        assert "Tu pourras donner ton avis après avoir échangé" in html(
            c.get(f"/annonces/{a.slug}")
        )
        conversation = chat.demarrer(loc, a.pk)
        chat.envoyer(loc, conversation.pk, "Bonjour", uuid.uuid4())
        chat.envoyer(a.gerant.user, conversation.pk, "Bonjour, oui", uuid.uuid4())
        assert 'name="rating"' in html(c.get(f"/annonces/{a.slug}"))
        page = html(c.post(f"/annonces/{a.slug}/avis", {"rating": "4", "comment": "Très bien"}))
        assert "Merci, ton avis est publié." in page and "4,0" in page and "1 avis" in page
        assert Review.objects.get(listing=a).rating == 4

    def test_sans_echange_refuse(self):
        a = ListingFactory()
        page = html(connecte(ClientFactory()).post(f"/annonces/{a.slug}/avis", {"rating": "5"}))
        assert "après avoir échangé avec le gérant" in page and not Review.objects.exists()


class TestProfilDuGerant:
    def test_page_publique_sans_numero(self):
        p = gerant_verifie()
        ListingFactory(gerant=p, title="Studio de démonstration")
        r = Client().get(f"/gerants/{p.user_id}")
        page = html(r)
        assert (
            r.status_code == 200 and "Studio de démonstration" in page and "Gérant vérifié" in page
        )
        assert p.user.phone_e164 not in page
        assert Client().get(f"/gerants/{uuid.uuid4()}").status_code == 404

    def test_lien_depuis_la_discussion(self):
        a = ListingFactory()
        loc = ClientFactory()
        conversation = chat.demarrer(loc, a.pk)
        page = html(connecte(loc).get(f"/compte/messages/{conversation.pk}"))
        assert f'href="/gerants/{a.gerant_id}"' in page


class TestBarreLaterale:
    def test_partout_sauf_a_l_accueil(self):
        c = connecte(ClientFactory())
        for chemin in ("/annonces", "/compte", "/compte/profil", "/compte/alertes"):
            assert 'class="espace-barre"' in html(c.get(chemin)), chemin
        assert 'class="espace-barre"' not in html(c.get("/"))
        assert 'class="espace-barre"' not in html(Client().get("/annonces"))  # visiteur
