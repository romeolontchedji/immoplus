"""Lectures des annonces et quartiers."""

from .enums import StatutAnnonce
from .models import District, Listing


def quartiers_actifs():
    return District.objects.filter(is_active=True)


def annonces_du_gerant(gerant, statut: str | None = None):
    requete = Listing.objects.filter(gerant=gerant, deleted_at__isnull=True).select_related(
        "district"
    )
    if statut:
        requete = requete.filter(status=statut)
    return requete.order_by("-updated_at")


def annonce_du_gerant(gerant, annonce_id) -> Listing | None:
    try:
        return annonces_du_gerant(gerant).filter(pk=annonce_id).first()
    except Exception:  # noqa: BLE001 - identifiant mal formé : introuvable
        return None


def statuts_publics() -> tuple[str, ...]:
    return (StatutAnnonce.PUBLISHED,)
