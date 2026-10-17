from django.apps import AppConfig


class AuditConfig(AppConfig):
    name = "apps.audit"
    verbose_name = "Journal d'activité"
    default_auto_field = "django.db.models.BigAutoField"
