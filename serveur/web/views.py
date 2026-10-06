"""Vues du site : adaptateurs minces, aucune règle métier."""

from django.conf import settings
from django.http import Http404
from django.shortcuts import render


def accueil(request):
    return render(request, "web/accueil.html")


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
