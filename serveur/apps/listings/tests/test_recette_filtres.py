"""Recette des filtres (plan d'actions v2, phase 6) : chaque critère seul et à ses limites, combinaisons, erreurs
lisibles, et parité entre le site (/annonces) et l'API (/v1/listings) : mêmes annonces, dans le même ordre."""

import datetime
import re

import pytest
from django.test import Client
from rest_framework.test import APIClient

from .fabriques import DistrictFactory, ListingFactory

pytestmark = [pytest.mark.api, pytest.mark.pg, pytest.mark.django_db]


@pytest.fixture
def jeu():
    """Six annonces qui se distinguent chacune par au moins un critère."""
    banikanni = DistrictFactory(name="Banikanni", slug="banikanni-test")
    zongo = DistrictFactory(name="Zongo", slug="zongo-test")
    aujourd_hui = datetime.date.today()
    base = {
        "is_fenced": False,
        "has_private_bathroom": False,
        "water_source": "well",
        "electricity_meter": "shared",
    }
    definitions = {
        "a": dict(district=banikanni, room_type="studio", rent_amount=15_000, distance_to_campus_m=300, has_private_bathroom=True, water_source="running"),
        "b": dict(district=banikanni, room_type="single", rent_amount=10_000, distance_to_campus_m=1_200),
        "c": dict(district=zongo, room_type="chambre_salon", rent_amount=25_000, distance_to_campus_m=800, is_fenced=True, electricity_meter="individual"),
        "d": dict(district=zongo, room_type="studio", rent_amount=35_000, distance_to_campus_m=2_500, water_source="borehole"),
        "e": dict(district=banikanni, room_type="entree_coucher", rent_amount=20_000, distance_to_campus_m=500, available_from=aujourd_hui + datetime.timedelta(days=60)),
        "f": dict(district=zongo, room_type="single", rent_amount=12_000, distance_to_campus_m=150, has_private_bathroom=True, is_fenced=True),
    }  # fmt: skip
    annonces = {}
    for cle, champs in definitions.items():
        valeurs = {
            **base,
            "available_from": aujourd_hui,
            **champs,
            "title": f"Chambre {cle.upper()}",
        }
        annonces[cle] = ListingFactory(**valeurs)
    return annonces


def _titres(params: dict) -> set[str]:
    r = APIClient().get("/v1/listings", {**params, "limit": 50})
    assert r.status_code == 200, r.content
    return {c["title"][-1].lower() for c in r.json()["items"]}


@pytest.mark.parametrize(
    "params,attendus",
    [
        ({"district": "banikanni-test"}, "abe"),
        ({"district": "banikanni-test,zongo-test"}, "abcdef"),
        ({"type": "studio"}, "ad"),
        ({"type": "single,studio"}, "abdf"),
        ({"rent_min": 20_000}, "cde"),  # borne incluse
        ({"rent_max": 12_000}, "bf"),  # borne incluse
        ({"rent_min": 12_000, "rent_max": 20_000}, "aef"),
        ({"bathroom": "true"}, "af"),
        ({"bathroom": "false"}, "bcde"),
        ({"water": "running"}, "a"),
        ({"water": "well,borehole"}, "bcdef"),
        ({"meter": "individual"}, "c"),
        ({"fenced": "true"}, "cf"),
        ({"max_distance_m": 500}, "aef"),  # borne incluse
        ({"available_before": datetime.date.today().isoformat()}, "abcdf"),
    ],
)
def test_chaque_filtre_seul(jeu, params, attendus):
    assert _titres(params) == set(attendus)


@pytest.mark.parametrize(
    "params,attendus",
    [
        ({"district": "zongo-test", "type": "single"}, "f"),
        ({"district": "banikanni-test", "rent_max": 15_000}, "ab"),
        ({"type": "studio", "max_distance_m": 1_000}, "a"),
        ({"bathroom": "true", "fenced": "true"}, "f"),
        ({"rent_max": 25_000, "max_distance_m": 800, "fenced": "true"}, "cf"),
        ({"district": "zongo-test", "water": "running"}, ""),  # aucune : vide, pas d'erreur
    ],
)
def test_combinaisons(jeu, params, attendus):
    assert _titres(params) == set(attendus)


@pytest.mark.parametrize(
    "tri,ordre",
    [("rent_asc", "bfaecd"), ("rent_desc", "dceafb"), ("distance", "faecbd")],
)
def test_tris(jeu, tri, ordre):
    r = APIClient().get("/v1/listings", {"sort": tri, "limit": 50})
    assert "".join(c["title"][-1].lower() for c in r.json()["items"]) == ordre


@pytest.mark.parametrize(
    "params,champ",
    [
        ({"rent_min": "abc"}, "rent_min"),
        ({"rent_min": 30_000, "rent_max": 10_000}, "rent_min"),
        ({"bathroom": "peut-être"}, "bathroom"),
        ({"water": "eau-de-pluie"}, "water"),
        ({"type": "chateau"}, "type"),
        ({"sort": "hasard"}, "sort"),
        ({"available_before": "demain"}, "available_before"),
        ({"max_distance_m": -5}, "max_distance_m"),
    ],
)
def test_erreurs_lisibles(jeu, params, champ):
    r = APIClient().get("/v1/listings", params)
    assert r.status_code == 400
    erreur = r.json()["error"]
    assert erreur["code"] == "validation_error" and champ in erreur["fields"] and erreur["message"]


def test_recherche_texte_accents_et_fautes(jeu):
    jeu["a"].title = "Studio lumineux près de l'université"
    jeu["a"].save(update_fields=["title"])
    from apps.listings.services import annonces

    annonces._vecteur_de_recherche(jeu["a"])
    for q in ("universite", "UNIVERSITÉ", "studoi lumineux"):
        titres = [c["title"] for c in APIClient().get("/v1/listings", {"q": q}).json()["items"]]
        assert "Studio lumineux près de l'université" in titres, q


@pytest.mark.parametrize(
    "params",
    [
        {},
        {"district": "banikanni-test"},
        {"type": "single,studio", "sort": "rent_asc"},
        {"rent_max": 25_000, "sort": "distance"},
        {"bathroom": "true", "fenced": "true"},
    ],
)
def test_parite_site_et_api(jeu, params):
    """La même recherche sur le site et l'API renvoie les mêmes annonces, dans le même ordre."""
    api = [
        c["slug"] for c in APIClient().get("/v1/listings", {**params, "limit": 50}).json()["items"]
    ]
    page = Client().get("/annonces", {**params, "limit": 50}).content.decode()
    site = []
    for slug in re.findall(r'href="/annonces/([a-z0-9-]+)"', page):
        if slug not in site:
            site.append(slug)
    assert site == api
