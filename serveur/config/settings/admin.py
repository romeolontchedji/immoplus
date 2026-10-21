"""Réglages du processus `admin` en production : autre clé, autre cookie, autre rôle PostgreSQL."""

from django.core.exceptions import ImproperlyConfigured

from config import env

from .admin_base import *  # noqa: F403

DEBUG = False

if env.texte("SECRET_KEY") == "" or env.texte("SECRET_KEY").startswith("dev-"):
    raise ImproperlyConfigured("SECRET_KEY de l'administration absente ou de développement.")
if env.booleen("DEBUG"):
    raise ImproperlyConfigured("DEBUG est interdit avec les réglages « admin ».")

SECRET_KEY = env.texte("SECRET_KEY")
# Seul l'hôte d'administration, plus l'adresse interne du contrôle de santé.
_DOMAINE = env.texte("DOMAIN")
if not _DOMAINE or _DOMAINE == "localhost":
    raise ImproperlyConfigured("DOMAIN de production absent (ex. immoplus.bj).")
ALLOWED_HOSTS = [f"pilotage.{_DOMAINE}", "127.0.0.1", "localhost"]
CSRF_TRUSTED_ORIGINS = [f"https://pilotage.{_DOMAINE}"]
ADMIN_2FA_ACTIVE = True  # jamais désactivable en production
PRODUCTION = True
ADMIN_ALLOWED_IPS = env.liste("ADMIN_ALLOWED_IPS")  # vide = tout refuser
PRIVATE_FILES_KEY = env.texte("PRIVATE_FILES_KEY")  # injectée uniquement dans admin et backup

SESSION_COOKIE_NAME = "__Host-lgadm"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_NAME = "__Host-lgadmcsrf"
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = 31536000

# Caddy porte la redirection HTTP→HTTPS et l'en-tête HSTS (includeSubDomains) : Django ne les double pas.
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SILENCED_SYSTEM_CHECKS = ["security.W008", "security.W021"]
USE_X_FORWARDED_FOR = True  # Caddy écrase tout X-Forwarded-For reçu
