"""Balises de gabarit : lien vers le CSS empreinté."""

import json
from functools import lru_cache

from django import template
from django.conf import settings
from django.templatetags.static import static

from apps.listings.services import annonces

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


@register.filter
def manque_publication(code: str) -> str:
    """Code technique de publication manquante → texte français (même source que l'API)."""
    return annonces.libelle_manque(code)


@register.filter
def horodatage_court(valeur) -> str:
    """Liste de conversations : heure si aujourd'hui, « Hier », sinon jj/mm (comme les messageries)."""
    if not valeur:
        return ""
    from django.utils import timezone

    local = timezone.localtime(valeur)
    ecart = (timezone.localdate() - local.date()).days
    if ecart == 0:
        return local.strftime("%H:%M")
    return "Hier" if ecart == 1 else local.strftime("%d/%m")
