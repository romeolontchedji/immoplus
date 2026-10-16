from django.contrib.admin.apps import AdminConfig


class AdminLogeoConfig(AdminConfig):
    """Remplace `django.contrib.admin` : le site d'administration par défaut est celui de Logeo (journal)."""

    default_site = "adminsite.site.AdminLogeo"
