"""API des médias de l'espace gérant et protocole d'envoi reprenable (CDC §11.2)."""

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts import selectors as comptes
from apps.accounts.api.authentication import AuthJwt, EstGerant
from apps.core.api.throttles import LimiteCompte
from apps.core.errors import ErreurMetier
from apps.media import stockage

from ..enums import StatutMedia
from ..services import medias
from . import serializers as s

TAG = ["Médias"]
TUS = {"Tus-Resumable": "1.0.0", "Cache-Control": "no-store"}


def _media_out(m) -> dict:
    envoi_ouvert = m.status == StatutMedia.UPLOADING
    return {
        "id": m.pk, "kind": m.kind, "status": m.status, "position": m.position, "is_cover": m.is_cover,
        "declared_size_bytes": m.declared_size_bytes, "received_bytes": m.received_bytes,
        "width": m.width, "height": m.height, "duration_s": float(m.duration_s) if m.duration_s is not None else None,
        "playback_url": stockage.url_publique(m.playback_path) if m.status == StatutMedia.READY else None,
        "poster_url": stockage.url_publique(m.poster_path) if m.status == StatutMedia.READY else None,
        "error_code": m.error_code, "error_detail": m.error_detail,
        "upload_url": f"/uploads/{m.pk}" if envoi_ouvert else None,
    }  # fmt: skip


class _Pro(APIView):
    authentication_classes = [
        AuthJwt,
        SessionAuthentication,
    ]  # application (Bearer) et site (session + CSRF)
    permission_classes = [EstGerant]
    throttle_classes = [LimiteCompte]

    def profil(self, request):
        return comptes.profil_gerant(request.user)


class MediasAnnonce(_Pro):
    @extend_schema(tags=TAG, summary="Médias d'une annonce", responses={200: s.MediaOut(many=True)})
    def get(self, request, annonce_id):
        return Response([_media_out(m) for m in medias.lister(self.profil(request), annonce_id)])

    @extend_schema(
        tags=TAG,
        summary="Ouvrir un envoi (quotas vérifiés)",
        request=s.MediaIn,
        responses={201: s.MediaOut},
    )
    def post(self, request, annonce_id):
        d = s.MediaIn(data=request.data)
        d.is_valid(raise_exception=True)
        media = medias.creer_envoi(
            self.profil(request),
            annonce_id,
            d.validated_data["kind"],
            d.validated_data["size_bytes"],
        )
        return Response(_media_out(media), status=201)


class OrdreMedias(_Pro):
    @extend_schema(
        tags=TAG,
        summary="Ordre des médias et couverture",
        request=s.OrdreMediasIn,
        responses={200: s.MediaOut(many=True)},
    )
    def patch(self, request, annonce_id):
        d = s.OrdreMediasIn(data=request.data)
        d.is_valid(raise_exception=True)
        cover = d.validated_data.get("cover")
        liste = medias.definir_ordre(
            self.profil(request),
            annonce_id,
            [str(i) for i in d.validated_data["order"]],
            str(cover) if cover else None,
        )
        return Response([_media_out(m) for m in liste])


class MediaDetail(_Pro):
    @extend_schema(tags=TAG, summary="Supprimer un média", responses={204: None})
    def delete(self, request, annonce_id, media_id):
        medias.supprimer(self.profil(request), annonce_id, media_id)
        return Response(status=204)


class Envoi(_Pro):
    """Protocole tus minimal : HEAD donne la position, PATCH ajoute un morceau (2 Mo au plus)."""

    throttle_classes = []  # un envoi de 150 Mo = 150 requêtes ; les quotas d'envoi protègent déjà

    @extend_schema(
        tags=TAG, summary="Position d'un envoi (reprise)", responses={200: None},
        parameters=[OpenApiParameter("Upload-Offset", str, OpenApiParameter.HEADER, response_only=True)] if False else None,
    )  # fmt: skip
    def head(self, request, media_id):
        m = medias.decalage(self.profil(request), None, media_id)
        return Response(
            headers={
                **TUS,
                "Upload-Offset": str(m.received_bytes),
                "Upload-Length": str(m.declared_size_bytes),
            }
        )

    @extend_schema(
        tags=TAG,
        summary="Envoyer un morceau",
        request={"application/offset+octet-stream": bytes},
        responses={204: None},
    )
    def patch(self, request, media_id):
        if request.headers.get("Tus-Resumable") != "1.0.0":
            raise ErreurMetier("tus_version", "En-tête Tus-Resumable: 1.0.0 requis.", statut=412)
        if request.content_type != "application/offset+octet-stream":
            raise ErreurMetier(
                "unsupported_media_type",
                "Content-Type application/offset+octet-stream requis.",
                statut=415,
            )
        try:
            decalage = int(request.headers["Upload-Offset"])
            taille = int(request.headers.get("Content-Length", "0"))
        except (KeyError, ValueError) as erreur:
            raise ErreurMetier(
                "validation_error", "En-tête Upload-Offset manquant ou invalide."
            ) from erreur
        if taille > medias.MORCEAU_MAX:
            raise ErreurMetier("validation_error", "Morceau trop gros (2 Mo au plus).", statut=413)
        morceau = request._request.body  # lu en une fois : borné par MORCEAU_MAX
        m = medias.recevoir_morceau(self.profil(request), None, media_id, decalage, morceau)
        return Response(status=204, headers={**TUS, "Upload-Offset": str(m.received_bytes)})
