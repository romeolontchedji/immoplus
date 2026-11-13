"""Paiements KKiaPay du site : préparation, confirmation (JSON) et page d'abonnement des gérants."""

import json

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.billing import services as abonnements
from apps.billing import transactions
from apps.billing.models import Transaction
from apps.core.errors import ErreurMetier

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


RAISONS = {
    "publier": "Pour publier une nouvelle chambre, il te faut un abonnement actif. Choisis ta formule ci-dessous : "
    "c'est rapide, et tes annonces déjà en ligne restent visibles.",
    "alerte": "Les alertes sont payantes : choisis-les d'abord, tu seras invité à payer au moment de les créer.",
}


@connecte_obligatoire
def abonnement(request):
    """Page « Abonnement » des deux rôles : formules, état, historique des paiements."""
    from apps.accounts import selectors as comptes
    from apps.core import parametres

    gerant = request.user.role == "gerant"
    historique = Transaction.objects.filter(user=request.user).order_by("-created_at")[:20]
    plans = {p["code"]: p["label"] for p in parametres.lire("PLANS")}
    contexte = {
        "titre": "Abonnement",
        "gerant": gerant,
        "raison": RAISONS.get(request.GET.get("raison", "")),
        "paiement_possible": transactions.configure(),
        "historique": [
            {"t": t, "formule": plans.get(t.plan_code, t.plan_code)} for t in historique
        ],
    }
    if gerant:
        profil = comptes.profil_gerant(request.user)
        courant = abonnements.abonnement_courant(profil.pk, creer=False)
        contexte.update(
            actif=abonnements.actif(),
            formules=transactions.formules_payantes(),
            abonnement=courant,
            formule_actuelle=plans.get(courant.plan_code, courant.plan_code) if courant else None,
            peut_publier=abonnements.can_publish(profil.pk),
        )
    else:
        contexte.update(
            actif=transactions.alertes_payantes(),
            prix_alerte=transactions.prix_alerte(),
            credits_alerte=transactions.credits_alerte(request.user),
            email_confirme=bool(request.user.email and request.user.email_verified_at),
        )
    return render(request, "web/abonnement.html", contexte)


@csrf_exempt
@require_POST
def webhook(request):
    """Appelé par KKiaPay (authentifié par son secret, pas par une session). 2xx = reçu ; sinon KKiaPay réessaie."""
    try:
        resultat = transactions.recevoir_webhook(request.body, dict(request.headers))
    except ErreurMetier as erreur:
        return _erreur(erreur)
    return JsonResponse({"received": True, "result": resultat})
