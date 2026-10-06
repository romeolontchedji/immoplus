"""Routes du site. Complétées phase par phase (CDC §10.9)."""

from django.conf import settings
from django.urls import path

from . import views

urlpatterns = [
    path("", views.accueil, name="accueil"),
]

if getattr(settings, "STYLEGUIDE_ENABLED", False):
    urlpatterns.append(path("styleguide", views.styleguide, name="styleguide"))
