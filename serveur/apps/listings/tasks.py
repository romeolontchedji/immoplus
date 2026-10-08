"""Tâches des médias (file `media`, sans accès Internet)."""

from celery import shared_task

from .services import medias


@shared_task(name="apps.media.traiter", soft_time_limit=620)
def traiter_media(media_id: str) -> None:
    medias.traiter(media_id)


@shared_task(name="apps.media.nettoyer_envois")
def nettoyer_envois() -> int:
    return medias.nettoyer_envois_expires()
