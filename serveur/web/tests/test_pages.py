import re

import pytest
from django.http import Http404
from django.test import Client, RequestFactory

from web import views

pytestmark = pytest.mark.integration


@pytest.mark.pg
@pytest.mark.django_db
def test_accueil():
    reponse = Client().get("/")
    assert reponse.status_code == 200
    html = reponse.content.decode()
    assert '<html lang="fr" data-theme="light">' in html
    assert "Trouve ta chambre à Parakou, sans courir partout." in html
    assert 'class="accueil-hero"' in html and "Comment ça marche" in html
    assert re.search(r'href="/static/css/dist/immoplus\.[0-9a-f]{10}\.css"', html)


@pytest.mark.pg
@pytest.mark.django_db  # le pied de page commun lit le contact de l'équipe (paramètre TEAM_PHONE)
def test_styleguide_en_local():
    reponse = Client().get("/styleguide")
    assert reponse.status_code == 200
    assert "Styleguide" in reponse.content.decode()


def test_styleguide_introuvable_si_desactive(settings):
    settings.STYLEGUIDE_ENABLED = False
    with pytest.raises(Http404):
        views.styleguide(RequestFactory().get("/styleguide"))


@pytest.mark.pg
@pytest.mark.django_db
def test_aucun_style_ni_script_en_ligne():
    for url in ("/", "/styleguide"):
        html = Client().get(url).content.decode()
        assert " style=" not in html
        assert "<style" not in html
        # Seul script sans src admis : les données structurées (JSON-LD), jamais exécutées par le navigateur.
        assert not re.search(r"<script(?![^>]*\bsrc=)(?![^>]*application/ld\+json)", html)
        assert not re.search(r"\son[a-z]+=", html)


def test_aucun_chemin_d_administration_sur_le_site_public():
    for chemin in ("/admin/", "/admin/login/", "/pilotage/"):
        assert Client().get(chemin).status_code == 404


@pytest.mark.pg
@pytest.mark.django_db
def test_accueil_annonce_le_prix_forfaitaire_des_alertes_quand_elles_sont_payantes():
    from apps.core import parametres

    page = Client().get("/").content.decode()
    assert "créer des alertes ne coûte rien" in page  # alertes gratuites par défaut
    parametres.definir("PAID_ALERTS_ENABLED", True)
    parametres.definir("ALERT_PRICE", 1500)
    page = Client().get("/").content.decode()
    assert "prix forfaitaire de 1 500&nbsp;F" in page
