"""Balises de gabarit : lien vers le CSS empreinté."""

import json
from functools import lru_cache

from django import template
from django.conf import settings
from django.templatetags.static import static

register = template.Library()


@lru_cache(maxsize=1)
def _manifeste() -> dict[str, str]:
    chemin = settings.BASE_DIR / "web" / "static" / "css" / "dist" / "manifest.json"
    return json.loads(chemin.read_text(encoding="utf-8"))


@register.simple_tag
def css_logeo() -> str:
    """URL du CSS assemblé (`make css`). Échoue clairement s'il n'a pas été construit."""
    try:
        return static(_manifeste()["logeo.css"])
    except FileNotFoundError as e:
        raise RuntimeError("CSS non construit : lance `make css`.") from e


@register.simple_tag(takes_context=True)
def nav_classe(context, prefixe: str) -> str:
    """Classes d'un lien de navigation, avec état « page courante » (`aria-current` à poser aussi)."""
    base = "navigation__lien"
    try:
        chemin = context["request"].path
    except (KeyError, AttributeError):
        return base
    nettoye = prefixe.rstrip("/") or "/"
    actif = chemin == prefixe or chemin == nettoye or chemin.startswith(nettoye + "/")
    return f"{base} {base}--actif" if actif else base


@register.simple_tag(takes_context=True)
def nav_courant(context, prefixe: str) -> str:
    """`page` si le chemin courant est sous `prefixe`, sinon une chaîne vide."""
    try:
        chemin = context["request"].path
    except (KeyError, AttributeError):
        return ""
    nettoye = prefixe.rstrip("/") or "/"
    return "page" if (chemin == prefixe or chemin.startswith(nettoye + "/")) else ""


@register.filter
def fcfa(montant) -> str:
    """Formate un entier en FCFA : 25000 → « 25 000 » (fine insécable)."""
    try:
        return f"{int(montant):,}".replace(",", "\u202f")
    except (TypeError, ValueError):
        return str(montant)


@register.filter
def duree_video(secondes) -> str:
    """Durée en secondes → « m:ss ». Vide si inconnue."""
    try:
        total = int(round(float(secondes)))
    except (TypeError, ValueError):
        return ""
    return f"{total // 60}:{total % 60:02d}"


STATUTS_CONVERSATION = {
    "open": "Ouverte",
    "read_only": "En lecture seule",
    "blocked": "Bloquée",
}


@register.filter
def statut_conversation(valeur: str) -> str:
    """Statut de conversation technique → libellé français visible."""
    return STATUTS_CONVERSATION.get(valeur, valeur)


MANQUES_PUBLICATION = {
    "gerant_non_verifie": "ton compte gérant n'est pas encore vérifié",
    "gerant_suspendu": "ton compte gérant est suspendu",
    "video_prete": "la vidéo n'est pas encore prête",
    "trois_photos_pretes": "il faut au moins 3 photos prêtes",
}

CHAMPS_ANNONCE = {
    "title": "le titre",
    "room_type": "le type de chambre",
    "district": "le quartier",
    "landmark_text": "le repère",
    "latitude": "la latitude",
    "longitude": "la longitude",
    "rent_amount": "le loyer",
    "deposit_months": "la caution",
    "advance_months": "l'avance",
    "available_from": "la date de disponibilité",
    "has_private_bathroom": "la douche interne",
    "is_fenced": "la clôture",
    "water_source": "la source d'eau",
    "electricity_meter": "le compteur SBEE",
}


@register.filter
def manque_publication(code: str) -> str:
    """Code technique de publication manquante → texte français."""
    if code in MANQUES_PUBLICATION:
        return MANQUES_PUBLICATION[code]
    if code.startswith("champ:"):
        nom = code.split(":", 1)[1]
        return CHAMPS_ANNONCE.get(nom, "une information à compléter")
    return code
