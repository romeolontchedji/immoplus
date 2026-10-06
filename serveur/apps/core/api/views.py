"""Sondes de vivacité et de disponibilité (CDC §10.7). Adaptateurs minces : la logique est dans `services`."""

from django.http import JsonResponse
from django.views.decorators.http import require_GET

from apps.core import services


@require_GET
def healthz(request):
    return JsonResponse({"status": "ok"}, headers={"Cache-Control": "no-store"})


@require_GET
def readyz(request):
    controles = services.verifier_disponibilite()
    pret = all(controles.values())
    return JsonResponse(
        {"status": "ok" if pret else "indisponible", "controles": controles},
        status=200 if pret else 503,
        headers={"Cache-Control": "no-store"},
    )
