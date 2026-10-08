import pytest
from django.test import Client

from apps.accounts.tests.fabriques import MOT_DE_PASSE, ClientFactory
from apps.listings.models import Listing
from apps.listings.tests.fabriques import (
    DistrictFactory,
    ListingFactory,
    gerant_verifie,
    medias_prets,
)

pytestmark = [pytest.mark.integration, pytest.mark.pg, pytest.mark.django_db]


@pytest.fixture
def session_gerant():
    g = gerant_verifie()
    c = Client()
    c.post("/connexion", {"phone": g.user.phone_e164[4:], "password": MOT_DE_PASSE})
    return c, g


def formulaire(quartier, **extra):
    return {
        "action": "enregistrer", "title": "Chambre propre près du campus", "room_type": "single", "district": str(quartier.pk),
        "landmark_text": "Derrière la pharmacie", "address_private": "", "latitude": "9.340000", "longitude": "2.633000",
        "rent_amount": "25000", "deposit_months": "2", "advance_months": "1", "agent_fee_amount": "0",
        "available_from": "2026-11-01", "has_private_bathroom": "on", "is_fenced": "on", "water_source": "running",
        "electricity_meter": "individual", "description_md": "Chambre **calme**", **extra,
    }  # fmt: skip


def test_creation_puis_edition(session_gerant):
    c, g = session_gerant
    q = DistrictFactory()
    r = c.post("/pro/annonces/nouvelle", formulaire(q))
    assert r.status_code == 302
    a = Listing.objects.get()
    assert a.gerant == g and r["Location"] == f"/pro/annonces/{a.pk}"
    r = c.post(f"/pro/annonces/{a.pk}", formulaire(q, rent_amount="30000"))
    assert r.status_code == 200 and "enregistrée" in r.content.decode()
    a.refresh_from_db()
    assert a.rent_amount == 30000
    assert "Mes annonces" in c.get("/pro/annonces").content.decode()


def test_coordonnees_refusees_dans_le_formulaire(session_gerant):
    c, _ = session_gerant
    r = c.post(
        "/pro/annonces/nouvelle",
        formulaire(DistrictFactory(), description_md="Appelle le 97 12 34 56"),
    )
    assert (
        r.status_code == 200 and "interdites" in r.content.decode() and not Listing.objects.exists()
    )


def test_publication_signale_ce_qui_manque(session_gerant):
    c, g = session_gerant
    q = DistrictFactory()
    c.post("/pro/annonces/nouvelle", formulaire(q))
    a = Listing.objects.get()
    r = c.post(f"/pro/annonces/{a.pk}", {"action": "publier"})
    assert "video_prete" in r.content.decode()
    medias_prets(a)
    ListingFactory(gerant=g)
    c.post(f"/pro/annonces/{a.pk}", {"action": "publier"})
    a.refresh_from_db()
    assert a.status == "published"


def test_un_locataire_n_a_pas_d_espace_gerant():
    ClientFactory(phone_e164="+2290197343434")
    c = Client()
    c.post("/connexion", {"phone": "97343434", "password": MOT_DE_PASSE})
    assert c.get("/pro/annonces").status_code == 404


def test_anonyme_redirige_vers_la_connexion():
    assert Client().get("/pro/annonces")["Location"].startswith("/connexion")


def test_l_annonce_d_un_autre_gerant_est_introuvable(session_gerant):
    c, _ = session_gerant
    autre = ListingFactory()
    assert c.get(f"/pro/annonces/{autre.pk}").status_code == 404
    assert c.post(f"/pro/annonces/{autre.pk}", {"action": "masquer"}).status_code == 404
