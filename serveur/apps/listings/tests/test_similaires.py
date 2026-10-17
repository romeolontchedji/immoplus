"""Chambres similaires (plan v2, S3) : score quartier, type, loyer, distance ; repli sur les plus récentes."""

import pytest
from rest_framework.test import APIClient

from apps.listings import selectors

from .fabriques import DistrictFactory, ListingFactory

pytestmark = [pytest.mark.api, pytest.mark.pg, pytest.mark.django_db]


def test_les_plus_proches_d_abord():
    quartier = DistrictFactory(latitude=9.34, longitude=2.63)
    loin = DistrictFactory(latitude=9.60, longitude=2.90)  # environ 40 km
    ref = ListingFactory(district=quartier, room_type="studio", rent_amount=30_000)
    jumelle = ListingFactory(
        district=quartier, room_type="studio", rent_amount=32_000, title="Jumelle"
    )
    meme_quartier = ListingFactory(
        district=quartier, room_type="single", rent_amount=90_000, title="Même quartier"
    )
    sans_rapport = ListingFactory(
        district=loin, room_type="villa", rent_amount=300_000, title="Sans rapport"
    )
    titres = [c["title"] for c in selectors.similaires(ref.pk)]
    assert titres[0] == "Jumelle" and titres.index("Même quartier") < titres.index("Sans rapport")
    assert ref.title not in titres and len(titres) == 3
    assert {jumelle.pk, meme_quartier.pk, sans_rapport.pk} == {
        c["id"] for c in selectors.similaires(ref.pk)
    }


def test_repli_sur_les_plus_recentes_et_seulement_en_ligne():
    ref = ListingFactory()
    ListingFactory(status="draft", title="Brouillon")
    autre = ListingFactory(
        district=DistrictFactory(latitude=11.0, longitude=3.5),
        room_type="villa",
        rent_amount=900_000,
    )
    titres = [c["title"] for c in selectors.similaires(ref.pk)]
    assert "Brouillon" not in titres and autre.title in titres


def test_api_similaires():
    ref = ListingFactory()
    ListingFactory(district=ref.district, room_type=ref.room_type)
    r = APIClient().get(f"/v1/listings/{ref.slug}/similar")
    assert r.status_code == 200 and len(r.json()) == 1 and "room_type_label" in r.json()[0]
    assert APIClient().get("/v1/listings/inconnue/similar").status_code == 404
