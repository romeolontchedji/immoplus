"""Outils HTTP transverses : adresse du client derrière Caddy, identifiant d'installation."""

import re

from django.conf import settings

_INSTALLATION = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


def ip_client(request) -> str | None:
    """Adresse du client. Derrière Caddy (qui écrase tout `X-Forwarded-For` reçu), on lit la dernière valeur."""
    if getattr(settings, "USE_X_FORWARDED_FOR", False):
        transmis = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if transmis:
            return transmis.split(",")[-1].strip() or None
    return request.META.get("REMOTE_ADDR") or None


def installation_id(request) -> str | None:
    """Valeur saine de `X-Installation-Id`, ou None."""
    valeur = request.headers.get("X-Installation-Id", "")
    return valeur if _INSTALLATION.match(valeur) else None


def user_agent(request) -> str:
    return request.headers.get("User-Agent", "")[:255]
