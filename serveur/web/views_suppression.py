"""Suppression de son compte sur le site, en deux temps : mot de passe (page du profil), puis cette page de confirmation
qui dit clairement ce qui sera perdu (abonnement payé, alertes payées, annonces en ligne)."""

import time

from django.contrib.auth import logout
from django.shortcuts import redirect, render
from django.utils import timezone

from apps.accounts import selectors as comptes
from apps.accounts.services import compte
from apps.billing import services as abonnements
from apps.billing import transactions
from apps.core import parametres
from apps.listings.models import Alert, Listing

from .views_public import connecte_obligatoire

DELAI_S = 600  # le mot de passe donné il y a plus de 10 minutes ne vaut plus : on le redemande


def pertes(utilisateur) -> dict:
    """Ce que la personne perd en supprimant son compte."""
    sortie = {"abonnement": None, "credits_alerte": 0, "annonces": 0, "alertes": 0}
    if utilisateur.role == "gerant":
        profil = comptes.profil_gerant(utilisateur)
        courant = abonnements.abonnement_courant(profil.pk, creer=False)
        if (
            courant is not None
            and courant.plan_code != abonnements.PLAN_GRATUIT
            and courant.status in abonnements.STATUTS_PUBLIABLES
            and courant.current_period_end > timezone.now()
        ):
            formules = {p["code"]: p["label"] for p in parametres.lire("PLANS")}
            sortie["abonnement"] = {
                "formule": formules.get(courant.plan_code, courant.plan_code),
                "fin": courant.current_period_end,
            }
        sortie["annonces"] = Listing.objects.filter(
            gerant_id=profil.pk, status="published", deleted_at__isnull=True
        ).count()
    else:
        sortie["credits_alerte"] = transactions.credits_alerte(utilisateur)
        sortie["alertes"] = Alert.objects.filter(user=utilisateur, is_active=True).count()
    return sortie


@connecte_obligatoire
def supprimer_mon_compte(request):
    u = request.user
    demande = request.session.get("suppression_demandee")
    if not demande or time.time() - demande > DELAI_S:
        request.session.pop("suppression_demandee", None)
        return redirect("/compte/profil")
    a_perdre = pertes(u)
    graves = bool(a_perdre["abonnement"] or a_perdre["credits_alerte"])
    erreur = None
    if request.method == "POST":
        if request.POST.get("annuler"):
            request.session.pop("suppression_demandee", None)
            return redirect("/compte/profil")
        if graves and request.POST.get("comprends") != "oui":
            erreur = "Coche la case pour confirmer que tu as compris ce que tu perds."
        else:
            compte.anonymiser(u, acteur=u)
            request.session.pop("suppression_demandee", None)
            logout(request)
            return redirect("/?compte_supprime=1")
    return render(
        request,
        "web/auth/confirmer-suppression.html",
        {
            "u": u,
            "titre": "Supprimer mon compte",
            "pertes": a_perdre,
            "graves": graves,
            "erreur": erreur,
        },
    )
