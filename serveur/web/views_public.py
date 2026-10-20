"""Pages publiques et espace locataire : fil, recherche, fiche, favoris, alertes, messages, notifications.

Adaptateurs minces : chaque vue appelle les mêmes services que l'API, sans règle métier propre.
"""

import json
import uuid
from functools import wraps
from urllib.parse import urlencode

from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.templatetags.static import static
from django.utils.safestring import mark_safe
from django.views.decorators.http import require_POST

from apps.chat import selectors as chat_selectors
from apps.chat import services as chat
from apps.core.errors import ErreurMetier
from apps.listings import selectors
from apps.listings.enums import Compteur, Cuisine, Eau
from apps.listings.services import alertes, avis, favoris, fil, partage, vues
from apps.listings.services import types as types_chambre
from apps.moderation import services as moderation
from apps.notifications import selectors as notif_selectors
from apps.notifications import services as notifications

BUDGETS = [15000, 20000, 25000, 30000, 40000, 50000, 75000, 100000, 150000]
# Critères de la page Chambres (le reste des paramètres est ignoré dans le récapitulatif et l'alerte).
CRITERES = ("q", "district", "type", "rent_max", "bathroom", "fenced", "water", "meter", "kitchen")

TRIS = [
    ("recent", "Plus récentes"),
    ("rent_asc", "Loyer croissant"),
    ("rent_desc", "Loyer décroissant"),
    ("distance", "Plus proches du campus"),
]


def connecte_obligatoire(vue):
    @wraps(vue)
    def enveloppe(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"/connexion?next={request.path}")
        if request.user.role not in ("client", "gerant"):
            raise Http404
        return vue(request, *args, **kwargs)

    return enveloppe


def _quartiers():
    return selectors.quartiers_actifs()


def _message(erreur: ErreurMetier) -> str:
    detail = " ".join(m for liste in erreur.champs.values() for m in liste)
    return f"{erreur.message} {detail}".strip()


# --------------------------------------------------------------- fil et recherche
def _types() -> list[tuple[str, str]]:
    """Types validés (décision V1), les plus courants d'abord."""
    return [(t["slug"], t["label"]) for t in types_chambre.publics()]


def _libelle_type(valeur: str) -> str:
    return types_chambre.libelle(valeur) or valeur


def _recapitulatif(request, action: str, quartier) -> list:
    """Filtres actifs, chacun assorti du lien qui le retire (pour les puces effaçables)."""
    params = {k: v for k, v in request.GET.items() if k not in ("cursor", "page") and v}
    quartiers = {d.slug: d.name for d in _quartiers()}

    def lien_sans(cle: str) -> str:
        reste = {k: v for k, v in params.items() if k != cle}
        return f"{action}?{urlencode(reste)}" if reste else action

    libelles = {
        "q": lambda v: f"Recherche : {v}",
        "district": lambda v: f"Quartier : {quartiers.get(v, v)}",
        "type": lambda v: f"Type : {_libelle_type(v)}",
        "rent_max": lambda v: f"Loyer ≤ {v} F",
        "bathroom": lambda v: "Douche interne" if v == "true" else None,
        "fenced": lambda v: "Clôturée" if v == "true" else None,
        "water": lambda v: f"Eau : {dict(Eau.choices).get(v, v)}",
        "meter": lambda v: f"Électricité : {dict(Compteur.choices).get(v, v)}",
        "kitchen": lambda v: dict(Cuisine.choices).get(v, v),
        "sort": lambda v: f"Tri : {dict(TRIS).get(v, v)}",
    }
    actifs = []
    if quartier is not None:
        actifs.append({"label": f"Quartier : {quartier.name}", "url": action, "fixe": True})
    for cle, libelle in libelles.items():
        if cle in params and not (cle == "district" and quartier is not None):
            texte = libelle(params[cle])
            if texte:
                actifs.append({"label": texte, "url": lien_sans(cle)})
    return actifs


def _liste(request, *, quartier=None, action="/annonces"):
    params = request.GET.copy()
    if quartier is not None:
        params["district"] = quartier.slug
    erreur = None
    try:
        resultat = fil.rechercher(params)
    except ErreurMetier as e:
        erreur, resultat = (
            _message(e),
            {
                "items": [],
                "next_cursor": None,
                "vide": True,
                "alerte_proposee": False,
                "voisins": None,
            },
        )
    suite = ""
    if resultat.get("next_cursor"):
        reste = {k: v for k, v in request.GET.items() if k != "cursor"}
        suite = urlencode({**reste, "cursor": resultat["next_cursor"]})
    critere_alerte = {k: v for k, v in request.GET.items() if k in CRITERES and v}
    if quartier is not None:
        critere_alerte["district"] = quartier.slug
    contexte = {
        "resultat": resultat, "params": {**request.GET.dict(), "district": params.get("district", "")},
        "quartiers": _quartiers(), "quartier": quartier, "types": _types(), "tris": TRIS, "action": action,
        "erreur": erreur, "suite": suite, "requete_alerte": urlencode(critere_alerte),
        "actifs": _recapitulatif(request, action, quartier), "budgets": BUDGETS,
        "eaux": Eau.choices, "compteurs": Compteur.choices, "cuisines": Cuisine.choices,
        "nombre_filtres": sum(1 for k in CRITERES if k != "q" and request.GET.get(k)),
    }  # fmt: skip
    # Filtres en temps réel (js/filtres.js) : seule la zone des résultats est renvoyée.
    if request.headers.get("X-Fragment") == "resultats":
        return render(request, "web/public/resultats.html", contexte)
    return render(request, "web/public/annonces.html", contexte)


def annonces(request):
    return _liste(request)


def quartier(request, slug):
    d = selectors.quartier_par_slug(slug)
    if d is None:
        raise Http404
    return _liste(request, quartier=d, action=f"/quartiers/{slug}")


# --------------------------------------------------------------- fiche
def _fiche_ou_404(slug):
    f = selectors.fiche_publique(slug)
    if f is None:
        raise Http404
    return f


def _rendre_fiche(request, f, **extra):
    est_client = request.user.is_authenticated and request.user.role == "client"
    favori = bool(est_client and selectors.ids_favoris(request.user.pk, [f["id"]]))
    criteres_alerte = {"district": f["district"]["slug"], "rent_max": f["rent_amount"]}
    if f.get("room_type"):
        criteres_alerte["type"] = f["room_type"]
    if f.get("has_private_bathroom"):
        criteres_alerte["bathroom"] = "true"
    similaires = [
        {**c, "type_label": _libelle_type(c["room_type"])}
        for c in selectors.similaires(f["id"], limite=3)
    ]  # plan v2, S3 : même source que l'API
    photos = [m for m in f["media"] if m["kind"] == "photo"]
    video = next((m for m in f["media"] if m["kind"] == "video"), None)
    contexte = {
        "f": {**f, "is_favorite": favori, "type_label": _libelle_type(f["room_type"])},
        "similaires": similaires,
        "peut_contacter": est_client,
        "est_proprietaire": request.user.is_authenticated
        and request.user.pk == f["gerant_user_id"],
        "alerte_url": f"/compte/alertes?{urlencode(criteres_alerte)}",
        "photos": photos,
        "video": video,
        # Galerie (plan v3, B1) : vidéo d'abord, puis les photos, toutes au même format.
        "diapos": ([video] if video else []) + photos,
        "avis": selectors.avis(annonce_id=f["id"]),
        "peut_donner_avis": avis.peut_donner(request.user if est_client else None, f["id"]),
        "mon_avis": selectors.avis_de(request.user.pk, f["id"]) if est_client else None,
        "notes": (5, 4, 3, 2, 1),
        "partage": _partage(request, f),
        **extra,
    }
    return render(request, "web/public/fiche.html", contexte)


def _base_site(request) -> str:
    """Adresse du site telle que vue par le visiteur (https derrière Caddy) : liens partagés et balises."""
    return request.build_absolute_uri("/").rstrip("/")


def _partage(request, f) -> dict:
    """Lien canonique, aperçu Open Graph et données structurées schema.org d'une fiche (un seul lien suffit)."""
    base = _base_site(request)
    url = f"{base}/annonces/{f['slug']}"
    image = f"{base}/annonces/{f['slug']}/apercu.jpg"
    loyer = f"{f['rent_amount']:,}".replace(",", " ")
    titre = f"{f['title']} — {loyer} F/mois · {f['district']['name']}, Parakou"
    description = partage.resume({**f, "room_type_label": _libelle_type(f["room_type"])})
    lieu = {
        "@type": "Accommodation",
        "name": f["title"],
        "address": {
            "@type": "PostalAddress",
            "addressLocality": "Parakou",
            "addressRegion": "Borgou",
            "addressCountry": "BJ",
            "streetAddress": f["district"]["name"],
        },
        "geo": {"@type": "GeoCoordinates", "latitude": f["latitude"], "longitude": f["longitude"]},
        "amenityFeature": [
            {"@type": "LocationFeatureSpecification", "name": nom, "value": True}
            for nom, present in (
                ("Douche intérieure", f.get("has_private_bathroom")),
                ("Cour clôturée", f.get("is_fenced")),
                (f.get("electricity_label"), bool(f.get("electricity_label"))),
                (f.get("water_label"), bool(f.get("water_label"))),
                (f.get("kitchen_label"), f.get("kitchen") in ("private", "shared")),
            )
            if present
        ],
    }
    if f["reviews"]["count"]:
        lieu["aggregateRating"] = {
            "@type": "AggregateRating",
            "ratingValue": round(float(f["reviews"]["average"]), 1),
            "reviewCount": f["reviews"]["count"],
            "bestRating": 5,
            "worstRating": 1,
        }
    donnees = [
        {
            "@context": "https://schema.org",
            "@type": "RealEstateListing",
            "name": f["title"],
            "description": description,
            "url": url,
            "image": [image]
            + [m["url"] for m in f["media"] if m["kind"] == "photo" and m["url"]][:5],
            "datePosted": f["published_at"].isoformat() if f.get("published_at") else None,
            "about": lieu,
            "offers": {
                "@type": "Offer",
                "price": f["rent_amount"],
                "priceCurrency": "XOF",
                "availability": "https://schema.org/InStock"
                if f["status"] == "published"
                else "https://schema.org/SoldOut",
                "businessFunction": "http://purl.org/goodrelations/v1#LeaseOut",
                "priceSpecification": {
                    "@type": "UnitPriceSpecification",
                    "price": f["rent_amount"],
                    "priceCurrency": "XOF",
                    "unitCode": "MON",
                },
            },
        },
        {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": 1,
                    "name": "Chambres",
                    "item": f"{base}/annonces",
                },
                {
                    "@type": "ListItem",
                    "position": 2,
                    "name": f["district"]["name"],
                    "item": f"{base}/quartiers/{f['district']['slug']}",
                },
                {"@type": "ListItem", "position": 3, "name": f["title"], "item": url},
            ],
        },
    ]
    return {
        "url": url,
        "image": image,
        "titre": titre,
        "description": description,
        "texte": f"{f['title']} à {f['district']['name']}, {loyer} F/mois, sur Immo+",
        "json_ld": _json_ld(donnees),
    }


def _json_ld(donnees) -> str:
    """JSON-LD inséré tel quel dans la page : `<`, `>` et `&` échappés, comme `json_script`."""
    brut = json.dumps(donnees, ensure_ascii=False, default=str)
    for car, code in (("<", "\\u003c"), (">", "\\u003e"), ("&", "\\u0026")):
        brut = brut.replace(car, code)
    return mark_safe(brut)  # noqa: S308  # nosec B308 B703 - <, > et & échappés ci-dessus


def apercu_partage(request, slug):
    """Image JPEG 1200 × 630 des aperçus de liens (WhatsApp, Facebook…), tirée de la couverture."""
    image = partage.image_apercu(slug)
    if image is None:
        return redirect(static("design/partage.jpg"))
    reponse = HttpResponse(image, content_type="image/jpeg")
    reponse["Cache-Control"] = "public, max-age=86400"
    return reponse


def fiche(request, slug):
    f = _fiche_ou_404(slug)
    proprietaire = request.user.is_authenticated and request.user.pk == f["gerant_user_id"]
    visiteur = (
        f"u:{request.user.pk}"
        if request.user.is_authenticated
        else f"a:{request.session.session_key or ''}"
    )
    if not request.user.is_authenticated and not request.session.session_key:
        request.session.create()
        visiteur = f"a:{request.session.session_key}"
    vues.enregistrer(
        f["id"], visiteur, user_agent=request.headers.get("User-Agent"), proprietaire=proprietaire
    )
    if not proprietaire:
        _noter_consultation(request, f["id"])
    return _rendre_fiche(request, f)


CONSULTEES_MAX = 8


def _noter_consultation(request, annonce_id) -> None:
    """Dernières chambres consultées, dans la session seulement (rien en base) : la plus récente d'abord."""
    ident = str(annonce_id)
    anciennes = [i for i in request.session.get("consultees", []) if i != ident]
    request.session["consultees"] = [ident, *anciennes][:CONSULTEES_MAX]


@require_POST
@connecte_obligatoire
def contacter(request, slug):
    """Un seul bouton : ouvre (ou retrouve) la discussion, où le locataire écrit ce qu'il veut (plan v3, B6)."""
    f = _fiche_ou_404(slug)
    try:
        conversation = chat.demarrer(request.user, f["id"])
    except ErreurMetier as e:
        return _rendre_fiche(request, f, message=_message(e), niveau="danger")
    return redirect(f"/compte/messages/{conversation.pk}")


@require_POST
@connecte_obligatoire
def basculer_favori(request, slug):
    f = _fiche_ou_404(slug)
    try:
        if selectors.ids_favoris(request.user.pk, [f["id"]]):
            favoris.retirer(request.user, f["id"])
            texte = "Retirée de tes favoris."
        else:
            favoris.ajouter(request.user, f["id"])
            texte = "Ajoutée à tes favoris."
    except ErreurMetier as e:
        return _rendre_fiche(request, f, message=_message(e), niveau="danger")
    f = _fiche_ou_404(slug)  # relue : note, favori et avis à jour
    return _rendre_fiche(request, f, message=texte)


@require_POST
@connecte_obligatoire
def signaler(request, slug):
    f = _fiche_ou_404(slug)
    motif = request.POST.get("reason_code", "other")
    try:
        if motif == "already_rented":
            moderation.signaler_deja_louee(request.user, f["id"])
        else:
            moderation.signaler(request.user, "listing", f["id"], motif)
    except ErreurMetier as e:
        return _rendre_fiche(request, f, message=_message(e), niveau="danger")
    f = _fiche_ou_404(slug)  # relue : note, favori et avis à jour
    return _rendre_fiche(
        request,
        f,
        message="Ton signalement a été pris en compte et sera traité par l'équipe Immo+.",
    )


@require_POST
@connecte_obligatoire
def donner_avis(request, slug):
    """Avis du locataire sur la chambre (après un échange réel avec le gérant)."""
    f = _fiche_ou_404(slug)
    try:
        if request.POST.get("action") == "retirer":
            avis.retirer(request.user, f["id"])
            texte = "Ton avis a été retiré."
        else:
            try:
                note = int(request.POST.get("rating", ""))
            except ValueError:
                note = 0
            avis.donner(request.user, f["id"], note, request.POST.get("comment", ""))
            texte = "Merci, ton avis est publié."
    except ErreurMetier as e:
        return _rendre_fiche(request, f, message=_message(e), niveau="danger")
    f = _fiche_ou_404(slug)  # relue : note, favori et avis à jour
    return _rendre_fiche(request, f, message=texte)


def profil_gerant(request, gerant_id):
    """Profil public d'un gérant : identité publique, chambres en ligne, avis ; jamais de numéro (plan v3, F1)."""
    profil = selectors.profil_gerant_public(gerant_id)
    if profil is None:
        raise Http404
    for carte in profil["listings"]:
        carte["type_label"] = _libelle_type(carte["room_type"])
    return render(request, "web/public/gerant.html", {"g": profil})


# --------------------------------------------------------------- favoris et alertes
@connecte_obligatoire
def mes_favoris(request):
    return render(
        request, "web/public/favoris.html", {"cartes": selectors.favoris_de(request.user.pk)}
    )


def _donnees_alerte(post) -> dict:
    d: dict = {"label": post.get("label", "")}
    if post.get("district_ids"):
        d["district_ids"] = [post["district_ids"]]
    if post.get("room_types"):
        d["room_types"] = [post["room_types"]]
    if post.get("max_rent"):
        d["max_rent"] = int(post["max_rent"]) if post["max_rent"].isdigit() else -1
    d["private_bathroom_required"] = bool(post.get("private_bathroom_required"))
    return d


def _lien_alerte(alerte, slugs_quartiers: dict) -> str:
    """Page Chambres filtrée comme l'alerte (le filtre « quartier » attend le slug, pas l'identifiant)."""
    params = {}
    if alerte.district_ids:
        params["district"] = slugs_quartiers.get(str(alerte.district_ids[0]), "")
    if alerte.room_types:
        params["type"] = alerte.room_types[0]
    if alerte.max_rent:
        params["rent_max"] = alerte.max_rent
    if alerte.private_bathroom_required:
        params["bathroom"] = "true"
    params = {k: v for k, v in params.items() if v}
    return "/annonces" + (f"?{urlencode(params)}" if params else "")


@connecte_obligatoire
def mes_alertes(request):
    if request.user.role != "client":
        raise Http404
    message = niveau = None
    if request.method == "POST":
        action = request.POST.get("action")
        try:
            if action == "supprimer":
                alertes.supprimer(request.user, request.POST.get("alerte_id"))
                message = "Alerte supprimée."
            elif action == "pause":
                alertes.modifier(request.user, request.POST.get("alerte_id"), {"is_active": False})
                message = "Alerte mise en pause."
            elif action == "reactiver":
                alertes.modifier(request.user, request.POST.get("alerte_id"), {"is_active": True})
                message = "Alerte réactivée."
            elif action == "modifier":
                alertes.modifier(
                    request.user, request.POST.get("alerte_id"), _donnees_alerte(request.POST)
                )
                message = "Alerte modifiée."
            else:
                alertes.creer(request.user, _donnees_alerte(request.POST))
                message = "Alerte créée : tu seras prévenu des nouvelles chambres."
        except ErreurMetier as e:
            message, niveau = _message(e), "danger"
    proposition = {
        "label": "", "district": request.GET.get("district", ""), "type": request.GET.get("type", ""),
        "rent_max": request.GET.get("rent_max", ""), "bathroom": request.GET.get("bathroom") == "true",
    }  # fmt: skip
    liste_alertes = selectors.alertes_de(request.user.pk)
    edition = None
    identifiant = request.GET.get("modifier")
    if identifiant:
        edition = next((a for a in liste_alertes if str(a.pk) == str(identifiant)), None)
        if edition is not None:
            proposition = {
                "label": edition.label or "",
                "district": str((edition.district_ids or [""])[0]),
                "type": (edition.room_types or [""])[0],
                "rent_max": edition.max_rent or "",
                "bathroom": edition.private_bathroom_required,
            }
    quartiers = _quartiers()
    noms_quartiers = {str(q.id): q.name for q in quartiers}
    slugs_quartiers = {str(q.id): q.slug for q in quartiers}
    libelles_types = types_chambre.libelles()
    alertes_vue = [
        {
            "objet": a,
            "quartiers": [
                noms_quartiers.get(str(identifiant), "") for identifiant in a.district_ids or []
            ],
            "types": [libelles_types.get(t, t) for t in a.room_types or []],
            "nombre": selectors.nombre_pour_alerte(
                a
            ),  # ce que l'alerte trouve aujourd'hui (plan v3, H1)
            "lien": _lien_alerte(a, slugs_quartiers),
        }
        for a in liste_alertes
    ]
    options = (
        alertes.options()
    )  # plan v2, M5 : quartiers les plus demandés d'abord, budgets fréquents
    return render(
        request,
        "web/public/alertes.html",
        {"alertes": alertes_vue, "quartiers": options["districts"], "budgets": options["budgets"], "types": _types(),
         "message": message, "niveau": niveau, "proposition": proposition, "edition": edition},
    )  # fmt: skip


# --------------------------------------------------------------- messages
@connecte_obligatoire
def mes_conversations(request):
    return _messagerie(request)


MOTIFS_CONVERSATION = [
    ("contact_leak", "Coordonnées partagées ou demande de sortir de Immo+"),
    ("scam", "Arnaque ou demande d'acompte sans visite"),
    ("harassment", "Harcèlement ou propos déplacés"),
    ("other", "Autre raison"),
]
DUREES_SOURDINE = {"8h": 8, "semaine": 7 * 24, "toujours": 10 * 365 * 24}


def _jour(date, aujourd_hui) -> str:
    if date == aujourd_hui:
        return "Aujourd'hui"
    if (aujourd_hui - date).days == 1:
        return "Hier"
    return date.strftime("%d/%m/%Y")


def _fil(c, lecteur_id) -> list[dict]:
    """Messages avec séparateurs de jour et état de lecture de mes messages (coches, plan v2 W5)."""
    from django.utils import timezone

    lignes, _ = chat_selectors.messages(c)
    lu_jusqua = chat_selectors.position_de_lecture(
        c, chat_selectors.autre_participant(c, lecteur_id)
    )
    aujourd_hui, precedent, sortie = timezone.localdate(), None, []
    for m in lignes:
        jour = timezone.localtime(m.created_at).date()
        if jour != precedent:
            sortie.append({"jour": _jour(jour, aujourd_hui)})
            precedent = jour
        mien = m.sender_id == lecteur_id
        sortie.append(
            {**chat.message_pour(m, lecteur_id), "mine": mien, "lu": mien and m.seq <= lu_jusqua}
        )
    return sortie


def _agir(request, c) -> tuple[str | None, str | None]:
    """Actions du formulaire de conversation : envoyer, bloquer, débloquer, sourdine, signaler."""
    import datetime

    from django.utils import timezone

    action = request.POST.get("action")
    if action == "envoyer":
        _, _, info = chat.envoyer(
            request.user, c.pk, request.POST.get("body", ""), request.POST.get("client_msg_id", "")
        )
        return (info["warning"], "avertissement") if info["warning"] else (None, None)
    if action == "bloquer":
        chat.bloquer(request.user, c.pk)
        return "Conversation bloquée : l'autre personne ne peut plus t'écrire.", "information"
    if action == "debloquer":
        chat.debloquer(request.user, c.pk)
        return "Conversation débloquée.", "succes"
    if action == "sourdine":
        heures = DUREES_SOURDINE.get(request.POST.get("duree", ""))
        jusqua = timezone.now() + datetime.timedelta(hours=heures) if heures else None
        chat.definir_silence(request.user, c.pk, jusqua)
        return (
            ("Notifications coupées pour cette conversation.", "information")
            if jusqua
            else ("Notifications réactivées.", "succes")
        )
    if action == "signaler":
        moderation.signaler(request.user, "conversation", c.pk, request.POST.get("motif", ""))
        return "Ton signalement a été pris en compte et sera traité par l'équipe Immo+.", "succes"
    return None, None


def _messagerie(request, c=None, message=None, niveau=None):
    """Messagerie façon WhatsApp (plan v2, W5) : liste à gauche, fil à droite (un seul panneau sur téléphone)."""
    lignes, _ = chat_selectors.liste(request.user.pk, role=request.user.role)
    contexte = {"conversations": chat_selectors.decrire(lignes, request.user.pk), "c": None}
    if c is not None:
        contexte.update(
            c=chat_selectors.decrire([c], request.user.pk)[0],
            fil=_fil(c, request.user.pk),
            client_msg_id=uuid.uuid4(),
            message=message,
            niveau=niveau,
            motifs=MOTIFS_CONVERSATION,
            adresse=selectors.adresse_privee(c.listing_id)
            if c.gerant_id == request.user.pk
            else None,
        )
    return render(request, "web/public/messagerie.html", contexte)


@connecte_obligatoire
def conversation(request, conversation_id):
    try:
        c = chat_selectors.conversation_du_participant(request.user.pk, conversation_id)
    except ErreurMetier as erreur:
        raise Http404 from erreur
    message = niveau = None
    if request.method == "POST":
        try:
            message, niveau = _agir(request, c)
        except ErreurMetier as e:
            message, niveau = _message(e), "danger"
        c = chat_selectors.conversation_par_id(c.pk)
    chat.lire(request.user, c.pk, c.last_seq)
    c = chat_selectors.conversation_par_id(c.pk)
    return _messagerie(request, c, message, niveau)


# --------------------------------------------------------------- notifications
def _lien_notification(n: dict) -> str | None:
    """Lien profond vers la ressource visée, quand elle existe (conversation d'abord, sinon annonce)."""
    data = n.get("data") or {}
    if data.get("conversation_id"):
        return f"/compte/messages/{data['conversation_id']}"
    if data.get("slug"):
        return f"/annonces/{data['slug']}"
    if data.get("alert_id"):
        return "/compte/alertes"  # récapitulatif d'alerte (plan v2, A2)
    return None


def _groupes_notifications(lignes) -> list[dict]:
    """Regroupe les notifications identiques (même type, titre, corps et données) en une ligne."""
    groupes: dict = {}
    for n in lignes:
        resume = notifications.resume(n)
        cle = (resume["kind"], resume["title"], resume["body"], repr(resume["data"]))
        groupe = groupes.setdefault(cle, {"compte": 0, "non_lues": 0, "ids": [], "derniere": None})
        groupe["compte"] += 1
        if resume["read_at"] is None:
            groupe["non_lues"] += 1
        groupe["ids"].append(resume["id"])
        if groupe["derniere"] is None or resume["created_at"] > groupe["derniere"]["created_at"]:
            groupe["derniere"] = {**resume, "lien": _lien_notification(resume)}
    return [
        {"derniere": groupe["derniere"], "compte": groupe["compte"], "non_lues": groupe["non_lues"]}
        for groupe in groupes.values()
    ]


@connecte_obligatoire
def mes_notifications(request):
    if request.method == "POST":
        if request.POST.get("action") == "lire" and request.POST.get("notification_id"):
            notifications.marquer_lue(request.user.pk, request.POST["notification_id"])
            return redirect("/compte/notifications")
        notifications.tout_marquer_lu(request.user.pk)
        return redirect("/compte/notifications")
    lignes, _ = notif_selectors.liste(request.user.pk)
    return render(
        request,
        "web/public/notifications.html",
        {
            "groupes": _groupes_notifications(lignes),
            "non_lues": notif_selectors.non_lues(request.user.pk),
        },
    )


# --------------------------------------------------------------- référencement
def robots(request):
    contenu = "User-agent: *\nAllow: /\nDisallow: /compte\nDisallow: /pro\nDisallow: /connexion\nDisallow: /inscription\n"
    contenu += f"Sitemap: {_base_site(request)}/sitemap.xml\n"
    return HttpResponse(contenu, content_type="text/plain; charset=utf-8")


def sitemap(request):
    base = _base_site(request)
    urls = [(f"{base}/", None), (f"{base}/annonces", None)]
    urls += [(f"{base}/quartiers/{d.slug}", None) for d in _quartiers()]
    urls += [(f"{base}/annonces/{slug}", maj) for slug, maj in selectors.slugs_publies()]
    corps = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    corps += "".join(
        f"<url><loc>{u}</loc>"
        + (f"<lastmod>{maj.date().isoformat()}</lastmod>" if maj else "")
        + "</url>\n"
        for u, maj in urls
    )
    corps += "</urlset>\n"
    return HttpResponse(corps, content_type="application/xml; charset=utf-8")
