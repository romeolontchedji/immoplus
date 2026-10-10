"""Fournisseurs de notifications push : interface, console (développement et tests), Expo, squelette FCM (CDC §8.9)."""

import json
import sys
import time
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured

CLE_BOITE_PUSH_DEV = "dev:boite-push"
EXPO_URL = "https://exp.host/--/api/v2/push/send"


@dataclass(frozen=True)
class ResultatPush:
    """`ok` : accepté par le fournisseur. `jeton_invalide` : à désactiver. Sinon : échec à reprendre."""

    ok: bool
    jeton_invalide: bool = False
    erreur: str = ""


class PushProvider(ABC):
    @abstractmethod
    def envoyer(
        self, jeton: str, titre: str, corps: str, data: dict, collapse_key: str | None = None
    ) -> ResultatPush:
        """Envoie un push à un appareil. Ne lève jamais : le résultat dit ce qui s'est passé."""


class ConsolePushProvider(PushProvider):
    """Écrit le push sur la sortie d'erreur et dans la boîte de développement ; un jeton `invalide-…` est refusé."""

    def __init__(self):
        if not (settings.DEBUG or getattr(settings, "DEV_INBOX_ENABLED", False)):
            raise ImproperlyConfigured(
                "Le fournisseur push « console » est réservé au développement."
            )

    def envoyer(self, jeton, titre, corps, data, collapse_key=None) -> ResultatPush:
        if jeton.startswith("invalide"):
            return ResultatPush(ok=False, jeton_invalide=True, erreur="jeton invalide")
        if jeton.startswith("panne"):
            return ResultatPush(ok=False, erreur="panne simulée")
        sys.stderr.write(f"[push console] {titre} : {corps}\n")
        boite = cache.get(CLE_BOITE_PUSH_DEV, [])
        boite.insert(
            0,
            {
                "jeton": jeton,
                "titre": titre,
                "corps": corps,
                "data": data,
                "collapse": collapse_key,
            },
        )
        cache.set(CLE_BOITE_PUSH_DEV, boite[:100], 3600)
        return ResultatPush(ok=True)


class ExpoPushProvider(PushProvider):
    """API HTTP d'Expo (application mobile Expo). Réglages : PUSH_HTTP_TIMEOUT_S."""

    def __init__(self):
        self.delai = float(getattr(settings, "PUSH_HTTP_TIMEOUT_S", 5))
        self.url = getattr(settings, "EXPO_PUSH_URL", EXPO_URL)

    def envoyer(self, jeton, titre, corps, data, collapse_key=None) -> ResultatPush:
        message = {"to": jeton, "title": titre, "body": corps, "data": data, "sound": "default"}
        if collapse_key:
            message["collapseId"] = collapse_key  # remplace la précédente dans le tiroir (Android)
        requete = urllib.request.Request(  # noqa: S310
            self.url,
            data=json.dumps(message).encode(),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(requete, timeout=self.delai) as reponse:  # noqa: S310  # nosec B310
                reponse_json = json.loads(reponse.read() or b"{}")
        except urllib.error.HTTPError as erreur:
            return ResultatPush(ok=False, erreur=f"http {erreur.code}")
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as erreur:
            return ResultatPush(ok=False, erreur=type(erreur).__name__)
        ticket = reponse_json.get("data") or {}
        if isinstance(ticket, list):
            ticket = ticket[0] if ticket else {}
        if ticket.get("status") == "ok":
            return ResultatPush(ok=True)
        if (ticket.get("details") or {}).get("error") == "DeviceNotRegistered":
            return ResultatPush(ok=False, jeton_invalide=True, erreur="DeviceNotRegistered")
        return ResultatPush(ok=False, erreur=str(ticket.get("message", "refus"))[:200])


class FcmPushProvider(PushProvider):
    """Squelette FCM (HTTP v1) : à compléter avec le compte de service du projet Firebase [À FOURNIR]."""

    def envoyer(self, jeton, titre, corps, data, collapse_key=None) -> ResultatPush:
        raise NotImplementedError(
            "FCM : fournir le compte de service Firebase puis implémenter l'appel HTTP v1."
        )


def fournisseur() -> PushProvider:
    nom = getattr(settings, "PUSH_PROVIDER", "console")
    if nom == "console":
        return ConsolePushProvider()
    if nom == "expo":
        return ExpoPushProvider()
    if nom == "fcm":
        return FcmPushProvider()
    raise ImproperlyConfigured(f"Fournisseur push inconnu : {nom}")


def attendre(secondes: float) -> None:  # pragma: no cover - point d'extension pour les tests
    time.sleep(secondes)
