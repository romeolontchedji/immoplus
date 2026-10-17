from django.apps import AppConfig


class AdminsiteConfig(AppConfig):
    default = True
    name = "adminsite"
    label = "adminsite"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        from django.apps import apps

        from . import signaux  # noqa: F401

        # Intitulés français des applications tierces affichées dans le menu.
        if apps.is_installed("axes"):
            apps.get_app_config("axes").verbose_name = "Sécurité des connexions"
