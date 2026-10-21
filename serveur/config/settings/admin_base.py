"""Socle commun des réglages d'administration (production et développement). Ne s'utilise pas seul."""

import copy

from config import env

from .base import *  # noqa: F403
from .base import INSTALLED_APPS, MIDDLEWARE
from .base import TEMPLATES as _TEMPLATES

ROOT_URLCONF = "config.urls_admin"

# `adminsite.apps.AdminImmoplusConfig` remplace `django.contrib.admin` : connexion par e-mail et mot de passe.
APPLICATIONS_ADMIN = [
    "django.contrib.messages",
    "axes",
    "adminsite.admin_config.AdminImmoplusConfig",
    "adminsite",
]
INSTALLED_APPS = [*INSTALLED_APPS, *APPLICATIONS_ADMIN]

MIDDLEWARE_ADMIN = [
    "adminsite.middleware.ListeBlancheIpMiddleware",
    *MIDDLEWARE,
    "django.contrib.messages.middleware.MessageMiddleware",
]
# La durée de session s'insère après l'authentification ; axes en dernier.
_i = MIDDLEWARE_ADMIN.index("django.contrib.auth.middleware.AuthenticationMiddleware") + 1
MIDDLEWARE_ADMIN[_i:_i] = [
    "adminsite.middleware.DureeDeSessionMiddleware",
    "adminsite.middleware.DoubleAuthMiddleware",
]
# Double authentification : un code à 6 chiffres envoyé par courriel à chaque connexion (adminsite/double_auth.py).
# Désactivable en développement seulement (ADMIN_2FA_ACTIVE=0) ; toujours active en production (settings/admin.py).
ADMIN_2FA_ACTIVE = env.booleen("ADMIN_2FA_ACTIVE", True)
MIDDLEWARE_ADMIN.append("axes.middleware.AxesMiddleware")
MIDDLEWARE = MIDDLEWARE_ADMIN

AUTHENTICATION_BACKENDS_ADMIN = [
    "axes.backends.AxesStandaloneBackend",
    "adminsite.authentification.AuthPersonnel",
]
AUTHENTICATION_BACKENDS = AUTHENTICATION_BACKENDS_ADMIN

TEMPLATES = copy.deepcopy(_TEMPLATES)
# Les gabarits d'`adminsite` priment (index « Vue d'ensemble »), puis ceux du site, puis les apps.
TEMPLATES[0]["DIRS"] = [BASE_DIR / "adminsite" / "templates", *TEMPLATES[0]["DIRS"]]  # noqa: F405
TEMPLATES[0]["OPTIONS"]["context_processors"].append(
    "django.contrib.messages.context_processors.messages"
)

# Sessions dans une table propre (`admin_sessions`), jamais celle du site ; cookie distinct.
SESSION_ENGINE = "adminsite.stockage_sessions"
SESSION_COOKIE_AGE = 60 * 60
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
# Historique des échecs (page « Échecs de connexion ») : sans lui, la page reste vide.
AXES_ENABLE_ACCESS_FAILURE_LOG = True
AXES_VERBOSE = False

# L'administration charge ses feuilles de style depuis son propre domaine ; les styles en ligne du site d'administration
# de Django (attributs `style`) sont tolérés ici, jamais les scripts en ligne.
CSP_STYLE_SOURCES = ["'self'", "'unsafe-inline'"]
CSP_SCRIPT_SOURCES = ["'self'"]
CSP_FRAME_SOURCES = ["'none'"]
LOGIN_URL = "/login/"
