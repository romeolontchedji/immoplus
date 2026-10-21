"""Favoris des locataires (CDC §7.5) et notification « plus disponible »."""

from django.db import IntegrityError, transaction

from apps.core import stats
from apps.core.errors import ErreurMetier
from apps.notifications import services as notifications
from apps.notifications import textes

from .. import selectors
from ..enums import StatutAnnonce
from ..models import Favorite, Listing

LIMITE = 200


def ajouter(utilisateur, annonce_id) -> None:
    annonce = Listing.objects.filter(
        pk=annonce_id, status__in=selectors.STATUTS_VISIBLES, deleted_at__isnull=True
    ).first()
    if annonce is None:
        raise ErreurMetier("not_found", "Annonce introuvable.", statut=404)
    if Favorite.objects.filter(user=utilisateur).count() >= LIMITE:
        raise ErreurMetier("favorites_limit", f"{LIMITE} favoris au plus.", statut=409)
    try:
        with transaction.atomic():
            Favorite.objects.create(user=utilisateur, listing=annonce)
    except IntegrityError:
        return  # idempotent
    stats.incrementer("favorites_added")
    stats.incrementer("favorites_added", sujet=str(annonce.pk))


def retirer(utilisateur, annonce_id) -> None:
    Favorite.objects.filter(user=utilisateur, listing_id=annonce_id).delete()


def notifier_indisponibilite(annonce_id, nouveau_statut: str) -> int:
    """Un favori devient loué ou masqué : une seule notification par favori et par statut (EF-ALR-04)."""
    annonce = Listing.objects.filter(pk=annonce_id).first()
    if annonce is None:
        return 0
    titre = textes.tronquer(annonce.title, 40)
    titre_notif = (
        f"« {titre} » vient d'être louée"
        if nouveau_statut == StatutAnnonce.RENTED
        else f"« {titre} » n'est plus disponible"
    )
    envoyees = 0
    for utilisateur_id in selectors.locataires_favoris(annonce_id):
        n = notifications.creer(
            utilisateur_id,
            "favorite.unavailable",
            titre_notif,
            "D'autres chambres t'attendent dans le même quartier.",
            data={"listing_id": str(annonce.pk), "slug": annonce.slug},
            dedupe_key=f"favorite:{utilisateur_id}:{annonce_id}:{nouveau_statut}",
        )
        envoyees += 1 if n else 0
    return envoyees
