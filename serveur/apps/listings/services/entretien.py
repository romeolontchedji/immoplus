"""Tâches d'entretien des annonces : fraîcheur, vidéos des annonces louées, archivage (CDC §7.3, §11.1)."""

import logging
from datetime import timedelta

from django.utils import timezone

from apps.core import parametres
from apps.media import stockage
from apps.notifications import services as notifications

from ..enums import StatutAnnonce, StatutMedia, TypeMedia
from ..models import Listing, ListingMedia
from . import annonces

journal = logging.getLogger(__name__)


def relances_de_fraicheur() -> dict:
    """Annonce non confirmée : relance à J+7 et J+10, masquage « sans confirmation » à J+14 (EF-ANN-12)."""
    maintenant = timezone.now()
    jours_relance = sorted(int(j) for j in parametres.lire("STALE_REMINDER_DAYS"))
    jour_masquage = int(parametres.lire("STALE_HIDE_DAYS"))
    bilan = {"relances": 0, "masquees": 0}
    for annonce in Listing.objects.filter(status=StatutAnnonce.PUBLISHED, deleted_at__isnull=True):
        reference = annonce.last_confirmed_at or annonce.published_at or annonce.created_at
        age = (maintenant - reference).days
        if age >= jour_masquage:
            annonces.changer_statut(annonce, StatutAnnonce.HIDDEN, acteur=None, raison="stale")
            bilan["masquees"] += 1
            continue
        etape = sum(1 for j in jours_relance if age >= j)
        if etape > annonce.reminder_stage:
            Listing.objects.filter(pk=annonce.pk).update(reminder_stage=etape)
            reste = jour_masquage - age
            notifications.creer(
                annonce.gerant_id,
                "listing.reminder",
                "Cette chambre est-elle toujours disponible ?",
                f"Confirme « {annonce.title} » : sans réponse, elle sera masquée dans {reste} jour(s).",
                data={"listing_id": str(annonce.pk), "slug": annonce.slug, "stage": etape},
                dedupe_key=f"reminder:{annonce.pk}:{etape}:{reference.date().isoformat()}",
            )
            bilan["relances"] += 1
    return bilan


def purger_medias() -> dict:
    """Vidéos des annonces louées supprimées à J+7 ; originaux supprimés 24 h après le traitement (EF-REC-10)."""
    maintenant = timezone.now()
    bilan = {"videos": 0, "originaux": 0}
    for media in ListingMedia.objects.filter(
        kind=TypeMedia.VIDEO, delete_after__lte=maintenant, deleted_at__isnull=True
    ):
        stockage.supprimer_derives(media.listing_id, media.pk)
        ListingMedia.objects.filter(pk=media.pk).update(
            deleted_at=maintenant, updated_at=maintenant
        )
        bilan["videos"] += 1
    for media in ListingMedia.objects.filter(
        status=StatutMedia.READY,
        original_path__isnull=False,
        updated_at__lt=maintenant - timedelta(hours=24),
    ):
        stockage.supprimer_original(media.pk)
        ListingMedia.objects.filter(pk=media.pk).update(original_path=None)
        bilan["originaux"] += 1
    return bilan


def annonces_louees_depuis(jours: int) -> list:
    limite = timezone.now() - timedelta(days=jours)
    return list(
        Listing.objects.filter(status=StatutAnnonce.RENTED, rented_at__lte=limite).values_list(
            "pk", flat=True
        )
    )


def archiver_louees() -> int:
    """Annonce louée depuis plus de 90 jours : archivée (EF-REC-10)."""
    total = 0
    jours = int(parametres.lire("ARCHIVE_AFTER_RENT_DAYS"))
    limite = timezone.now() - timedelta(days=jours)
    for annonce in Listing.objects.filter(status=StatutAnnonce.RENTED, rented_at__lte=limite):
        annonces.changer_statut(annonce, StatutAnnonce.ARCHIVED, acteur=None)
        total += 1
    return total
