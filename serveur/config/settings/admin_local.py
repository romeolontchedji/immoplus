"""Administration en développement (HTTP local, secret de développement autorisé). Jamais en production."""

from .admin_base import *  # noqa: F403

DEBUG = True
ALLOWED_HOSTS = ["*"]
SESSION_COOKIE_NAME = "lgadm"
CSRF_COOKIE_NAME = "lgadmcsrf"
