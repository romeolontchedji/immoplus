"""Tâches du stockage distant (ADR 0010) : file `default`, celle du worker qui a accès à Internet et aux clés.

Leur nom ne commence pas par `apps.media.` : ce préfixe envoie sur la file `media`, dont le worker n'a pas Internet.
"""

from celery import shared_task

from apps.core.providers import stockage as fournisseurs


@shared_task(
    name="apps.stockage_distant.supprimer",
    autoretry_for=(fournisseurs.ErreurStockageDistant,),
    retry_backoff=60,
    max_retries=5,
)
def supprimer_distant(prefixe: str) -> None:
    fournisseurs.CloudinaryStorageProvider().supprimer_distant(prefixe)
