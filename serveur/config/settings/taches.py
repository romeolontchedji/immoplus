"""Réglages des tâches de fond en production qui ne servent aucune requête : `worker-media` et `beat`.

Ils ne reçoivent volontairement ni la clé des jetons ni celle des codes OTP (moindre privilège) : les réglages
« public » les exigent, ces processus ne pouvaient donc pas démarrer avec eux.
"""

from django.core.exceptions import ImproperlyConfigured

from config import env

from .base import *  # noqa: F403

DEBUG = False

if env.texte("SECRET_KEY") == "" or env.texte("SECRET_KEY").startswith("dev-"):
    raise ImproperlyConfigured("SECRET_KEY de production absente ou de développement.")
if env.booleen("DEBUG"):
    raise ImproperlyConfigured("DEBUG est interdit avec les réglages « taches ».")

SECRET_KEY = env.texte("SECRET_KEY")
PRODUCTION = True
ALLOWED_HOSTS: list[str] = []  # aucune requête HTTP
