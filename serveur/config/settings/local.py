"""Réglages de développement (Docker Compose, profil `dev`). Jamais utilisés en production."""

from config import env

from .base import *  # noqa: F403
from .base import INSTALLED_APPS, MIDDLEWARE_SITE

DEBUG = True
ALLOWED_HOSTS = ["*"]
OTP_DEBUG_CODE = env.texte("OTP_DEBUG_CODE", "")
INSTALLED_APPS = [*INSTALLED_APPS, "django.contrib.messages"]
STYLEGUIDE_ENABLED = True
DEV_INBOX_ENABLED = True
SCHEMA_ENABLED = True
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"
SESSION_COOKIE_NAME = "lgsid"
CSRF_COOKIE_NAME = "lgcsrf"
MIDDLEWARE = list(MIDDLEWARE_SITE)
