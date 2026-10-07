"""Attestation d'appareil (Play Integrity côté Android) : interface, version factice, squelette (CDC §5.3)."""

from abc import ABC, abstractmethod

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class ErreurAttestation(Exception):
    """Le fournisseur d'attestation n'a pas pu répondre (distinct d'une attestation refusée)."""


class DeviceAttestationProvider(ABC):
    @abstractmethod
    def verifier(self, jeton: str | None, installation_id: str | None) -> bool:
        """Vrai si l'appareil est jugé authentique. Faux (jamais d'exception) si le jeton est absent ou refusé."""


class FakeAttestationProvider(DeviceAttestationProvider):
    """Développement et tests : le jeton « attestation-valide » est accepté, tout autre est refusé."""

    JETON_VALIDE = "attestation-valide"

    def verifier(self, jeton, installation_id) -> bool:
        return jeton == self.JETON_VALIDE


class PlayIntegrityAttestationProvider(DeviceAttestationProvider):
    """Squelette Play Integrity : décode le jeton via l'API Google puis contrôle le verdict.

    À compléter avant la mise en production : [À FOURNIR : identifiant du paquet Android, compte de service Google].
    Étapes : (1) obtenir un jeton OAuth du compte de service ; (2) POST
    `https://playintegrity.googleapis.com/v1/{package}:decodeIntegrityToken` ; (3) exiger
    `appRecognitionVerdict == PLAY_RECOGNIZED` et `deviceRecognitionVerdict` contenant `MEETS_DEVICE_INTEGRITY` ;
    (4) comparer le `nonce` à `installation_id`.
    """

    def __init__(self):
        self.paquet = getattr(settings, "PLAY_INTEGRITY_PACKAGE", "")
        self.compte_service = getattr(settings, "PLAY_INTEGRITY_CREDENTIALS", "")
        if not (self.paquet and self.compte_service):
            raise ImproperlyConfigured(
                "PLAY_INTEGRITY_PACKAGE et PLAY_INTEGRITY_CREDENTIALS sont requis pour « play_integrity »."
            )

    def verifier(self, jeton, installation_id) -> bool:
        if not jeton:
            return False
        raise ErreurAttestation("Appel à l'API Play Integrity à implémenter (voir la docstring).")


def fournisseur() -> DeviceAttestationProvider:
    nom = getattr(settings, "DEVICE_ATTESTATION_PROVIDER", "fake")
    if nom == "fake":
        return FakeAttestationProvider()
    if nom == "play_integrity":
        return PlayIntegrityAttestationProvider()
    raise ImproperlyConfigured(f"Fournisseur d'attestation inconnu : {nom}")
