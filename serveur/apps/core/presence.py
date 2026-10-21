"""Présence « conversation ouverte à l'écran » par appareil (CDC §11.9).

Elle est portée par la connexion WebSocket : posée par `conversation.focus`, rafraîchie par chaque `ping`,
effacée à la déconnexion, et expire seule après 60 s sans `ping`. Elle ne vit jamais seule.
"""

from . import redis_file

EXPIRATION_S = 60


def _cle(utilisateur_id, appareil_id) -> str:
    return f"presence:{utilisateur_id}:{appareil_id}"


def poser(utilisateur_id, appareil_id, conversation_id) -> None:
    redis_file.client().set(
        _cle(utilisateur_id, appareil_id), str(conversation_id), ex=EXPIRATION_S
    )


def rafraichir(utilisateur_id, appareil_id) -> None:
    redis_file.client().expire(_cle(utilisateur_id, appareil_id), EXPIRATION_S)


def effacer(utilisateur_id, appareil_id) -> None:
    redis_file.client().delete(_cle(utilisateur_id, appareil_id))


def appareils_sur_conversation(utilisateur_id, conversation_id) -> set[str]:
    """Appareils de l'utilisateur dont l'écran montre actuellement cette conversation."""
    r = redis_file.client()
    trouves = set()
    for cle in r.scan_iter(match=f"presence:{utilisateur_id}:*", count=100):
        if r.get(cle) == str(conversation_id):
            trouves.add(cle.rsplit(":", 1)[1])
    return trouves
