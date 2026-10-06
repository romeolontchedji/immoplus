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
