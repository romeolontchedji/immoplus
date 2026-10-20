"""Actions du personnel sur les comptes (appelées par l'administration ; toujours journalisées)."""

import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import GerantProfile, Role, Statut, StatutVerification, User
from apps.audit import services as audit
from apps.core.errors import ErreurMetier

from .. import signals
from . import appareils, identifiants, jetons

journal = logging.getLogger(__name__)


def creer_gerant(
    *,
    acteur: User,
    telephone: str,
    prenom: str,
    nom: str,
    zone: str,
    nom_affiche: str | None = None,
) -> User:
    """Crée un gérant sans mot de passe (ADR 0009) : il choisit nom d'utilisateur et mot de passe par le lien
    d'activation (`lien_activation`) que l'équipe lui transmet."""
    from . import inscription

    e164 = inscription.telephone_valide(telephone)
    prenom, nom = inscription.noms_valides(prenom, nom)
    with transaction.atomic():
        gerant = User(phone_e164=e164, role=Role.GERANT)
        gerant.definir_noms(prenom, nom)
        gerant.set_unusable_password()
        gerant.save()
        GerantProfile.complets.create(
            user=gerant,
            zone=zone.strip(),
            display_name=(nom_affiche or "").strip() or None,
            created_by=acteur,
        )
        audit.enregistrer("gerant.cree", acteur=acteur, cible=gerant)
    return gerant


def lien_activation(*, acteur: User, gerant: User) -> str:
    """Lien d'activation d'un gérant (72 h, usage unique), à transmettre par WhatsApp ou e-mail."""
    if gerant.role != Role.GERANT or gerant.has_usable_password():
        raise ErreurMetier("already_active", "Ce compte gérant est déjà activé.", statut=409)
    audit.enregistrer("gerant.lien_activation", acteur=acteur, cible=gerant)
    return f"{settings.SITE_URL}/activer/{identifiants.creer_jeton(gerant, 'activation')}"


def activer_gerant(
    jeton: str, *, nom_utilisateur: str, mot_de_passe: str, ip: str | None = None
) -> tuple[User, str]:
    """Le gérant choisit son nom d'utilisateur et son mot de passe ; retourne (compte, clé de secours)."""
    gerant, _ = identifiants.lire_jeton(jeton, "activation")
    if gerant.role != Role.GERANT or gerant.has_usable_password():
        raise ErreurMetier("link_invalid", "Ce lien n'est plus valable.", statut=400)
    gerant.username = identifiants.valider_nom_utilisateur(nom_utilisateur)
    from . import mots_de_passe

    mots_de_passe.valider(mot_de_passe, utilisateur=gerant)
    gerant.password = mots_de_passe.hacher(mot_de_passe)
    cle = identifiants.nouvelle_cle_de_secours(gerant)
    gerant.save(
        update_fields=[
            "username",
            "password",
            "recovery_key_hash",
            "recovery_key_created_at",
            "updated_at",
        ]
    )
    audit.enregistrer("gerant.active", acteur=gerant, cible=gerant, ip=ip)
    return gerant, cle


def lien_reinitialisation(*, acteur: User, cible: User) -> str:
    """Dernier recours du mot de passe oublié (ADR 0009) : lien de 24 h, après vérification de l'identité."""
    if cible.role not in (Role.CLIENT, Role.GERANT) or not cible.has_usable_password():
        raise ErreurMetier(
            "forbidden", "Seul un locataire ou un gérant activé peut recevoir ce lien.", statut=403
        )
    audit.enregistrer("auth.lien_reinitialisation_equipe", acteur=acteur, cible=cible)
    return f"{settings.SITE_URL}/mot-de-passe/nouveau/{identifiants.creer_jeton(cible, 'reinitialisation_equipe')}"


def definir_verification(*, acteur: User, profil: GerantProfile, statut: str) -> None:
    if statut not in StatutVerification.values:
        raise ErreurMetier(
            "validation_error",
            "Statut inconnu.",
            champs={"verification_status": ["Valeur inconnue"]},
        )
    profil.verification_status = statut
    if statut == StatutVerification.VERIFIED:
        profil.verified_at, profil.verified_by = timezone.now(), acteur
    else:
        profil.verified_at = profil.verified_by = None
    profil.save()
    audit.enregistrer(
        "gerant.verification", acteur=acteur, cible=profil.user, metadata={"statut": statut}
    )
    if statut == StatutVerification.VERIFIED:
        signals.gerant_verifie.send(sender=None, gerant_id=profil.pk)


def changer_statut(
    *, acteur: User, cible: User, statut: str, jusqu_a=None, motif: str = ""
) -> None:
    """Suspension, bannissement ou réactivation : coupe aussitôt les appareils de la personne sanctionnée."""
    if statut not in (Statut.ACTIVE, Statut.SUSPENDED, Statut.BANNED):
        raise ErreurMetier(
            "validation_error", "Statut non autorisé.", champs={"status": ["Valeur interdite"]}
        )
    if cible.role in (Role.MODERATOR, Role.ADMIN) and acteur.role != Role.ADMIN:
        raise ErreurMetier("forbidden", "Seul un administrateur modifie le personnel.", statut=403)
    if cible.pk == acteur.pk:
        raise ErreurMetier("forbidden", "Tu ne peux pas modifier ton propre statut.", statut=403)
    ancien = cible.status
    cible.status = statut
    cible.suspended_until = jusqu_a if statut == Statut.SUSPENDED else None
    if statut != Statut.ACTIVE:
        cible.token_version += 1
    cible.save()
    jetons.invalider_utilisateur(cible.pk)
    if statut != Statut.ACTIVE:
        appareils.revoquer_autres(cible, None, raison=f"statut_{statut}")
    audit.enregistrer(
        "compte.statut",
        acteur=acteur,
        cible=cible,
        metadata={
            "statut": statut,
            "jusqu_a": jusqu_a.isoformat() if jusqu_a else None,
            "motif": motif[:200],
        },
    )
    signals.statut_compte_change.send(sender=User, utilisateur=cible, ancien=ancien, nouveau=statut)


def changer_role(*, acteur: User, cible: User, role: str) -> None:
    """Seul un administrateur change un rôle. Un compte ne change jamais son propre rôle."""
    if acteur.role != Role.ADMIN:
        raise ErreurMetier("forbidden", "Réservé aux administrateurs.", statut=403)
    if cible.pk == acteur.pk:
        raise ErreurMetier("forbidden", "Tu ne peux pas modifier ton propre rôle.", statut=403)
    if role not in Role.values:
        raise ErreurMetier(
            "validation_error", "Rôle inconnu.", champs={"role": ["Valeur inconnue"]}
        )
    ancien = cible.role
    cible.role = role
    cible.token_version += 1
    cible.save()
    jetons.invalider_utilisateur(cible.pk)
    appareils.revoquer_autres(cible, None, raison="role_change")
    audit.enregistrer(
        "compte.role", acteur=acteur, cible=cible, metadata={"ancien": ancien, "nouveau": role}
    )


def lever_suspension_echue(cible: User) -> bool:
    """Fin de suspension : le compte redevient actif, sans acteur humain (tâche planifiée)."""
    if (
        cible.status != Statut.SUSPENDED
        or cible.suspended_until is None
        or cible.suspended_until > timezone.now()
    ):
        return False
    cible.status, cible.suspended_until = Statut.ACTIVE, None
    cible.save()
    audit.enregistrer("compte.suspension_levee", cible=cible, metadata={"automatique": True})
    signals.statut_compte_change.send(
        sender=User, utilisateur=cible, ancien=Statut.SUSPENDED, nouveau=Statut.ACTIVE
    )
    return True


def maj_indicateurs_gerants(indicateurs: dict) -> int:
    """Écrit le taux et le délai de réponse calculés chaque nuit : {identifiant du gérant: (taux %, délai en minutes)}."""
    total = 0
    for gerant_id, (taux, delai) in indicateurs.items():
        total += GerantProfile.objects.filter(pk=gerant_id).update(
            response_rate_30d=taux, median_response_min=delai
        )
    return total
