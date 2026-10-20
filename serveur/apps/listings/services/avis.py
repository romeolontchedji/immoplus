"""Avis des locataires sur les chambres (plan d'actions v3, G).

Règles :
- seul un locataire qui a vraiment échangé avec le gérant de la chambre (le gérant a répondu) peut donner un avis ;
- un avis par locataire et par chambre : le redonner le modifie ;
- note de 1 à 5, commentaire facultatif (600 caractères), sans coordonnées ;
- publié tout de suite ; la modération peut le masquer, l'auteur peut le retirer.
"""

from django.db import transaction

from apps.audit import services as audit
from apps.core.errors import ErreurMetier
from apps.notifications import services as notifications

from ..enums import StatutAnnonce
from ..models import Listing, Review
from . import contenu

COMMENTAIRE_MAX = 600
STATUTS_AVIS = (StatutAnnonce.PUBLISHED, StatutAnnonce.RENTED, StatutAnnonce.HIDDEN)


def _annonce(annonce_id) -> Listing:
    try:
        return Listing.objects.get(pk=annonce_id, status__in=STATUTS_AVIS, deleted_at__isnull=True)
    except (Listing.DoesNotExist, ValueError, TypeError, Exception) as erreur:
        raise ErreurMetier("not_found", "Annonce introuvable.", statut=404) from erreur


def peut_donner(utilisateur, annonce_id) -> bool:
    """Locataire qui a échangé avec le gérant de cette chambre (le gérant a répondu au moins une fois)."""
    from apps.chat import selectors as messagerie

    if utilisateur is None or getattr(utilisateur, "role", None) != "client":
        return False
    return messagerie.a_echange_avec_le_gerant(utilisateur.pk, annonce_id)


@transaction.atomic
def donner(utilisateur, annonce_id, note, commentaire: str = "") -> Review:
    annonce = _annonce(annonce_id)
    if not peut_donner(utilisateur, annonce.pk):
        raise ErreurMetier(
            "review_not_allowed",
            "Tu pourras donner ton avis après avoir échangé avec le gérant de cette chambre.",
            statut=403,
        )
    if not isinstance(note, int) or isinstance(note, bool) or not 1 <= note <= 5:
        raise ErreurMetier(
            "validation_error", "La note va de 1 à 5.", champs={"rating": ["Entre 1 et 5"]}
        )
    texte = " ".join((commentaire or "").split())
    if len(texte) > COMMENTAIRE_MAX:
        raise ErreurMetier(
            "validation_error",
            f"Ton commentaire est trop long ({COMMENTAIRE_MAX} caractères au plus).",
            champs={"comment": ["Trop long"]},
        )
    contenu.refuser_si_coordonnees(comment=texte)
    avis, cree = Review.objects.update_or_create(
        listing=annonce, author_id=utilisateur.pk, defaults={"rating": note, "comment": texte}
    )
    audit.enregistrer(
        "listing.avis_donne" if cree else "listing.avis_modifie",
        acteur=utilisateur, cible=annonce, metadata={"note": note},
    )  # fmt: skip
    if cree:
        transaction.on_commit(lambda: _prevenir_gerant(annonce, note))
    return avis


def _prevenir_gerant(annonce: Listing, note: int) -> None:
    notifications.creer(
        annonce.gerant_id,
        "listing.review",
        "Nouvel avis sur ta chambre",
        f"« {annonce.title[:60]} » a reçu une note de {note}/5.",
        data={"listing_id": str(annonce.pk), "slug": annonce.slug},
    )


@transaction.atomic
def retirer(utilisateur, annonce_id) -> None:
    """L'auteur retire son avis."""
    supprimes, _ = Review.objects.filter(listing_id=annonce_id, author_id=utilisateur.pk).delete()
    if not supprimes:
        raise ErreurMetier("not_found", "Aucun avis à retirer.", statut=404)
    audit.enregistrer(
        "listing.avis_retire", acteur=utilisateur, metadata={"annonce": str(annonce_id)}
    )


@transaction.atomic
def masquer(avis_id, *, acteur, raison: str = "") -> None:
    """Modération : l'avis disparaît du public (il reste lisible dans l'administration)."""
    mis_a_jour = Review.objects.filter(pk=avis_id).update(
        is_hidden=True, hidden_reason=raison[:200]
    )
    if not mis_a_jour:
        raise ErreurMetier("not_found", "Avis introuvable.", statut=404)
    audit.enregistrer("moderation.avis_masque", acteur=acteur, metadata={"avis": str(avis_id)})


@transaction.atomic
def reafficher(avis_id, *, acteur) -> None:
    Review.objects.filter(pk=avis_id).update(is_hidden=False, hidden_reason="")
    audit.enregistrer("moderation.avis_reaffiche", acteur=acteur, metadata={"avis": str(avis_id)})
