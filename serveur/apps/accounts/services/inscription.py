"""Inscription du locataire et mot de passe oublié, sans code SMS (ADR 0009, CDC EF-AUT-01, 06, 10).

Mot de passe oublié, dans l'ordre où l'interface les propose : lien par e-mail confirmé, clé de secours, puis
lien généré par l'équipe (`administration.lien_reinitialisation`).
"""

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import ROLES_CLIENTELE, Occupation, Role, User
from apps.accounts.phone import NumeroInvalide, normaliser
from apps.audit import services as audit
from apps.core import parametres
from apps.core.errors import ErreurMetier

from . import appareils, identifiants, jetons, mots_de_passe, verrouillage


def _nom_valide(valeur: str, champ: str, libelle: str) -> str:
    valeur = " ".join((valeur or "").split())
    if not 1 <= len(valeur) <= 60:
        raise ErreurMetier(
            "validation_error",
            f"Indique ton {libelle} (60 caractères au plus).",
            champs={champ: ["Obligatoire"]},
        )
    return valeur


def noms_valides(prenom: str, nom: str) -> tuple[str, str]:
    return _nom_valide(prenom, "first_name", "prénom"), _nom_valide(nom, "last_name", "nom")


def telephone_valide(saisie: str) -> str:
    """Numéro conservé mais ni vérifié ni unique (ADR 0009) : seul son format est contrôlé."""
    try:
        return normaliser(saisie, tuple(parametres.lire("OTP_ALLOWED_COUNTRIES")))
    except NumeroInvalide as erreur:
        raise ErreurMetier(
            "validation_error", "Numéro de téléphone invalide.", champs={"phone": [str(erreur)]}
        ) from erreur


def occupation_valide(occupation: str | None) -> str | None:
    """« Tu es » est facultatif ; une valeur inconnue est refusée plutôt qu'ignorée."""
    if occupation in (None, ""):
        return None
    if occupation not in Occupation.values:
        raise ErreurMetier(
            "validation_error",
            "Choisis une des réponses proposées.",
            champs={"occupation": ["Valeur inconnue"]},
        )
    return occupation


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
    *,
    nom_utilisateur: str,
    prenom: str,
    nom: str,
    telephone: str,
    mot_de_passe: str,
    cgu_acceptees: bool,
    occupation: str | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
) -> tuple[User, str]:
    """Crée le compte tout de suite (aucun code) et retourne (compte, clé de secours à afficher une seule fois)."""
    prenom, nom = noms_valides(prenom, nom)
    nom_utilisateur = identifiants.valider_nom_utilisateur(nom_utilisateur)
    e164 = telephone_valide(telephone)
    occupation = occupation_valide(occupation)
    _exiger_cgu(cgu_acceptees)
    utilisateur = User(
        username=nom_utilisateur, phone_e164=e164, occupation=occupation, role=Role.CLIENT
    )
    utilisateur.definir_noms(prenom, nom)
    mots_de_passe.valider(mot_de_passe, utilisateur=utilisateur)
    utilisateur.password = mots_de_passe.hacher(mot_de_passe)
    cle = identifiants.nouvelle_cle_de_secours(utilisateur)
    try:
        with transaction.atomic():
            _accepter_cgu(utilisateur, ip, user_agent)
            utilisateur.save()
    except IntegrityError as erreur:  # nom pris entre la vérification et l'enregistrement
        raise ErreurMetier(
            "username_taken", "Ce nom d'utilisateur est déjà pris.", statut=409,
            champs={"username": ["Déjà pris"]},
        ) from erreur  # fmt: skip
    audit.enregistrer(
        "auth.inscription", acteur=utilisateur, cible=utilisateur, ip=ip, user_agent=user_agent
    )
    return utilisateur, cle


# --------------------------------------------------------------------------- mot de passe oublié
def _nouveau_mot_de_passe(
    utilisateur: User, nouveau: str, *, porte: str, ip: str | None, user_agent: str | None
) -> None:
    """Change le mot de passe, coupe toutes les sessions et tous les appareils (EF-AUT-06), journalise la porte."""
    mots_de_passe.valider(nouveau, utilisateur=utilisateur)
    utilisateur.password = mots_de_passe.hacher(nouveau)  # invalide aussi les sessions du site
    utilisateur.token_version += 1
    # Colonnes nommées : le rôle `app` n'a le droit de modifier que certaines colonnes de `users`.
    champs = ["password", "token_version", "updated_at"]
    if utilisateur.recovery_key_hash is not None:
        champs += ["recovery_key_hash", "recovery_key_created_at"]
    utilisateur.save(update_fields=champs)
    jetons.invalider_utilisateur(utilisateur.pk)
    appareils.revoquer_autres(utilisateur, None, raison="mot_de_passe_reinitialise")
    audit.enregistrer(
        "auth.mot_de_passe_reinitialise", acteur=utilisateur, cible=utilisateur,
        metadata={"porte": porte}, ip=ip, user_agent=user_agent,
    )  # fmt: skip


def _compte_par_nom(nom_utilisateur: str) -> User | None:
    return User.objects.filter(
        username=identifiants.normaliser_nom_utilisateur(nom_utilisateur),
        role__in=ROLES_CLIENTELE, deleted_at__isnull=True,
    ).first()  # fmt: skip


def reinitialiser_par_cle(
    nom_utilisateur: str, cle: str, nouveau: str, *, client: str,
    ip: str | None = None, user_agent: str | None = None,
) -> tuple[User, str]:  # fmt: skip
    """Clé de secours correcte : nouveau mot de passe et nouvelle clé (l'ancienne ne sert qu'une fois).

    Verrouillage progressif par (nom, appareil ou adresse IP), comme la connexion : refus uniforme qui ne dit
    jamais si le nom existe.
    """
    compteur = "cle:" + identifiants.normaliser_nom_utilisateur(nom_utilisateur)
    verrouillage.controler(compteur, client)
    utilisateur = _compte_par_nom(nom_utilisateur)
    if not identifiants.cle_correcte(utilisateur, cle) or utilisateur is None:
        verrouillage.enregistrer_echec(compteur, client)
        raise ErreurMetier(
            "invalid_recovery_key", "Nom d'utilisateur ou clé de secours incorrects.", statut=401
        )
    verrouillage.enregistrer_succes(compteur, client)
    nouvelle_cle = identifiants.nouvelle_cle_de_secours(utilisateur)
    with transaction.atomic():
        _nouveau_mot_de_passe(
            utilisateur, nouveau, porte="cle_de_secours", ip=ip, user_agent=user_agent
        )
    return utilisateur, nouvelle_cle


def demander_lien_par_email(identifiant: str, *, ip: str | None = None) -> None:
    """Envoie un lien de réinitialisation si le nom d'utilisateur ou l'e-mail désigne un compte à e-mail confirmé.

    La réponse est toujours la même, que le compte existe ou non (rien ne se devine).
    """
    from apps.core.tasks import envoyer_courriel

    saisie = (identifiant or "").strip()
    requete = User.objects.filter(
        role__in=ROLES_CLIENTELE, deleted_at__isnull=True, email_verified_at__isnull=False
    )
    utilisateur = (
        requete.filter(email__iexact=saisie).first()
        if "@" in saisie
        else requete.filter(username=identifiants.normaliser_nom_utilisateur(saisie)).first()
    )
    if utilisateur is None or not utilisateur.email:
        return
    lien = f"{settings.SITE_URL}/mot-de-passe/nouveau/{identifiants.creer_jeton(utilisateur, 'reinitialisation')}"
    envoyer_courriel.delay(
        [utilisateur.email],
        "Immo+ · choisis un nouveau mot de passe",
        f"Bonjour {utilisateur.first_name or utilisateur.username},\n\n"
        f"Pour choisir un nouveau mot de passe pour le compte « {utilisateur.username} », ouvre ce lien :\n"
        f"{lien}\n\nIl est valable 30 minutes et ne sert qu'une fois.\n"
        "Si tu n'as rien demandé, ignore ce courriel : ton mot de passe ne change pas.\n",
    )
    audit.enregistrer("auth.lien_reinitialisation_envoye", cible=utilisateur, ip=ip)


def reinitialiser_par_lien(
    jeton: str, nouveau: str, *, ip: str | None = None, user_agent: str | None = None
) -> User:
    """Lien reçu par e-mail ou transmis par l'équipe : un seul usage (il change le mot de passe qu'il signe)."""
    try:
        utilisateur, _ = identifiants.lire_jeton(jeton, "reinitialisation")
        porte = "email"
    except ErreurMetier:
        utilisateur, _ = identifiants.lire_jeton(jeton, "reinitialisation_equipe")
        porte = "equipe"
    if utilisateur.role not in ROLES_CLIENTELE:
        raise ErreurMetier("link_invalid", "Ce lien n'est plus valable.", statut=400)
    with transaction.atomic():
        _nouveau_mot_de_passe(utilisateur, nouveau, porte=porte, ip=ip, user_agent=user_agent)
    return utilisateur
