"""Verrou Redis à jeton : garantit qu'une seule instance de `beat` tourne (CDC §4.3)."""

import uuid

import redis


class VerrouRedis:
    def __init__(self, client: redis.Redis, cle: str, duree_s: int = 30):
        self.client = client
        self.cle = cle
        self.duree_s = duree_s
        self.jeton = uuid.uuid4().hex

    def acquerir(self) -> bool:
        """Prend le verrou s'il est libre (SET NX EX)."""
        return bool(self.client.set(self.cle, self.jeton, nx=True, ex=self.duree_s))

    def _est_a_moi(self, pipe) -> bool:
        valeur = pipe.get(self.cle)
        return valeur is not None and valeur.decode() == self.jeton

    def renouveler(self) -> bool:
        """Prolonge le verrou seulement s'il nous appartient encore (transaction optimiste)."""
        with self.client.pipeline() as pipe:
            try:
                pipe.watch(self.cle)
                if not self._est_a_moi(pipe):
                    return False
                pipe.multi()
                pipe.expire(self.cle, self.duree_s)
                pipe.execute()
                return True
            except redis.WatchError:
                return False

    def liberer(self) -> bool:
        with self.client.pipeline() as pipe:
            try:
                pipe.watch(self.cle)
                if not self._est_a_moi(pipe):
                    return False
                pipe.multi()
                pipe.delete(self.cle)
                pipe.execute()
                return True
            except redis.WatchError:
                return False
