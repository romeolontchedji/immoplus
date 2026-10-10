"""API du centre de notifications (CDC §10.5)."""

from django.utils.dateparse import parse_datetime
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.api.authentication import AuthJwt, Connecte
from apps.core.api.throttles import LimiteCompte, LimiteLecture
from apps.core.errors import ErreurMetier

from .. import selectors, services
from . import serializers as s

TAG = ["Notifications"]


class _Connecte(APIView):
    authentication_classes = [AuthJwt]
    permission_classes = [Connecte]
    throttle_classes = [LimiteLecture]


class _Ecriture(_Connecte):
    throttle_classes = [LimiteCompte]


class Liste(_Connecte):
    @extend_schema(
        tags=TAG,
        summary="Centre de notifications",
        parameters=[
            OpenApiParameter("cursor", str, description="Curseur de la page précédente"),
            OpenApiParameter("limit", int, description="30 par défaut, 50 au plus"),
        ],
        responses={200: s.ListeNotificationsOut},
    )
    def get(self, request):
        avant = None
        if request.query_params.get("cursor"):
            avant = parse_datetime(request.query_params["cursor"])
            if avant is None:
                raise ErreurMetier(
                    "invalid_cursor", "Curseur invalide.", champs={"cursor": ["Invalide"]}
                )
        try:
            limite = min(50, max(1, int(request.query_params.get("limit", 30))))
        except ValueError as erreur:
            raise ErreurMetier(
                "validation_error", "Limite invalide.", champs={"limit": ["Entier attendu"]}
            ) from erreur
        lignes, suivant = selectors.liste(request.user.pk, avant=avant, limite=limite)
        return Response(
            {
                "items": [services.resume(n) for n in lignes],
                "next_cursor": suivant,
                "unread_count": selectors.non_lues(request.user.pk),
            }
        )


class Compteur(_Connecte):
    @extend_schema(tags=TAG, summary="Compteur de non lues", responses={200: s.CompteurOut})
    def get(self, request):
        return Response({"unread_count": selectors.non_lues(request.user.pk)})


class Lue(_Ecriture):
    @extend_schema(
        tags=TAG, summary="Marquer une notification comme lue", request=None, responses={204: None}
    )
    def post(self, request, notification_id):
        services.marquer_lue(request.user.pk, notification_id)
        return Response(status=204)


class ToutLu(_Ecriture):
    @extend_schema(
        tags=TAG, summary="Tout marquer comme lu", request=None, responses={200: s.ToutLuOut}
    )
    def post(self, request):
        return Response({"updated": services.tout_marquer_lu(request.user.pk)})
