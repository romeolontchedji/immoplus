from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = "apps.core"
    verbose_name = "Configuration"
    label = "core"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        from django.conf import settings

        from . import lookups  # noqa: F401  (enregistre le filtre `dans_reseau`)

        if getattr(settings, "PRODUCTION", False) and getattr(
            settings, "TURNSTILE_SECRET", ""
        ) in getattr(settings, "TURNSTILE_CLES_DE_TEST", ()):
            # Erreur volontaire : elle remonte dans l'administration (« Erreurs ») et par courriel.
            import logging

            logging.getLogger("apps.core.securite").error(
                "Clés de TEST Turnstile en production : l'anti-robot laisse tout passer. "
                "Renseigne TURNSTILE_SITE_KEY et TURNSTILE_SECRET (Cloudflare) puis redémarre."
            )
