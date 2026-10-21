"""Déplacer les médias déjà en ligne entre le disque du serveur et Cloudinary (ADR 0010).

Le réglage MEDIA_STORAGE ne concerne que les nouveaux envois ; ces fonctions rangent l'existant. À lancer dans le
conteneur `worker` (accès Internet, clés Cloudinary, volume des médias). Chaque média est traité seul : une panne au
milieu laisse les médias déjà déplacés lisibles à leur nouvelle place et les autres à l'ancienne.
"""

import logging
import posixpath
import shutil

from django.utils import timezone

from apps.core.providers import stockage as fournisseurs
from apps.media import stockage

from .. import selectors
from ..enums import StatutMedia
from ..models import ListingMedia

journal = logging.getLogger(__name__)


def _fichiers(media: ListingMedia) -> set[str]:
    """Noms des fichiers publiés d'un média (variantes, lecture, affiche)."""
    noms = {posixpath.basename(c) for c in (media.poster_path, media.playback_path) if c}
    return noms | {v for v in (media.variants or {}).values() if isinstance(v, str)}


def _a_deplacer(vers_cloudinary: bool):
    medias = ListingMedia.objects.filter(status=StatutMedia.READY, deleted_at__isnull=True)
    debut = fournisseurs.PREFIXE_CLOUDINARY
    medias = (
        medias.exclude(poster_path__startswith=debut)
        if vers_cloudinary
        else medias.filter(poster_path__startswith=debut)
    )
    return medias.exclude(poster_path__isnull=True).order_by("created_at")


def _nouvelles_cles(media: ListingMedia, distant: bool) -> dict:
    def cle(chemin):
        return (
            stockage.cle(media.listing_id, media.pk, posixpath.basename(chemin), distant=distant)
            if chemin
            else None
        )

    return {"poster_path": cle(media.poster_path), "playback_path": cle(media.playback_path)}


def vers_cloudinary(limite: int | None = None) -> dict:
    bilan = {"deplaces": 0, "absents": 0, "echecs": 0}
    for media in _a_deplacer(True)[:limite]:
        dossier = stockage.dossier_public(media.listing_id, media.pk)
        if not any(dossier.iterdir()):
            bilan["absents"] += 1
            continue
        try:
            stockage.publier_distant(media.listing_id, media.pk, dossier)
        except fournisseurs.ErreurStockageDistant:
            journal.exception("Transfert du média %s vers Cloudinary impossible", media.pk)
            bilan["echecs"] += 1
            continue
        ListingMedia.objects.filter(pk=media.pk).update(
            **_nouvelles_cles(media, True), updated_at=timezone.now()
        )
        shutil.rmtree(dossier, ignore_errors=True)
        bilan["deplaces"] += 1
    selectors.invalider_fil()
    return bilan


def vers_disque(limite: int | None = None) -> dict:
    bilan = {"deplaces": 0, "absents": 0, "echecs": 0}
    cloudinary = fournisseurs.CloudinaryStorageProvider()
    for media in _a_deplacer(False)[:limite]:
        dossier = stockage.dossier_public(media.listing_id, media.pk)
        try:
            for nom in _fichiers(media):
                cloudinary.telecharger(
                    stockage.cle(media.listing_id, media.pk, nom, distant=True), dossier / nom
                )
        except fournisseurs.ErreurStockageDistant:
            journal.exception("Rapatriement du média %s impossible", media.pk)
            shutil.rmtree(dossier, ignore_errors=True)
            bilan["echecs"] += 1
            continue
        ListingMedia.objects.filter(pk=media.pk).update(
            **_nouvelles_cles(media, False), updated_at=timezone.now()
        )
        try:
            cloudinary.supprimer_distant(f"listings/{media.listing_id}/{media.pk}")
        except fournisseurs.ErreurStockageDistant:
            journal.warning(
                "Copie Cloudinary du média %s laissée en place (suppression impossible)", media.pk
            )
        bilan["deplaces"] += 1
    selectors.invalider_fil()
    return bilan
