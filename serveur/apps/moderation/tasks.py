from celery import shared_task

from . import resume, services


@shared_task(name="apps.moderation.expirer_sanctions")
def expirer_sanctions() -> int:
    return services.expirer_sanctions()


@shared_task(name="apps.moderation.resume_hebdomadaire")
def resume_hebdomadaire() -> dict:
    return resume.envoyer()

