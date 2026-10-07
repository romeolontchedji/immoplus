"""Défi anti-robot du site : Cloudflare Turnstile et version factice (CDC §5.3)."""

import json
import urllib.error
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

URL_VERIFICATION = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


class CaptchaProvider(ABC):
    @abstractmethod
    def verifier(self, jeton: str | None, ip: str | None = None) -> bool:
        """Vrai si le défi est réussi. Faux si le jeton est absent, refusé ou si la vérification échoue."""


class FakeCaptchaProvider(CaptchaProvider):
    JETON_VALIDE = "captcha-ok"

    def verifier(self, jeton, ip=None) -> bool:
        return jeton == self.JETON_VALIDE


class TurnstileProvider(CaptchaProvider):
    def __init__(self):
        self.secret = getattr(settings, "TURNSTILE_SECRET", "")
        if not self.secret:
            raise ImproperlyConfigured(
                "TURNSTILE_SECRET est requis pour le fournisseur « turnstile »."
            )

    def verifier(self, jeton, ip=None) -> bool:
        if not jeton:
            return False
        donnees = {"secret": self.secret, "response": jeton}
        if ip:
            donnees["remoteip"] = ip
        requete = urllib.request.Request(  # noqa: S310
            URL_VERIFICATION, data=urllib.parse.urlencode(donnees).encode(), method="POST"
        )
        try:
            with urllib.request.urlopen(requete, timeout=5) as reponse:  # noqa: S310
                return bool(json.loads(reponse.read()).get("success"))
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            return False  # en cas de doute, le défi est considéré comme échoué


def fournisseur() -> CaptchaProvider:
    nom = getattr(settings, "CAPTCHA_PROVIDER", "fake")
    if nom == "fake":
        return FakeCaptchaProvider()
    if nom == "turnstile":
        return TurnstileProvider()
    raise ImproperlyConfigured(f"Fournisseur anti-robot inconnu : {nom}")
