from django.apps import AppConfig


class ModerationConfig(AppConfig):
    name = "apps.moderation"
    verbose_name = "Modération"
    label = "moderation"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        from . import receivers  # noqa: F401  (signalement automatique des coordonnées détectées)
