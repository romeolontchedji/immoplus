"""Application installable (PWA) : manifeste, service worker et page hors ligne."""

import json

from django.http import HttpResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.views.decorators.http import require_GET

COULEUR_THEME = "#1B44D6"  # bleu Immo+
COULEUR_FOND = "#F5F6FA"


def _manifeste() -> dict:
    icone = static("design/icones/icone-512.png")
    return {
        "id": "/",
        "name": "Immo+ · chambres à Parakou",
        "short_name": "Immo+",
        "description": "Trouve une chambre à Parakou : visite en vidéo, zéro paiement avant la visite.",
        "lang": "fr",
        "start_url": "/?source=pwa",
        "scope": "/",
        "display": "standalone",
        "orientation": "portrait",
        "background_color": COULEUR_FOND,
        "theme_color": COULEUR_THEME,
        "categories": ["lifestyle", "business"],
        "icons": [
            {
                "src": static("design/icones/icone-192.png"),
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any",
            },
            {"src": icone, "sizes": "512x512", "type": "image/png", "purpose": "any"},
            # La maison occupe la moitié du carré : l'icône tient dans la zone sûre et sert aussi de masquable.
            {"src": icone, "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
        "shortcuts": [
            {"name": "Chambres", "url": "/annonces?source=pwa"},
            {"name": "Mes alertes", "url": "/compte/alertes?source=pwa"},
            {"name": "Messages", "url": "/compte/messages?source=pwa"},
        ],
    }


@require_GET
def manifeste(request):
    reponse = HttpResponse(
        json.dumps(_manifeste(), ensure_ascii=False), content_type="application/manifest+json"
    )
    reponse["Cache-Control"] = "public, max-age=3600"
    return reponse


@require_GET
def service_worker(request):
    """Servi à la racine pour que son périmètre couvre tout le site ; jamais mis en cache par le navigateur."""
    reponse = render(request, "web/sw.js", content_type="application/javascript")
    reponse["Cache-Control"] = "no-cache"
    return reponse


@require_GET
def hors_ligne(request):
    return render(request, "web/hors-ligne.html")
