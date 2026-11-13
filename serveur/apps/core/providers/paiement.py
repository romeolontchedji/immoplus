"""Fournisseurs de paiement Mobile Money (CDC §7.11, EF-ABO-04) : interface, factice (local et tests), KKiaPay.

Décision V10 (2026-10-17) : KKiaPay est le fournisseur réel. Le payeur règle dans la fenêtre KKiaPay du site ;
le serveur vérifie la transaction (`apps/billing/transactions.py`). Tant que les paiements sont éteints dans
l'administration (`SUBSCRIPTION_ENABLED`, `PAID_ALERTS_ENABLED`), rien n'est appelé.
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
    """KKiaPay : le payeur règle dans la fenêtre KKiaPay ouverte par le site (aucun appel serveur pour initier) ;
    le serveur vérifie ensuite la transaction avec la clé privée (`transaction`)."""

    nom = "kkiapay"
    URL_REELLE = "https://api.kkiapay.me/api/v1/transactions/status"
    URL_TEST = "https://api-sandbox.kkiapay.me/api/v1/transactions/status"

    def __init__(self):
        if not all(
            getattr(settings, cle, "")
            for cle in ("KKIAPAY_PUBLIC_KEY", "KKIAPAY_PRIVATE_KEY", "KKIAPAY_SECRET")
        ):
            raise ImproperlyConfigured(
                "Clés KKiaPay absentes (KKIAPAY_PUBLIC_KEY, KKIAPAY_PRIVATE_KEY, KKIAPAY_SECRET)."
            )

    def transaction(self, reference: str) -> dict:
        """Transaction vue par KKiaPay : {"status": "SUCCESS"|"FAILED"|…, "amount": int, …}."""
        import urllib.error
        import urllib.request

        url = self.URL_TEST if settings.KKIAPAY_SANDBOX else self.URL_REELLE
        requete = urllib.request.Request(  # noqa: S310 - URL fixe (HTTPS), jamais saisie par un utilisateur
            url,
            data=json.dumps({"transactionId": reference}).encode(),
            headers={
                "Content-Type": "application/json",
                "x-api-key": settings.KKIAPAY_PUBLIC_KEY,
                "x-private-key": settings.KKIAPAY_PRIVATE_KEY,
                "x-secret-key": settings.KKIAPAY_SECRET,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(requete, timeout=15) as reponse:  # noqa: S310  # nosec B310 - URL fixe ci-dessus (HTTPS)
                return json.loads(reponse.read() or b"{}")
        except (urllib.error.URLError, TimeoutError, ValueError) as erreur:
            raise ErreurPaiement("KKiaPay ne répond pas.") from erreur

    def initier(self, *, montant: int, methode: str, telephone: str, cle: str) -> Initiation:
        raise NotImplementedError("KKiaPay : le paiement se fait dans la fenêtre du site.")

    def verifier(self, reference: str) -> str:
        etat = str(self.transaction(reference).get("status", "")).upper()
        return {"SUCCESS": "succeeded", "FAILED": "failed"}.get(etat, "pending")

    def rembourser(self, reference: str) -> None:
        raise NotImplementedError("Remboursement : depuis le tableau de bord KKiaPay.")

    def signature_valide(self, corps: bytes, entetes: dict) -> bool:
        recue = entetes.get("x-kkiapay-secret") or entetes.get("X-Kkiapay-Secret") or ""
        attendue = getattr(settings, "KKIAPAY_WEBHOOK_SECRET", "")
        return bool(attendue) and hmac.compare_digest(recue, attendue)

    def lire_evenement(self, corps: bytes) -> Evenement:
        raise NotImplementedError


_FOURNISSEURS = {"fake": PaiementFactice, "sandbox": PaiementFactice, "kkiapay": PaiementKkiapay}


def fournisseur(nom: str | None = None) -> PaymentProvider:
    """Fournisseur configuré (`PAYMENT_PROVIDER`), ou celui nommé dans l'URL d'un webhook."""
    cle = nom or settings.PAYMENT_PROVIDER
    if cle not in _FOURNISSEURS:
        raise ImproperlyConfigured(f"Fournisseur de paiement inconnu : {cle}")
    return _FOURNISSEURS[cle]()
