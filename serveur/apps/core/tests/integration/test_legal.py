"""Textes légaux : même source pour le site (/conditions, /confidentialite) et l'API (/v1/legal/{slug})."""

import pytest
from django.test import Client

from apps.core import parametres

pytestmark = [pytest.mark.integration, pytest.mark.pg, pytest.mark.django_db]


@pytest.mark.parametrize("slug", ["conditions", "confidentialite"])
def test_api_rend_un_document_structure(slug):
    r = Client().get(f"/v1/legal/{slug}")
    assert r.status_code == 200, r.content
    doc = r.json()
    assert doc["slug"] == slug and doc["title"] and doc["summary"]
    assert doc["provisional"] is True  # identité fictive tant que LEGAL_PROVISIONAL est vrai
    assert len(doc["sections"]) >= 8
    for section in doc["sections"]:
        assert section["title"] and section["blocks"] and section["html"]
    assert "[[" not in r.content.decode()  # aucun gabarit laissé non rempli


def test_puces_avec_libelle_en_gras():
    doc = Client().get("/v1/legal/confidentialite").json()
    donnees = next(s for s in doc["sections"] if s["title"].startswith("2."))
    assert donnees["blocks"][0] == {
        "type": "li",
        "label": "Compte",
        "text": donnees["blocks"][0]["text"],
    }


def test_identite_de_l_editeur_vient_des_parametres():
    parametres.definir("LEGAL_COMPANY", "ÉDITEUR TEST SARL")
    parametres.definir("LEGAL_PROVISIONAL", False)
    doc = Client().get("/v1/legal/confidentialite").json()
    assert doc["editor"]["company"] == "ÉDITEUR TEST SARL" and doc["provisional"] is False
    assert "ÉDITEUR TEST SARL" in doc["sections"][0]["blocks"][0]["text"]


def test_document_inconnu_404():
    assert Client().get("/v1/legal/inconnu").status_code == 404


@pytest.mark.parametrize(
    ("url", "titre"),
    [
        ("/conditions", "Conditions d&#x27;utilisation"),
        ("/confidentialite", "Politique de confidentialité"),
    ],
)
def test_pages_web(url, titre):
    r = Client().get(url)
    assert r.status_code == 200
    html = r.content.decode()
    assert titre in html and 'class="legal-hero"' in html and "Version provisoire" in html
    assert "style=" not in html.split('class="legal-hero"')[1]  # CSP : aucun style en ligne
