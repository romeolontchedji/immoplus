"""Tâches de la messagerie. Les noms commencent par `apps.notifications.` pour partir dans la file dédiée."""

from celery import shared_task

from . import services


@shared_task(name="apps.notifications.message")
def notifier_message(message_id: str) -> str:
    return services.notifier(message_id)


@shared_task(name="apps.notifications.sweep_unnotified_messages")
def rattraper_messages() -> int:
    return services.rattraper()


@shared_task(name="apps.notifications.remind_unanswered_messages")
def rappeler_gerants() -> int:
    return services.rappeler_gerants_sans_reponse()


@shared_task(name="apps.chat.lecture_seule")
def lecture_seule_apres_location() -> int:
    return services.passer_en_lecture_seule_apres_location()


@shared_task(name="apps.accounts.indicateurs_gerants")
def indicateurs_gerants() -> int:
    from apps.accounts.services import administration

    return administration.maj_indicateurs_gerants(services.calculer_indicateurs_gerants())
