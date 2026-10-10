from celery import shared_task

from . import services


@shared_task(name="apps.moderation.expirer_sanctions")
def expirer_sanctions() -> int:
    return services.expirer_sanctions()
