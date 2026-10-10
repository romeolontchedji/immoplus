"""Tâches des médias (file `media`, sans accès Internet)."""

from celery import shared_task

from .services import medias


@shared_task(name="apps.media.traiter", soft_time_limit=620)
def traiter_media(media_id: str) -> None:
    medias.traiter(media_id)


@shared_task(name="apps.media.nettoyer_envois")
def nettoyer_envois() -> int:
    return medias.nettoyer_envois_expires()


@shared_task(name="apps.listings.alertes")
def notifier_alertes(annonce_id: str) -> int:
    from .services import alertes

    return alertes.notifier_correspondances(annonce_id)


@shared_task(name="apps.listings.favoris_indisponibles")
def notifier_indisponibilite(annonce_id: str, statut: str) -> int:
    from .services import favoris

    return favoris.notifier_indisponibilite(annonce_id, statut)


@shared_task(name="apps.listings.vider_vues")
def vider_compteurs_vues() -> int:
    from .services import vues

    return vues.vider_compteurs()


@shared_task(name="apps.listings.fraicheur")
def relances_de_fraicheur() -> dict:
    from .services import entretien

    return entretien.relances_de_fraicheur()


@shared_task(name="apps.media.purger")
def purger_medias() -> dict:
    from .services import entretien

    return entretien.purger_medias()


@shared_task(name="apps.listings.archiver_louees")
def archiver_louees() -> int:
    from .services import entretien

    return entretien.archiver_louees()
