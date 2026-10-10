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
from apps.listings.enums import TypeChambre
from apps.listings.services import alertes, favoris, fil, vues
from apps.moderation import services as moderation
from apps.notifications import selectors as notif_selectors
from apps.notifications import services as notifications

TYPES = list(TypeChambre.choices)
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
            "quartiers": _quartiers(), "quartier": quartier, "types": TYPES, "tris": TRIS, "action": action,
            "erreur": erreur, "suite": suite, "requete_alerte": urlencode(critere_alerte),
        },
    )  # fmt: skip


def accueil(request):
    return _liste(request, action="/annonces")


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
    contexte = {
        "f": {**f, "is_favorite": favori},
        "peut_contacter": est_client,
        "message_propose": f"Bonjour, la chambre « {f['title']} » est-elle toujours disponible ?",
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
        try:
            if request.POST.get("action") == "supprimer":
                alertes.supprimer(request.user, request.POST.get("alerte_id"))
                message = "Alerte supprimée."
            else:
                alertes.creer(request.user, _donnees_alerte(request.POST))
                message = "Alerte créée : tu seras prévenu des nouvelles chambres."
        except ErreurMetier as e:
            message, niveau = _message(e), "danger"
    proposition = {
        "label": "", "district": request.GET.get("district", ""), "type": request.GET.get("type", ""),
        "rent_max": request.GET.get("rent_max", ""), "bathroom": request.GET.get("bathroom") == "true",
    }  # fmt: skip
    return render(
        request,
        "web/public/alertes.html",
        {"alertes": selectors.alertes_de(request.user.pk), "quartiers": _quartiers(), "types": TYPES,
         "message": message, "niveau": niveau, "proposition": proposition},
    )  # fmt: skip


# --------------------------------------------------------------- messages
@connecte_obligatoire
def mes_conversations(request):
    lignes, _ = chat_selectors.liste(request.user.pk, role=request.user.role)
    return render(
        request,
        "web/public/messages.html",
        {"conversations": chat_selectors.decrire(lignes, request.user.pk)},
    )


@connecte_obligatoire
def conversation(request, conversation_id):
    try:
        c = chat_selectors.conversation_du_participant(request.user.pk, conversation_id)
    except ErreurMetier as erreur:
        raise Http404 from erreur
    message = niveau = None
    if request.method == "POST":
        action = request.POST.get("action")
        try:
            if action == "envoyer":
                _, _, info = chat.envoyer(
                    request.user,
                    c.pk,
                    request.POST.get("body", ""),
                    request.POST.get("client_msg_id", ""),
                )
                if info["warning"]:
                    message, niveau = info["warning"], "avertissement"
            elif action == "bloquer":
                chat.bloquer(request.user, c.pk)
            elif action == "debloquer":
                chat.debloquer(request.user, c.pk)
        except ErreurMetier as e:
            message, niveau = _message(e), "danger"
        c = chat_selectors.conversation_par_id(c.pk)
    chat.lire(request.user, c.pk, c.last_seq)
    lignes, _ = chat_selectors.messages(c)
    description = chat_selectors.decrire([c], request.user.pk)[0]
    return render(
        request,
        "web/public/conversation.html",
        {
            "c": description, "message": message, "niveau": niveau, "client_msg_id": uuid.uuid4(),
            "messages": [{**chat.message_pour(m, request.user.pk), "mine": m.sender_id == request.user.pk} for m in lignes],
            "adresse": selectors.adresse_privee(c.listing_id) if c.gerant_id == request.user.pk else None,
        },
    )  # fmt: skip


# --------------------------------------------------------------- notifications
@connecte_obligatoire
def mes_notifications(request):
    if request.method == "POST":
        notifications.tout_marquer_lu(request.user.pk)
        return redirect("/compte/notifications")
    lignes, _ = notif_selectors.liste(request.user.pk)
    return render(request, "web/public/notifications.html", {"notifications": lignes})


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
