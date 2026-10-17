"""API des quartiers et de l'espace gérant (CDC §10.3, §10.4)."""

from drf_spectacular.utils import extend_schema
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts import selectors as comptes
from apps.accounts.api.authentication import AuthJwt, EstGerant
from apps.core.api.throttles import LimiteCompte, LimiteParIp
from apps.core.errors import ErreurMetier

from .. import selectors
from ..services import annonces, contenu, types
from . import serializers as s

TAG_PRO = ["Espace gérant"]


class _Public(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [LimiteParIp]


class _Pro(APIView):
    authentication_classes = [AuthJwt]
    permission_classes = [EstGerant]
    throttle_classes = [LimiteCompte]

    def profil(self, request):
        return comptes.profil_gerant(request.user)


def _donnees(serializer_class, request, partial=False) -> dict:
    serializer = serializer_class(data=request.data, partial=partial)
    serializer.is_valid(raise_exception=True)
    donnees = dict(serializer.validated_data)
    if "district" in donnees:
        donnees["district"] = str(donnees["district"])
    return donnees


def _sortie(annonce) -> dict:
    return s.AnnonceProOut(annonce).data


class Quartiers(_Public):
    @extend_schema(
        tags=["Référentiels"], summary="Quartiers actifs", responses={200: s.DistrictOut(many=True)}
    )
    def get(self, request):
        return Response(s.DistrictOut(selectors.quartiers_actifs(), many=True).data)


class TypesChambre(_Public):
    @extend_schema(
        tags=["Référentiels"],
        summary="Types de logement (validés, les plus courants d'abord)",
        responses={200: s.TypeChambreOut(many=True)},
    )
    def get(self, request):
        return Response(s.TypeChambreOut(types.publics(), many=True).data)


class TypesChambrePro(_Pro):
    @extend_schema(
        tags=TAG_PRO,
        summary="Types utilisables par le gérant (validés et ses propositions)",
        responses={200: s.TypeChambreProOut(many=True)},
    )
    def get(self, request):
        return Response(
            s.TypeChambreProOut(types.pour_gerant(self.profil(request)), many=True).data
        )

    @extend_schema(
        tags=TAG_PRO,
        summary="Proposer un type de logement",
        description="Renvoie le type équivalent s'il existe déjà (accents et casse ignorés), sinon le crée en "
        "attente de validation. Utilisable tout de suite par le gérant ; dans les filtres après validation.",
        request=s.PropositionTypeIn,
        responses={200: s.TypeChambreProOut, 201: s.TypeChambreProOut},
    )
    def post(self, request):
        d = _donnees(s.PropositionTypeIn, request)
        avant = types.libelles()
        t = types.proposer(self.profil(request), d["label"])
        corps = {"slug": t.slug, "label": t.label, "status": t.status}
        return Response(s.TypeChambreProOut(corps).data, status=200 if t.slug in avant else 201)


class AnnoncesPro(_Pro):
    @extend_schema(
        tags=TAG_PRO, summary="Mes annonces", responses={200: s.AnnonceProOut(many=True)}
    )
    def get(self, request):
        statut = request.query_params.get("status")
        return Response(
            s.AnnonceProOut(
                selectors.annonces_du_gerant(self.profil(request), statut), many=True
            ).data
        )

    @extend_schema(
        tags=TAG_PRO,
        summary="Créer un brouillon",
        request=s.AnnonceIn,
        responses={201: s.AnnonceProOut},
    )
    def post(self, request):
        annonce = annonces.creer_brouillon(self.profil(request), _donnees(s.AnnonceIn, request))
        return Response(_sortie(annonce), status=201)


class AnnonceProDetail(_Pro):
    def _trouver(self, request, annonce_id):
        annonce = selectors.annonce_du_gerant(self.profil(request), annonce_id)
        if annonce is None:
            raise ErreurMetier("not_found", "Annonce introuvable.", statut=404)
        return annonce

    @extend_schema(
        tags=TAG_PRO,
        summary="Lire une annonce (adresse privée comprise)",
        responses={200: s.AnnonceProOut},
    )
    def get(self, request, annonce_id):
        return Response(_sortie(self._trouver(request, annonce_id)))

    @extend_schema(
        tags=TAG_PRO,
        summary="Modifier une annonce",
        request=s.AnnonceIn,
        responses={200: s.AnnonceProOut},
    )
    def patch(self, request, annonce_id):
        annonce = annonces.modifier(
            self.profil(request), annonce_id, _donnees(s.AnnonceIn, request, partial=True)
        )
        return Response(_sortie(annonce))

    @extend_schema(tags=TAG_PRO, summary="Supprimer un brouillon", responses={204: None})
    def delete(self, request, annonce_id):
        annonces.supprimer_brouillon(self.profil(request), annonce_id)
        return Response(status=204)


def _action(nom: str, fonction, resume: str):
    class Action(_Pro):
        @extend_schema(tags=TAG_PRO, summary=resume, request=None, responses={200: s.AnnonceProOut})
        def post(self, request, annonce_id):
            return Response(_sortie(fonction(self.profil(request), annonce_id)))

    Action.__name__ = nom
    return Action


Publication = _action("Publication", annonces.publier, "Publier (règles du §9.23)")
Confirmation = _action("Confirmation", annonces.confirmer, "Confirmer la disponibilité")
Masquage = _action("Masquage", annonces.masquer, "Masquer l'annonce")
MarquerLouee = _action("MarquerLouee", annonces.marquer_louee, "Marquer comme louée")
AnnulerLouee = _action("AnnulerLouee", annonces.annuler_louee, "Annuler « louée »")


class ApercuMarkdown(_Pro):
    # Aussi depuis l'éditeur du site (barre de mise en forme, session + CSRF), comme l'envoi des médias.
    authentication_classes = [AuthJwt, SessionAuthentication]

    @extend_schema(
        tags=TAG_PRO,
        summary="Aperçu du texte enrichi",
        request=s.ApercuIn,
        responses={200: s.ApercuOut},
    )
    def post(self, request):
        d = _donnees(s.ApercuIn, request)
        md, html = contenu.rendre(d["markdown"])
        return Response({"markdown": md, "html": html})
