"""Diffusion d'événements aux appareils d'un utilisateur par la couche de canaux (groupe `user.{id}`, CDC §10.8).

La diffusion est « au mieux » : elle ne lève jamais d'erreur (la garantie de livraison est portée par HTTP).
"""

import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

journal = logging.getLogger(__name__)


def groupe(utilisateur_id) -> str:
    return f"user.{utilisateur_id}"


def diffuser(utilisateur_id, type_evenement: str, data: dict) -> None:
    couche = get_channel_layer()
    if couche is None:
        return
    try:
        async_to_sync(couche.group_send)(
            groupe(utilisateur_id),
            {"type": "evenement", "evenement": {"type": type_evenement, "data": data}},
        )
    except Exception:  # noqa: BLE001 - le temps réel est au mieux
        journal.warning("diffusion_echouee", extra={"evenement": type_evenement})
