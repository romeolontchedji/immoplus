"""Pages publiques et espace locataire : fil, recherche, fiche, favoris, alertes, messages, notifications.

Adaptateurs minces : chaque vue appelle les mêmes services que l'API, sans règle métier propre.
"""

import uuid
from functools import wraps
from urllib.parse import urlencode

from django.conf import settings
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.chat import selectors as chat_selectors
from apps.chat import services as chat
from apps.core.errors import ErreurMetier
from apps.listings import selectors
from apps.listings.enums import Compteur, Eau
from apps.listings.services import alertes, favoris, fil, vues
from apps.listings.services import types as types_chambre
from apps.moderation import services as moderation
from apps.notifications import selectors as notif_selectors
from apps.notifications import services as notifications

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
    params = {k: v for k, v in request.GET.items() if k not in ("cursor", "page")}
    quartiers = {d.slug: d.name for d in _quartiers()}

    def lien_sans(cle: str) -> str:
        reste = {k: v for k, v in params.items() if k != cle}
        return f"{action}?{urlencode(reste)}" if reste else action

    actifs = []
    if params.get("q"):
        actifs.append({"label": f"Recherche : {params['q']}", "url": lien_sans("q")})
    if quartier is not None:
        actifs.append(
            {"label": f"Quartier : {quartier.name}", "url": lien_sans("district"), "fixe": True}
        )
    elif params.get("district"):
        nom = quartiers.get(params["district"], params["district"])
        actifs.append({"label": f"Quartier : {nom}", "url": lien_sans("district")})
    if params.get("type"):
        actifs.append(
            {"label": f"Type : {_libelle_type(params['type'])}", "url": lien_sans("type")}
        )
    if params.get("rent_max"):
        actifs.append({"label": f"Loyer ≤ {params['rent_max']} F", "url": lien_sans("rent_max")})
    if params.get("bathroom") == "true":
        actifs.append({"label": "Douche et WC internes", "url": lien_sans("bathroom")})
    if params.get("sort"):
        actifs.append(
            {
                "label": f"Tri : {dict(TRIS).get(params['sort'], params['sort'])}",
                "url": lien_sans("sort"),
            }
        )
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
            {"items": [], "next_cursor": None, "vide": True, "alerte_proposee": False},
        )
    suite = ""
    if resultat.get("next_cursor"):
        reste = {k: v for k, v in request.GET.items() if k != "cursor"}
        suite = urlencode({**reste, "cursor": resultat["next_cursor"]})
    critere_alerte = {
        k: v
        for k, v in request.GET.items()
        if k in ("district", "type", "rent_max", "bathroom", "q")
    }
    if quartier is not None:
        critere_alerte["district"] = quartier.slug
    return render(
        request,
        "web/public/annonces.html",
        {
            "resultat": resultat, "params": {**request.GET.dict(), "district": params.get("district", "")},
            "quartiers": _quartiers(), "quartier": quartier, "types": _types(), "tris": TRIS, "action": action,
            "erreur": erreur, "suite": suite, "requete_alerte": urlencode(critere_alerte),
            "actifs": _recapitulatif(request, action, quartier),
        },
    )  # fmt: skip


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
    try:
        similaires_res = fil.rechercher({"district": f["district"]["slug"], "limit": 6})
        similaires = [
            c for c in similaires_res.get("items", []) if str(c.get("id")) != str(f["id"])
        ][:3]
        if len(similaires) < 3:
            tous_res = fil.rechercher({"limit": 6})
            autres = [
                c
                for c in tous_res.get("items", [])
                if str(c.get("id")) != str(f["id"]) and c not in similaires
            ]
            similaires.extend(autres[: 3 - len(similaires)])
    except Exception:
        similaires = []

    contexte = {
        "f": {
            **f,
            "is_favorite": favori,
            "type_label": _libelle_type(f["room_type"]),
            "eau_label": dict(Eau.choices).get(f["water_source"] or "", ""),
            "compteur_label": dict(Compteur.choices).get(f["electricity_meter"] or "", ""),
        },
        "similaires": similaires,
        "peut_contacter": est_client,
        "est_proprietaire": request.user.is_authenticated
        and request.user.pk == f["gerant_user_id"],
        "alerte_url": f"/compte/alertes?{urlencode(criteres_alerte)}",
        "message_propose": f"Bonjour, la chambre « {f['title']} » est-elle toujours disponible ?",
        "photos": [m for m in f["media"] if m["kind"] == "photo"],
        "video": next((m for m in f["media"] if m["kind"] == "video"), None),
        **extra,
    }
    return render(request, "web/public/fiche.html", contexte)


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
    return _rendre_fiche(request, f)


@require_POST
@connecte_obligatoire
def contacter(request, slug):
    f = _fiche_ou_404(slug)
    try:
        conversation, _, _, info = chat.ouvrir(
            request.user, f["id"], request.POST.get("body", ""), uuid.uuid4()
        )
    except ErreurMetier as e:
        return _rendre_fiche(
            request,
            f,
            message=_message(e),
            niveau="danger",
            message_propose=request.POST.get("body", ""),
        )
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
    return _rendre_fiche(request, f, message="Merci, ton signalement a été transmis à l'équipe.")


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
    libelles_types = types_chambre.libelles()
    alertes_vue = [
        {
            "objet": a,
            "quartiers": [
                noms_quartiers.get(str(identifiant), "") for identifiant in a.district_ids or []
            ],
            "types": [libelles_types.get(t, t) for t in a.room_types or []],
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
    ("contact_leak", "Coordonnées partagées ou demande de sortir de Logeo"),
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
        return "Merci, ton signalement a été transmis à l'équipe.", "succes"
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
    contenu += (
        f"Sitemap: {settings.SITE_URL}/sitemap.xml\n" if getattr(settings, "SITE_URL", "") else ""
    )
    return HttpResponse(contenu, content_type="text/plain; charset=utf-8")


def sitemap(request):
    base = getattr(settings, "SITE_URL", "") or f"{request.scheme}://{request.get_host()}"
    urls = [f"{base}/", f"{base}/annonces"]
    urls += [f"{base}/quartiers/{d.slug}" for d in _quartiers()]
    urls += [f"{base}/annonces/{slug}" for slug, _ in selectors.slugs_publies()]
    corps = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    corps += "".join(f"<url><loc>{u}</loc></url>\n" for u in urls) + "</urlset>\n"
    return HttpResponse(corps, content_type="application/xml; charset=utf-8")
