from django.apps import AppConfig


class ChatConfig(AppConfig):
    name = "apps.chat"
    label = "chat"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        from . import (
            receivers,  # noqa: F401  (abonnements aux signaux des annonces et des notifications)
        )
