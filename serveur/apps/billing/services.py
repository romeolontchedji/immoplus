"""Abonnement des gérants (CDC §7.11, EF-ABO-01 à 08) : prêt, testé, inactif.

Tant que `SUBSCRIPTION_ENABLED` est faux : `can_publish` répond toujours vrai, les points d'entrée répondent
`404 feature_disabled`, et chaque gérant vérifié porte le plan Gratuit V1 (l'activation future ne demande aucune
migration de données). Décision du porteur (2026-10-17) : aucun écran de paiement dans les applications en V1.
"""

import datetime
import logging

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.audit import services as audit
from apps.core import parametres
from apps.core.errors import ErreurMetier
from apps.core.providers import paiement as fournisseurs

from .enums import TRANSITIONS, Fournisseur, Methode, StatutAbonnement, StatutPaiement
from .models import Payment, Subscription

journal = logging.getLogger(__name__)
PLAN_GRATUIT = "free_v1"
STATUTS_PUBLIABLES = {StatutAbonnement.TRIALING, StatutAbonnement.ACTIVE, StatutAbonnement.PAST_DUE}


# --------------------------------------------------------------------------- drapeau et plans
def actif() -> bool:
    return bool(parametres.lire("SUBSCRIPTION_ENABLED"))


def exiger_actif() -> None:
    """EF-ABO-02 : les points d'entrée de l'abonnement n'existent pas tant que le drapeau est faux."""
    if not actif():
        raise ErreurMetier(
            "feature_disabled", "Cette fonctionnalité n'est pas disponible.", statut=404
        )


def plans() -> list[dict]:
    return [p for p in parametres.lire("PLANS") if p.get("active")]


def plan(code: str) -> dict:
    trouve = next((p for p in plans() if p["code"] == code), None)
    if trouve is None:
        raise ErreurMetier(
            "validation_error", "Plan inconnu.", champs={"plan_code": ["Plan inconnu ou inactif"]}
        )
    return trouve


def _fin_de_periode(debut: datetime.datetime, mois: int) -> datetime.datetime:
    return debut + datetime.timedelta(days=30 * max(1, mois))


# --------------------------------------------------------------------------- abonnement courant
def attribuer_gratuit(gerant_id) -> Subscription:
    """EF-ABO-06 : plan Gratuit V1 pour tout gérant vérifié ; sans effet s'il a déjà un abonnement non expiré."""
    existant = abonnement_courant(gerant_id, creer=False)
    if existant is not None:
        return existant
    maintenant = timezone.now()
    try:
        with transaction.atomic():
            return Subscription.objects.create(
                gerant_id=gerant_id, plan_code=PLAN_GRATUIT, status=StatutAbonnement.ACTIVE,
                current_period_start=maintenant, current_period_end=_fin_de_periode(maintenant, 1200),
            )  # fmt: skip
    except (
        IntegrityError
    ):  # attribution concurrente : l'index unique partiel garantit un seul abonnement vivant
        return abonnement_courant(gerant_id, creer=False)


def abonnement_courant(gerant_id, *, creer: bool = True) -> Subscription | None:
    courant = (
        Subscription.objects.filter(gerant_id=gerant_id)
        .exclude(status=StatutAbonnement.EXPIRED)
        .order_by("-created_at")
        .first()
    )
    if courant is None and creer and any(p["code"] == PLAN_GRATUIT for p in plans()):
        return attribuer_gratuit(gerant_id)
    return courant


def changer_statut(abonnement: Subscription, nouveau: str, *, motif: str = "") -> Subscription:
    """Seules les transitions de la machine à états (EF-ABO-08) sont permises."""
    if nouveau not in TRANSITIONS.get(abonnement.status, set()):
        raise ErreurMetier(
            "invalid_transition",
            f"Passage de « {abonnement.status} » à « {nouveau} » impossible.",
            statut=409,
        )
    ancien, abonnement.status = abonnement.status, nouveau
    if nouveau == StatutAbonnement.CANCELED:
        abonnement.canceled_at = timezone.now()
    abonnement.save(update_fields=["status", "canceled_at", "updated_at"])
    audit.enregistrer(
        "abonnement.statut",
        metadata={"abonnement": str(abonnement.pk), "de": ancien, "vers": nouveau, "motif": motif},
    )
    return abonnement


# --------------------------------------------------------------------------- point d'extension (EF-ABO-03)
def can_publish(gerant_id) -> bool:
    """Appelé à la création et à la publication d'une annonce ; toujours vrai tant que le drapeau est faux."""
    if not actif():
        return True
    courant = abonnement_courant(gerant_id)
    return courant is not None and courant.status in STATUTS_PUBLIABLES


# --------------------------------------------------------------------------- paiement
def _masquer(telephone: str) -> str:
    return telephone[:-4] + "••••" if len(telephone) > 4 else "••••"


def demarrer_paiement(
    gerant_id, *, plan_code: str, methode: str, telephone: str, cle: str
) -> Payment:
    """Lance un paiement Mobile Money ; idempotent par clé (un double appui ne débite jamais deux fois)."""
    exiger_actif()
    if not cle or len(cle) > 64:
        raise ErreurMetier(
            "validation_error",
            "Clé d'idempotence obligatoire.",
            champs={"idempotency_key": ["1 à 64 caractères"]},
        )
    deja = Payment.objects.filter(idempotency_key=cle).first()
    if deja is not None:
        if str(deja.gerant_id) != str(gerant_id):
            raise ErreurMetier("conflict", "Clé déjà utilisée.", statut=409)
        return deja
    if methode not in Methode.values:
        raise ErreurMetier(
            "validation_error", "Moyen de paiement inconnu.", champs={"method": ["Valeur inconnue"]}
        )
    choisi = plan(plan_code)
    if not choisi.get("price"):
        raise ErreurMetier(
            "validation_error", "Ce plan ne se paie pas.", champs={"plan_code": ["Plan gratuit"]}
        )
    fournisseur = fournisseurs.fournisseur()
    try:
        initiation = fournisseur.initier(
            montant=int(choisi["price"]), methode=methode, telephone=telephone, cle=cle
        )
    except fournisseurs.ErreurPaiement as erreur:
        raise ErreurMetier(
            "payment_failed", "Le paiement n'a pas pu être lancé. Réessaie.", statut=502
        ) from erreur
    paiement = Payment.objects.create(
        gerant_id=gerant_id, subscription=abonnement_courant(gerant_id), plan_code=plan_code,
        amount=int(choisi["price"]), provider=Fournisseur(fournisseur.nom), provider_ref=initiation.reference,
        method=methode, payer_phone_e164=telephone, status=initiation.statut, idempotency_key=cle,
    )  # fmt: skip
    audit.enregistrer(
        "paiement.demarre",
        metadata={"paiement": str(paiement.pk), "telephone": _masquer(telephone)},
    )
    return paiement


def annuler(gerant_id) -> Subscription:
    """L'abonnement s'arrête à la fin de la période payée (EF-ABO-08)."""
    exiger_actif()
    courant = abonnement_courant(gerant_id, creer=False)
    if courant is None or courant.plan_code == PLAN_GRATUIT:
        raise ErreurMetier("not_found", "Aucun abonnement payant à annuler.", statut=404)
    courant.cancel_at_period_end = True
    courant.save(update_fields=["cancel_at_period_end", "updated_at"])
    return courant


# --------------------------------------------------------------------------- webhooks (EF-ABO-05)
def recevoir_webhook(nom_fournisseur: str, corps: bytes, entetes: dict) -> tuple[Payment, bool]:
    """Signature vérifiée, événement enregistré une seule fois ; le traitement part en tâche asynchrone.

    Retourne (paiement, nouveau) : `nouveau` est faux quand l'événement avait déjà été reçu (idempotence).
    """
    try:
        fournisseur = fournisseurs.fournisseur(nom_fournisseur)
    except Exception as erreur:  # noqa: BLE001 - fournisseur inconnu ou non configuré
        raise ErreurMetier("not_found", "Fournisseur inconnu.", statut=404) from erreur
    if not fournisseur.signature_valide(corps, entetes):
        audit.enregistrer("paiement.webhook_refuse", metadata={"fournisseur": nom_fournisseur})
        raise ErreurMetier("invalid_signature", "Signature invalide.", statut=400)
    evenement = fournisseur.lire_evenement(corps)
    with transaction.atomic():
        paiement = (
            Payment.objects.select_for_update().filter(provider_ref=evenement.reference).first()
        )
        if paiement is None:
            raise ErreurMetier("not_found", "Paiement inconnu.", statut=404)
        if any(e.get("event_id") == evenement.identifiant for e in paiement.webhook_events):
            return paiement, False
        paiement.webhook_events = [
            *paiement.webhook_events,
            {"event_id": evenement.identifiant, "received_at": timezone.now().isoformat(),
             "signature_valid": True, "status": evenement.statut},
        ]  # fmt: skip
        paiement.save(update_fields=["webhook_events"])
        identifiant = paiement.pk

        def planifier():
            from . import tasks

            tasks.appliquer_evenement.delay(str(identifiant), evenement.statut)

        transaction.on_commit(planifier)
    return paiement, True


@transaction.atomic
def appliquer_evenement(paiement_id, statut: str) -> Payment:
    """Tâche : paiement réussi → abonnement actif pour une nouvelle période ; échec → statut d'échec."""
    paiement = Payment.objects.select_for_update().get(pk=paiement_id)
    if statut not in StatutPaiement.values or paiement.status == statut:
        return paiement
    paiement.status = statut
    if statut == StatutPaiement.SUCCEEDED:
        paiement.paid_at = timezone.now()
        choisi = next(
            (p for p in parametres.lire("PLANS") if p["code"] == paiement.plan_code),
            {"period_months": 1},
        )
        courant = abonnement_courant(paiement.gerant_id, creer=False)
        maintenant = timezone.now()
        if (
            courant is not None
            and courant.plan_code == paiement.plan_code
            and courant.status in STATUTS_PUBLIABLES
        ):
            debut = max(
                courant.current_period_end, maintenant
            )  # renouvellement : la période s'ajoute
            courant.current_period_end = _fin_de_periode(debut, choisi["period_months"])
            courant.save(update_fields=["current_period_end", "updated_at"])
            if courant.status != StatutAbonnement.ACTIVE:
                changer_statut(courant, StatutAbonnement.ACTIVE, motif="paiement")
        else:
            if courant is not None:
                Subscription.objects.filter(pk=courant.pk).update(
                    status=StatutAbonnement.EXPIRED, updated_at=maintenant
                )
            courant = Subscription.objects.create(
                gerant_id=paiement.gerant_id, plan_code=paiement.plan_code, status=StatutAbonnement.ACTIVE,
                current_period_start=maintenant, current_period_end=_fin_de_periode(maintenant, choisi["period_months"]),
            )  # fmt: skip
        paiement.subscription = courant
    paiement.save(update_fields=["status", "paid_at", "subscription"])
    audit.enregistrer("paiement.statut", metadata={"paiement": str(paiement.pk), "statut": statut})
    return paiement


# --------------------------------------------------------------------------- échéances (tâche quotidienne)
def echeances(maintenant: datetime.datetime | None = None) -> dict:
    """Fin de période : annulé → expiré ; actif → impayé (grâce) ; impayé au-delà de la grâce → expiré.

    Le plan Gratuit V1 n'expire jamais. Le masquage des annonces 7 jours après l'expiration est une règle « à valider
    avant activation » (CDC EF-ABO-08) : non appliqué tant que le porteur ne l'a pas confirmée.
    """
    maintenant = maintenant or timezone.now()
    grace = datetime.timedelta(days=int(parametres.lire("SUBSCRIPTION_GRACE_DAYS")))
    compte = {"expires": 0, "impayes": 0}
    echus = Subscription.objects.filter(current_period_end__lte=maintenant).exclude(
        plan_code=PLAN_GRATUIT
    )
    for a in echus.filter(status__in=[StatutAbonnement.CANCELED]) | echus.filter(
        cancel_at_period_end=True, status=StatutAbonnement.ACTIVE
    ):
        if a.status == StatutAbonnement.ACTIVE:
            changer_statut(a, StatutAbonnement.CANCELED, motif="fin_de_periode")
        changer_statut(a, StatutAbonnement.EXPIRED, motif="fin_de_periode")
        compte["expires"] += 1
    for a in echus.filter(
        status__in=[StatutAbonnement.ACTIVE, StatutAbonnement.TRIALING], cancel_at_period_end=False
    ):
        changer_statut(a, StatutAbonnement.PAST_DUE, motif="echeance")
        compte["impayes"] += 1
    for a in echus.filter(
        status=StatutAbonnement.PAST_DUE, current_period_end__lte=maintenant - grace
    ):
        changer_statut(a, StatutAbonnement.EXPIRED, motif="grace_depassee")
        compte["expires"] += 1
    return compte
