"""Adaptateurs HTTP de l'API de comptes : valident l'entrée, appellent les services, formatent la sortie."""

from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts import selectors
from apps.accounts.services import (
    appareils,
    authentification,
    compte,
    inscription,
    jetons,
    otp,
)
from apps.core.api.throttles import LimiteAuth, LimiteCompte
from apps.core.errors import ErreurMetier
from apps.core.http import installation_id, ip_client, user_agent

from . import serializers as s
from .authentication import AuthJwt, Connecte

TAG_AUTH = ["Authentification"]
TAG_COMPTE = ["Compte"]
TAG_APPAREILS = ["Appareils"]
ERREUR = {"description": "Erreur au format {error: {code, message, fields, request_id}}"}


def _installation(request) -> str:
    valeur = installation_id(request)
    if valeur is None:
        raise ErreurMetier(
            "validation_error",
            "L'identifiant d'installation est manquant ou invalide.",
            champs={"X-Installation-Id": ["En-tête requis (8 à 64 caractères)"]},
        )
    return valeur


def _utilisateur_out(u) -> dict:
    return {
        "id": u.pk,
        "full_name": u.full_name,
        "role": u.role,
        "phone": u.phone_e164,
        "terms_version": u.terms_version,
        "created_at": u.created_at,
    }


def _session(request, utilisateur, donnees) -> dict:
    """Crée l'appareil de l'installation et retourne l'utilisateur, la paire de jetons et l'appareil."""
    appareil, refresh = appareils.ouvrir(
        utilisateur,
        installation_id=_installation(request),
        platform=donnees["platform"],
        app_version=request.headers.get("X-App-Version"),
        label=donnees.get("label"),
        ip=ip_client(request),
    )
    paire = jetons.emettre_paire(utilisateur, appareil, refresh)
    return {
        "user": _utilisateur_out(utilisateur),
        "tokens": {
            "access": paire.acces,
            "refresh": paire.refresh,
            "expires_in": paire.expire_dans_s,
        },
        "device_id": appareil.pk,
    }


class _SansCache(APIView):
    """Les réponses d'authentification et de compte ne sont jamais mises en cache (jetons, données personnelles)."""

    def finalize_response(self, request, response, *args, **kwargs):
        reponse = super().finalize_response(request, response, *args, **kwargs)
        reponse["Cache-Control"] = "no-store"
        return reponse


class _Public(_SansCache):
    authentication_classes = [AuthJwt]
    permission_classes = [AllowAny]
    throttle_classes = [LimiteAuth]


class _Prive(_SansCache):
    authentication_classes = [AuthJwt]
    permission_classes = [Connecte]
    throttle_classes = [LimiteCompte]


def _valide(serializer_class, request) -> dict:
    serializer = serializer_class(data=request.data)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


# ---------------------------------------------------------------- OTP
class OtpDemande(_Public):
    @extend_schema(
        tags=TAG_AUTH,
        summary="Demander un code à usage unique",
        description="Réponse identique que le numéro ait un compte ou non. Plafonds et coupe-circuit : CDC §5.3.",
        request=s.OtpDemandeIn,
        responses={
            202: inline_serializer("OtpDemandeOut", {"resend_after_s": serializers.IntegerField()})
        },
    )
    def post(self, request):
        d = _valide(s.OtpDemandeIn, request)
        if d["purpose"] == "change_phone" and request.auth is None:
            raise ErreurMetier("not_authenticated", "Connexion requise.", statut=401)
        otp.demander(
            d["phone"],
            d["purpose"],
            otp.Contexte(
                installation_id=installation_id(request),
                ip=ip_client(request),
                jeton_attestation=d.get("attestation_token"),
                surface="app",
            ),
        )
        return Response({"resend_after_s": 60}, status=202)


class OtpVerification(_Public):
    @extend_schema(
        tags=TAG_AUTH,
        summary="Vérifier un code",
        request=s.OtpVerificationIn,
        responses={200: s.OtpJetonOut},
    )
    def post(self, request):
        d = _valide(s.OtpVerificationIn, request)
        jeton = otp.verifier(d["phone"], d["purpose"], d["code"])
        return Response({"otp_token": jeton, "expires_in": otp.VALIDITE_JETON_S})


# ---------------------------------------------------------------- Session
class Inscription(_Public):
    @extend_schema(
        tags=TAG_AUTH,
        summary="Créer un compte locataire",
        request=s.InscriptionIn,
        responses={201: s.SessionOut},
    )
    def post(self, request):
        _installation(
            request
        )  # avant toute écriture : un compte ne doit pas être créé sans session possible
        d = _valide(s.InscriptionIn, request)
        utilisateur = inscription.inscrire_client(
            d["otp_token"],
            d["full_name"],
            d["password"],
            d["terms_accepted"],
            ip=ip_client(request),
            user_agent=user_agent(request),
        )
        return Response(_session(request, utilisateur, d), status=201)


class Connexion(_Public):
    @extend_schema(
        tags=TAG_AUTH, summary="Se connecter", request=s.ConnexionIn, responses={200: s.SessionOut}
    )
    def post(self, request):
        client = _installation(request)
        d = _valide(s.ConnexionIn, request)
        utilisateur = authentification.authentifier(d["phone"], d["password"], client)
        return Response(_session(request, utilisateur, d))


class Rafraichissement(_Public):
    @extend_schema(
        tags=TAG_AUTH,
        summary="Renouveler les jetons",
        request=s.RafraichissementIn,
        responses={200: s.JetonsOut},
    )
    def post(self, request):
        d = _valide(s.RafraichissementIn, request)
        paire = jetons.echanger_refresh(
            d["refresh_token"], installation_id(request), ip_client(request)
        )
        return Response(
            {"access": paire.acces, "refresh": paire.refresh, "expires_in": paire.expire_dans_s}
        )


class Deconnexion(_Prive):
    @extend_schema(
        tags=TAG_AUTH, summary="Se déconnecter de cet appareil", request=None, responses={204: None}
    )
    def post(self, request):
        appareil = selectors.appareil_par_id(request.auth.appareil_id)
        if appareil is not None:
            jetons.revoquer_appareil(appareil, raison="deconnexion")
        return Response(status=204)


class MotDePasseOublie(_Public):
    @extend_schema(
        tags=TAG_AUTH,
        summary="Réinitialiser le mot de passe",
        request=s.MotDePasseOublieIn,
        responses={204: None},
    )
    def post(self, request):
        d = _valide(s.MotDePasseOublieIn, request)
        inscription.reinitialiser_mot_de_passe(
            d["otp_token"], d["new_password"], ip=ip_client(request), user_agent=user_agent(request)
        )
        return Response(status=204)


class ChangementMotDePasse(_Prive):
    @extend_schema(
        tags=TAG_AUTH,
        summary="Changer le mot de passe",
        request=s.ChangementMotDePasseIn,
        responses={204: None},
    )
    def post(self, request):
        d = _valide(s.ChangementMotDePasseIn, request)
        compte.changer_mot_de_passe(
            request.user, d["current_password"], d["new_password"], request.auth.appareil_id
        )
        return Response(status=204)


# ---------------------------------------------------------------- Compte
class Moi(_Prive):
    @extend_schema(tags=TAG_COMPTE, summary="Mon profil", responses={200: s.UtilisateurOut})
    def get(self, request):
        return Response(_utilisateur_out(request.user))

    @extend_schema(
        tags=TAG_COMPTE,
        summary="Modifier mon profil",
        request=s.ProfilIn,
        responses={200: s.UtilisateurOut},
    )
    def patch(self, request):
        d = _valide(s.ProfilIn, request)
        utilisateur = compte.modifier_profil(request.user, nom=d.get("full_name"))
        return Response(_utilisateur_out(utilisateur))

    @extend_schema(
        tags=TAG_COMPTE,
        summary="Supprimer mon compte",
        request=s.SuppressionIn,
        responses={204: None},
    )
    def delete(self, request):
        d = _valide(s.SuppressionIn, request)
        compte.supprimer(request.user, d["password"])
        return Response(status=204)


class ChangementNumero(_Prive):
    @extend_schema(
        tags=TAG_COMPTE,
        summary="Changer de numéro",
        request=s.ChangementNumeroIn,
        responses={200: s.UtilisateurOut},
    )
    def post(self, request):
        d = _valide(s.ChangementNumeroIn, request)
        utilisateur = compte.changer_numero(
            request.user, d["password"], d["otp_token"], request.auth.appareil_id
        )
        return Response(_utilisateur_out(utilisateur))


class Preferences(_Prive):
    @extend_schema(
        tags=TAG_COMPTE, summary="Préférences de notification", responses={200: s.PreferencesIO}
    )
    def get(self, request):
        return Response(compte.preferences(request.user))

    @extend_schema(
        tags=TAG_COMPTE,
        summary="Modifier les préférences de notification",
        request=s.PreferencesIO,
        responses={200: s.PreferencesIO},
    )
    def put(self, request):
        return Response(compte.definir_preferences(request.user, request.data))


# ---------------------------------------------------------------- Appareils
class Appareils(_Prive):
    @extend_schema(
        tags=TAG_APPAREILS,
        summary="Mes appareils connectés",
        responses={200: s.AppareilOut(many=True)},
    )
    def get(self, request):
        courant = str(request.auth.appareil_id)
        return Response(
            [
                {
                    "id": a.pk,
                    "label": a.label,
                    "platform": a.platform,
                    "app_version": a.app_version,
                    "last_seen_at": a.last_seen_at,
                    "created_at": a.created_at,
                    "current": str(a.pk) == courant,
                }
                for a in appareils.lister(request.user)
            ]
        )


class AppareilDetail(_Prive):
    @extend_schema(tags=TAG_APPAREILS, summary="Déconnecter un appareil", responses={204: None})
    def delete(self, request, appareil_id):
        appareils.revoquer(request.user, appareil_id)
        return Response(status=204)


class JetonPush(_Prive):
    @extend_schema(
        tags=TAG_APPAREILS,
        summary="Enregistrer le jeton de notification",
        request=s.JetonPushIn,
        responses={204: None},
    )
    def put(self, request):
        d = _valide(s.JetonPushIn, request)
        appareil = selectors.appareil_par_id(request.auth.appareil_id)
        appareils.enregistrer_push(appareil, d["provider"], d["token"])
        return Response(status=204)
