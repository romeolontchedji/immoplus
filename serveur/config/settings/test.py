"""Réglages des tests : PostgreSQL réel, cache et canaux en mémoire, tâches immédiates."""

import secrets

from . import admin_base as _admin
from .base import *  # noqa: F403
from .base import MIDDLEWARE_SITE

# Le schéma de test contient aussi les tables de l'administration ; les intergiciels restent ceux du site
# (les tests de l'administration substituent les leurs, voir adminsite/tests).
INSTALLED_APPS = _admin.INSTALLED_APPS
TEMPLATES = _admin.TEMPLATES
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
SILENCED_SYSTEM_CHECKS = [
    "axes.W002",
    "axes.W003",
]  # intergiciels du site en test (voir adminsite/tests)
MIDDLEWARE = [*MIDDLEWARE_SITE, "django.contrib.messages.middleware.MessageMiddleware"]
AXES_FAILURE_LIMIT = _admin.AXES_FAILURE_LIMIT
AXES_COOLOFF_TIME = _admin.AXES_COOLOFF_TIME
AXES_LOCKOUT_PARAMETERS = _admin.AXES_LOCKOUT_PARAMETERS
AXES_RESET_ON_SUCCESS = _admin.AXES_RESET_ON_SUCCESS
AXES_IPWARE_PROXY_COUNT = _admin.AXES_IPWARE_PROXY_COUNT
AXES_IPWARE_META_PRECEDENCE_ORDER = _admin.AXES_IPWARE_META_PRECEDENCE_ORDER
AXES_ENABLE_ACCESS_FAILURE_LOG = _admin.AXES_ENABLE_ACCESS_FAILURE_LOG
AXES_USERNAME_FORM_FIELD = _admin.AXES_USERNAME_FORM_FIELD
AXES_VERBOSE = False
