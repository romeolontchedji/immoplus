"""Réglages de `web-api` et `realtime` : site, API, WebSocket. Jamais de route d'administration ici."""

from config import env

from .base import *  # noqa: F403
from .base import MIDDLEWARE

ROOT_URLCONF = "config.urls_public"
DEBUG = False

if env.texte("SECRET_KEY") == "" or env.texte("SECRET_KEY").startswith("dev-"):
    from django.core.exceptions import ImproperlyConfigured

    raise ImproperlyConfigured("SECRET_KEY de production absente ou de développement.")
if env.booleen("DEBUG") or env.texte("OTP_DEBUG_CODE"):
    from django.core.exceptions import ImproperlyConfigured

    raise ImproperlyConfigured(
        "DEBUG et OTP_DEBUG_CODE sont interdits avec les réglages « public »."
    )

SECRET_KEY = env.texte("SECRET_KEY")
JWT_SIGNING_KEY = env.texte("JWT_SIGNING_KEY")  # distincte de celle de l'administration

# Site : cookie `__Host-lgsid`, sessions en `cached_db`.
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"
SESSION_COOKIE_NAME = "__Host-lgsid"
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_PATH = "/"
CSRF_COOKIE_NAME = "__Host-lgcsrf"
CSRF_COOKIE_SECURE = True
CSRF_TRUSTED_ORIGINS = [f"https://www.{env.texte('DOMAIN')}"]
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = 31536000
MIDDLEWARE = list(MIDDLEWARE)

# Caddy porte la redirection HTTP→HTTPS et l'en-tête HSTS (includeSubDomains) : Django ne les double pas.
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SILENCED_SYSTEM_CHECKS = ["security.W008", "security.W021"]
