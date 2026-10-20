"""Espace gérant du site : tableau de bord, liste et éditeur d'annonces (adaptateurs minces)."""

from functools import wraps

from django.http import Http404
from django.shortcuts import redirect, render

from apps.accounts import selectors as comptes
from apps.chat import selectors as chat_selectors
from apps.core.errors import ErreurMetier
from apps.listings import selectors
from apps.listings.enums import StatutAnnonce, StatutMedia
from apps.listings.services import annonces, medias, types
from apps.media import stockage

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


TITRES_STATUTS = {
    StatutAnnonce.DRAFT: "Brouillons",
    StatutAnnonce.PROCESSING: "En attente de validation",
    StatutAnnonce.PUBLISHED: "Publiées",
    StatutAnnonce.HIDDEN: "Masquées",
    StatutAnnonce.RENTED: "Louées",
    StatutAnnonce.ARCHIVED: "Archivées",
    StatutAnnonce.REMOVED: "Retirées",
}
# Statut d'une ligne : (libellé, classe de pastille).
STATUT_LIGNE = {
    StatutAnnonce.DRAFT: ("Brouillon", "statut-attente"),
    StatutAnnonce.PROCESSING: ("En traitement", "statut-attente"),
    StatutAnnonce.PUBLISHED: ("En ligne", "statut-active"),
    StatutAnnonce.HIDDEN: ("Masquée", "statut-sans-video"),
    StatutAnnonce.RENTED: ("Louée", "statut-louee"),
    StatutAnnonce.ARCHIVED: ("Archivée", "statut-attente"),
    StatutAnnonce.REMOVED: ("Retirée", "statut-suspendu"),
}


def commandes_autorisees(annonce) -> list[dict]:
    """Actions réellement permises par le statut (les services revérifient côté serveur)."""
    statut = annonce.status
    if statut == StatutAnnonce.DRAFT:
        return [
            {"action": "publier", "libelle": "Publier", "primaire": True},
            {"action": "supprimer", "libelle": "Supprimer", "danger": True},
        ]
    if statut == StatutAnnonce.PUBLISHED:
        return [
            {"action": "confirmer", "libelle": "Confirmer la disponibilité", "primaire": True},
            {"action": "masquer", "libelle": "Masquer"},
            {"action": "louee", "libelle": "Marquer louée"},
        ]
    if statut == StatutAnnonce.HIDDEN:
        return [{"action": "publier", "libelle": "Republier", "primaire": True}]
    if statut == StatutAnnonce.RENTED:
        return [{"action": "annuler-louee", "libelle": "Remettre en ligne", "primaire": True}]
    return []


@gerant_obligatoire
def tableau_de_bord(request, profil):
    message = None
    if request.method == "POST" and request.POST.get("action") == "disponible":
        # Plan v2, W4 : décocher « encore disponible » = louée (retirée du fil) ; recocher = remise en ligne.
        try:
            if request.POST.get("disponible") == "1":
                annonces.annuler_louee(profil, request.POST.get("annonce_id"))
            else:
                annonces.marquer_louee(profil, request.POST.get("annonce_id"))
            return redirect("/pro/dashboard")
        except ErreurMetier as erreur:
            message = erreur.message
    donnees = selectors.tableau_de_bord_gerant(profil)
    taux = comptes.taux_de_reponse(request.user.pk)
    statuts = [
        {"code": code, "libelle": TITRES_STATUTS.get(code, code), "nombre": nombre}
        for code, nombre in donnees["listings_by_status"].items()
        if nombre
    ]
    toutes = list(selectors.annonces_du_gerant(profil))
    recentes_objets = toutes[:5]
    stats_annonces = selectors.stats_par_annonce([a.pk for a in recentes_objets])
    recentes = [
        {
            "annonce": a,
            "type_label": types.libelle(a.room_type),
            "statut": STATUT_LIGNE.get(a.status, (a.status, "statut-attente")),
            "commandes": commandes_autorisees(a),
            "url": f"/pro/annonces/{a.pk}",
            "stats": stats_annonces.get(a.pk, {"views": 0, "contacts": 0}),
        }
        for a in recentes_objets
    ]
    lignes, _ = chat_selectors.liste(request.user.pk, role="gerant")
    derniers_contacts = chat_selectors.decrire(lignes[:4], request.user.pk)
    return render(
        request,
        "web/pro/tableau.html",
        {
            "donnees": donnees,
            "statuts": statuts,
            "taux": taux,
            "non_lus": chat_selectors.total_non_lus(request.user.pk, "gerant"),
            "profil": profil,
            "titre": "Tableau de bord",
            "recentes": recentes,
            "total_annonces": len(toutes),
            "derniers_contacts": derniers_contacts,
            "message": message,
        },
    )


@gerant_obligatoire
def liste(request, profil):
    toutes = list(selectors.annonces_du_gerant(profil))
    stats_annonces = selectors.stats_par_annonce([a.pk for a in toutes])
    lignes = [
        {
            "annonce": a,
            "commandes": commandes_autorisees(a),
            "url": f"/pro/annonces/{a.pk}",
            "stats": stats_annonces.get(a.pk, {"views": 0, "contacts": 0}),
        }
        for a in toutes
    ]
    return render(
        request,
        "web/pro/liste.html",
        {
            "lignes": lignes,
            "statuts": TITRES_STATUTS,
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


ACTIONS_MEDIAS = {"couvrir", "monter", "descendre", "media-supprimer"}


def _medias_vue(liste) -> list[dict]:
    """Prépare les médias pour l'éditeur : aperçu, couverture et commandes disponibles."""
    vue = []
    for m in liste:
        apercu = None
        if m.status == StatutMedia.READY:
            # Vidéo : l'affiche (le flux HLS n'est pas une image) ; photo : la variante publiée.
            chemins = (
                (m.poster_path, m.playback_path)
                if m.kind == "video"
                else (m.playback_path, m.poster_path)
            )
            apercu = next((u for u in (stockage.url_publique(c) for c in chemins if c) if u), None)
        vue.append(
            {
                "id": m.pk,
                "kind": m.kind,
                "kind_display": m.get_kind_display(),
                "status_display": m.get_status_display(),
                "is_cover": m.is_cover,
                "error_detail": m.error_detail,
                "apercu": apercu,
                "est_photo": m.kind == "photo",
                "pret": m.status == StatutMedia.READY,
                "erreur": m.status == StatutMedia.FAILED,
                "en_cours": m.status
                in (StatutMedia.UPLOADING, StatutMedia.UPLOADED, StatutMedia.PROCESSING),
            }
        )
    return vue


def _agir_sur_media(profil, annonce, action, media_id):
    """Réordonne, choisit la couverture ou supprime un média via les services métier."""
    liste = medias.lister(profil, annonce.pk)
    identifiants = [str(m.pk) for m in liste]
    couverture = next((str(m.pk) for m in liste if m.is_cover), None)
    if action == "media-supprimer":
        medias.supprimer(profil, annonce.pk, media_id)
        return "Média supprimé."
    if media_id not in identifiants:
        raise ErreurMetier("not_found", "Média introuvable.", statut=404)
    if action == "couvrir":
        medias.definir_ordre(profil, annonce.pk, identifiants, media_id)
        return "Photo de couverture mise à jour."
    i = identifiants.index(media_id)
    j = i - 1 if action == "monter" else i + 1
    if 0 <= j < len(identifiants):
        identifiants[i], identifiants[j] = identifiants[j], identifiants[i]
        medias.definir_ordre(profil, annonce.pk, identifiants, couverture)
    return "Ordre des médias mis à jour."


def _initial(annonce) -> dict:
    return {
        "title": annonce.title, "room_type": annonce.room_type, "district": str(annonce.district_id),
        "landmark_text": annonce.landmark_text, "address_private": annonce.address_private,
        "rent_amount": annonce.rent_amount,
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
                       initial=_initial(annonce) if annonce else None, gerant=profil)  # fmt: skip
    message, manques, erreur_media = None, [], None
    if request.method == "POST":
        try:
            if action == "enregistrer" and form.is_valid():
                donnees = form.donnees()
                if form.cleaned_data.get(
                    "nouveau_type"
                ):  # décision V1 : type proposé (ou équivalent existant)
                    donnees["room_type"] = types.proposer(
                        profil, form.cleaned_data["nouveau_type"]
                    ).slug
                if annonce is None:
                    annonce = annonces.creer_brouillon(profil, donnees)
                    return redirect(f"/pro/annonces/{annonce.pk}")
                annonce = annonces.modifier(profil, annonce.pk, donnees)
                message = "Annonce enregistrée."
            elif action == "supprimer" and annonce:
                annonces.supprimer(profil, annonce.pk)
                return redirect("/pro/annonces")
            elif action in ACTIONS and annonce:
                annonce = ACTIONS[action](profil, annonce.pk)
                message = "Statut mis à jour."
            elif action in ACTIONS_MEDIAS and annonce:
                message = _agir_sur_media(profil, annonce, action, request.POST.get("media_id"))
        except ErreurMetier as erreur:
            if action in ACTIONS_MEDIAS:
                erreur_media = erreur.message
            elif erreur.code == "listing_not_publishable":
                manques = erreur.champs.get("manques", [])
            else:
                _signaler(form, erreur)
    if annonce is not None:
        annonce.refresh_from_db()
    liste_medias = _medias_vue(medias.lister(profil, annonce.pk)) if annonce else []
    en_cours = any(m["en_cours"] for m in liste_medias)
    apercu = selectors.carte_apercu(annonce) if annonce else None
    contexte = {"form": form, "annonce": annonce, "message": message, "manques": manques,
                "erreur_media": erreur_media, "apercu": apercu, "titre": "Modifier l'annonce" if annonce else "Nouvelle annonce", "medias": liste_medias, "medias_en_cours": en_cours,
                "photos_pretes": sum(1 for m in liste_medias if m["est_photo"] and m["pret"]),
                "video_prete": any(not m["est_photo"] and m["pret"] for m in liste_medias), "commandes": commandes_autorisees(annonce) if annonce else []}  # fmt: skip
    return render(request, "web/pro/editeur.html", contexte)
