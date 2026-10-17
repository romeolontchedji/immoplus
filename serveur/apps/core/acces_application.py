"""Mise à jour obligatoire (426) et maintenance (503) pour l'API et le site public (CDC §10, `GET /v1/app-config`).

L'application lit `app-config` au démarrage ; ces réponses couvrent les requêtes faites entre deux lectures.
L'administration n'est jamais concernée (elle n'utilise pas cet intergiciel) : on peut couper le site et travailler.
"""

from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string

from . import parametres
from .errors import corps_erreur

# Toujours joignables : configuration de l'app, textes légaux, webhooks de paiement, santé, fichiers statiques.
TOUJOURS_OUVERTS = (
    "/v1/app-config",
    "/v1/legal/",
    "/v1/webhooks/",
    "/healthz",
    "/readyz",
    "/static/",
    "/media/",
)
MESSAGE_MAINTENANCE = "Logeo est en maintenance pour quelques minutes. Réessaie bientôt."


def _composantes(version: str) -> list[int] | None:
    try:
        morceaux = [int(x) for x in version.strip().split(".")]
    except ValueError:
        return None
    return morceaux if morceaux and all(n >= 0 for n in morceaux) else None


def est_inferieure(installee: str, minimale: str) -> bool:
    """Même règle que l'application (mobile/src/lib/version.ts) : une version illisible n'est jamais trop ancienne."""
    a, b = _composantes(installee), _composantes(minimale)
    if a is None or b is None:
        return False
    longueur = max(len(a), len(b))
    return a + [0] * (longueur - len(a)) < b + [0] * (longueur - len(b))


class AccesApplicationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        chemin = request.path
        if chemin.startswith(TOUJOURS_OUVERTS):
            return self.get_response(request)
        api = chemin.startswith("/v1/")
        try:
            maintenance = bool(parametres.lire("MAINTENANCE_ENABLED"))
            minimale = str(parametres.lire("MIN_SUPPORTED_VERSION"))
        except Exception:  # noqa: BLE001 - paramètres illisibles (base indisponible) : on laisse passer
            return self.get_response(request)
        if maintenance:
            message = parametres.lire("MAINTENANCE_MESSAGE") or MESSAGE_MAINTENANCE
            if api:
                reponse = JsonResponse(corps_erreur("maintenance", message), status=503)
            else:
                reponse = HttpResponse(
                    render_to_string("web/maintenance.html", {"message": message}, request=request),
                    status=503,
                )
            reponse["Retry-After"] = "300"
            return reponse
        version = request.headers.get("X-App-Version")
        if api and version and est_inferieure(version, minimale):
            return JsonResponse(
                corps_erreur(
                    "upgrade_required",
                    "Cette version de Logeo n'est plus prise en charge. Mets l'application à jour.",
                ),
                status=426,
            )
        return self.get_response(request)
