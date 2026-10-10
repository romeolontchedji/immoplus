"""Ticket de connexion WebSocket : usage unique, 30 secondes (CDC §10.8)."""

import json
import secrets

from apps.core import redis_file

DUREE_TICKET_S = 30


def emettre(utilisateur_id, appareil_id) -> str:
    ticket = secrets.token_urlsafe(32)
    redis_file.client().set(
        f"ws:ticket:{ticket}",
        json.dumps({"u": str(utilisateur_id), "d": str(appareil_id)}),
        ex=DUREE_TICKET_S,
    )
    return ticket


def consommer(ticket: str) -> dict | None:
    """Lit et détruit le ticket en une opération : le rejouer échoue toujours."""
    if not ticket or len(ticket) > 100:
        return None
    brut = redis_file.client().getdel(f"ws:ticket:{ticket}")
    if not brut:
        return None
    try:
        donnees = json.loads(brut)
        return {"utilisateur_id": donnees["u"], "appareil_id": donnees["d"]}
    except (ValueError, KeyError):
        return None
