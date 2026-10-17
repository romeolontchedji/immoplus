"""Médias d'annonce : création d'envoi, protocole d'envoi reprenable (tus), traitement, ordre, suppression."""

import logging
from datetime import timedelta
from typing import TYPE_CHECKING

from django.db import transaction
from django.db.models import Count, Sum
from django.utils import timezone

from apps.audit import services as audit
from apps.core.errors import ErreurMetier
from apps.media import stockage, traitement
from apps.notifications import services as notifications

from .. import selectors
from ..enums import StatutAnnonce, StatutMedia, TypeMedia
from ..models import Listing, ListingMedia

if TYPE_CHECKING:
    from apps.accounts.models import GerantProfile

journal = logging.getLogger(__name__)

PHOTOS_MAX = 10
ENVOIS_OUVERTS_MAX = 2
EN_ATTENTE_MAX_OCTETS = 500 * 1024 * 1024
TAILLE_MAX = {TypeMedia.VIDEO: 150 * 1024 * 1024, TypeMedia.PHOTO: 12 * 1024 * 1024}
MORCEAU_MAX = 2 * 1024 * 1024
ACTIFS = [StatutMedia.UPLOADING, StatutMedia.UPLOADED, StatutMedia.PROCESSING, StatutMedia.READY]


def _annonce(gerant: "GerantProfile", annonce_id) -> Listing:
    try:
        return Listing.objects.select_for_update().get(
            pk=annonce_id, gerant=gerant, deleted_at__isnull=True
        )
    except Exception as erreur:  # noqa: BLE001 - absente, étrangère ou identifiant mal formé : même réponse
        raise ErreurMetier("not_found", "Annonce introuvable.", statut=404) from erreur


def _media(gerant: "GerantProfile", annonce_id, media_id, *, verrou=False) -> ListingMedia:
    requete = ListingMedia.objects.select_related("listing")
    requete = requete.select_for_update(of=("self",)) if verrou else requete
    filtres = {"pk": media_id, "listing__gerant": gerant}
    if annonce_id is not None:
        filtres["listing_id"] = annonce_id
    try:
        return requete.get(**filtres)
    except Exception as erreur:  # noqa: BLE001
        raise ErreurMetier("not_found", "Média introuvable.", statut=404) from erreur


@transaction.atomic
def creer_envoi(gerant: "GerantProfile", annonce_id, kind: str, taille: int) -> ListingMedia:
    """Crée le média et son envoi, après quotas (CDC §11.2) : `429 upload_quota`, `503 storage_full`."""
    annonce = _annonce(gerant, annonce_id)
    if kind not in TypeMedia.values:
        raise ErreurMetier(
            "validation_error", "Type de média inconnu.", champs={"kind": ["video ou photo"]}
        )
    if not isinstance(taille, int) or not 0 < taille <= TAILLE_MAX[kind]:
        raise ErreurMetier(
            "validation_error", "Taille de fichier invalide.",
            champs={"size_bytes": [f"Entre 1 octet et {TAILLE_MAX[kind] // (1024 * 1024)} Mo"]},
        )  # fmt: skip
    if annonce.status in (StatutAnnonce.ARCHIVED, StatutAnnonce.REMOVED, StatutAnnonce.RENTED):
        raise ErreurMetier("listing_locked", "Cette annonce n'accepte plus de médias.", statut=409)
    if not stockage.espace_disque_suffisant():
        raise ErreurMetier("storage_full", "Le stockage est plein. Réessaie plus tard.", statut=503)
    actifs = ListingMedia.objects.filter(listing=annonce, status__in=ACTIFS, kind=kind)
    if (kind == TypeMedia.VIDEO and actifs.exists()) or (
        kind == TypeMedia.PHOTO and actifs.count() >= PHOTOS_MAX
    ):
        raise ErreurMetier(
            "upload_quota", "Nombre maximal de médias atteint pour cette annonce.", statut=429
        )
    ouverts = ListingMedia.objects.filter(listing__gerant=gerant, status=StatutMedia.UPLOADING)
    agr = ouverts.aggregate(n=Count("id"), octets=Sum("declared_size_bytes"))
    if (agr["n"] or 0) >= ENVOIS_OUVERTS_MAX or (
        agr["octets"] or 0
    ) + taille > EN_ATTENTE_MAX_OCTETS:
        raise ErreurMetier(
            "upload_quota",
            "Trop d'envois en cours. Termine-les avant d'en lancer d'autres.",
            statut=429,
        )
    position = ListingMedia.objects.filter(listing=annonce, status__in=ACTIFS).count()
    return ListingMedia.objects.create(
        listing=annonce, kind=kind, declared_size_bytes=taille, position=position,
        upload_expires_at=timezone.now() + timedelta(hours=24),
    )  # fmt: skip


# --------------------------------------------------------------- protocole tus (reprise)
def decalage(gerant: "GerantProfile", annonce_id, media_id) -> ListingMedia:
    return _media(gerant, annonce_id, media_id)


def recevoir_morceau(
    gerant: "GerantProfile", annonce_id, media_id, offset: int, morceau: bytes
) -> ListingMedia:
    """Ajoute un morceau au fichier. L'offset doit être exactement `received_bytes` (sinon 409 : le client relit)."""
    with transaction.atomic():
        media = _media(gerant, annonce_id, media_id, verrou=True)
        if media.status != StatutMedia.UPLOADING or (
            media.upload_expires_at and media.upload_expires_at <= timezone.now()
        ):
            raise ErreurMetier("upload_closed", "Cet envoi est terminé ou expiré.", statut=410)
        if offset != media.received_bytes:
            raise ErreurMetier(
                "upload_offset_mismatch", "Décalage inattendu : relis la position avant de continuer.", statut=409,
                entetes={"Upload-Offset": str(media.received_bytes)},
            )  # fmt: skip
        if not morceau or len(morceau) > MORCEAU_MAX:
            raise ErreurMetier(
                "validation_error",
                "Morceau invalide (2 Mo au plus).",
                statut=413 if morceau else 400,
            )
        if media.received_bytes + len(morceau) > media.declared_size_bytes:
            raise ErreurMetier(
                "upload_too_large", "Le fichier dépasse la taille annoncée.", statut=413
            )
        with open(stockage.chemin_original(media.pk), "ab") as fichier:
            fichier.write(morceau)
        media.received_bytes += len(morceau)
        termine = media.received_bytes == media.declared_size_bytes
        if termine:
            media.status = StatutMedia.UPLOADED
            media.original_path = str(stockage.chemin_original(media.pk))
        media.save(update_fields=["received_bytes", "status", "original_path", "updated_at"])
        if termine:
            from ..tasks import traiter_media

            transaction.on_commit(lambda: traiter_media.delay(str(media.pk)))
    return media


# --------------------------------------------------------------- traitement (tâche de la file `media`)
def traiter(media_id) -> None:
    media = ListingMedia.objects.select_related("listing").filter(pk=media_id).first()
    if media is None or media.status != StatutMedia.UPLOADED:
        return
    ListingMedia.objects.filter(pk=media.pk).update(status=StatutMedia.PROCESSING)
    source = stockage.chemin_original(media.pk)
    destination = stockage.dossier_public(media.listing_id, media.pk)
    try:
        empreinte = traitement.sha256(source)
        if media.kind == TypeMedia.PHOTO:
            meta = traitement.traiter_photo(source, destination)
            champs = {"variants": meta["variants"], "playback_path": None}
            principale = meta["variants"][max(meta["variants"], key=int)]
            champs["poster_path"] = stockage.relatif(destination / principale)
        else:
            meta = traitement.traiter_video(source, destination)
            champs = {
                "playback_path": stockage.relatif(destination / meta["playback"]),
                "poster_path": stockage.relatif(destination / meta["poster"])
                if meta["poster"]
                else None,
                "variants": {"mp4": meta["playback"]},
            }
        ListingMedia.objects.filter(pk=media.pk).update(
            status=StatutMedia.READY, sha256=empreinte, mime_type=meta["mime"], size_bytes=source.stat().st_size,
            width=meta["width"], height=meta["height"], duration_s=meta.get("duration_s"), error_code=None,
            error_detail=None, updated_at=timezone.now(), **champs,
        )  # fmt: skip
        _poser_couverture(media.listing_id)
        selectors.invalider_fil()
        _suite_de_publication(media.listing_id)
    except traitement.ErreurTraitement as erreur:
        stockage.supprimer_derives(media.listing_id, media.pk)
        ListingMedia.objects.filter(pk=media.pk).update(
            status=StatutMedia.FAILED,
            error_code=erreur.code,
            error_detail=erreur.message,
            updated_at=timezone.now(),
        )
        _notifier_echec(media, erreur.message)
        _suite_de_publication(media.listing_id, echec=True)
    except Exception:  # noqa: BLE001 - une panne imprévue ne doit pas laisser le média bloqué en traitement
        journal.exception("Échec inattendu du traitement du média %s", media.pk)
        stockage.supprimer_derives(media.listing_id, media.pk)
        ListingMedia.objects.filter(pk=media.pk).update(
            status=StatutMedia.FAILED, error_code="erreur_interne", error_detail="Traitement impossible. Réessaie.",
            updated_at=timezone.now(),
        )  # fmt: skip


def _poser_couverture(annonce_id) -> None:
    if ListingMedia.objects.filter(
        listing_id=annonce_id, is_cover=True, status=StatutMedia.READY
    ).exists():
        return
    premiere = (
        ListingMedia.objects.filter(
            listing_id=annonce_id, kind=TypeMedia.PHOTO, status=StatutMedia.READY
        )
        .order_by("position", "created_at")
        .first()
    )
    if premiere:
        ListingMedia.objects.filter(listing_id=annonce_id, is_cover=True).update(is_cover=False)
        ListingMedia.objects.filter(pk=premiere.pk).update(is_cover=True)


def _notifier_echec(media: ListingMedia, motif: str) -> None:
    """Le gérant est prévenu avec un motif lisible (annexe B : listing.media_failed)."""
    gerant_id = (
        Listing.objects.filter(pk=media.listing_id).values_list("gerant_id", flat=True).first()
    )
    if gerant_id is None:
        return
    nature = "vidéo" if media.kind == TypeMedia.VIDEO else "photo"
    notifications.creer(
        gerant_id,
        "listing.media_failed",
        f"Ta {nature} n'a pas pu être traitée",
        motif,
        data={"listing_id": str(media.listing_id), "media_id": str(media.pk)},
        dedupe_key=f"media-failed:{media.pk}",
    )


def _suite_de_publication(annonce_id, *, echec: bool = False) -> None:
    """Une annonce en attente de traitement repasse en brouillon si un média échoue (CDC §11.1)."""
    from . import annonces

    # Pas de `select_related("gerant")` : il charge toutes les colonnes de `gerant_profiles`, y compris celles que le
    # rôle `app` ne peut pas lire. L'accès `annonce.gerant` passe par le gestionnaire qui les laisse de côté.
    annonce = Listing.objects.filter(pk=annonce_id, status=StatutAnnonce.PROCESSING).first()
    if annonce is None:
        return
    if echec:
        annonces.changer_statut(annonce, StatutAnnonce.DRAFT, acteur=annonce.gerant.user)
        return
    en_cours = ListingMedia.objects.filter(
        listing=annonce, status__in=[StatutMedia.UPLOADED, StatutMedia.PROCESSING]
    ).exists()
    deja_publie = Listing.objects.filter(gerant=annonce.gerant, published_at__isnull=False).exists()
    if not en_cours and deja_publie and not annonces.manques_a_la_publication(annonce):
        annonces.mettre_en_ligne(annonce, acteur=annonce.gerant.user)


# --------------------------------------------------------------- lecture, ordre, suppression
def lister(gerant: "GerantProfile", annonce_id) -> list[ListingMedia]:
    return list(
        ListingMedia.objects.filter(listing_id=annonce_id, listing__gerant=gerant)
        .exclude(status=StatutMedia.DELETED).order_by("position", "created_at")
    )  # fmt: skip


@transaction.atomic
def definir_ordre(
    gerant: "GerantProfile", annonce_id, ordre: list[str], couverture: str | None
) -> list[ListingMedia]:
    _annonce(gerant, annonce_id)
    medias = {str(m.pk): m for m in lister(gerant, annonce_id)}
    if set(ordre) != set(medias) or len(ordre) != len(set(ordre)):
        raise ErreurMetier(
            "validation_error",
            "La liste doit contenir exactement les médias de l'annonce.",
            champs={"order": ["Liste incomplète"]},
        )
    if couverture is not None and (
        couverture not in medias or medias[couverture].kind != TypeMedia.PHOTO
    ):
        raise ErreurMetier(
            "validation_error",
            "La couverture doit être une photo de l'annonce.",
            champs={"cover": ["Photo attendue"]},
        )
    if couverture is not None:
        ListingMedia.objects.filter(listing_id=annonce_id, is_cover=True).update(is_cover=False)
        ListingMedia.objects.filter(pk=couverture).update(is_cover=True)
    for position, identifiant in enumerate(ordre):
        ListingMedia.objects.filter(pk=identifiant).update(position=position)
    return lister(gerant, annonce_id)


@transaction.atomic
def supprimer(gerant: "GerantProfile", annonce_id, media_id) -> None:
    media = _media(gerant, annonce_id, media_id, verrou=True)
    if media.status == StatutMedia.DELETED:
        raise ErreurMetier("not_found", "Média introuvable.", statut=404)
    annonce = media.listing
    if annonce.status == StatutAnnonce.PUBLISHED and media.status == StatutMedia.READY:
        pret = ListingMedia.objects.filter(listing=annonce, status=StatutMedia.READY)
        restant_video = pret.filter(kind=TypeMedia.VIDEO).exclude(pk=media.pk).exists()
        restant_photos = pret.filter(kind=TypeMedia.PHOTO).exclude(pk=media.pk).count()
        if not restant_video or restant_photos < 3:
            raise ErreurMetier(
                "media_required", "Une annonce publiée garde sa vidéo et au moins 3 photos. Masque l'annonce avant de supprimer.",
                statut=409,
            )  # fmt: skip
    media.status, media.deleted_at, media.is_cover = StatutMedia.DELETED, timezone.now(), False
    media.save(update_fields=["status", "deleted_at", "is_cover", "updated_at"])
    stockage.supprimer_derives(annonce.pk, media.pk)
    stockage.supprimer_original(media.pk)
    _poser_couverture(annonce.pk)
    audit.enregistrer(
        "listing.media_supprime", acteur=gerant.user, cible=annonce, metadata={"type": media.kind}
    )


def nettoyer_envois_expires() -> int:
    """Abandonne les envois inactifs depuis 24 h (tâche planifiée)."""
    expires = ListingMedia.objects.filter(
        status=StatutMedia.UPLOADING, upload_expires_at__lt=timezone.now()
    )
    n = 0
    for m in expires:
        stockage.supprimer_original(m.pk)
        ListingMedia.objects.filter(pk=m.pk).update(
            status=StatutMedia.DELETED, deleted_at=timezone.now()
        )
        n += 1
    return n
