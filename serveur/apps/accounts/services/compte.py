"""Gestion du compte connecté : mot de passe, numéro, profil, suppression (CDC EF-AUT-12, 13, EF-PRO)."""

import uuid

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts import signals, tasks
from apps.accounts.models import OtpCode, Role, Statut, User
from apps.accounts.phone import masquer
from apps.audit import services as audit
from apps.core.errors import ErreurMetier

from . import appareils, inscription, jetons, mots_de_passe, otp

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
    mots_de_passe.valider(nouveau, champ="new_password")
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


def changer_numero(
    utilisateur: User, mot_de_passe: str, jeton_otp: str, appareil_courant_id=None
) -> User:
    """Mot de passe actuel + OTP du nouveau numéro ; autres appareils révoqués, ancien numéro prévenu (EF-AUT-12)."""
    _exiger_mot_de_passe(utilisateur, mot_de_passe)
    nouveau = otp.consommer_jeton(jeton_otp, "change_phone")
    ancien = utilisateur.phone_e164
    try:
        with transaction.atomic():
            utilisateur.phone_e164 = nouveau
            utilisateur.phone_verified_at = timezone.now()
            utilisateur.save(update_fields=["phone_e164", "phone_verified_at", "updated_at"])
    except IntegrityError as erreur:
        utilisateur.phone_e164 = ancien
        raise ErreurMetier(
            "phone_already_registered",
            "Ce numéro est déjà utilisé par un autre compte.",
            statut=409,
        ) from erreur
    appareils.revoquer_autres(utilisateur, appareil_courant_id, raison="numero_change")
    audit.enregistrer(
        "auth.numero_change",
        acteur=utilisateur,
        cible=utilisateur,
        metadata={"ancien": masquer(ancien), "nouveau": masquer(nouveau)},
    )
    transaction.on_commit(
        lambda: tasks.envoyer_sms.delay(
            ancien,
            "Logeo : le numéro de ton compte vient d'être modifié. Si ce n'est pas toi, contacte le support.",
        )
    )
    return utilisateur


_NON_FOURNI = object()


def modifier_profil(utilisateur: User, *, nom: str | None = None, occupation=_NON_FOURNI) -> User:
    """`occupation` absent : inchangé ; `None` ou vide : effacé (la réponse reste facultative)."""
    champs = ["updated_at"]
    if nom is not None:
        nom = " ".join(nom.split())
        if not 2 <= len(nom) <= 120:
            raise ErreurMetier(
                "validation_error",
                "Nom invalide (2 à 120 caractères).",
                champs={"full_name": ["Nom invalide"]},
            )
        utilisateur.full_name = nom
        champs.append("full_name")
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
    ancien_numero, role, uid = utilisateur.phone_e164, utilisateur.role, utilisateur.pk
    with transaction.atomic():
        utilisateur.phone_e164 = f"del:{uuid.uuid4().hex[:12]}"
        utilisateur.full_name = "Compte supprimé"
        utilisateur.avatar_path = None
        utilisateur.status = Statut.DELETED
        utilisateur.deleted_at = timezone.now()
        utilisateur.notif_prefs = {}
        utilisateur.token_version += 1
        utilisateur.set_unusable_password()
        # Colonnes nommées : le rôle `app` ne peut pas modifier `email` ni `role` (seul le personnel a un e-mail).
        utilisateur.save(
            update_fields=[
                "phone_e164", "full_name", "avatar_path", "status", "deleted_at", "notif_prefs",
                "token_version", "password", "updated_at",
            ]
        )  # fmt: skip
        OtpCode.objects.filter(phone_e164=ancien_numero).update(phone_e164="")
        appareils_a_revoquer = list(utilisateur.devices.all())
        for appareil in appareils_a_revoquer:
            jetons.marquer_appareil_revoque(appareil.pk)
        utilisateur.devices.all().delete()
        audit.enregistrer(
            "compte.supprime", acteur=utilisateur, cible=utilisateur, metadata={"role": role}
        )
    jetons.invalider_utilisateur(uid)
    signals.compte_supprime.send(sender=User, utilisateur_id=uid, role=role)
