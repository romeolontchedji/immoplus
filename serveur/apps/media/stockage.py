"""Chemins et espace disque des médias : originaux dans `media_tmp`, dérivés publics dans `media_public`."""

import shutil
from pathlib import Path

from django.conf import settings


def chemin_original(media_id) -> Path:
    dossier = Path(settings.MEDIA_TMP_ROOT)
    dossier.mkdir(parents=True, exist_ok=True)
    return dossier / str(media_id)


def dossier_public(annonce_id, media_id) -> Path:
    dossier = Path(settings.MEDIA_ROOT) / "listings" / str(annonce_id) / str(media_id)
    dossier.mkdir(parents=True, exist_ok=True)
    return dossier


def url_publique(chemin_relatif: str | None) -> str | None:
    """URL de lecture d'un dérivé (servi par Caddy sous /media/)."""
    return f"{settings.MEDIA_URL}{chemin_relatif}" if chemin_relatif else None


def relatif(chemin: Path) -> str:
    return str(Path(chemin).relative_to(settings.MEDIA_ROOT))


def espace_disque_suffisant() -> bool:
    racine = Path(settings.MEDIA_ROOT)
    racine.mkdir(parents=True, exist_ok=True)
    usage = shutil.disk_usage(racine)
    return usage.used / usage.total * 100 < settings.MEDIA_DISK_REFUS_POURCENT


def supprimer_derives(annonce_id, media_id) -> None:
    shutil.rmtree(
        Path(settings.MEDIA_ROOT) / "listings" / str(annonce_id) / str(media_id), ignore_errors=True
    )


def supprimer_original(media_id) -> None:
    chemin_original(media_id).unlink(missing_ok=True)
