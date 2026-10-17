"""URL du site et de l'API (hôtes www et api). Aucune route d'administration ici."""

from django.conf import settings
from django.urls import include, path

from apps.core.api import views as vues_core
from apps.listings.api.views_media import Envoi

envoi_media = Envoi.as_view()

urlpatterns = [
    path("healthz", vues_core.healthz, name="healthz"),
    path("readyz", vues_core.readyz, name="readyz"),
    path("uploads/<uuid:media_id>", envoi_media, name="uploads"),
    path("v1/app-config", vues_core.ConfigurationApp.as_view(), name="app-config"),
    path("v1/legal/<slug:slug>", vues_core.DocumentLegal.as_view(), name="legal"),
    path("v1/", include("apps.accounts.api.urls")),
    path("v1/", include("apps.listings.api.urls")),
    path("v1/", include("apps.notifications.api.urls")),
    path("v1/", include("apps.chat.api.urls")),
    path("v1/", include("apps.moderation.api.urls")),
    path("v1/", include("apps.billing.api.urls")),
    path("", include("web.urls")),
]

if getattr(settings, "SCHEMA_ENABLED", False):
    from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerSplitView

    urlpatterns += [
        path("schema/", SpectacularAPIView.as_view(), name="schema"),
        path(
            "schema/docs/",
            SpectacularSwaggerSplitView.as_view(url_name="schema"),
            name="schema-docs",
        ),
    ]
