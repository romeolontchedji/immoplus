"""Actions du personnel sur les comptes (appelées par l'administration ; toujours journalisées)."""

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import GerantProfile, Role, Statut, StatutVerification, User
from apps.accounts.phone import NumeroInvalide, normaliser
from apps.audit import services as audit
from apps.core import parametres
from apps.core.errors import ErreurMetier

from .. import signals
from . import appareils, jetons


def creer_gerant(
    *, acteur: User, telephone: str, nom: str, zone: str, nom_affiche: str | None = None
) -> User:
    """Crée un compte gérant sans mot de passe utilisable : le gérant l'active par OTP (EF-AUT-09)."""
    try:
        e164 = normaliser(telephone, tuple(parametres.lire("OTP_ALLOWED_COUNTRIES")))
    except NumeroInvalide as erreur:
        raise ErreurMetier(
            "validation_error", "Numéro invalide.", champs={"phone": [str(erreur)]}
        ) from erreur
    if User.objects.filter(phone_e164=e164).exists():
        raise ErreurMetier("phone_already_registered", "Ce numéro a déjà un compte.", statut=409)
    with transaction.atomic():
        gerant = User(phone_e164=e164, full_name=" ".join(nom.split()), role=Role.GERANT)
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


def purger_otp(jours: int = 7) -> int:
    """Supprime les codes à usage unique expirés depuis plus de `jours` jours."""
    from apps.accounts.models import OtpCode

    limite = timezone.now() - timezone.timedelta(days=jours)
    return OtpCode.objects.filter(expires_at__lt=limite).delete()[0]
