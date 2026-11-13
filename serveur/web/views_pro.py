"""Espace gérant du site : tableau de bord, liste et éditeur d'annonces (adaptateurs minces)."""

from datetime import timedelta
from functools import wraps

from django.http import Http404
from django.shortcuts import redirect, render
from django.utils import timezone

from apps.accounts import selectors as comptes
from apps.chat import selectors as chat_selectors
from apps.core.errors import ErreurMetier
from apps.listings import selectors
from apps.listings.enums import PHOTOS_MIN, StatutAnnonce, StatutMedia
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


SUPPRIMER = {"action": "supprimer", "libelle": "Supprimer l'annonce", "danger": True}


def commandes_autorisees(annonce) -> list[dict]:
    """Actions réellement permises par le statut (les services revérifient côté serveur).

    « Confirmer la disponibilité » a disparu (plan v3, D1) : une chambre louée se marque louée, une chambre
    momentanément indisponible se masque ; toute annonce peut être supprimée (C6)."""
    statut = annonce.status
    if statut == StatutAnnonce.DRAFT:
        return [{"action": "publier", "libelle": "Publier", "primaire": True}, SUPPRIMER]
    if statut == StatutAnnonce.PUBLISHED:
        return [
            {
                "action": "louee",
                "libelle": "Marquer louée",
                "primaire": True,
                "confirmation": "Marquer cette chambre louée ? Ses photos et sa vidéo seront supprimées et l'annonce archivée. "
                "Pour la reproposer, il faudra ajouter de nouvelles photos.",
            },
            {"action": "masquer", "libelle": "Masquer"},
            SUPPRIMER,
        ]
    if statut == StatutAnnonce.HIDDEN:
        return [{"action": "publier", "libelle": "Remettre en ligne", "primaire": True}, SUPPRIMER]
    if statut == StatutAnnonce.RENTED:
        return [
            {"action": "annuler-louee", "libelle": "Remettre en ligne", "primaire": True},
            SUPPRIMER,
        ]
    if statut == StatutAnnonce.ARCHIVED and annonce.rented_at is not None:
        return [  # louée puis archivée : ses médias sont supprimés, la reproposer repart d'un brouillon
            {"action": "annuler-louee", "libelle": "Reproposer (nouveau brouillon)", "primaire": True},
            SUPPRIMER,
        ]
    if statut in (StatutAnnonce.PROCESSING, StatutAnnonce.ARCHIVED):
        return [SUPPRIMER]
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
    """Mes annonces : les brouillons à part, en tête, pour ne jamais les confondre avec une annonce en ligne (C5)."""
    toutes = list(selectors.annonces_du_gerant(profil))
    stats_annonces = selectors.stats_par_annonce([a.pk for a in toutes])
    message = {
        "supprimee": "Annonce supprimée.",
        "publiee": "Annonce publiée : elle est en ligne.",
        "louee": "Chambre marquée louée : ses photos et sa vidéo ont été supprimées et l'annonce est archivée.",
        "attente": "Annonce enregistrée : elle sera en ligne dès que ses médias seront prêts.",
    }.get(request.GET.get("ok", ""))
    lignes = [
        {
            "annonce": a,
            "type_label": types.libelle(a.room_type),
            "statut": STATUT_LIGNE.get(a.status, (a.status, "statut-attente")),
            "commandes": commandes_autorisees(a),
            "url": f"/pro/annonces/{a.pk}",
            "stats": stats_annonces.get(a.pk, {"views": 0, "views_total": 0, "contacts": 0}),
        }
        for a in toutes
    ]
    return render(
        request,
        "web/pro/liste.html",
        {
            "brouillons": [x for x in lignes if x["annonce"].status == StatutAnnonce.DRAFT],
            "lignes": [x for x in lignes if x["annonce"].status != StatutAnnonce.DRAFT],
            "profil": profil,
            "titre": "Mes annonces",
            "message": message,
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


ENVOI_INTERROMPU_APRES = timedelta(minutes=5)


def _medias_vue(liste) -> list[dict]:
    """Prépare les médias pour l'éditeur : aperçu, couverture et commandes disponibles.

    Un envoi resté « en cours » sans nouveau morceau depuis 5 minutes est interrompu (page fermée, réseau coupé) :
    il ne bloque plus la suite, et le gérant est invité à le supprimer puis à renvoyer le fichier."""
    vue = []
    limite = timezone.now() - ENVOI_INTERROMPU_APRES
    for m in liste:
        interrompu = m.status == StatutMedia.UPLOADING and m.updated_at < limite
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
                "interrompu": interrompu,
                "en_cours": not interrompu
                and m.status
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
        "water_deposit_amount": annonce.water_deposit_amount,
        "electricity_deposit_amount": annonce.electricity_deposit_amount,
        "has_private_bathroom": annonce.has_private_bathroom, "is_fenced": annonce.is_fenced,
        "water_sources": annonce.water_sources, "electricity_meter": annonce.electricity_meter,
        "kitchen": annonce.kitchen, "rent_negotiable": annonce.rent_negotiable,
        "description_md": annonce.description_md,
    }  # fmt: skip


ETAPES = ["La chambre", "Localisation", "Loyer", "Équipements", "Autres détails", "Vidéo et photos",
          "Publication"]  # fmt: skip


def _suite_des_medias(en_cours: bool, photos_pretes: int) -> tuple[bool, str]:
    """« Suivant » reste grisé tant que des fichiers sont en route ou en traitement, ou que les photos manquent."""
    if en_cours:
        return (
            True,
            "Envoi et traitement en cours : « Suivant » s'activera dès que tout est prêt. Un envoi interrompu ? Supprime-le puis renvoie le fichier.",
        )
    if photos_pretes < PHOTOS_MIN:
        reste = PHOTOS_MIN - photos_pretes
        return (
            True,
            f"Ajoute encore {reste} photo{'s' if reste > 1 else ''} pour continuer ({PHOTOS_MIN} au minimum).",
        )
    return False, ""


def _etape_initiale(request, annonce, action, manques, en_cours, video_prete, photos_pretes) -> int:
    """Étape ouverte à l'affichage : celle de l'action qu'on vient de faire, sinon la prochaine chose à faire."""
    demandee = request.GET.get("etape", "")
    if demandee.isdigit() and 1 <= int(demandee) <= len(ETAPES) and annonce is not None:
        return int(demandee)
    if annonce is None:
        return 1
    if request.method == "POST":
        if action in ACTIONS_MEDIAS:
            return 6
        if action in ACTIONS or manques:
            return 7
        return 6 if annonce.status == StatutAnnonce.DRAFT else 1
    if annonce.status == StatutAnnonce.DRAFT:
        return 7 if (photos_pretes >= PHOTOS_MIN and not en_cours) else 6
    return 6 if en_cours else 1


LIEN_ABONNEMENT = "/compte/abonnement?raison=publier"
MESSAGES_OK = {
    "enregistree": "Annonce enregistrée.",
    "statut": "Statut mis à jour.",
    "media": "Médias mis à jour.",
}


def _abonnement_manquant(profil) -> bool:
    """Paiement des gérants activé et pas d'abonnement qui permette de publier."""
    from apps.billing import services as abonnements

    return abonnements.actif() and not abonnements.can_publish(profil.pk)


@gerant_obligatoire
def editeur(request, profil, annonce_id=None):
    annonce = None
    if annonce_id is None and request.method == "GET" and _abonnement_manquant(profil):
        return redirect(LIEN_ABONNEMENT)  # nouvelle chambre sans abonnement : page des formules, avec un mot aimable
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
                    return redirect(f"/pro/annonces/{annonce.pk}?etape=6")
                annonce = annonces.modifier(profil, annonce.pk, donnees)
                etape = 6 if annonce.status == StatutAnnonce.DRAFT else 1
                return redirect(f"/pro/annonces/{annonce.pk}?etape={etape}&ok=enregistree")
            elif action == "supprimer" and annonce:
                annonces.supprimer(profil, annonce.pk)
                return redirect("/pro/annonces?ok=supprimee")
            elif action in ACTIONS and annonce:
                annonce = ACTIONS[action](profil, annonce.pk)
                if action == "publier":  # fini avec l'éditeur : retour à la liste, pas sur l'étape des médias
                    attente = annonce.status != StatutAnnonce.PUBLISHED
                    return redirect(f"/pro/annonces?ok={'attente' if attente else 'publiee'}")
                if action == "louee":  # chambre louée = archivée : retour sur « Mes annonces », pas sur l'étape 7
                    return redirect("/pro/annonces?ok=louee")
                return redirect(f"/pro/annonces/{annonce.pk}?etape=7&ok=statut")
            elif action in ACTIONS_MEDIAS and annonce:
                _agir_sur_media(profil, annonce, action, request.POST.get("media_id"))
                return redirect(f"/pro/annonces/{annonce.pk}?etape=6&ok=media")
        except ErreurMetier as erreur:
            if erreur.code == "subscription_required":
                return redirect(LIEN_ABONNEMENT)
            if action in ACTIONS_MEDIAS:
                erreur_media = erreur.message
            elif erreur.code == "listing_not_publishable":
                manques = erreur.champs.get("manques", [])
            else:
                _signaler(form, erreur)
    if annonce is not None:
        annonce.refresh_from_db()
    if request.method == "GET":  # après une action : on revient ici par une redirection (pas de « renvoyer les données »)
        message = MESSAGES_OK.get(request.GET.get("ok", ""))
    liste_medias = _medias_vue(medias.lister(profil, annonce.pk)) if annonce else []
    en_cours = any(m["en_cours"] for m in liste_medias)
    apercu = selectors.carte_apercu(annonce) if annonce else None
    photos_pretes = sum(1 for m in liste_medias if m["est_photo"] and m["pret"])
    video_prete = any(not m["est_photo"] and m["pret"] for m in liste_medias)
    suite_bloquee, raison_blocage = _suite_des_medias(en_cours, photos_pretes)
    etape = _etape_initiale(request, annonce, action, manques, en_cours, video_prete, photos_pretes)
    contexte = {"form": form, "annonce": annonce, "message": message, "manques": manques,
                "etapes": ETAPES, "etape_initiale": etape,
                "statut": STATUT_LIGNE.get(annonce.status, (annonce.status, "")) if annonce else None,
                "erreur_media": erreur_media, "apercu": apercu, "titre": "Modifier l'annonce" if annonce else "Nouvelle annonce", "medias": liste_medias, "medias_en_cours": en_cours,
                "photos_pretes": sum(1 for m in liste_medias if m["est_photo"] and m["pret"]),
                "photos_min": PHOTOS_MIN, "suite_bloquee": suite_bloquee, "raison_blocage": raison_blocage,
                "video_prete": any(not m["est_photo"] and m["pret"] for m in liste_medias), "commandes": commandes_autorisees(annonce) if annonce else []}  # fmt: skip
    return render(request, "web/pro/editeur.html", contexte)
