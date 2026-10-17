"""Vues du site : adaptateurs minces, aucune règle métier."""

from django.conf import settings
from django.http import Http404
from django.shortcuts import render

from apps.core import legal
from apps.listings.services import types


def accueil(request):
    # Onglets de la recherche : les 3 types validés les plus courants (décision V1).
    return render(request, "web/accueil.html", {"types_accueil": types.publics()[:3]})


def conditions(request):
    return render(request, "web/public/legal.html", {"doc": legal.document("conditions")})


def confidentialite(request):
    return render(request, "web/public/legal.html", {"doc": legal.document("confidentialite")})


def styleguide(request):
    """Revue visuelle de tous les composants (activée en `local` et en test seulement)."""
    if not settings.STYLEGUIDE_ENABLED:
        raise Http404
    contexte = {
        "echelles": [
            ("marque", [50, 100, 200, 300, 400, 500, 600, 700, 800, 900]),
            ("accent", [50, 100, 200, 300, 400, 500, 600, 700, 800, 900]),
            ("sable", [0, 25, 50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950]),
        ],
        "semantiques": ["succes", "avertissement", "danger", "information"],
    }
    return render(request, "web/styleguide.html", contexte)
