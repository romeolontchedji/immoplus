"""Réglages de `web-api` et `realtime` : site, API, WebSocket. Jamais de route d'administration ici."""

from django.core.exceptions import ImproperlyConfigured

from config import env

from .base import *  # noqa: F403
from .base import MIDDLEWARE_SITE

ROOT_URLCONF = "config.urls_public"
DEBUG = False

if env.texte("SECRET_KEY") == "" or env.texte("SECRET_KEY").startswith("dev-"):
    raise ImproperlyConfigured("SECRET_KEY de production absente ou de développement.")
if env.booleen("DEBUG") or env.texte("OTP_DEBUG_CODE"):
    raise ImproperlyConfigured(
        "DEBUG et OTP_DEBUG_CODE sont interdits avec les réglages « public »."
    )

SECRET_KEY = env.texte("SECRET_KEY")
PRODUCTION = True
# Le défi anti-robot factice se remplit tout seul : en production, il laisserait passer n'importe quel robot.
if env.texte("CAPTCHA_PROVIDER", "fake") in ("", "fake"):
    raise ImproperlyConfigured(
        "CAPTCHA_PROVIDER=turnstile est obligatoire en production (clés Cloudflare)."
    )
# Hôtes servis : le site et l'API du domaine, plus l'adresse interne des contrôles de santé (curl 127.0.0.1).
# Sans cette liste, Django répondrait 400 à toute requête en production.
_DOMAINE = env.texte("DOMAIN")
if not _DOMAINE or _DOMAINE == "localhost":
    raise ImproperlyConfigured("DOMAIN de production absent (ex. immoplus.bj).")
ALLOWED_HOSTS = [f"www.{_DOMAINE}", f"api.{_DOMAINE}", "127.0.0.1", "localhost"]
JWT_SIGNING_KEY = env.texte("JWT_SIGNING_KEY")  # distincte de celle de l'administration
OTP_HMAC_KEY = env.texte("OTP_HMAC_KEY")
# `realtime` (WebSocket) vérifie les jetons mais n'émet aucun code OTP : il ne reçoit pas cette clé (moindre privilège).
_TEMPS_REEL = env.texte("IMMOPLUS_PROCESSUS") == "realtime"
_EXIGEES = [("JWT_SIGNING_KEY", JWT_SIGNING_KEY)] + (
    [] if _TEMPS_REEL else [("OTP_HMAC_KEY", OTP_HMAC_KEY)]
)
for _nom, _valeur in _EXIGEES:
    if not _valeur or _valeur.startswith("dev-"):
        raise ImproperlyConfigured(f"{_nom} de production absente ou de développement.")
_CLES = [c for c in (SECRET_KEY, JWT_SIGNING_KEY, OTP_HMAC_KEY) if c]
if len(set(_CLES)) != len(_CLES):
    raise ImproperlyConfigured(
        "SECRET_KEY, JWT_SIGNING_KEY et OTP_HMAC_KEY doivent être trois clés différentes."
    )

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
MIDDLEWARE = list(MIDDLEWARE_SITE)

# Caddy porte la redirection HTTP→HTTPS et l'en-tête HSTS (includeSubDomains) : Django ne les double pas.
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SILENCED_SYSTEM_CHECKS = ["security.W008", "security.W021"]
USE_X_FORWARDED_FOR = True  # Caddy écrase tout X-Forwarded-For reçu
