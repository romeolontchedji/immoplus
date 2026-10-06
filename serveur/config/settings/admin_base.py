"""Socle commun des réglages d'administration (production et développement). Ne s'utilise pas seul."""

import copy

from .base import *  # noqa: F403
from .base import INSTALLED_APPS, MIDDLEWARE
from .base import TEMPLATES as _TEMPLATES

ROOT_URLCONF = "config.urls_admin"
INSTALLED_APPS = [*INSTALLED_APPS, "django.contrib.admin", "django.contrib.messages", "adminsite"]
MIDDLEWARE = [*MIDDLEWARE, "django.contrib.messages.middleware.MessageMiddleware"]

TEMPLATES = copy.deepcopy(_TEMPLATES)
TEMPLATES[0]["OPTIONS"]["context_processors"].append(
    "django.contrib.messages.context_processors.messages"
)

# Sessions en base seule (hors du Redis partagé), courtes ; cookie distinct de celui du site.
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_AGE = 8 * 3600
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Strict"
