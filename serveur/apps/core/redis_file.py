"""Accès à `redis-queue` pour les compteurs de sécurité (jamais le cache à éviction : CDC §8.4)."""

import redis
from django.conf import settings

_client = None


def client() -> redis.Redis:
    """Client partagé. En test, `REDIS_QUEUE_FAKE` le remplace par un serveur en mémoire."""
    global _client
    if _client is None:
        if getattr(settings, "REDIS_QUEUE_FAKE", False):
            import fakeredis

            _client = fakeredis.FakeRedis(decode_responses=True)
        else:
            _client = redis.Redis.from_url(
                settings.REDIS_QUEUE_URL, decode_responses=True, socket_timeout=2
            )
    return _client


def reinitialiser() -> None:
    """Oublie le client (tests)."""
    global _client
    _client = None
