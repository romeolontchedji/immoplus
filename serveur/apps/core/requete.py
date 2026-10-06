"""Identifiant de requête propagé aux journaux et aux tâches (contexte d'exécution)."""

import re
import uuid
from contextvars import ContextVar

_identifiant: ContextVar[str] = ContextVar("identifiant_requete", default="-")
_VALIDE = re.compile(r"^[A-Za-z0-9-]{8,64}$")


def nouvel_identifiant(propose: str | None = None) -> str:
    """Reprend l'identifiant du proxy s'il est sain, sinon en fabrique un."""
    if propose and _VALIDE.match(propose):
        return propose
    return uuid.uuid4().hex


def definir(identifiant: str):
    return _identifiant.set(identifiant)


def courant() -> str:
    return _identifiant.get()
