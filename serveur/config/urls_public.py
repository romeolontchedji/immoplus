"""URL du site et de l'API (hôtes www et api). Aucune route d'administration ici."""

from django.conf import settings
from django.urls import include, path

from apps.core.api import views as vues_core

urlpatterns = [
    path("healthz", vues_core.healthz, name="healthz"),
    path("readyz", vues_core.readyz, name="readyz"),
    path("", include("web.urls")),
]

if getattr(settings, "SCHEMA_ENABLED", False):
    from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

    urlpatterns += [
        path("schema/", SpectacularAPIView.as_view(), name="schema"),
        path("schema/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="schema-docs"),
    ]
