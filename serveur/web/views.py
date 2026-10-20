"""Vues du site : adaptateurs minces, aucune règle métier."""

from django.conf import settings
from django.http import Http404
from django.shortcuts import render

from apps.core import legal
from apps.listings import selectors as annonces


def accueil(request):
    return render(
        request,
        "web/accueil.html",
        {"quartiers": annonces.quartiers_avec_chambres()},
    )


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


def boite_dev(request):
    """Développement seulement : derniers courriels et push « envoyés » (rien ne part réellement)."""
    from django.core.cache import cache

    from apps.core.courriel_dev import CLE_BOITE_COURRIELS
    from apps.core.providers.push import CLE_BOITE_PUSH_DEV

    if not (settings.DEBUG and getattr(settings, "DEV_INBOX_ENABLED", False)):
        raise Http404
    return render(
        request,
        "web/boite-dev.html",
        {
            "titre": "Boîte de développement",
            "courriels": cache.get(CLE_BOITE_COURRIELS, []),
            "push": cache.get(CLE_BOITE_PUSH_DEV, []),
        },
    )
