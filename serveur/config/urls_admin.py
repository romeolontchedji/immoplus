"""URL de l'hôte d'administration. Aucune route publique ici ; contenu ajouté en phase 1."""

from django.contrib import admin
from django.urls import path

from apps.core.api import views as vues_core

urlpatterns = [
    path("healthz", vues_core.healthz, name="healthz"),
    path("", admin.site.urls),
]
