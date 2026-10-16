"""Tâches asynchrones des comptes : envoi des SMS (la réponse HTTP ne dépend jamais de l'envoi)."""

import logging

from celery import shared_task

from apps.core.providers import sms

journal = logging.getLogger(__name__)


@shared_task(name="apps.accounts.envoyer_sms", bind=True, max_retries=2, default_retry_delay=5)
def envoyer_sms(self, numero_e164: str, message: str, otp_id: str | None = None) -> None:
    """Envoie un SMS ; pour un OTP, enregistre la référence et le coût (budget, statistiques)."""
    try:
        resultat = sms.fournisseur().envoyer(numero_e164, message)
    except sms.ErreurFournisseurSms as erreur:
        journal.error("Échec d'envoi SMS (%s)", type(erreur).__name__)
        raise self.retry(exc=erreur) from erreur
    if otp_id:
        from apps.accounts.services import otp

        otp.noter_envoi(otp_id, resultat.reference, resultat.cout_xof)


@shared_task(name="apps.accounts.notifier_gerant_cree")
def notifier_gerant_cree(gerant_id: str) -> None:
    """Prévient un gérant que son compte est prêt ; la création du compte ne dépend jamais de cet envoi."""
    from apps.accounts.services import administration

    administration.notifier_creation_gerant(gerant_id)


@shared_task(name="apps.accounts.purger_otp")
def purger_otp() -> int:
    from apps.accounts.services import administration

    return administration.purger_otp()
