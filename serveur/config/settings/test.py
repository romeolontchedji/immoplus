"""Réglages des tests : PostgreSQL réel, cache et canaux en mémoire, tâches immédiates."""

import secrets

from .base import *  # noqa: F403

DEBUG = False
SECRET_KEY = secrets.token_urlsafe(50)  # aléatoire à chaque session de test, jamais écrit en dur
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
STYLEGUIDE_ENABLED = True
DEV_INBOX_ENABLED = True
SCHEMA_ENABLED = True
ALLOWED_HOSTS = ["*"]
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"
REDIS_QUEUE_FAKE = True
SMS_PROVIDER = "console"
