"""API de la messagerie (CDC §10.5) : l'envoi passe par HTTP, la réception par WebSocket."""

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.api.authentication import AuthJwt, EstClientOuGerant
from apps.core.api.throttles import LimiteCompte, LimiteLecture
from apps.core.errors import ErreurMetier
from apps.listings import selectors as annonces

from .. import selectors, services, ws
from . import serializers as s

TAG = ["Messagerie"]


def role_de(request) -> str:
    return request.auth.role if request.auth is not None else request.user.role


class _Participant(APIView):
    authentication_classes = [AuthJwt]
    permission_classes = [EstClientOuGerant]
    throttle_classes = [LimiteLecture]


class _Ecriture(_Participant):
    throttle_classes = [LimiteCompte]


def _conversation_out(conversation, utilisateur_id) -> dict:
    return selectors.decrire([conversation], utilisateur_id)[0]


def _entier(valeur, champ):
    if valeur in (None, ""):
        return None
    try:
        return int(valeur)
    except ValueError as erreur:
        raise ErreurMetier(
            "validation_error", "Entier attendu.", champs={champ: ["Entier attendu"]}
        ) from erreur


class Conversations(_Participant):
    @extend_schema(
        tags=TAG,
        operation_id="conversations_list",
        summary="Mes conversations",
        parameters=[
            OpenApiParameter("listing", str, description="Filtre par annonce (gérant)"),
            OpenApiParameter("cursor", str),
            OpenApiParameter("limit", int),
        ],
        responses={200: s.ListeConversationsOut},
    )
    def get(self, request):
        role = role_de(request)
        limite = min(50, max(1, _entier(request.query_params.get("limit"), "limit") or 30))
        lignes, suivant = selectors.liste(
            request.user.pk,
            role=role,
            annonce_id=request.query_params.get("listing") or None,
            avant=selectors.parse_curseur(request.query_params.get("cursor")),
            limite=limite,
        )
        return Response(
            {
                "items": selectors.decrire(lignes, request.user.pk),
                "next_cursor": suivant,
                "unread_total": selectors.total_non_lus(request.user.pk, role),
            }
        )

    @extend_schema(
        tags=TAG,
        summary="Ouvrir ou retrouver la conversation d'une annonce et envoyer le premier message",
        request=s.ConversationOuvertureIn,
        responses={200: s.OuvertureOut, 201: s.OuvertureOut},
    )
    def post(self, request):
        d = s.ConversationOuvertureIn(data=request.data)
        d.is_valid(raise_exception=True)
        conversation, message, cree, info = services.ouvrir(
            request.user,
            d.validated_data["listing_id"],
            d.validated_data["body"],
            d.validated_data["client_msg_id"],
        )
        return Response(
            {
                "conversation": _conversation_out(conversation, request.user.pk),
                "message": services.message_pour(message, request.user.pk),
                "warning": info["warning"],
            },
            status=201 if cree else 200,
        )


class Demarrage(_Participant):
    @extend_schema(
        tags=TAG,
        summary="« Contacter le gérant » : ouvrir ou retrouver la conversation sans message imposé",
        request=s.DemarrageIn,
        responses={200: s.ConversationOut},
    )
    def post(self, request):
        d = s.DemarrageIn(data=request.data)
        d.is_valid(raise_exception=True)
        conversation = services.demarrer(request.user, d.validated_data["listing_id"])
        return Response(_conversation_out(conversation, request.user.pk))


class ConversationDetail(_Participant):
    @extend_schema(
        tags=TAG, summary="Détail d'une conversation", responses={200: s.ConversationDetailOut}
    )
    def get(self, request, conversation_id):
        conversation = selectors.conversation_du_participant(request.user.pk, conversation_id)
        sortie = _conversation_out(conversation, request.user.pk)
        sortie["address_private"] = (
            annonces.adresse_privee(conversation.listing_id)
            if conversation.gerant_id == request.user.pk
            else None
        )
        autre = selectors.autre_participant(conversation, request.user.pk)
        sortie["my_read_seq"] = selectors.position_de_lecture(conversation, request.user.pk)
        sortie["other_read_seq"] = selectors.position_de_lecture(conversation, autre)
        sortie["last_seq"] = conversation.last_seq
        return Response(sortie)

    @extend_schema(
        tags=TAG,
        summary="Mettre la conversation en silence",
        request=s.SilenceIn,
        responses={200: s.ConversationOut},
    )
    def patch(self, request, conversation_id):
        d = s.SilenceIn(data=request.data)
        d.is_valid(raise_exception=True)
        conversation = services.definir_silence(
            request.user, conversation_id, d.validated_data["muted_until"]
        )
        return Response(_conversation_out(conversation, request.user.pk))


class Messages(_Participant):
    @extend_schema(
        tags=TAG,
        summary="Historique (50 par page)",
        parameters=[OpenApiParameter("before_seq", int), OpenApiParameter("after_seq", int)],
        responses={200: s.HistoriqueOut},
    )
    def get(self, request, conversation_id):
        conversation = selectors.conversation_du_participant(request.user.pk, conversation_id)
        avant = _entier(request.query_params.get("before_seq"), "before_seq")
        apres = _entier(request.query_params.get("after_seq"), "after_seq")
        lignes, plus = selectors.messages(conversation, avant_seq=avant, apres_seq=apres)
        return Response(
            {
                "items": [services.message_pour(m, request.user.pk) for m in lignes],
                "has_more": plus,
                "last_seq": conversation.last_seq,
            }
        )

    @extend_schema(
        tags=TAG,
        summary="Envoyer un message (idempotent)",
        request=s.MessageIn,
        responses={200: s.EnvoiOut, 201: s.EnvoiOut},
    )
    def post(self, request, conversation_id):
        d = s.MessageIn(data=request.data)
        d.is_valid(raise_exception=True)
        message, cree, info = services.envoyer(
            request.user,
            conversation_id,
            d.validated_data["body"],
            d.validated_data["client_msg_id"],
        )
        return Response(
            {
                "message": services.message_pour(message, request.user.pk),
                "warning": info["warning"],
            },
            status=201 if cree else 200,
        )

    throttle_classes = [LimiteCompte]


class Lecture(_Ecriture):
    @extend_schema(
        tags=TAG,
        summary="Marquer comme lu jusqu'à une position",
        request=s.LectureIn,
        responses={200: s.ConversationOut},
    )
    def post(self, request, conversation_id):
        d = s.LectureIn(data=request.data)
        d.is_valid(raise_exception=True)
        conversation = services.lire(request.user, conversation_id, d.validated_data["up_to_seq"])
        return Response(_conversation_out(conversation, request.user.pk))


class Blocage(_Ecriture):
    @extend_schema(
        tags=TAG,
        summary="Bloquer la conversation",
        request=None,
        responses={200: s.ConversationOut},
    )
    def post(self, request, conversation_id):
        return Response(
            _conversation_out(services.bloquer(request.user, conversation_id), request.user.pk)
        )


class Deblocage(_Ecriture):
    @extend_schema(
        tags=TAG,
        summary="Débloquer la conversation",
        request=None,
        responses={200: s.ConversationOut},
    )
    def post(self, request, conversation_id):
        return Response(
            _conversation_out(services.debloquer(request.user, conversation_id), request.user.pk)
        )


class TicketWebSocket(_Ecriture):
    authentication_classes = [AuthJwt, SessionAuthentication]

    @extend_schema(
        tags=TAG,
        summary="Ticket de connexion WebSocket (usage unique, 30 s)",
        request=None,
        responses={200: s.TicketOut},
    )
    def post(self, request):
        appareil = (
            request.auth.appareil_id
            if request.auth is not None
            else f"web:{request.session.session_key}"
        )
        return Response(
            {"ticket": ws.emettre(request.user.pk, appareil), "expires_in": ws.DUREE_TICKET_S}
        )
