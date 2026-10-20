"""Gestion du compte connecté : mot de passe, numéro, e-mail, clé de secours, profil, suppression (ADR 0009)."""

import uuid

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts import signals
from apps.accounts.models import Role, Statut, User
from apps.accounts.phone import masquer
from apps.audit import services as audit
from apps.core.errors import ErreurMetier

from . import appareils, identifiants, inscription, jetons, mots_de_passe

CATEGORIES_NOTIFICATION = ("messages", "alertes", "rappels")


def _exiger_mot_de_passe(utilisateur: User, mot_de_passe: str) -> None:
    if not mots_de_passe.verifier(utilisateur, mot_de_passe or ""):
        raise ErreurMetier(
            "invalid_password",
            "Le mot de passe actuel est incorrect.",
            statut=400,
            champs={"current_password": ["Incorrect"]},
        )


def changer_mot_de_passe(
    utilisateur: User, ancien: str, nouveau: str, appareil_courant_id=None
) -> None:
    """Change le mot de passe (l'ancien est requis) et déconnecte les autres appareils."""
    _exiger_mot_de_passe(utilisateur, ancien)
    mots_de_passe.valider(nouveau, champ="new_password", utilisateur=utilisateur)
    utilisateur.password = mots_de_passe.hacher(nouveau)
    utilisateur.save(update_fields=["password", "updated_at"])
    appareils.revoquer_autres(utilisateur, appareil_courant_id, raison="mot_de_passe_change")
    audit.enregistrer("auth.mot_de_passe_change", acteur=utilisateur, cible=utilisateur)


def deconnecter_partout(utilisateur: User) -> int:
    """Déconnecte tous les appareils et toutes les sessions du site (nouvelle version de sécurité).

    L'appelant qui veut garder sa propre session web la remet à la nouvelle version (`session["tv"]`).
    Retourne le nombre d'appareils de l'application déconnectés.
    """
    with transaction.atomic():
        utilisateur.token_version += 1
        utilisateur.save(update_fields=["token_version", "updated_at"])
    jetons.invalider_utilisateur(utilisateur.pk)
    nombre = appareils.revoquer_autres(utilisateur, None, raison="deconnexion_partout")
    audit.enregistrer(
        "auth.deconnexion_partout",
        acteur=utilisateur,
        cible=utilisateur,
        metadata={"appareils": nombre},
    )
    return nombre


def changer_numero(utilisateur: User, mot_de_passe: str, telephone: str) -> User:
    """Nouveau numéro, sans code (ADR 0009) : le mot de passe actuel suffit ; le changement est journalisé."""
    _exiger_mot_de_passe(utilisateur, mot_de_passe)
    nouveau = inscription.telephone_valide(telephone)
    ancien = utilisateur.phone_e164
    utilisateur.phone_e164 = nouveau
    utilisateur.save(update_fields=["phone_e164", "updated_at"])
    audit.enregistrer(
        "auth.numero_change", acteur=utilisateur, cible=utilisateur,
        metadata={"ancien": masquer(ancien), "nouveau": masquer(nouveau)},
    )  # fmt: skip
    return utilisateur


def demander_ajout_email(utilisateur: User, email: str) -> None:
    """Envoie un lien de confirmation : l'e-mail n'est enregistré qu'une fois le lien ouvert (24 h)."""
    from django.core.exceptions import ValidationError
    from django.core.validators import validate_email

    from apps.core.tasks import envoyer_courriel

    adresse = (email or "").strip().lower()
    try:
        validate_email(adresse)
    except ValidationError as erreur:
        raise ErreurMetier(
            "validation_error", "Adresse e-mail invalide.", champs={"email": ["Invalide"]}
        ) from erreur
    if User.objects.filter(email__iexact=adresse).exclude(pk=utilisateur.pk).exists():
        raise ErreurMetier(
            "email_taken", "Cette adresse est déjà liée à un autre compte.", statut=409,
            champs={"email": ["Déjà utilisée"]},
        )  # fmt: skip
    jeton = identifiants.creer_jeton(utilisateur, "email", a=adresse)
    envoyer_courriel.delay(
        [adresse],
        "Immo+ · confirme ton adresse e-mail",
        f"Bonjour {utilisateur.first_name or utilisateur.username},\n\n"
        f"Pour lier cette adresse au compte « {utilisateur.username} », ouvre ce lien :\n"
        f"{settings.SITE_URL}/compte/email/confirmer/{jeton}\n\n"
        "Il est valable 24 heures. Avec un e-mail confirmé, tu peux retrouver l'accès à ton compte si tu "
        "oublies ton mot de passe.\n",
    )
    audit.enregistrer("compte.email_demande", acteur=utilisateur, cible=utilisateur)


def confirmer_email(jeton: str) -> User:
    utilisateur, donnees = identifiants.lire_jeton(jeton, "email")
    utilisateur.email, utilisateur.email_verified_at = donnees["a"], timezone.now()
    try:
        utilisateur.save(update_fields=["email", "email_verified_at", "updated_at"])
    except IntegrityError as erreur:
        raise ErreurMetier(
            "email_taken", "Cette adresse est déjà liée à un autre compte.", statut=409
        ) from erreur
    audit.enregistrer("compte.email_confirme", acteur=utilisateur, cible=utilisateur)
    return utilisateur


def regenerer_cle_de_secours(utilisateur: User, mot_de_passe: str) -> str:
    """Nouvelle clé de secours (l'ancienne cesse de valoir) ; affichée une seule fois."""
    _exiger_mot_de_passe(utilisateur, mot_de_passe)
    cle = identifiants.nouvelle_cle_de_secours(utilisateur)
    utilisateur.save(update_fields=["recovery_key_hash", "recovery_key_created_at", "updated_at"])
    audit.enregistrer("compte.cle_de_secours_regeneree", acteur=utilisateur, cible=utilisateur)
    return cle


_NON_FOURNI = object()


def modifier_profil(
    utilisateur: User, *, prenom: str | None = None, nom: str | None = None, occupation=_NON_FOURNI
) -> User:
    """Prénom et nom ensemble ou séparément ; `occupation` absent : inchangé, vide : effacé (facultative)."""
    champs = ["updated_at"]
    if prenom is not None or nom is not None:
        prenom, nom = inscription.noms_valides(
            utilisateur.first_name if prenom is None else prenom,
            utilisateur.last_name if nom is None else nom,
        )
        utilisateur.definir_noms(prenom, nom)
        champs += ["first_name", "last_name", "full_name"]
    if occupation is not _NON_FOURNI:
        utilisateur.occupation = inscription.occupation_valide(occupation)
        champs.append("occupation")
    utilisateur.save(update_fields=champs)
    return utilisateur


def preferences(utilisateur: User) -> dict:
    return utilisateur.notif_prefs or {}


def definir_preferences(utilisateur: User, valeurs: dict) -> dict:
    """Préférences par catégorie ({push, apercu}) ; les notifications de sécurité ne se coupent pas (EF-PRO-02)."""
    if not isinstance(valeurs, dict):
        raise ErreurMetier(
            "validation_error", "Préférences invalides.", champs={"preferences": ["Objet attendu"]}
        )
    propres: dict = {}
    for categorie, reglage in valeurs.items():
        if categorie in ("securite", "sanction"):
            raise ErreurMetier(
                "validation_error",
                "Les notifications de sécurité et de sanction ne peuvent pas être désactivées.",
                champs={categorie: ["Non modifiable"]},
            )
        if categorie not in CATEGORIES_NOTIFICATION and categorie != "silence":
            raise ErreurMetier(
                "validation_error", "Catégorie inconnue.", champs={categorie: ["Inconnue"]}
            )
        if categorie == "silence":
            if not isinstance(reglage, list) or not all(
                isinstance(x, str) and len(x) <= 64 for x in reglage
            ):
                raise ErreurMetier(
                    "validation_error",
                    "Liste de conversations invalide.",
                    champs={"silence": ["Liste attendue"]},
                )
            propres["silence"] = reglage[:200]
        else:
            if (
                not isinstance(reglage, dict)
                or set(reglage) - {"push", "apercu"}
                or not all(isinstance(v, bool) for v in reglage.values())
            ):
                raise ErreurMetier(
                    "validation_error",
                    "Réglage invalide.",
                    champs={categorie: ["{push, apercu} booléens attendus"]},
                )
            propres[categorie] = reglage
    utilisateur.notif_prefs = {**preferences(utilisateur), **propres}
    utilisateur.save(update_fields=["notif_prefs", "updated_at"])
    return utilisateur.notif_prefs


def supprimer(utilisateur: User, mot_de_passe: str) -> None:
    """Supprime le compte à la demande (application et site) : anonymisation, appareils supprimés (CDC §9.23)."""
    if utilisateur.role not in (Role.CLIENT, Role.GERANT):
        raise ErreurMetier("forbidden", "Ce compte ne peut pas être supprimé ici.", statut=403)
    _exiger_mot_de_passe(utilisateur, mot_de_passe)
    role, uid = utilisateur.role, utilisateur.pk
    with transaction.atomic():
        utilisateur.phone_e164 = f"del:{uuid.uuid4().hex[:12]}"
        # Le nom d'utilisateur est libéré pour un autre (format valide, unique, sans rien d'identifiant).
        utilisateur.username = f"supprime.{uuid.uuid4().hex[:12]}"
        utilisateur.definir_noms("Compte", "supprimé")
        utilisateur.email, utilisateur.email_verified_at = None, None
        utilisateur.recovery_key_hash, utilisateur.recovery_key_created_at = None, None
        utilisateur.avatar_path = None
        utilisateur.status = Statut.DELETED
        utilisateur.deleted_at = timezone.now()
        utilisateur.notif_prefs = {}
        utilisateur.token_version += 1
        utilisateur.set_unusable_password()
        # Colonnes nommées : le rôle `app` ne peut modifier que certaines colonnes (jamais `role`).
        utilisateur.save(
            update_fields=[
                "phone_e164", "username", "first_name", "last_name", "full_name", "email", "email_verified_at",
                "recovery_key_hash", "recovery_key_created_at", "avatar_path", "status", "deleted_at",
                "notif_prefs", "token_version", "password", "updated_at",
            ]
        )  # fmt: skip
        appareils_a_revoquer = list(utilisateur.devices.all())
        for appareil in appareils_a_revoquer:
            jetons.marquer_appareil_revoque(appareil.pk)
        utilisateur.devices.all().delete()
        audit.enregistrer(
            "compte.supprime", acteur=utilisateur, cible=utilisateur, metadata={"role": role}
        )
    jetons.invalider_utilisateur(uid)
    signals.compte_supprime.send(sender=User, utilisateur_id=uid, role=role)
