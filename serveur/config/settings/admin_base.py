"""Socle commun des réglages d'administration (production et développement). Ne s'utilise pas seul."""

import copy

from .base import *  # noqa: F403
from .base import INSTALLED_APPS, MIDDLEWARE
from .base import TEMPLATES as _TEMPLATES

ROOT_URLCONF = "config.urls_admin"

# `adminsite.apps.AdminLogeoConfig` remplace `django.contrib.admin` : son site par défaut impose la 2FA.
APPLICATIONS_ADMIN = [
    "django.contrib.messages",
    "django_otp",
    "django_otp.plugins.otp_totp",
    "django_otp.plugins.otp_static",
    "axes",
    "adminsite.admin_config.AdminLogeoConfig",
    "adminsite",
]
INSTALLED_APPS = [*INSTALLED_APPS, *APPLICATIONS_ADMIN]

MIDDLEWARE_ADMIN = [
    "adminsite.middleware.ListeBlancheIpMiddleware",
    *MIDDLEWARE,
    "django.contrib.messages.middleware.MessageMiddleware",
]
# django-otp s'insère après l'authentification ; la durée de session après django-otp ; axes en dernier.
_i = MIDDLEWARE_ADMIN.index("django.contrib.auth.middleware.AuthenticationMiddleware") + 1
MIDDLEWARE_ADMIN[_i:_i] = [
    "django_otp.middleware.OTPMiddleware",
    "adminsite.middleware.DureeDeSessionMiddleware",
]
MIDDLEWARE_ADMIN.append("axes.middleware.AxesMiddleware")
MIDDLEWARE = MIDDLEWARE_ADMIN

AUTHENTICATION_BACKENDS_ADMIN = [
    "axes.backends.AxesStandaloneBackend",
    "adminsite.authentification.AuthPersonnel",
]
AUTHENTICATION_BACKENDS = AUTHENTICATION_BACKENDS_ADMIN

TEMPLATES = copy.deepcopy(_TEMPLATES)
TEMPLATES[0]["OPTIONS"]["context_processors"].append(
    "django.contrib.messages.context_processors.messages"
)

# Sessions dans une table propre (`admin_sessions`), jamais celle du site ; cookie distinct.
SESSION_ENGINE = "adminsite.stockage_sessions"
SESSION_COOKIE_AGE = 30 * 60
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Strict"
SESSION_SAVE_EVERY_REQUEST = True

# Verrouillage du compte après 5 échecs (le seuil et la durée sont repris des paramètres à l'exécution).
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 0.5  # heures
AXES_LOCKOUT_PARAMETERS = ["ip_address", "username"]  # verrouille sur l'une OU l'autre
AXES_IPWARE_PROXY_COUNT = 1  # une seule couche de proxy : Caddy
AXES_IPWARE_META_PRECEDENCE_ORDER = ["HTTP_X_FORWARDED_FOR", "REMOTE_ADDR"]
AXES_RESET_ON_SUCCESS = True
AXES_USERNAME_FORM_FIELD = "username"
AXES_VERBOSE = False

# L'administration charge ses feuilles de style depuis son propre domaine ; les styles en ligne du site d'administration
# de Django (attributs `style`) sont tolérés ici, jamais les scripts en ligne.
CSP_STYLE_SOURCES = ["'self'", "'unsafe-inline'"]
CSP_SCRIPT_SOURCES = ["'self'"]
CSP_FRAME_SOURCES = ["'none'"]
OTP_TOTP_ISSUER = "Logeo"
LOGIN_URL = "/login/"
