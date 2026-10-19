"""Réglages communs à tous les processus. Les réglages `public`, `admin`, `local` et `test` les complètent."""

from pathlib import Path

from config import env

BASE_DIR = Path(__file__).resolve().parent.parent.parent

DEBUG = False
SECRET_KEY = env.texte("SECRET_KEY", "dev-secret-ne-jamais-utiliser-en-production")
ALLOWED_HOSTS = env.liste("ALLOWED_HOSTS", "localhost,127.0.0.1")
DOMAIN = env.texte("DOMAIN", "localhost")
OTP_DEBUG_CODE = env.texte("OTP_DEBUG_CODE", "")

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "channels",
    "apps.core",
    "apps.accounts",
    "apps.listings",
    "apps.media",
    "apps.chat",
    "apps.notifications",
    "apps.moderation",
    "apps.billing",
    "apps.audit",
    "web",
]

MIDDLEWARE = [
    "apps.core.middleware.IdentifiantRequeteMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "apps.core.middleware.EnTetesSecuriteMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
]

# Le site (pas l'administration) déconnecte une session dont la version de sécurité a changé.
MIDDLEWARE_SITE = [
    *MIDDLEWARE[: MIDDLEWARE.index("django.contrib.auth.middleware.AuthenticationMiddleware") + 1],
    "web.middleware.VersionDeSessionMiddleware",
    "apps.core.acces_application.AccesApplicationMiddleware",  # 426 et 503 (le site et l'API, pas l'administration)
]

ROOT_URLCONF = "config.urls_public"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "web" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "web.context_processors.navigation",
                "web.context_processors.contact",
            ],
        },
    }
]

# --- Base de données : un rôle PostgreSQL par processus (app, admin_app, migrate) ---
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env.texte("DB_NAME", "logeo"),
        "USER": env.texte("DB_USER", "app"),
        "PASSWORD": env.texte("DB_PASSWORD", "app-dev"),
        "HOST": env.texte("DB_HOST", "localhost"),
        "PORT": env.texte("DB_PORT", "5432"),
        "CONN_MAX_AGE": 0,
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {
            "pool": {"min_size": 2, "max_size": env.entier("DB_POOL_MAX", 10), "timeout": 5},
            "options": f"-c statement_timeout={env.entier('DB_STATEMENT_TIMEOUT_MS', 5000)}",
        },
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Redis : `redis-cache` (éviction LRU, perdable) et `redis-queue` (AOF, sans éviction) ---
REDIS_CACHE_URL = env.texte("REDIS_CACHE_URL", "redis://localhost:6379/0")
REDIS_QUEUE_URL = env.texte("REDIS_QUEUE_URL", "redis://localhost:6379/1")

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_CACHE_URL,
        "KEY_PREFIX": "logeo",
    }
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [REDIS_QUEUE_URL], "capacity": 500, "expiry": 30},
    }
}

# --- Celery : files séparées pour qu'une vidéo lente ne retarde jamais un message ---
CELERY_BROKER_URL = REDIS_QUEUE_URL
CELERY_RESULT_BACKEND = None
CELERY_TASK_DEFAULT_QUEUE = "default"
CELERY_TASK_ROUTES = {
    "apps.notifications.*": {"queue": "notifications"},
    "apps.media.*": {"queue": "media"},
}
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_BROKER_TRANSPORT_OPTIONS = {"visibility_timeout": 3600}
CELERY_TIMEZONE = "Africa/Porto-Novo"
CELERY_WORKER_HIJACK_ROOT_LOGGER = (
    False  # garde la journalisation de Django (et donc le suivi des erreurs)
)

# --- Authentification ---
AUTH_USER_MODEL = "accounts.User"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.Argon2PasswordHasher"]
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]

# --- Régionalisation : français, fuseau du Bénin, montants en FCFA entiers ---
LANGUAGE_CODE = "fr"
TIME_ZONE = "Africa/Porto-Novo"
USE_I18N = True
USE_TZ = True
LOCALE_PATHS = [BASE_DIR / "locale"]

# --- Fichiers statiques et médias ---
STATIC_URL = "/static/"
STATIC_ROOT = Path(env.texte("STATIC_ROOT", str(BASE_DIR / "var" / "static")))
STATICFILES_DIRS = [BASE_DIR / "web" / "static"]
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(env.texte("MEDIA_PUBLIC_ROOT", str(BASE_DIR / "var" / "media_public")))
MEDIA_TMP_ROOT = Path(env.texte("MEDIA_TMP_ROOT", str(BASE_DIR / "var" / "media_tmp")))
MEDIA_DISK_REFUS_POURCENT = 85

# --- API ---
REST_FRAMEWORK = {
    "EXCEPTION_HANDLER": "apps.core.errors.gestionnaire_exceptions",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": ["apps.accounts.api.authentication.AuthJwt"],
    "DEFAULT_PERMISSION_CLASSES": ["apps.core.api.permissions.RefusParDefaut"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "UNAUTHENTICATED_USER": None,
}
SPECTACULAR_SETTINGS = {
    "TITLE": "API Logeo",
    "DESCRIPTION": "API REST de Logeo (additive uniquement, versionnée sous /v1).",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SWAGGER_UI_DIST": "/static/vendor/swagger-ui",
    "SWAGGER_UI_FAVICON_HREF": "/static/vendor/swagger-ui/favicon-32x32.png",
}

# --- Fournisseurs (interfaces dans apps.core.providers) ---
SMS_PROVIDER = env.texte("SMS_PROVIDER", "console")
PUSH_PROVIDER = env.texte("PUSH_PROVIDER", "console")
STORAGE_PROVIDER = env.texte("STORAGE_PROVIDER", "local")
VIDEO_PROVIDER = env.texte("VIDEO_PROVIDER", "local_ffmpeg")
PAYMENT_PROVIDER = env.texte("PAYMENT_PROVIDER", "fake")
PAYMENT_WEBHOOK_SECRET = env.texte(
    "PAYMENT_WEBHOOK_SECRET"
)  # signature des webhooks (factice et réels)
KKIAPAY_PRIVATE_KEY = env.texte("KKIAPAY_PRIVATE_KEY")  # décision V10 : branché au lancement payant
# Attestation que l'application est authentique (Play Integrity, App Attest) : `fake` tant qu'elle n'est pas développée.
DEVICE_ATTESTATION_PROVIDER = env.texte("DEVICE_ATTESTATION_PROVIDER", "fake")
# Anti-robot du site : `turnstile` (Cloudflare, gratuit) ou `fake` (tests ; refusé en production, settings/public.py).
CAPTCHA_PROVIDER = env.texte("CAPTCHA_PROVIDER") or "fake"
TURNSTILE_SECRET = env.texte(
    "TURNSTILE_SECRET"
)  # clé secrète Turnstile (vérification côté serveur)
TURNSTILE_SITE_KEY = env.texte(
    "TURNSTILE_SITE_KEY"
)  # clé publique Turnstile (affichage du défi dans la page)
# Clés de test publiées par Cloudflare (le défi réussit toujours) : signalées comme erreur en production.
TURNSTILE_CLES_DE_TEST = ("1x00000000000000000000AA", "1x0000000000000000000000000000000AA")
PRODUCTION = False  # vrai dans les réglages public, admin et taches (garde-fous de démarrage)
SMS_HTTP_URL = env.texte("SMS_HTTP_URL")
SMS_HTTP_TOKEN = env.texte("SMS_HTTP_TOKEN")
SMS_HTTP_SECRET = env.texte("SMS_HTTP_SECRET")

# --- Clés de sécurité : distinctes entre elles et de SECRET_KEY ; refusées en production si elles viennent d'ici ---
JWT_SIGNING_KEY = env.texte("JWT_SIGNING_KEY", "dev-jwt-ne-jamais-utiliser-en-production")
OTP_HMAC_KEY = env.texte("OTP_HMAC_KEY", "dev-otp-ne-jamais-utiliser-en-production")
REDIS_QUEUE_FAKE = False

# --- Drapeaux (valeur initiale ; `app_settings` fait foi une fois la phase 8 livrée) ---
SUBSCRIPTION_ENABLED = env.booleen("SUBSCRIPTION_ENABLED", False)

# --- Courriels : codes de l'administration et alertes d'erreurs ---
# N'importe quel serveur SMTP convient. Gratuit pour notre volume : Brevo (300 / jour), Gmail avec un « mot de passe
# d'application » (500 / jour), ou la messagerie du nom de domaine. Seul le `worker` envoie (il a accès à Internet).
# Envoi par SMTP (production) ; en développement, settings/local.py affiche les courriels dans la console.
EMAIL_BACKEND = env.texte("EMAIL_BACKEND") or "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env.texte("EMAIL_HOST", "localhost")  # adresse du serveur SMTP du fournisseur
EMAIL_PORT = env.entier("EMAIL_PORT", 587)  # 587 avec STARTTLS (le plus courant), 465 avec SSL
EMAIL_HOST_USER = env.texte("EMAIL_HOST_USER")  # identifiant SMTP (souvent l'adresse d'envoi)
EMAIL_HOST_PASSWORD = env.texte("EMAIL_HOST_PASSWORD")  # mot de passe ou clé SMTP du fournisseur
EMAIL_USE_TLS = env.booleen("EMAIL_USE_TLS", True)  # chiffrement STARTTLS (port 587)
EMAIL_USE_SSL = env.booleen(
    "EMAIL_USE_SSL", False
)  # chiffrement SSL direct (port 465) ; jamais avec TLS
EMAIL_TIMEOUT = 15  # secondes avant d'abandonner un envoi (la tâche réessaie ensuite)
# Expéditeur affiché dans les courriels de Logeo.
DEFAULT_FROM_EMAIL = env.texte("DEFAULT_FROM_EMAIL") or "Logeo <no-reply@localhost>"

# --- Journalisation JSON ---
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"masque": {"()": "apps.core.logging.FiltreMasque"}},
    "formatters": {"json": {"()": "apps.core.logging.FormateurJson"}},
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "json", "filters": ["masque"]},
        # Suivi des erreurs (apps/core/erreurs.py) : regroupées, visibles dans l'administration, courriel limité.
        "erreurs": {"class": "apps.core.erreurs.JournalErreursHandler", "level": "ERROR"},
    },
    "root": {"handlers": ["console", "erreurs"], "level": env.texte("LOG_LEVEL", "INFO")},
}
# Adresses qui reçoivent un courriel à chaque nouvelle erreur (au plus une fois par heure et par erreur),
# séparées par des virgules. Vide : les erreurs restent visibles dans l'administration, sans courriel.
ERREURS_DESTINATAIRES = env.liste("ERREURS_DESTINATAIRES")

# --- En-têtes de sécurité (la CSP est posée par EnTetesSecuriteMiddleware) ---
CSP_SCRIPT_SOURCES = ["'self'", "https://challenges.cloudflare.com"]
USE_X_FORWARDED_FOR = False  # vrai derrière Caddy (réglages public et admin)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
