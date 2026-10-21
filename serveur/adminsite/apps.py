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
            config = apps.get_app_config("axes")
            config.verbose_name = "Sécurité des connexions"
            # Intitulés explicites : ces trois pages ne concernent que les connexions à l'administration.
            for modele, nom in (
                ("AccessAttempt", "Verrouillages en cours (administration)"),
                ("AccessFailureLog", "Échecs d'accès (administration)"),
                ("AccessLog", "Connexions réussies (administration)"),
            ):
                config.get_model(modele)._meta.verbose_name_plural = nom
