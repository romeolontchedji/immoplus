"""Paiements KKiaPay du site : préparation, confirmation (JSON) et page d'abonnement des gérants."""

import json

from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from apps.billing import services as abonnements
from apps.billing import transactions
from apps.billing.models import Transaction
from apps.core.errors import ErreurMetier

from .views_pro import gerant_obligatoire
from .views_public import connecte_obligatoire


def _corps(request) -> dict:
    try:
        corps = json.loads(request.body or b"{}")
    except ValueError:
        return {}
    return corps if isinstance(corps, dict) else {}


def _erreur(erreur: ErreurMetier) -> JsonResponse:
    return JsonResponse(
        {"error": {"code": erreur.code, "message": erreur.message}}, status=erreur.statut
    )


@connecte_obligatoire
@require_POST
def preparer(request):
    """Crée la transaction en attente et renvoie de quoi ouvrir la fenêtre KKiaPay."""
    corps = _corps(request)
    objet = str(corps.get("objet", ""))
    try:
        _, fenetre = transactions.preparer(request.user, objet, str(corps.get("plan_code", "")))
    except ErreurMetier as erreur:
        return _erreur(erreur)
    return JsonResponse(fenetre)


@connecte_obligatoire
@require_POST
def confirmer(request):
    """Le navigateur donne l'identifiant KKiaPay ; le serveur vérifie lui-même auprès de KKiaPay."""
    corps = _corps(request)
    try:
        ligne = transactions.confirmer(
            request.user, str(corps.get("reference", "")), str(corps.get("transaction_id", ""))
        )
    except ErreurMetier as erreur:
        return _erreur(erreur)
    return JsonResponse({"status": ligne.status, "objet": ligne.objet})


def contexte_alertes(utilisateur) -> dict:
    """Ce que la page « Mes alertes » doit savoir du paiement des alertes."""
    if utilisateur.role != "client" or not transactions.alertes_payantes():
        return {"alertes_payantes": False}
    return {
        "alertes_payantes": True,
        "prix_alerte": transactions.prix_alerte(),
        "credits_alerte": transactions.credits_alerte(utilisateur),
        "paiement_possible": transactions.configure(),
    }


@gerant_obligatoire
def abonnement(request, profil):
    """Formules payantes et état de l'abonnement du gérant."""
    if not abonnements.actif():
        raise Http404
    courant = abonnements.abonnement_courant(profil.pk, creer=False)
    derniers = Transaction.objects.filter(
        user=request.user, objet=Transaction.Objet.ABONNEMENT
    ).order_by("-created_at")[:5]
    return render(
        request,
        "web/pro/abonnement.html",
        {
            "titre": "Mon abonnement",
            "formules": transactions.formules_payantes(),
            "abonnement": courant,
            "peut_publier": abonnements.can_publish(profil.pk),
            "paiement_possible": transactions.configure(),
            "derniers": derniers,
        },
    )
