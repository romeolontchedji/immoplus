"""Réglages de développement (Docker Compose, profil `dev`). Jamais utilisés en production."""

from config import env

from .base import *  # noqa: F403
from .base import INSTALLED_APPS, MIDDLEWARE_SITE

DEBUG = True
SITE_URL = env.texte("SITE_URL") or "http://www.localhost:8080"
ALLOWED_HOSTS = ["*"]
# Développement : les courriels (codes de l'administration…) sont rangés dans la boîte de développement,
# lisible sur http://www.localhost:8080/dev/boite (avec les push).
EMAIL_BACKEND = env.texte("EMAIL_BACKEND") or "apps.core.courriel_dev.BoiteDevCourriels"
INSTALLED_APPS = [*INSTALLED_APPS, "django.contrib.messages"]
STYLEGUIDE_ENABLED = True
DEV_INBOX_ENABLED = True
SCHEMA_ENABLED = True
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"
SESSION_COOKIE_NAME = "lgsid"
CSRF_COOKIE_NAME = "lgcsrf"
MIDDLEWARE = list(MIDDLEWARE_SITE)
