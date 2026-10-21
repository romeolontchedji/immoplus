"""Adaptateurs HTTP de l'API de comptes : valident l'entrée, appellent les services, formatent la sortie."""

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts import selectors
from apps.accounts.services import (
    appareils,
    authentification,
    compte,
    identifiants,
    inscription,
    jetons,
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
        "username": u.username,
        "first_name": u.first_name,
        "last_name": u.last_name,
        "full_name": u.full_name,
        "email": u.email if u.email_verified_at else None,
        "recovery_key_created_at": u.recovery_key_created_at,
        "occupation": u.occupation,
        "role": u.role,
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


# ---------------------------------------------------------------- Nom d'utilisateur
class Disponibilite(_Public):
    @extend_schema(
        tags=TAG_AUTH,
        summary="Le nom d'utilisateur est-il libre ?",
        description="Vérifié pendant la frappe à l'inscription ; propose des noms libres tirés du prénom et du nom.",
        parameters=[
            OpenApiParameter("username", str, required=True),
            OpenApiParameter("first_name", str, required=False),
            OpenApiParameter("last_name", str, required=False),
        ],
        responses={200: s.DisponibiliteOut},
    )
    def get(self, request):
        q = request.query_params
        try:
            identifiants.valider_nom_utilisateur(q.get("username", ""))
            libre, message = True, ""
        except ErreurMetier as erreur:
            libre, message = False, erreur.champs.get("username", [erreur.message])[0]
        proposes = (
            []
            if libre
            else identifiants.suggestions(q.get("first_name", ""), q.get("last_name", ""))
        )
        return Response({"available": libre, "message": message, "suggestions": proposes})


# ---------------------------------------------------------------- Session
class Inscription(_Public):
    @extend_schema(
        tags=TAG_AUTH,
        summary="Créer un compte locataire",
        description="Aucun code : le compte est créé tout de suite. La clé de secours n'est donnée qu'ici.",
        request=s.InscriptionIn,
        responses={201: s.InscriptionOut},
    )
    def post(self, request):
        _installation(
            request
        )  # avant toute écriture : un compte ne doit pas être créé sans session possible
        d = _valide(s.InscriptionIn, request)
        utilisateur, cle = inscription.inscrire_client(
            nom_utilisateur=d["username"],
            prenom=d["first_name"],
            nom=d["last_name"],
            mot_de_passe=d["password"],
            cgu_acceptees=d["terms_accepted"],
            occupation=d.get("occupation"),
            ip=ip_client(request),
            user_agent=user_agent(request),
        )
        return Response({**_session(request, utilisateur, d), "recovery_key": cle}, status=201)


class Connexion(_Public):
    @extend_schema(
        tags=TAG_AUTH, summary="Se connecter", request=s.ConnexionIn, responses={200: s.SessionOut}
    )
    def post(self, request):
        client = _installation(request)
        d = _valide(s.ConnexionIn, request)
        utilisateur = authentification.authentifier(d["username"], d["password"], client)
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


class LienParEmail(_Public):
    @extend_schema(
        tags=TAG_AUTH,
        summary="Mot de passe oublié : recevoir un lien par e-mail",
        description="Réponse identique que le compte existe ou non. Le lien (30 min) s'ouvre sur le site.",
        request=s.LienParEmailIn,
        responses={202: None},
    )
    def post(self, request):
        d = _valide(s.LienParEmailIn, request)
        inscription.demander_lien_par_email(d["identifier"], ip=ip_client(request))
        return Response(status=202)


class CleDeSecours(_Public):
    @extend_schema(
        tags=TAG_AUTH,
        summary="Mot de passe oublié : clé de secours",
        description="Nouveau mot de passe ; retourne la nouvelle clé (l'ancienne ne sert qu'une fois).",
        request=s.CleDeSecoursIn,
        responses={200: s.CleDeSecoursOut},
    )
    def post(self, request):
        client = _installation(request)
        d = _valide(s.CleDeSecoursIn, request)
        _, cle = inscription.reinitialiser_par_cle(
            d["username"], d["recovery_key"], d["new_password"], client=client,
            ip=ip_client(request), user_agent=user_agent(request),
        )  # fmt: skip
        return Response({"recovery_key": cle})


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
        options = {"occupation": d["occupation"]} if "occupation" in d else {}
        utilisateur = compte.modifier_profil(
            request.user, prenom=d.get("first_name"), nom=d.get("last_name"), **options
        )
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


class AjoutEmail(_Prive):
    @extend_schema(
        tags=TAG_COMPTE,
        summary="Ajouter ou changer mon e-mail",
        description="Envoie un lien de confirmation (24 h) ; l'e-mail ne compte qu'une fois confirmé sur le site.",
        request=s.EmailIn,
        responses={202: None},
    )
    def post(self, request):
        d = _valide(s.EmailIn, request)
        compte.demander_ajout_email(request.user, d["email"])
        return Response(status=202)


class NouvelleCleDeSecours(_Prive):
    @extend_schema(
        tags=TAG_COMPTE,
        summary="Régénérer ma clé de secours",
        request=s.MotDePasseIn,
        responses={200: s.CleDeSecoursOut},
    )
    def post(self, request):
        d = _valide(s.MotDePasseIn, request)
        return Response(
            {"recovery_key": compte.regenerer_cle_de_secours(request.user, d["password"])}
        )


class Preferences(_Prive):
    @extend_schema(
        tags=TAG_COMPTE, summary="Préférences de notification", responses={200: s.PreferencesSchema}
    )
    def get(self, request):
        return Response(compte.preferences(request.user))

    @extend_schema(
        tags=TAG_COMPTE,
        summary="Modifier les préférences de notification",
        request=s.PreferencesSchema,
        responses={200: s.PreferencesSchema},
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
