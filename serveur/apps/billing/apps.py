from django.apps import AppConfig


class BillingConfig(AppConfig):
    """Abonnement : architecture prête, non activée (CDC §7.11). Rien n'est visible tant que le drapeau est faux."""

    name = "apps.billing"
    label = "billing"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        from . import (
            receivers,  # noqa: F401  (plan Gratuit V1 attribué à la vérification d'un gérant)
        )
