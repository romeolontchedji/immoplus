"""Stockage des médias pour le code métier : originaux en cours d'envoi (local) et dérivés publics (fournisseur).

Les dérivés passent par `apps.core.providers.stockage` : disque du serveur par défaut (`STORAGE_PROVIDER`), ou
Cloudinary quand l'administration l'active (paramètre `MEDIA_STORAGE`, ADR 0010). Une clé rangée chez Cloudinary
porte le préfixe `cloudinary:` : chaque média reste lu là où il a été rangé, même après un changement de réglage.
Le code métier manipule des clés, jamais de chemins du disque public.
"""

import shutil
from pathlib import Path

from django.conf import settings

from apps.core import parametres
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


# --------------------------------------------------------------- choix du rangement
def envois_distants() -> bool:
    """Vrai quand les nouveaux médias vont chez Cloudinary : activé dans l'administration et compte renseigné."""
    return (
        parametres.lire("MEDIA_STORAGE") == "cloudinary"
        and fournisseurs.CloudinaryStorageProvider.configure()
    )


def est_distant(cle_fichier: str | None) -> bool:
    return fournisseurs.est_distant(cle_fichier)


# --------------------------------------------------------------- dérivés publics (fournisseur)
def dossier_public(annonce_id, media_id) -> Path:
    """Dossier où le traitement écrit les dérivés ; `publier` les rend ensuite visibles."""
    return fournisseurs.fournisseur().dossier_de_travail(_prefixe(annonce_id, media_id))


def publier(annonce_id, media_id, dossier: Path) -> None:
    fournisseurs.fournisseur().publier(_prefixe(annonce_id, media_id), dossier)


def publier_distant(annonce_id, media_id, dossier: Path) -> None:
    """Envoie les dérivés préparés chez Cloudinary (worker seulement) ; lève `ErreurStockageDistant`."""
    fournisseurs.CloudinaryStorageProvider().publier(_prefixe(annonce_id, media_id), dossier)


def cle(annonce_id, media_id, nom_fichier: str, *, distant: bool = False) -> str:
    """Clé enregistrée en base pour un dérivé (`listings/<annonce>/<média>/<fichier>`, préfixée chez Cloudinary)."""
    chemin = fournisseurs.StorageProvider.cle(_prefixe(annonce_id, media_id), nom_fichier)
    return fournisseurs.PREFIXE_CLOUDINARY + chemin if distant else chemin


def url_publique(cle_fichier: str | None) -> str | None:
    """URL de lecture d'un dérivé (disque servi par Caddy sous /media/, ou CDN de Cloudinary)."""
    return fournisseurs.pour_cle(cle_fichier).url_publique(cle_fichier)


def lire(cle_fichier: str) -> bytes | None:
    """Contenu d'un dérivé publié, `None` s'il est absent."""
    return fournisseurs.pour_cle(cle_fichier).lire(cle_fichier)


def supprimer_derives(annonce_id, media_id, *, distant: bool = False) -> None:
    """Supprime les dérivés sur le disque et, pour un média rangé chez Cloudinary, demande au worker de les y effacer."""
    prefixe = _prefixe(annonce_id, media_id)
    fournisseurs.fournisseur().supprimer(prefixe)
    if distant:
        from .tasks import supprimer_distant

        supprimer_distant.delay(prefixe)
