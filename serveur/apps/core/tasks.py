"""Tâches transverses : envoi d'un courriel (codes de l'administration, alertes d'erreurs).

L'envoi part du `worker` (réseau `sortie`) : l'administration n'a volontairement pas accès à Internet, elle dépose la
demande dans la file et n'envoie jamais elle-même.
"""

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail


# Le nom commence par `apps.notifications.` : même file que les push, traitée en priorité (config.celery).
@shared_task(
    name="apps.notifications.envoyer_courriel",
    autoretry_for=(OSError,),
    retry_backoff=10,
    retry_kwargs={"max_retries": 4},
)
def envoyer_courriel(destinataires: list[str], sujet: str, texte: str) -> int:
    """Envoie un courriel texte. Reprises en cas de panne réseau ou SMTP (4 essais, attente croissante)."""
    return send_mail(sujet, texte, settings.DEFAULT_FROM_EMAIL, destinataires, fail_silently=False)
