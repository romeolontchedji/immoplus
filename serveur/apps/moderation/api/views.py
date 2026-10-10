"""API des signalements (CDC §10.5)."""

from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.api.authentication import AuthJwt, EstClient, EstClientOuGerant
from apps.core.api.throttles import LimiteCompte

from .. import services
from . import serializers as s


class Signaler(APIView):
    authentication_classes = [AuthJwt]
    permission_classes = [EstClientOuGerant]
    throttle_classes = [LimiteCompte]

    @extend_schema(
        tags=["Signalements"], summary="Signaler une annonce, un message, une conversation ou un utilisateur",
        request=s.SignalementIn, responses={200: s.SignalementOut, 201: s.SignalementOut},
    )  # fmt: skip
    def post(self, request):
        d = s.SignalementIn(data=request.data)
        d.is_valid(raise_exception=True)
        v = d.validated_data
        rapport, cree = services.signaler(
            request.user, v["target_type"], v["target_id"], v["reason_code"], v["details"]
        )
        return Response(
            {"id": rapport.pk, "status": rapport.status, "created": cree},
            status=201 if cree else 200,
        )


class SignalerDejaLouee(APIView):
    authentication_classes = [AuthJwt]
    permission_classes = [EstClient]
    throttle_classes = [LimiteCompte]

    @extend_schema(
        tags=["Signalements"], summary="Signaler qu'une annonce est déjà louée", request=None,
        responses={200: s.SignalementOut, 201: s.SignalementOut},
    )  # fmt: skip
    def post(self, request, annonce_id):
        rapport, cree = services.signaler_deja_louee(request.user, annonce_id)
        return Response(
            {"id": rapport.pk, "status": rapport.status, "created": cree},
            status=201 if cree else 200,
        )
