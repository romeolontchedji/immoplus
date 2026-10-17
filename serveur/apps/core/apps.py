from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = "apps.core"
    verbose_name = "Configuration"
    label = "core"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        from . import lookups  # noqa: F401  (enregistre le filtre `dans_reseau`)
