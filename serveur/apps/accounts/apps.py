from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = "apps.accounts"
    verbose_name = "Comptes"
    label = "accounts"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        # Pas de colonne `last_login` : l'activité est suivie par `last_seen_at` (au plus une fois par jour).
        from django.contrib.auth import user_logged_in
        from django.contrib.auth.models import update_last_login

        from .api import schema  # noqa: F401  (extension OpenAPI)

        user_logged_in.disconnect(update_last_login, dispatch_uid="update_user_last_login")
