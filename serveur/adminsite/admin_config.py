from django.contrib.admin.apps import AdminConfig


class AdminImmoplusConfig(AdminConfig):
    """Remplace `django.contrib.admin` : le site d'administration par défaut est celui de Immo+ (journal)."""

    default_site = "adminsite.site.AdminImmoplus"
