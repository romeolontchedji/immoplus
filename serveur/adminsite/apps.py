from django.apps import AppConfig


class AdminsiteConfig(AppConfig):
    default = True
    name = "adminsite"
    label = "adminsite"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        from . import signaux  # noqa: F401
