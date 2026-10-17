"""Sondes de vivacité et de disponibilité (CDC §10.7). Adaptateurs minces : la logique est dans `services`."""

from django.http import JsonResponse
from django.views.decorators.http import require_GET
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core import configuration, services

from .serializers import AppConfigOut
from .throttles import LimiteLecture


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


class ConfigurationApp(APIView):
    """GET /v1/app-config : version minimale, maintenance, avis, drapeaux, limites, temps réel, contact de l'équipe."""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [LimiteLecture]

    @extend_schema(
        tags=["Application"],
        operation_id="app_config",
        summary="Configuration distante",
        responses={200: AppConfigOut},
    )
    def get(self, request):
        return Response(
            configuration.configuration_app(), headers={"Cache-Control": "public, max-age=60"}
        )
