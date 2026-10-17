"""API publique du fil et des fiches, favoris et alertes du locataire (CDC §10.3)."""

import hashlib

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.api.authentication import AuthJwt, EstClient
from apps.core.api.throttles import LimiteCompte, LimiteLecture, LimiteParIp
from apps.core.errors import ErreurMetier
from apps.core.http import ip_client

from .. import selectors
from ..services import alertes, favoris, fil, vues
from . import serializers_publics as s

TAG = ["Fil et fiches"]
TAG_LOC = ["Espace locataire"]
PARAMETRES_FIL = [
    OpenApiParameter(nom, str, description=desc)
    for nom, desc in (
        ("q", "Recherche texte (sans accents, tolérante aux fautes)"),
        ("district", "Slugs de quartiers séparés par des virgules"),
        ("type", "Types de logement séparés par des virgules"),
        ("rent_min", "Loyer minimum (FCFA)"),
        ("rent_max", "Loyer maximum (FCFA)"),
        ("bathroom", "Douche et WC internes (true/false)"),
        ("water", "Sources d'eau séparées par des virgules"),
        ("meter", "Compteurs séparés par des virgules"),
        ("fenced", "Clôture (true/false)"),
        ("available_before", "Disponible avant cette date (AAAA-MM-JJ)"),
        ("max_distance_m", "Distance maximale au campus (m)"),
        ("sort", "recent, rent_asc, rent_desc, distance"),
        ("cursor", "Curseur de la page précédente"),
        ("limit", "10 par défaut, 50 au plus"),
    )
]


class _Public(APIView):
    authentication_classes = [AuthJwt]  # facultative : sans en-tête, la requête reste anonyme
    permission_classes = [AllowAny]
    throttle_classes = [LimiteParIp]


class Fil(_Public):
    throttle_classes = [LimiteLecture]

    @extend_schema(
        tags=TAG,
        operation_id="listings_list",
        summary="Fil et recherche",
        parameters=PARAMETRES_FIL,
        responses={200: s.FilOut},
    )
    def get(self, request):
        resultat = fil.rechercher(request.query_params)
        reponse = Response({"items": resultat["items"], "next_cursor": resultat["next_cursor"]})
        reponse["Cache-Control"] = "public, max-age=30"
        return reponse


class Fiche(_Public):
    throttle_classes = [LimiteLecture]

    @extend_schema(
        tags=TAG,
        operation_id="listings_retrieve",
        summary="Fiche d'une annonce (identifiant ou slug)",
        responses={200: s.FicheOut},
    )
    def get(self, request, ident):
        fiche = selectors.fiche_publique(ident)
        if fiche is None:
            raise ErreurMetier("not_found", "Annonce introuvable.", statut=404)
        utilisateur = request.user
        favori = bool(
            utilisateur is not None
            and getattr(utilisateur, "role", None) == "client"
            and selectors.ids_favoris(utilisateur.pk, [fiche["id"]])
        )
        reponse = Response({**fiche, "is_favorite": favori})
        reponse["Cache-Control"] = (
            "private, max-age=0" if utilisateur is not None else "public, max-age=30"
        )
        return reponse


def _visiteur(request) -> str:
    if request.user is not None:
        return f"u:{request.user.pk}"
    installation = request.headers.get("X-Installation-Id", "")
    base = installation or f"{ip_client(request)}|{request.headers.get('User-Agent', '')}"
    return "a:" + hashlib.sha256(base.encode()).hexdigest()[:24]


class Similaires(_Public):
    throttle_classes = [LimiteLecture]

    @extend_schema(
        tags=TAG,
        summary="Chambres similaires (quartier, type, loyer, distance)",
        responses={200: s.CarteOut(many=True)},
    )
    def get(self, request, ident):
        fiche = selectors.fiche_publique(ident)
        if fiche is None:
            raise ErreurMetier("not_found", "Annonce introuvable.", statut=404)
        reponse = Response(s.CarteOut(selectors.similaires(fiche["id"]), many=True).data)
        reponse["Cache-Control"] = "public, max-age=60"
        return reponse


class Vue(_Public):
    @extend_schema(tags=TAG, summary="Compter une vue", request=None, responses={200: s.VueOut})
    def post(self, request, ident):
        fiche = selectors.fiche_publique(ident)
        if fiche is None:
            raise ErreurMetier("not_found", "Annonce introuvable.", statut=404)
        proprietaire = request.user is not None and request.user.pk == fiche["gerant_user_id"]
        compte = vues.enregistrer(
            fiche["id"], _visiteur(request),
            user_agent=request.headers.get("User-Agent"), proprietaire=proprietaire,
        )  # fmt: skip
        return Response({"counted": compte})


class _Client(APIView):
    authentication_classes = [AuthJwt]
    permission_classes = [EstClient]
    throttle_classes = [LimiteCompte]


class Favoris(_Client):
    @extend_schema(tags=TAG_LOC, summary="Mes favoris", responses={200: s.CarteOut(many=True)})
    def get(self, request):
        return Response(selectors.favoris_de(request.user.pk))


class FavoriDetail(_Client):
    @extend_schema(tags=TAG_LOC, summary="Ajouter aux favoris", request=None, responses={204: None})
    def put(self, request, annonce_id):
        favoris.ajouter(request.user, annonce_id)
        return Response(status=204)

    @extend_schema(tags=TAG_LOC, summary="Retirer des favoris", responses={204: None})
    def delete(self, request, annonce_id):
        favoris.retirer(request.user, annonce_id)
        return Response(status=204)


def _alerte_out(a) -> dict:
    return s.AlerteOut(a).data


class OptionsAlerte(_Public):
    throttle_classes = [LimiteLecture]

    @extend_schema(
        tags=TAG_LOC,
        summary="Listes de l'éditeur d'alerte (quartiers les plus demandés, budgets fréquents)",
        responses={200: s.OptionsAlerteOut},
    )
    def get(self, request):
        return Response(s.OptionsAlerteOut(alertes.options()).data)


class Alertes(_Client):
    @extend_schema(tags=TAG_LOC, summary="Mes alertes", responses={200: s.AlerteOut(many=True)})
    def get(self, request):
        return Response([_alerte_out(a) for a in selectors.alertes_de(request.user.pk)])

    @extend_schema(
        tags=TAG_LOC,
        summary="Créer une alerte (5 actives au plus)",
        request=s.AlerteIn,
        responses={201: s.AlerteOut},
    )
    def post(self, request):
        d = s.AlerteIn(data=request.data)
        d.is_valid(raise_exception=True)
        return Response(
            _alerte_out(alertes.creer(request.user, dict(d.validated_data))), status=201
        )


class AlerteDetail(_Client):
    @extend_schema(
        tags=TAG_LOC,
        summary="Modifier une alerte",
        request=s.AlerteIn,
        responses={200: s.AlerteOut},
    )
    def patch(self, request, alerte_id):
        d = s.AlerteIn(data=request.data, partial=True)
        d.is_valid(raise_exception=True)
        return Response(
            _alerte_out(alertes.modifier(request.user, alerte_id, dict(d.validated_data)))
        )

    @extend_schema(tags=TAG_LOC, summary="Supprimer une alerte", responses={204: None})
    def delete(self, request, alerte_id):
        alertes.supprimer(request.user, alerte_id)
        return Response(status=204)
