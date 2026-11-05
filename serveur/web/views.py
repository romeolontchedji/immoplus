"""Vues du site : adaptateurs minces, aucune règle métier."""

from django.conf import settings
from django.http import Http404
from django.shortcuts import render
from django.templatetags.static import static

from apps.core import configuration, legal
from apps.listings import selectors as annonces

from .views_public import _base_site, _json_ld


def _json_ld_accueil(request) -> str:
    """Données structurées de l'accueil : le site et l'organisation qui l'édite (nom, logo, zone, contact)."""
    base = _base_site(request)
    contact = configuration.contact_equipe()
    return _json_ld(
        [
            {
                "@context": "https://schema.org",
                "@type": "WebSite",
                "name": "Immo+",
                "url": f"{base}/",
                "inLanguage": "fr",
                "description": "Chambres à louer à Parakou et près de l'Université de Parakou, visite en vidéo.",
            },
            {
                "@context": "https://schema.org",
                "@type": "Organization",
                "name": "Immo+",
                "url": f"{base}/",
                "logo": f"{base}{static('design/logo.svg')}",
                "areaServed": {"@type": "City", "name": "Parakou"},
                "contactPoint": {
                    "@type": "ContactPoint",
                    "telephone": contact["phone"],
                    "contactType": "customer service",
                    "availableLanguage": "fr",
                },
            },
        ]
    )


def accueil(request):
    return render(
        request,
        "web/accueil.html",
        {
            "quartiers": annonces.quartiers_avec_chambres(),
            "json_ld": _json_ld_accueil(request),
            "canonique": f"{_base_site(request)}/",
        },
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
