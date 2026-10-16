"""Inscription du locataire, mot de passe oublié (CDC EF-AUT-01, 06, 10)."""

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import Role, User
from apps.audit import services as audit
from apps.core import parametres
from apps.core.errors import ErreurMetier

from . import appareils, jetons, mots_de_passe, otp


def _nom_valide(nom: str) -> str:
    nom = " ".join((nom or "").split())
    if not 2 <= len(nom) <= 120:
        raise ErreurMetier(
            "validation_error",
            "Indique ton nom complet (2 à 120 caractères).",
            champs={"full_name": ["Nom invalide"]},
        )
    return nom


def _exiger_cgu(acceptees: bool) -> None:
    if acceptees is not True:
        raise ErreurMetier(
            "terms_not_accepted",
            "Accepte les conditions d'utilisation pour continuer.",
            champs={"terms_accepted": ["Obligatoire"]},
        )


def _accepter_cgu(utilisateur: User, ip: str | None, user_agent: str | None) -> None:
    version = str(parametres.lire("TERMS_VERSION"))
    utilisateur.terms_version = version
    utilisateur.terms_accepted_at = timezone.now()
    audit.enregistrer(
        "terms.accepted",
        acteur=utilisateur,
        cible=utilisateur,
        metadata={"version": version},
        ip=ip,
        user_agent=user_agent,
    )


def inscrire_client(
    jeton_otp: str,
    nom: str,
    mot_de_passe: str,
    cgu_acceptees: bool,
    *,
    ip: str | None = None,
    user_agent: str | None = None,
) -> User:
    """Second temps de l'inscription : le compte n'existe qu'ici, après preuve de possession du numéro."""
    nom = _nom_valide(nom)
    _exiger_cgu(cgu_acceptees)
    mots_de_passe.valider(mot_de_passe)
    telephone = otp.consommer_jeton(jeton_otp, "signup")
    try:
        with transaction.atomic():
            utilisateur = User(
                phone_e164=telephone,
                full_name=nom,
                role=Role.CLIENT,
                phone_verified_at=timezone.now(),
                password=mots_de_passe.hacher(mot_de_passe),
            )
            _accepter_cgu(utilisateur, ip, user_agent)
            utilisateur.save()
    except IntegrityError as erreur:
        # L'existence du compte n'est révélée qu'ici : le numéro a été prouvé par OTP (CDC §5.3).
        raise ErreurMetier(
            "phone_already_registered",
            "Un compte existe déjà avec ce numéro. Connecte-toi ou réinitialise ton mot de passe.",
            statut=409,
        ) from erreur
    audit.enregistrer(
        "auth.inscription", acteur=utilisateur, cible=utilisateur, ip=ip, user_agent=user_agent
    )
    return utilisateur


def reinitialiser_mot_de_passe(
    jeton_otp: str, nouveau: str, *, ip: str | None = None, user_agent: str | None = None
) -> User:
    """Nouveau mot de passe après OTP ; tous les appareils et toutes les sessions sont révoqués (EF-AUT-06)."""
    mots_de_passe.valider(nouveau)
    telephone = otp.consommer_jeton(jeton_otp, "reset_password")
    with transaction.atomic():
        utilisateur = (
            User.objects.select_for_update()
            .filter(
                phone_e164=telephone, role__in=(Role.CLIENT, Role.GERANT), deleted_at__isnull=True
            )
            .first()
        )
        if utilisateur is None or not utilisateur.has_usable_password():
            raise ErreurMetier("not_found", "Compte introuvable.", statut=404)
        utilisateur.password = mots_de_passe.hacher(nouveau)  # invalide aussi les sessions du site
        utilisateur.token_version += 1
        utilisateur.save()
    jetons.invalider_utilisateur(utilisateur.pk)
    appareils.revoquer_autres(utilisateur, None, raison="mot_de_passe_reinitialise")
    audit.enregistrer(
        "auth.mot_de_passe_reinitialise",
        acteur=utilisateur,
        cible=utilisateur,
        ip=ip,
        user_agent=user_agent,
    )
    return utilisateur
