"""Réglages du service `migrer` : toutes les applications (site et administration) pour créer tout le schéma.

Seul processus qui exécute du DDL, avec le rôle PostgreSQL `migrate`. Il ne sert aucune requête.
"""

from config import env

from .admin_base import *  # noqa: F403
from .admin_base import INSTALLED_APPS

DEBUG = False
SECRET_KEY = env.texte("SECRET_KEY", "migration-uniquement")
ADMIN_ALLOWED_IPS = []

# La commande `lintmigrations` (verifier_tout.sh) vit ici : c'est le seul processus qui voit les migrations.
INSTALLED_APPS = [*INSTALLED_APPS, "django_migration_linter"]
