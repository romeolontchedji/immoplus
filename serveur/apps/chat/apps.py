from django.apps import AppConfig


class ChatConfig(AppConfig):
    name = "apps.chat"
    label = "chat"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        from apps.core import configuration

        from . import (
            consumers,
            receivers,  # noqa: F401  (abonnements aux signaux des annonces et des notifications)
            services,
            ws,
        )

        configuration.declarer_limites(message_max_length=services.LONGUEUR_MAX)
        configuration.declarer_temps_reel(
            path="/ws/v1/",
            ticket_ttl_s=ws.DUREE_TICKET_S,
            ping_interval_s=consumers.INACTIVITE_S // 2,
            inactivity_close_s=consumers.INACTIVITE_S,
            max_connections=consumers.MAX_CONNEXIONS,
        )
