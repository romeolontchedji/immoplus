"""WebSocket (CDC §10.8) : réception seulement, plus la conversation ouverte à l'écran.

Protection : ticket à usage unique, 5 connexions par utilisateur, trame de 8 Ko, 30 événements par minute,
fermeture après 60 s sans `ping`. Codes : 4401 ticket invalide, 4403 compte suspendu, 4429 trop d'événements.
"""

import asyncio
import json
import time
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from apps.accounts import selectors as comptes
from apps.core import presence, redis_file, temps_reel

from . import selectors, ws

MAX_CONNEXIONS = 5
TAILLE_TRAME_MAX = 8 * 1024
EVENEMENTS_PAR_MINUTE = 30
INACTIVITE_S = 60


class MessagerieConsumer(AsyncWebsocketConsumer):
    inactivite_s = INACTIVITE_S  # surchargé dans les tests

    async def connect(self):
        self.utilisateur_id = self.appareil_id = None
        self.compte_connexion = False
        ticket = parse_qs(self.scope.get("query_string", b"").decode()).get("ticket", [""])[0]
        identite = await database_sync_to_async(ws.consommer)(ticket)
        if identite is None:
            await self.close(code=4401)
            return
        self.utilisateur_id, self.appareil_id = identite["utilisateur_id"], identite["appareil_id"]
        if not await database_sync_to_async(comptes.utilisateur_actif)(self.utilisateur_id):
            await self.close(code=4403)
            return
        if not await database_sync_to_async(self._reserver_connexion)():
            await self.close(code=4429)
            return
        self.compte_connexion = True
        self.groupe = temps_reel.groupe(self.utilisateur_id)
        await self.channel_layer.group_add(self.groupe, self.channel_name)
        await self.accept()
        self.dernier_signe = time.monotonic()
        self.evenements = []
        self.garde = asyncio.create_task(self._surveiller())

    def _reserver_connexion(self) -> bool:
        r = redis_file.client()
        cle = f"ws:connexions:{self.utilisateur_id}"
        total = r.incr(cle)
        r.expire(cle, 7200)  # filet de sécurité si une déconnexion n'a pas pu décrémenter
        if total > MAX_CONNEXIONS:
            r.decr(cle)
            return False
        return True

    def _liberer_connexion(self) -> None:
        r = redis_file.client()
        if int(r.get(f"ws:connexions:{self.utilisateur_id}") or 0) > 0:
            r.decr(f"ws:connexions:{self.utilisateur_id}")
        presence.effacer(self.utilisateur_id, self.appareil_id)

    async def _surveiller(self):
        """Ferme la connexion sans `ping` depuis `inactivite_s` secondes (la présence expire avec elle)."""
        try:
            while True:
                await asyncio.sleep(min(1.0, self.inactivite_s / 4))
                if time.monotonic() - self.dernier_signe > self.inactivite_s:
                    await self.close(code=4408)
                    return
        except asyncio.CancelledError:
            return

    async def disconnect(self, code):
        garde = getattr(self, "garde", None)
        if garde:
            garde.cancel()
        if getattr(self, "groupe", None):
            await self.channel_layer.group_discard(self.groupe, self.channel_name)
        if self.compte_connexion:
            await database_sync_to_async(self._liberer_connexion)()

    def _limite_atteinte(self) -> bool:
        maintenant = time.monotonic()
        self.evenements = [t for t in self.evenements if maintenant - t < 60]
        self.evenements.append(maintenant)
        return len(self.evenements) > EVENEMENTS_PAR_MINUTE

    async def receive(self, text_data=None, bytes_data=None):
        if text_data is None or len(text_data.encode()) > TAILLE_TRAME_MAX:
            await self.close(code=1009)
            return
        if self._limite_atteinte():
            await self.send(json.dumps({"type": "error", "data": {"code": 4429}}))
            await self.close(code=4429)
            return
        try:
            trame = json.loads(text_data)
            type_ = trame["type"]
            data = trame.get("data") or {}
        except (ValueError, KeyError, TypeError):
            await self.send(json.dumps({"type": "error", "data": {"code": "bad_frame"}}))
            return
        self.dernier_signe = time.monotonic()
        if type_ == "ping":
            await database_sync_to_async(presence.rafraichir)(self.utilisateur_id, self.appareil_id)
            await self.send(json.dumps({"type": "pong", "data": {}}))
        elif type_ == "conversation.focus":
            await database_sync_to_async(self._focus)(data.get("conversation_id"))
        else:
            await self.send(json.dumps({"type": "error", "data": {"code": "unknown_event"}}))

    def _focus(self, conversation_id) -> None:
        """Pose la présence si l'utilisateur est participant de la conversation ; sinon (ou si nul) l'efface."""
        if conversation_id:
            try:
                selectors.conversation_du_participant(self.utilisateur_id, conversation_id)
            except Exception:  # noqa: BLE001 - non participant : même effet que « aucune conversation »
                presence.effacer(self.utilisateur_id, self.appareil_id)
                return
            presence.poser(self.utilisateur_id, self.appareil_id, conversation_id)
        else:
            presence.effacer(self.utilisateur_id, self.appareil_id)

    async def evenement(self, message):
        """Relaie un événement du groupe `user.{id}` au client."""
        await self.send(json.dumps(message["evenement"]))
