"""Tâches de la file `notifications` (CDC §7.7 EF-NTF-07) : cinq essais à temporisation croissante."""

from celery import shared_task

from . import services


@shared_task(name="apps.notifications.envoyer_push", bind=True, max_retries=services.MAX_ESSAIS - 1)
def envoyer_push(self, notification_id: str) -> str:
    etat = services.envoyer_push(notification_id)
    if etat == "a_reprendre" and not self.request.is_eager:
        raise self.retry(countdown=min(15 * 2**self.request.retries, 600))
    return etat
