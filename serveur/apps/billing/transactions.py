"""Paiements par la fenêtre KKiaPay du site : abonnement des gérants, alertes des locataires.

Déroulé : `preparer` crée une transaction « en attente » et donne au navigateur de quoi ouvrir la fenêtre ; le payeur
règle chez KKiaPay ; le navigateur renvoie l'identifiant KKiaPay ; `confirmer` interroge KKiaPay avec la clé privée et
ne valide qu'un paiement réussi, du bon montant, jamais utilisé deux fois. Le navigateur n'est jamais cru sur parole.
"""

import json
import uuid

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.audit import services as audit
from apps.core import parametres
from apps.core.errors import ErreurMetier
from apps.core.providers import paiement as fournisseurs

from . import services
from .enums import StatutPaiement
from .models import Transaction


def configure() -> bool:
    return bool(settings.KKIAPAY_PRIVATE_KEY and settings.KKIAPAY_PUBLIC_KEY and settings.KKIAPAY_SECRET)


def alertes_payantes() -> bool:
    return bool(parametres.lire("PAID_ALERTS_ENABLED"))


def prix_alerte() -> int:
    return int(parametres.lire("ALERT_PRICE") or 0)


def _verifier(reference: str) -> dict:
    """Transaction vue par KKiaPay (point de substitution des tests)."""
    return fournisseurs.PaiementKkiapay().transaction(reference)


def formules_payantes() -> list[dict]:
    return [p for p in services.plans() if p.get("price") and p["code"] != services.PLAN_GRATUIT]


def preparer(utilisateur, objet: str, plan_code: str = "") -> tuple[Transaction, dict]:
    """Crée la transaction en attente ; retourne aussi les paramètres d'ouverture de la fenêtre KKiaPay."""
    if not configure():
        raise ErreurMetier(
            "payment_unavailable", "Le paiement n'est pas disponible pour le moment.", statut=503
        )
    if objet == Transaction.Objet.ABONNEMENT:
        if utilisateur.role != "gerant" or not services.actif():
            raise ErreurMetier(
                "feature_disabled", "Cette fonctionnalité n'est pas disponible.", statut=404
            )
        choisie = next((p for p in formules_payantes() if p["code"] == plan_code), None)
        if choisie is None:
            raise ErreurMetier(
                "validation_error", "Formule inconnue.", champs={"plan_code": ["Formule inconnue"]}
            )
        montant = int(choisie["price"])
    elif objet == Transaction.Objet.ALERTE:
        if utilisateur.role != "client" or not alertes_payantes() or prix_alerte() <= 0:
            raise ErreurMetier(
                "feature_disabled", "Cette fonctionnalité n'est pas disponible.", statut=404
            )
        montant, plan_code = prix_alerte(), ""
    else:
        raise ErreurMetier("validation_error", "Objet de paiement inconnu.")
    attente = Transaction.objects.create(
        user=utilisateur, objet=objet, plan_code=plan_code, amount=montant
    )
    return attente, {
        "reference": str(attente.pk),
        "amount": montant,
        "key": settings.KKIAPAY_PUBLIC_KEY,
        "sandbox": bool(settings.KKIAPAY_SANDBOX),
    }


def _montant_vu(vue: dict) -> int:
    try:
        return int(float(vue.get("amount") or 0))
    except (TypeError, ValueError):
        return 0


def confirmer(utilisateur, reference: str, id_kkiapay: str) -> Transaction:
    """Vérifie le paiement chez KKiaPay et, s'il est réussi et du bon montant, en tire l'effet (idempotent)."""
    id_kkiapay = (id_kkiapay or "").strip()[:120]
    try:
        attente = Transaction.objects.filter(pk=reference, user=utilisateur).first()
    except (ValueError, TypeError):  # identifiant mal formé
        attente = None
    if attente is None or not id_kkiapay:
        raise ErreurMetier("not_found", "Paiement introuvable.", statut=404)
    return _appliquer(attente, id_kkiapay)


def _appliquer(attente: Transaction, id_kkiapay: str) -> Transaction:
    """Vérifie chez KKiaPay puis applique l'effet du paiement ; commun au retour de la fenêtre et au webhook."""
    utilisateur = attente.user
    if attente.status == StatutPaiement.SUCCEEDED:
        return attente
    try:
        vue = _verifier(id_kkiapay)
    except fournisseurs.ErreurPaiement as erreur:
        raise ErreurMetier(
            "payment_unverified",
            "Paiement non vérifié pour l'instant. Réessaie dans un instant.",
            statut=502,
        ) from erreur
    etat, montant = str(vue.get("status", "")).upper(), _montant_vu(vue)
    if etat != "SUCCESS" or montant < attente.amount:
        if etat == "FAILED":
            Transaction.objects.filter(pk=attente.pk).update(status=StatutPaiement.FAILED)
        audit.enregistrer(
            "paiement.kkiapay_refuse",
            acteur=utilisateur,
            metadata={"transaction": str(attente.pk), "etat": etat, "montant": montant},
        )
        raise ErreurMetier(
            "payment_failed", "Le paiement n'a pas abouti. Tu n'as pas été débité.", statut=402
        )
    try:
        with transaction.atomic():
            ligne = Transaction.objects.select_for_update().get(pk=attente.pk)
            if ligne.status == StatutPaiement.SUCCEEDED:
                return ligne
            ligne.provider_ref, ligne.status = id_kkiapay, StatutPaiement.SUCCEEDED
            ligne.paid_at = timezone.now()
            ligne.save(update_fields=["provider_ref", "status", "paid_at"])
            if ligne.objet == Transaction.Objet.ABONNEMENT:
                from apps.accounts.models import GerantProfile

                profil = GerantProfile.objects.get(user=utilisateur)
                services.activer_formule(profil.pk, ligne.plan_code)
            audit.enregistrer(
                "paiement.kkiapay",
                acteur=utilisateur,
                metadata={
                    "transaction": str(ligne.pk),
                    "objet": ligne.objet,
                    "montant": ligne.amount,
                },
            )
    except IntegrityError as erreur:  # l'identifiant KKiaPay a déjà servi pour un autre paiement
        raise ErreurMetier("conflict", "Ce paiement a déjà été utilisé.", statut=409) from erreur
    return ligne


# --------------------------------------------------------------------------- crédits d'alerte
def credits_alerte(utilisateur) -> int:
    return Transaction.objects.filter(
        user=utilisateur,
        objet=Transaction.Objet.ALERTE,
        status=StatutPaiement.SUCCEEDED,
        used_at__isnull=True,
    ).count()


def consommer_credit(utilisateur, alerte) -> None:
    """Une alerte se crée contre un paiement réussi non encore utilisé ; sinon 402 `payment_required`."""
    credit = (
        Transaction.objects.select_for_update()
        .filter(
            user=utilisateur,
            objet=Transaction.Objet.ALERTE,
            status=StatutPaiement.SUCCEEDED,
            used_at__isnull=True,
        )
        .order_by("paid_at")
        .first()
    )
    if credit is None:
        raise ErreurMetier(
            "payment_required",
            f"Une alerte coûte {prix_alerte()} F (paiement unique). Paie depuis la page « Mes alertes » du site.",
            statut=402,
        )
    credit.used_at, credit.alert = timezone.now(), alerte
    credit.save(update_fields=["used_at", "alert"])


# --------------------------------------------------------------------------- webhook
def _reference_dans(etat) -> str | None:
    """Notre référence (identifiant de transaction) renvoyée par KKiaPay dans `stateData` (texte ou objet)."""
    valeurs = list(etat.values()) if isinstance(etat, dict) else [etat]
    for valeur in valeurs:
        try:
            return str(uuid.UUID(str(valeur)))
        except ValueError:
            continue
    return None


def recevoir_webhook(corps: bytes, entetes: dict) -> str:
    """Webhook KKiaPay : secret vérifié, puis le paiement est revérifié auprès de KKiaPay (le corps n'est pas cru).

    Retourne un mot pour le journal. Lève `invalid_signature` (403) si le secret est faux, `payment_unverified` (502)
    si KKiaPay ne répond pas : KKiaPay réessaie alors lui-même (5 fois), ce qui rattrape une panne passagère."""
    if not configure() or not settings.KKIAPAY_WEBHOOK_SECRET:
        raise ErreurMetier("payment_unavailable", "Paiement non configuré.", statut=503)
    if not fournisseurs.PaiementKkiapay().signature_valide(corps, entetes):
        audit.enregistrer("paiement.webhook_refuse", metadata={"fournisseur": "kkiapay"})
        raise ErreurMetier("invalid_signature", "Signature invalide.", statut=403)
    try:
        donnees = json.loads(corps)
    except ValueError:
        return "ignore"
    if not isinstance(donnees, dict):
        return "ignore"
    id_kkiapay = str(donnees.get("transactionId") or "")[:120]
    attente = Transaction.objects.filter(provider_ref=id_kkiapay).first() if id_kkiapay else None
    if attente is None:
        reference = _reference_dans(donnees.get("stateData"))
        attente = Transaction.objects.filter(pk=reference).first() if reference else None
    if attente is None or not id_kkiapay:
        return "inconnu"
    if donnees.get("event") == "transaction.failed":
        Transaction.objects.filter(pk=attente.pk, status=StatutPaiement.PENDING).update(
            status=StatutPaiement.FAILED
        )
        return "echec"
    if donnees.get("event") != "transaction.success":
        return "ignore"
    try:
        _appliquer(attente, id_kkiapay)
    except ErreurMetier as erreur:
        if erreur.code == "payment_unverified":
            raise
        return "refuse"  # montant ou statut incohérent : déjà journalisé, inutile que KKiaPay réessaie
    return "applique"
