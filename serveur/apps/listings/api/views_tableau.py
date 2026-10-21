"""Tableau de bord du gérant (CDC §10.4)."""

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts import selectors as comptes
from apps.accounts.api.authentication import AuthJwt, EstGerant
from apps.chat import selectors as chat_selectors
from apps.core.api.throttles import LimiteLecture

from .. import selectors


class TableauOut(serializers.Serializer):
    listings_by_status = serializers.DictField(child=serializers.IntegerField())
    views_30d = serializers.IntegerField()
    views_total = serializers.IntegerField(
        help_text="Vues de toutes tes annonces depuis leur publication."
    )
    favorites_30d = serializers.IntegerField()
    conversations_30d = serializers.IntegerField()
    to_confirm = serializers.IntegerField()
    unread_messages = serializers.IntegerField()
    response_rate_30d = serializers.FloatField(allow_null=True)
    median_response_min = serializers.IntegerField(allow_null=True)


class Tableau(APIView):
    authentication_classes = [AuthJwt]
    permission_classes = [EstGerant]
    throttle_classes = [LimiteLecture]

    @extend_schema(tags=["Espace gérant"], summary="Tableau de bord", responses={200: TableauOut})
    def get(self, request):
        profil = comptes.profil_gerant(request.user)
        donnees = selectors.tableau_de_bord_gerant(profil)
        publics = comptes.gerants_publics([request.user.pk]).get(request.user.pk, {})
        taux = comptes.taux_de_reponse(request.user.pk)
        return Response(
            {
                **donnees,
                "unread_messages": chat_selectors.total_non_lus(request.user.pk, "gerant"),
                "response_rate_30d": taux,
                "median_response_min": publics.get("median_response_min"),
            }
        )
