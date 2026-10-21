"""Fournisseurs de paiement Mobile Money (CDC §7.11, EF-ABO-04) : interface, factice (local et tests), KKiaPay.

Décision V10 (2026-10-17) : KKiaPay sera le fournisseur réel ; seul son squelette est livré, branché au lancement
payant. Tant que `SUBSCRIPTION_ENABLED` est faux, aucun de ces fournisseurs n'est appelé hors des tests.
"""

import hashlib
import hmac
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


@dataclass(frozen=True)
class Initiation:
    """Réponse du fournisseur au lancement d'un paiement : référence, et statut s'il est déjà connu."""

    reference: str
    statut: str = "pending"  # pending | succeeded | failed


@dataclass(frozen=True)
class Evenement:
    """Événement de webhook décodé : identifiant unique (idempotence), référence du paiement, nouveau statut."""

    identifiant: str
    reference: str
    statut: str  # succeeded | failed | refunded


class ErreurPaiement(Exception):
    """Le fournisseur a refusé ou n'a pas répondu (le paiement n'est pas lancé)."""


class PaymentProvider(ABC):
    nom: str = ""

    @abstractmethod
    def initier(self, *, montant: int, methode: str, telephone: str, cle: str) -> Initiation:
        """Lance un paiement (demande de validation envoyée au téléphone du payeur)."""

    @abstractmethod
    def verifier(self, reference: str) -> str:
        """Statut actuel chez le fournisseur : pending, succeeded, failed ou refunded."""

    @abstractmethod
    def rembourser(self, reference: str) -> None:
        """Rembourse un paiement réussi."""

    @abstractmethod
    def signature_valide(self, corps: bytes, entetes: dict) -> bool:
        """Vérifie que le webhook vient bien du fournisseur."""

    @abstractmethod
    def lire_evenement(self, corps: bytes) -> Evenement:
        """Décode le corps d'un webhook (après vérification de la signature)."""


class PaiementFactice(PaymentProvider):
    """Déterministe, sans réseau : la référence dérive de la clé d'idempotence ; les numéros finissant par 0 échouent.

    Les webhooks sont signés en HMAC-SHA256 avec `PAYMENT_WEBHOOK_SECRET` (en-tête `X-Signature`), comme un vrai
    fournisseur, pour que la chaîne complète (signature, idempotence, tâche) soit testée.
    """

    nom = "sandbox"

    def initier(self, *, montant: int, methode: str, telephone: str, cle: str) -> Initiation:
        if montant < 0:
            raise ErreurPaiement("Montant négatif.")
        reference = "sbx_" + hashlib.sha256(cle.encode()).hexdigest()[:24]
        return Initiation(
            reference=reference, statut="failed" if telephone.endswith("0") else "pending"
        )

    def verifier(self, reference: str) -> str:
        return "pending"

    def rembourser(self, reference: str) -> None:
        return None

    @staticmethod
    def signer(corps: bytes) -> str:
        secret = getattr(settings, "PAYMENT_WEBHOOK_SECRET", "") or "secret-factice"
        return hmac.new(secret.encode(), corps, hashlib.sha256).hexdigest()

    def signature_valide(self, corps: bytes, entetes: dict) -> bool:
        recue = entetes.get("X-Signature") or entetes.get("x-signature") or ""
        return hmac.compare_digest(recue, self.signer(corps))

    def lire_evenement(self, corps: bytes) -> Evenement:
        donnees = json.loads(corps)
        return Evenement(
            identifiant=str(donnees["event_id"]),
            reference=str(donnees["reference"]),
            statut=str(donnees["status"]),
        )


class PaiementKkiapay(PaymentProvider):
    """Squelette KKiaPay (décision V10) : à compléter avec la documentation et les clés du contrat au lancement payant."""

    nom = "kkiapay"

    def __init__(self):
        if not getattr(settings, "KKIAPAY_PRIVATE_KEY", ""):
            raise ImproperlyConfigured(
                "KKIAPAY_PRIVATE_KEY manquante : KKiaPay n'est pas encore branché."
            )

    def initier(self, *, montant: int, methode: str, telephone: str, cle: str) -> Initiation:
        raise NotImplementedError(
            "KKiaPay : à brancher au lancement payant (docs/plan-actions-v2.md §7 bis)."
        )

    def verifier(self, reference: str) -> str:
        raise NotImplementedError

    def rembourser(self, reference: str) -> None:
        raise NotImplementedError

    def signature_valide(self, corps: bytes, entetes: dict) -> bool:
        return False  # refuse tout tant que la vérification réelle n'est pas écrite

    def lire_evenement(self, corps: bytes) -> Evenement:
        raise NotImplementedError


_FOURNISSEURS = {"fake": PaiementFactice, "sandbox": PaiementFactice, "kkiapay": PaiementKkiapay}


def fournisseur(nom: str | None = None) -> PaymentProvider:
    """Fournisseur configuré (`PAYMENT_PROVIDER`), ou celui nommé dans l'URL d'un webhook."""
    cle = nom or settings.PAYMENT_PROVIDER
    if cle not in _FOURNISSEURS:
        raise ImproperlyConfigured(f"Fournisseur de paiement inconnu : {cle}")
    return _FOURNISSEURS[cle]()
