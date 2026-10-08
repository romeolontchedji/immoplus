"""Espace gérant du site : liste et éditeur d'annonces (adaptateurs minces)."""

from functools import wraps

from django.http import Http404
from django.shortcuts import redirect, render

from apps.accounts import selectors as comptes
from apps.core.errors import ErreurMetier
from apps.listings import selectors
from apps.listings.services import annonces

from .forms_pro import AnnonceForm
from .views_auth import _signaler


def gerant_obligatoire(vue):
    @wraps(vue)
    def enveloppe(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"/connexion?next={request.path}")
        if request.user.role != "gerant":
            raise Http404
        return vue(request, comptes.profil_gerant(request.user), *args, **kwargs)

    return enveloppe


@gerant_obligatoire
def liste(request, profil):
    return render(
        request,
        "web/pro/liste.html",
        {
            "annonces": selectors.annonces_du_gerant(profil),
            "profil": profil,
            "titre": "Mes annonces",
        },
    )


ACTIONS = {
    "publier": annonces.publier,
    "confirmer": annonces.confirmer,
    "masquer": annonces.masquer,
    "louee": annonces.marquer_louee,
    "annuler-louee": annonces.annuler_louee,
}


def _initial(annonce) -> dict:
    return {
        "title": annonce.title, "room_type": annonce.room_type, "district": str(annonce.district_id),
        "landmark_text": annonce.landmark_text, "address_private": annonce.address_private,
        "latitude": annonce.latitude, "longitude": annonce.longitude, "rent_amount": annonce.rent_amount,
        "deposit_months": annonce.deposit_months, "advance_months": annonce.advance_months,
        "agent_fee_amount": annonce.agent_fee_amount, "available_from": annonce.available_from,
        "has_private_bathroom": annonce.has_private_bathroom, "is_fenced": annonce.is_fenced,
        "water_source": annonce.water_source, "electricity_meter": annonce.electricity_meter,
        "description_md": annonce.description_md,
    }  # fmt: skip


@gerant_obligatoire
def editeur(request, profil, annonce_id=None):
    annonce = None
    if annonce_id is not None:
        annonce = selectors.annonce_du_gerant(profil, annonce_id)
        if annonce is None:
            raise Http404
    action = request.POST.get("action", "enregistrer")
    form = AnnonceForm(request.POST if request.method == "POST" and action == "enregistrer" else None,
                       initial=_initial(annonce) if annonce else None)  # fmt: skip
    message, manques = None, []
    if request.method == "POST":
        try:
            if action == "enregistrer" and form.is_valid():
                if annonce is None:
                    annonce = annonces.creer_brouillon(profil, form.donnees())
                    return redirect(f"/pro/annonces/{annonce.pk}")
                annonce = annonces.modifier(profil, annonce.pk, form.donnees())
                message = "Annonce enregistrée."
            elif action == "supprimer" and annonce:
                annonces.supprimer_brouillon(profil, annonce.pk)
                return redirect("/pro/annonces")
            elif action in ACTIONS and annonce:
                annonce = ACTIONS[action](profil, annonce.pk)
                message = "Statut mis à jour."
        except ErreurMetier as erreur:
            if erreur.code == "listing_not_publishable":
                manques = erreur.champs.get("manques", [])
            else:
                _signaler(form, erreur)
    if annonce is not None:
        annonce.refresh_from_db()
    contexte = {"form": form, "annonce": annonce, "message": message, "manques": manques,
                "titre": "Modifier l'annonce" if annonce else "Nouvelle annonce", "medias": annonce.media.exclude(status="deleted") if annonce else []}  # fmt: skip
    return render(request, "web/pro/editeur.html", contexte)
