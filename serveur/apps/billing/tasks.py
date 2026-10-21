from celery import shared_task

from . import services


@shared_task(
    name="apps.billing.appliquer_evenement",
    autoretry_for=(Exception,),
    max_retries=5,
    retry_backoff=True,
)
def appliquer_evenement(paiement_id: str, statut: str) -> str:
    return services.appliquer_evenement(paiement_id, statut).status


@shared_task(name="apps.billing.echeances")
def echeances() -> dict:
    return services.echeances()
