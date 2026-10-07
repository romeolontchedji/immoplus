"""Fournisseurs de SMS : interface, implémentation console (développement) et HTTP générique (CDC §8.9)."""

import hashlib
import hmac
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

CLE_BOITE_DEV = "dev:boite-sms"


@dataclass(frozen=True)
class ResultatSms:
    reference: str
    cout_xof: int | None = None


class ErreurFournisseurSms(Exception):
    """L'envoi a échoué après les reprises (le message n'est pas parti)."""


class SmsProvider(ABC):
    @abstractmethod
    def envoyer(self, numero_e164: str, message: str) -> ResultatSms:
        """Envoie `message` ; lève `ErreurFournisseurSms` si l'envoi échoue."""


class ConsoleSmsProvider(SmsProvider):
    """Écrit le message sur la sortie d'erreur et dans la boîte de développement. Interdit en production."""

    def __init__(self):
        if not (settings.DEBUG or getattr(settings, "DEV_INBOX_ENABLED", False)):
            raise ImproperlyConfigured(
                "Le fournisseur SMS « console » est réservé au développement."
            )

    def envoyer(self, numero_e164: str, message: str) -> ResultatSms:
        sys.stderr.write(f"[SMS console] à {numero_e164} : {message}\n")
        boite = cache.get(CLE_BOITE_DEV, [])
        boite.insert(0, {"a": numero_e164, "message": message})
        cache.set(CLE_BOITE_DEV, boite[:50], 3600)
        return ResultatSms(reference=f"console-{int(time.time() * 1000)}", cout_xof=0)


class GenericHttpSmsProvider(SmsProvider):
    """Agrégateur SMS configurable : corps JSON signé (HMAC-SHA256), délai maximal, reprises, lecture du coût.

    Réglages : SMS_HTTP_URL, SMS_HTTP_TOKEN, SMS_HTTP_SECRET, SMS_HTTP_TIMEOUT_S, SMS_HTTP_RETRIES,
    SMS_HTTP_REF_FIELD (défaut « id »), SMS_HTTP_COST_FIELD (défaut « cost »).
    Agrégateur retenu : [À FOURNIR : agrégateur SMS] — adapter le corps et les champs ci-dessous.
    """

    def __init__(self):
        self.url = getattr(settings, "SMS_HTTP_URL", "")
        if not self.url:
            raise ImproperlyConfigured(
                "SMS_HTTP_URL est requis pour le fournisseur « generic_http »."
            )
        self.jeton = getattr(settings, "SMS_HTTP_TOKEN", "")
        self.secret = getattr(settings, "SMS_HTTP_SECRET", "").encode()
        self.delai = float(getattr(settings, "SMS_HTTP_TIMEOUT_S", 5))
        self.reprises = int(getattr(settings, "SMS_HTTP_RETRIES", 2))
        self.champ_ref = getattr(settings, "SMS_HTTP_REF_FIELD", "id")
        self.champ_cout = getattr(settings, "SMS_HTTP_COST_FIELD", "cost")

    def _requete(self, corps: bytes) -> urllib.request.Request:
        en_tetes = {"Content-Type": "application/json", "Authorization": f"Bearer {self.jeton}"}
        if self.secret:
            en_tetes["X-Signature"] = hmac.new(self.secret, corps, hashlib.sha256).hexdigest()
        return urllib.request.Request(self.url, data=corps, headers=en_tetes, method="POST")  # noqa: S310

    def envoyer(self, numero_e164: str, message: str) -> ResultatSms:
        corps = json.dumps({"to": numero_e164, "message": message}).encode()
        derniere: Exception | None = None
        for essai in range(self.reprises + 1):
            try:
                with urllib.request.urlopen(self._requete(corps), timeout=self.delai) as reponse:  # noqa: S310
                    donnees = json.loads(reponse.read() or b"{}")
                cout = donnees.get(self.champ_cout)
                return ResultatSms(
                    reference=str(donnees.get(self.champ_ref, "")),
                    cout_xof=int(cout) if cout is not None else None,
                )
            except urllib.error.HTTPError as erreur:
                derniere = erreur
                if erreur.code < 500:  # une erreur du client ne se corrige pas en réessayant
                    break
            except (urllib.error.URLError, TimeoutError, OSError, ValueError) as erreur:
                derniere = erreur
            time.sleep(min(0.2 * (2**essai), 2))
        raise ErreurFournisseurSms(f"envoi impossible : {type(derniere).__name__}") from derniere


def fournisseur() -> SmsProvider:
    nom = getattr(settings, "SMS_PROVIDER", "console")
    if nom == "console":
        return ConsoleSmsProvider()
    if nom == "generic_http":
        return GenericHttpSmsProvider()
    raise ImproperlyConfigured(f"Fournisseur SMS inconnu : {nom}")
