"""Abonnement (CDC §10.6) : absents du schéma public et en `404 feature_disabled` tant que le drapeau est faux."""

from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.api.authentication import AuthJwt, EstGerant
from apps.core.api.throttles import LimiteCompte, LimiteParIp
from apps.core.errors import ErreurMetier

from .. import services
from . import serializers as s


def _valide(classe, request) -> dict:
    serializer = classe(data=request.data)
    if not serializer.is_valid():
        raise ErreurMetier(
            "validation_error", "Les données envoyées sont invalides.",
            champs={k: [str(m) for m in v] for k, v in serializer.errors.items()},
        )  # fmt: skip
    return serializer.validated_data


class _Pro(APIView):
    authentication_classes = [AuthJwt]
    permission_classes = [EstGerant]
    throttle_classes = [LimiteCompte]

    def initial(self, request, *args, **kwargs):
        services.exiger_actif()  # avant l'authentification : rien ne trahit l'existence de ces routes
        super().initial(request, *args, **kwargs)


@extend_schema(exclude=True)
class Plans(_Pro):
    def get(self, request):
        return Response(s.PlanOut(services.plans(), many=True).data)


@extend_schema(exclude=True)
class Abonnement(_Pro):
    def get(self, request):
        return Response(s.AbonnementOut(services.abonnement_courant(request.user.pk)).data)


@extend_schema(exclude=True)
class Paiement(_Pro):
    def post(self, request):
        d = _valide(s.PaiementIn, request)
        paiement = services.demarrer_paiement(
            request.user.pk, plan_code=d["plan_code"], methode=d["method"], telephone=d["phone"],
            cle=d["idempotency_key"],
        )  # fmt: skip
        return Response(s.PaiementOut(paiement).data, status=202)


@extend_schema(exclude=True)
class Annulation(_Pro):
    def post(self, request):
        return Response(s.AbonnementOut(services.annuler(request.user.pk)).data)


@extend_schema(exclude=True)
class Webhook(APIView):
    """Appelé par le fournisseur : authentifié par la signature, pas par un jeton."""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [LimiteParIp]

    def initial(self, request, *args, **kwargs):
        services.exiger_actif()
        super().initial(request, *args, **kwargs)

    def post(self, request, fournisseur):
        _, nouveau = services.recevoir_webhook(fournisseur, request.body, dict(request.headers))
        return Response({"received": True, "duplicate": not nouveau})
