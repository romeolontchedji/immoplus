"""Plan d'actions v3 (19/10/2026) : équipements, loyer à débattre, quartiers voisins, avis, profil public du gérant."""

import uuid

import pytest
from django.test import Client
from rest_framework.test import APIClient

from apps.accounts.services import appareils, jetons
from apps.accounts.tests.fabriques import ClientFactory
from apps.chat import services as chat
from apps.core.errors import ErreurMetier
from apps.notifications.models import Notification

from ..models import Listing, Review
from ..services import annonces, avis, fil
from .fabriques import DistrictFactory, ListingFactory, donnees_annonce, gerant_verifie

pytestmark = [pytest.mark.integration, pytest.mark.pg, pytest.mark.django_db]


def api_de(utilisateur) -> APIClient:
    d, _ = appareils.ouvrir(
        utilisateur, installation_id=f"inst-{utilisateur.pk}", platform="android"
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {jetons.emettre_acces(utilisateur, d)}")
    return c


def echanger(locataire, annonce, *, reponse=True):
    """Le locataire écrit au gérant ; le gérant répond (ou pas)."""
    conversation, *_ = chat.ouvrir(locataire, annonce.pk, "Bonjour, toujours libre ?", uuid.uuid4())
    if reponse:
        chat.envoyer(annonce.gerant.user, conversation.pk, "Oui, passe la voir.", uuid.uuid4())
    return conversation


class TestEquipementsEtPrix:
    def test_cuisine_et_loyer_a_debattre_a_la_creation(self):
        p = gerant_verifie()
        q = DistrictFactory()
        a = annonces.creer_brouillon(
            p,
            {**donnees_annonce(q), "district": q.pk, "kitchen": "private", "rent_negotiable": True,
             "water_source": "sub_meter", "electricity_meter": "sub_meter"},
        )  # fmt: skip
        a.refresh_from_db()
        assert (a.kitchen, a.rent_negotiable, a.water_source) == ("private", True, "sub_meter")

    def test_valeurs_inconnues_refusees(self):
        p = gerant_verifie()
        a = ListingFactory(gerant=p)
        for champ, valeur in (("kitchen", "garage"), ("rent_negotiable", "oui")):
            with pytest.raises(ErreurMetier):
                annonces.modifier(p, a.pk, {champ: valeur})

    def test_la_fiche_donne_les_libelles_et_le_prix_a_debattre(self):
        a = ListingFactory(kitchen="shared", rent_negotiable=True, water_source="borehole")
        f = APIClient().get(f"/v1/listings/{a.slug}").json()
        assert f["kitchen_label"] == "Cuisine commune" and f["water_label"] == "Forage"
        assert f["rent_negotiable"] is True and f["gerant"]["id"] == str(a.gerant_id)
        assert f["reviews"] == {"average": None, "count": 0}

    def test_filtre_cuisine(self):
        ListingFactory(kitchen="private", title="Avec cuisine")
        ListingFactory(kitchen="none", title="Sans cuisine")
        titres = [
            c["title"] for c in APIClient().get("/v1/listings?kitchen=private").json()["items"]
        ]
        assert titres == ["Avec cuisine"]

    def test_la_recherche_lit_les_equipements_et_les_autres_details(self):
        p = gerant_verifie()
        q = DistrictFactory()
        a = annonces.creer_brouillon(
            p, {**donnees_annonce(q), "district": q.pk, "water_source": "borehole",
                "description_md": "Proche du marché Arzèkè"},
        )  # fmt: skip
        Listing.objects.filter(pk=a.pk).update(status="published")
        for mot in ("forage", "arzeke"):
            items = APIClient().get(f"/v1/listings?q={mot}").json()["items"]
            assert [i["id"] for i in items] == [str(a.pk)], mot


class TestQuartiersVoisins:
    def test_quartier_vide_propose_les_quartiers_proches_a_part(self):
        demande = DistrictFactory(name="Zongo", slug="zongo", latitude=9.340, longitude=2.630)
        proche = DistrictFactory(name="Madina", slug="madina", latitude=9.350, longitude=2.635)
        loin = DistrictFactory(name="Lointain", slug="loin", latitude=9.600, longitude=2.900)
        ListingFactory(district=proche, room_type="studio", title="Studio proche")
        ListingFactory(district=loin, room_type="studio", title="Studio loin")
        r = fil.rechercher({"district": "zongo", "type": "studio"})
        assert r["items"] == []
        assert [d["name"] for d in r["voisins"]["districts"]] == ["Madina"]
        assert [i["title"] for i in r["voisins"]["items"]] == ["Studio proche"]
        assert demande.slug == "zongo"

    def test_pas_de_voisins_si_le_quartier_suffit(self):
        q = DistrictFactory(slug="banikanni")
        DistrictFactory(slug="voisin")
        ListingFactory.create_batch(3, district=q)
        assert fil.rechercher({"district": "banikanni"})["voisins"] is None

    def test_l_api_renvoie_les_voisins(self):
        DistrictFactory(slug="vide", latitude=9.340, longitude=2.630)
        ListingFactory(district=DistrictFactory(latitude=9.345, longitude=2.632))
        assert APIClient().get("/v1/listings?district=vide").json()["voisins"]["items"]


class TestAvis:
    def test_il_faut_avoir_echange_avec_le_gerant(self):
        a = ListingFactory()
        loc = ClientFactory()
        with pytest.raises(ErreurMetier) as e:
            avis.donner(loc, a.pk, 5)
        assert e.value.code == "review_not_allowed"
        echanger(loc, a, reponse=False)  # pas encore de réponse du gérant
        assert not avis.peut_donner(loc, a.pk)

    def test_avis_donne_modifie_puis_resume(self, django_capture_on_commit_callbacks):
        a = ListingFactory()
        loc = ClientFactory(full_name="Awa Bio")
        echanger(loc, a)
        with django_capture_on_commit_callbacks(execute=True):
            avis.donner(loc, a.pk, 4, "Chambre propre, gérant sérieux.")
        avis.donner(loc, a.pk, 5, "Encore mieux après visite.")  # un seul avis : il est modifié
        assert Review.objects.filter(listing=a).count() == 1
        reponse = APIClient().get(f"/v1/listings/{a.slug}/reviews").json()
        assert reponse["summary"] == {"average": 5.0, "count": 1}
        assert reponse["items"][0]["author_name"] == "Awa B."
        assert Notification.objects.filter(user=a.gerant.user, kind="listing.review").count() == 1

    def test_coordonnees_refusees_et_note_bornee(self):
        a = ListingFactory()
        loc = ClientFactory()
        echanger(loc, a)
        with pytest.raises(ErreurMetier):
            avis.donner(loc, a.pk, 5, "Appelle-moi au 97 12 34 56")
        with pytest.raises(ErreurMetier):
            avis.donner(loc, a.pk, 6)

    def test_api_donner_et_retirer(self):
        a = ListingFactory()
        loc = ClientFactory()
        echanger(loc, a)
        c = api_de(loc)
        assert c.get(f"/v1/listings/{a.slug}/reviews").json()["can_review"] is True
        assert (
            c.put(f"/v1/listings/{a.slug}/my-review", {"rating": 3}, format="json").status_code
            == 204
        )
        assert c.get(f"/v1/listings/{a.slug}/reviews").json()["my_review"]["rating"] == 3
        assert c.delete(f"/v1/listings/{a.slug}/my-review").status_code == 204
        assert not Review.objects.exists()

    def test_avis_masque_par_la_moderation_disparait_du_public(self):
        a = ListingFactory()
        loc = ClientFactory()
        echanger(loc, a)
        r = avis.donner(loc, a.pk, 1, "Pas terrible")
        avis.masquer(r.pk, acteur=None, raison="Propos déplacés")
        assert APIClient().get(f"/v1/listings/{a.slug}/reviews").json()["summary"]["count"] == 0


class TestProfilPublicDuGerant:
    def test_profil_sans_numero_avec_chambres_et_avis(self):
        p = gerant_verifie()
        a = ListingFactory(gerant=p, title="Studio du gérant")
        ListingFactory(gerant=p, status="draft", title="Brouillon caché")
        r = APIClient().get(f"/v1/gerants/{p.user_id}")
        assert r.status_code == 200
        profil = r.json()
        assert profil["verified"] is True and [c["title"] for c in profil["listings"]] == [a.title]
        assert p.user.phone_e164 not in r.content.decode()

    def test_gerant_inconnu(self):
        assert APIClient().get(f"/v1/gerants/{uuid.uuid4()}").status_code == 404
        assert APIClient().get("/v1/gerants/pas-un-uuid").status_code == 404


class TestFiltresTempsReel:
    def test_fragment_des_resultats_seul(self):
        ListingFactory(title="Chambre témoin")
        r = Client().get("/annonces", HTTP_X_FRAGMENT="resultats")
        page = r.content.decode()
        assert "Chambre témoin" in page and "<html" not in page and 'id="filtres"' not in page

    def test_page_complete_avec_listes_deroulantes(self):
        page = Client().get("/annonces").content.decode()
        for nom in ("district", "type", "rent_max", "water", "meter", "kitchen", "sort"):
            assert f'<select class="champ__saisie" name="{nom}"' in page, nom
        assert 'type="radio" name="type"' not in page  # plus de longue liste de boutons radio
