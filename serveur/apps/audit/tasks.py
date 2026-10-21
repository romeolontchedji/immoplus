from celery import shared_task

from . import services


@shared_task(name="apps.audit.purger")
def purger_audit() -> dict:
    return services.purger_selon_retention()
