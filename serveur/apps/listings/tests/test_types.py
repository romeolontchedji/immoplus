"""Types de logement (décision V1) : propositions des gérants, validation, rattachement, filtres et alertes."""

from contextlib import contextmanager

import pytest
from django.db import connection
from django.test import Client

from apps.accounts.tests.fabriques import MOT_DE_PASSE, ClientFactory
from apps.audit.models import AuditLog
from apps.listings.models import Alert, Listing, RoomType
from apps.listings.services import types

from .fabriques import DistrictFactory, ListingFactory, donnees_annonce, gerant_verifie
from .test_annonces_pro import client_de

pytestmark = [pytest.mark.api, pytest.mark.pg, pytest.mark.django_db]


@pytest.fixture
def gerant():
    return gerant_verifie()


@pytest.fixture
def pro(gerant):
    return client_de(gerant.user)


@contextmanager
def en_tant_que_app():
    with connection.cursor() as c:
        c.execute("SET LOCAL ROLE app")
    try:
        yield
    finally:
        with connection.cursor() as c:
            c.execute("RESET ROLE")


class TestReferentiel:
    def test_les_officiels_vont_de_la_chambre_a_la_villa(self):
        attendus = {
            "single",
            "entree_coucher",
            "chambre_salon",
            "studio",
            "colocation",
            "appartement_meuble",
            "villa",
        }
        assert set(types.slugs_valides()) >= attendus

    def test_appartement_meuble_est_deja_officiel(self, pro):
        r = pro.post("/v1/pro/room-types", {"label": "appartement meublé"}, format="json")
        assert r.status_code == 200 and r.json()["status"] == "approved"

    def test_liste_publique_les_plus_courants_d_abord(self):
        ListingFactory.create_batch(2, room_type="studio")
        r = Client().get("/v1/room-types")
        assert r.status_code == 200
        assert r.json()[0] == {"slug": "studio", "label": "Studio", "count": 2}

    def test_proposition_absente_de_la_liste_publique(self, gerant):
        types.proposer(gerant, "Chambre avec mezzanine")
        slugs = [t["slug"] for t in Client().get("/v1/room-types").json()]
        assert "chambre_avec_mezzanine" not in slugs


class TestProposition:
    def test_creer_puis_utiliser_tout_de_suite(self, pro):
        r = pro.post("/v1/pro/room-types", {"label": "chambre avec mezzanine"}, format="json")
        assert r.status_code == 201
        assert r.json() == {
            "slug": "chambre_avec_mezzanine",
            "label": "Chambre avec mezzanine",
            "status": "pending",
        }
        assert "chambre_avec_mezzanine" in [t["slug"] for t in pro.get("/v1/pro/room-types").json()]
        a = pro.post(
            "/v1/pro/listings",
            donnees_annonce(DistrictFactory(), room_type="chambre_avec_mezzanine"),
            format="json",
        )
        assert a.status_code == 201, a.content
        assert a.json()["room_type_label"] == "Chambre avec mezzanine"
        assert AuditLog.objects.filter(action="room_type.propose").exists()

    @pytest.mark.parametrize("saisie", ["Entrée coucher", "ENTREE-COUCHER", "entrée  couchér"])
    def test_equivalent_existant_reutilise(self, pro, saisie):
        avant = RoomType.objects.count()
        r = pro.post("/v1/pro/room-types", {"label": saisie}, format="json")
        assert r.status_code == 200 and r.json()["slug"] == "entree_coucher"
        assert RoomType.objects.count() == avant

    def test_la_proposition_d_un_autre_gerant_est_partagee(self, gerant, pro):
        autre = gerant_verifie()
        t = types.proposer(autre, "Chambre à deux lits")
        r = pro.post("/v1/pro/room-types", {"label": "chambre a deux lits"}, format="json")
        assert r.json()["slug"] == t.slug
        a = pro.post(
            "/v1/pro/listings", donnees_annonce(DistrictFactory(), room_type=t.slug), format="json"
        )
        assert a.status_code == 201

    def test_limite_de_propositions_en_attente(self, pro):
        for nom in ("Type un", "Type deux", "Type trois"):
            assert pro.post("/v1/pro/room-types", {"label": nom}, format="json").status_code == 201
        r = pro.post("/v1/pro/room-types", {"label": "Type quatre"}, format="json")
        assert r.status_code == 400

    @pytest.mark.parametrize("saisie", ["ab", "x" * 41, "Appelle 97 00 00 00"])
    def test_libelle_refuse(self, pro, saisie):
        assert pro.post("/v1/pro/room-types", {"label": saisie}, format="json").status_code == 400

    def test_type_inconnu_refuse_pour_une_annonce(self, pro):
        r = pro.post(
            "/v1/pro/listings",
            donnees_annonce(DistrictFactory(), room_type="chateau"),
            format="json",
        )
        assert r.status_code == 400 and "room_type" in r.json()["error"]["fields"]

    def test_un_locataire_ne_propose_pas(self):
        c = client_de(ClientFactory())
        assert c.post("/v1/pro/room-types", {"label": "Bungalow"}, format="json").status_code == 403


class TestFiltresEtAlertes:
    def test_filtre_sur_un_type_en_attente_refuse(self, gerant):
        t = types.proposer(gerant, "Bungalow")
        assert Client().get(f"/v1/listings?type={t.slug}").status_code == 400

    def test_filtre_sur_un_type_valide(self, gerant):
        t = types.valider(types.proposer(gerant, "Bungalow"), acteur=None)
        ListingFactory(room_type=t.slug)
        r = Client().get(f"/v1/listings?type={t.slug}")
        assert r.status_code == 200 and len(r.json()["items"]) == 1
        assert r.json()["items"][0]["room_type_label"] == "Bungalow"

    def test_alerte_sur_un_type_en_attente_refusee(self, gerant):
        t = types.proposer(gerant, "Bungalow")
        c = client_de(ClientFactory())
        r = c.post("/v1/me/alerts", {"room_types": [t.slug]}, format="json")
        assert r.status_code == 400


class TestModeration:
    def test_rattacher_reecrit_annonces_et_alertes(self, gerant):
        t = types.proposer(gerant, "Entre couche")  # faute de frappe, sans équivalent exact
        a = ListingFactory(room_type=t.slug)
        types.valider(t, acteur=None)
        alerte = Alert.objects.create(
            user=ClientFactory(), room_types=[t.slug, "entree_coucher", "studio"]
        )
        cible = RoomType.objects.get(slug="entree_coucher")
        assert types.rattacher(t, cible, acteur=None) == 1
        assert Listing.objects.get(pk=a.pk).room_type == "entree_coucher"
        alerte.refresh_from_db()
        assert sorted(alerte.room_types) == ["entree_coucher", "studio"]
        assert not RoomType.objects.filter(pk=t.pk).exists()

    def test_un_officiel_ne_se_rattache_pas(self):
        from apps.core.errors import ErreurMetier

        with pytest.raises(ErreurMetier):
            types.rattacher(
                RoomType.objects.get(slug="studio"),
                RoomType.objects.get(slug="single"),
                acteur=None,
            )


class TestRoleApp:
    def test_le_role_app_ne_peut_que_proposer(self, gerant):
        with en_tant_que_app():
            t = RoomType.objects.create(
                slug="bungalow", label="Bungalow", status="approved", sort_order=1
            )
        t.refresh_from_db()
        assert (t.status, t.sort_order) == ("pending", 100)  # forcé par le déclencheur

    def test_le_role_app_ne_peut_pas_valider(self, gerant):
        from django.db.utils import ProgrammingError

        t = types.proposer(gerant, "Bungalow")
        with pytest.raises(ProgrammingError), en_tant_que_app():
            RoomType.objects.filter(pk=t.pk).update(status="approved")


@pytest.mark.integration
def test_site_proposer_un_type_depuis_l_editeur():
    g = gerant_verifie()
    c = Client()
    c.post("/connexion", {"phone": g.user.phone_e164[4:], "password": MOT_DE_PASSE})
    q = DistrictFactory()
    page = c.get("/pro/annonces/nouvelle").content.decode()
    assert "Ou un autre type" in page and 'value="studio"' in page
    r = c.post(
        "/pro/annonces/nouvelle",
        {
            "action": "enregistrer", "title": "Appartement près du campus", "room_type": "",
            "nouveau_type": "Chambre avec mezzanine", "district": str(q.pk), "landmark_text": "Derrière la pharmacie",
            "rent_amount": "45000", "deposit_months": "2", "advance_months": "1", "agent_fee_amount": "0",
            "available_from": "2026-11-01", "water_source": "running", "electricity_meter": "individual",
        },
    )  # fmt: skip
    assert r.status_code == 302, r.content.decode()[:2000]
    assert Listing.objects.get(gerant=g).room_type == "chambre_avec_mezzanine"


@pytest.mark.integration
def test_site_les_onglets_de_l_accueil_viennent_de_la_base():
    ListingFactory.create_batch(3, room_type="single")
    page = Client().get("/").content.decode()
    assert 'data-type="single"' in page
