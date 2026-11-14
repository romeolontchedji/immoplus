"""Loyer pré-payé : nombre de mois à régler avant d'entrer dans la chambre (0 = aucun)."""

import pytest
from django.test import Client

from apps.accounts.tests.fabriques import MOT_DE_PASSE
from apps.core.errors import ErreurMetier

from ..models import Listing
from ..services import annonces
from .fabriques import DistrictFactory, donnees_annonce, gerant_verifie, medias_prets

pytestmark = [pytest.mark.integration, pytest.mark.pg, pytest.mark.django_db]


def _brouillon(**extra):
    p, q = gerant_verifie(), DistrictFactory()
    return p, annonces.creer_brouillon(p, {**donnees_annonce(q), "district": q.pk, **extra})


def test_sans_precision_le_pre_paiement_vaut_zero():
    _, a = _brouillon()
    assert a.prepaid_months == 0


def test_un_nombre_de_mois_se_enregistre_et_se_modifie():
    p, a = _brouillon(prepaid_months=2)
    assert Listing.objects.get(pk=a.pk).prepaid_months == 2
    annonces.modifier(p, a.pk, {"prepaid_months": 0})
    assert Listing.objects.get(pk=a.pk).prepaid_months == 0


@pytest.mark.parametrize("valeur", [-1, 13, "2", 1.5])
def test_valeurs_refusees(valeur):
    with pytest.raises(ErreurMetier) as e:
        _brouillon(prepaid_months=valeur)
    assert "prepaid_months" in e.value.champs


def test_le_gerant_le_renseigne_dans_l_editeur_et_la_fiche_l_affiche():
    p = gerant_verifie()
    c = Client()
    c.post("/connexion", {"username": p.user.username, "password": MOT_DE_PASSE})
    q = DistrictFactory()
    page = c.get("/pro/annonces/nouvelle").content.decode()
    assert "Pré-payé (mois)" in page
    donnees = {
        "action": "enregistrer", "title": "Chambre propre près du campus", "room_type": "single",
        "district": str(q.pk), "landmark_text": "Derrière la pharmacie", "rent_amount": "25000",
        "advance_months": "1", "prepaid_months": "3", "agent_fee_amount": "0", "available_from": "2026-11-01",
        "has_private_bathroom": "on", "is_fenced": "on", "water_sources": "running",
        "electricity_meter": "individual", "kitchen": "private", "description_md": "Chambre calme",
    }  # fmt: skip
    r = c.post("/pro/annonces/nouvelle", donnees)
    assert r.status_code == 302, r.content.decode()[:1500]
    annonce = Listing.objects.get(gerant=p)
    assert annonce.prepaid_months == 3
    Listing.objects.filter(pk=annonce.pk).update(status="published")
    medias_prets(annonce)
    fiche = Client().get(f"/annonces/{annonce.slug}").content.decode()
    assert "Pré-payé" in fiche and "3 mois avant d'entrer" in fiche


def test_les_frais_de_visite_valent_zero_par_defaut_et_se_modifient():
    p, a = _brouillon()
    assert a.visit_fee_amount == 0
    annonces.modifier(p, a.pk, {"visit_fee_amount": 1500})
    assert Listing.objects.get(pk=a.pk).visit_fee_amount == 1500


@pytest.mark.parametrize("valeur", [-1, "500", 1.5, 10_000_001])
def test_frais_de_visite_refuses(valeur):
    with pytest.raises(ErreurMetier) as e:
        _brouillon(visit_fee_amount=valeur)
    assert "visit_fee_amount" in e.value.champs


def test_la_fiche_affiche_les_frais_de_visite():
    p, a = _brouillon(visit_fee_amount=2000)
    Listing.objects.filter(pk=a.pk).update(status="published")
    medias_prets(a)
    fiche = Client().get(f"/annonces/{a.slug}").content.decode()
    assert "Frais de visite" in fiche and "2 000" in fiche.replace(" ", " ").replace("\xa0", " ")
