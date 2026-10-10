"""Commande `seed` : idempotente, quartiers de Parakou, données de démonstration réservées au développement."""

from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.core import parametres
from apps.core.models import AppSetting
from apps.listings import selectors
from apps.listings.models import District, Listing

pytestmark = [pytest.mark.integration, pytest.mark.pg, pytest.mark.django_db]


def lancer(*args):
    sortie = StringIO()
    call_command("seed", *args, stdout=sortie)
    return sortie.getvalue()


def test_cree_parametres_et_quartiers_sans_doublon():
    lancer()
    assert District.objects.count() == 12 and AppSetting.objects.count() == len(parametres.DEFAUTS)
    assert "0 créé" in lancer().split("\n")[0]
    assert District.objects.count() == 12
    assert District.objects.filter(slug="banikanni", city="Parakou", is_active=True).exists()


def test_demonstration_reservee_au_developpement(settings):
    settings.DEBUG = False
    with pytest.raises(CommandError):
        lancer("--demo")
    assert not Listing.objects.exists()


def test_demonstration_cree_des_annonces_visibles_dans_le_fil(settings):
    settings.DEBUG = True
    lancer("--demo")
    assert Listing.objects.count() == 6
    lancer("--demo")
    assert Listing.objects.count() == 6
    from apps.listings.services import filtres

    assert len(selectors.fil(filtres.normaliser({}))["items"]) == 6
    assert selectors.fil(filtres.normaliser({"q": "studio"}))["items"]
