"""Administration en développement (HTTP local, secret de développement autorisé). Jamais en production."""

from .admin_base import *  # noqa: F403

DEBUG = True
ALLOWED_HOSTS = ["*"]
SESSION_COOKIE_NAME = "lgadm"
CSRF_COOKIE_NAME = "lgadmcsrf"
ADMIN_ALLOWED_IPS = None  # pas de liste blanche en développement
USE_X_FORWARDED_FOR = False
CSRF_TRUSTED_ORIGINS = [
    "http://pilotage.localhost:8080",
    "http://admin.localhost:8080",
    "http://localhost:8080",
    "http://www.localhost:8080",
]
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False
