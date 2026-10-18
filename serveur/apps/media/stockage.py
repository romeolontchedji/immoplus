"""Stockage des médias pour le code métier : originaux en cours d'envoi (local) et dérivés publics (fournisseur).

Les dérivés passent par `apps.core.providers.stockage` (réglage `STORAGE_PROVIDER` : `local` ou `s3`). Le code métier
manipule des clés, jamais de chemins du disque public : changer de fournisseur ne le touche pas.
"""

import shutil
from pathlib import Path

from django.conf import settings

from apps.core.providers import stockage as fournisseurs


def _prefixe(annonce_id, media_id) -> str:
    return f"listings/{annonce_id}/{media_id}"


# --------------------------------------------------------------- originaux (espace de travail local)
def chemin_original(media_id) -> Path:
    dossier = Path(settings.MEDIA_TMP_ROOT)
    dossier.mkdir(parents=True, exist_ok=True)
    return dossier / str(media_id)


def supprimer_original(media_id) -> None:
    chemin_original(media_id).unlink(missing_ok=True)


def espace_disque_suffisant() -> bool:
    """Refuse les envois si le stockage public est plein ou si le disque de travail l'est."""
    travail = Path(settings.MEDIA_TMP_ROOT)
    travail.mkdir(parents=True, exist_ok=True)
    usage = shutil.disk_usage(travail)
    disque_ok = usage.used / usage.total * 100 < settings.MEDIA_DISK_REFUS_POURCENT
    return disque_ok and fournisseurs.fournisseur().espace_suffisant()


# --------------------------------------------------------------- dérivés publics (fournisseur)
def dossier_public(annonce_id, media_id) -> Path:
    """Dossier où le traitement écrit les dérivés ; `publier` les rend ensuite visibles."""
    return fournisseurs.fournisseur().dossier_de_travail(_prefixe(annonce_id, media_id))


def publier(annonce_id, media_id, dossier: Path) -> None:
    fournisseurs.fournisseur().publier(_prefixe(annonce_id, media_id), dossier)


def cle(annonce_id, media_id, nom_fichier: str) -> str:
    """Clé enregistrée en base pour un dérivé (`listings/<annonce>/<média>/<fichier>`)."""
    return fournisseurs.StorageProvider.cle(_prefixe(annonce_id, media_id), nom_fichier)


def url_publique(cle_fichier: str | None) -> str | None:
    """URL de lecture d'un dérivé (disque servi par Caddy sous /media/, ou CDN du stockage objet)."""
    return fournisseurs.fournisseur().url_publique(cle_fichier)


def supprimer_derives(annonce_id, media_id) -> None:
    fournisseurs.fournisseur().supprimer(_prefixe(annonce_id, media_id))
