"""Lecture et validation des critères du fil et de la recherche (CDC §10.3), communes à l'API et au site."""

import datetime
from collections.abc import Mapping

from apps.core.errors import ErreurMetier

from ..enums import Compteur, Eau, TypeChambre

TRIS = ("recent", "rent_asc", "rent_desc", "distance")
LIMITE_DEFAUT = 10
LIMITE_MAX = 50


def _liste(valeur: str | None, autorises=None, champ: str = "") -> list[str]:
    if not valeur:
        return []
    elements = [e.strip() for e in valeur.split(",") if e.strip()][:20]
    if autorises is not None:
        inconnus = [e for e in elements if e not in autorises]
        if inconnus:
            raise ErreurMetier(
                "validation_error",
                "Valeur de filtre inconnue.",
                champs={champ: [f"Valeur inconnue : {inconnus[0]}"]},
            )
    return elements


def _entier(valeur, champ: str, minimum: int = 0, maximum: int = 10**9) -> int | None:
    if valeur in (None, ""):
        return None
    try:
        nombre = int(valeur)
    except (TypeError, ValueError) as erreur:
        raise ErreurMetier(
            "validation_error", "Nombre attendu.", champs={champ: ["Nombre entier attendu"]}
        ) from erreur
    if not minimum <= nombre <= maximum:
        raise ErreurMetier(
            "validation_error", "Valeur hors limites.", champs={champ: ["Valeur hors limites"]}
        )
    return nombre


def _booleen(valeur, champ: str) -> bool | None:
    if valeur in (None, ""):
        return None
    if str(valeur).lower() in ("1", "true", "oui", "on"):
        return True
    if str(valeur).lower() in ("0", "false", "non", "off"):
        return False
    raise ErreurMetier(
        "validation_error", "Booléen attendu.", champs={champ: ["Valeur true ou false attendue"]}
    )


def normaliser(params: Mapping) -> dict:
    """Transforme les paramètres bruts (chaînes) en critères typés ; lève `validation_error` sinon."""
    q = " ".join(str(params.get("q") or "").split())[:100]
    tri = params.get("sort") or "recent"
    if tri not in TRIS:
        raise ErreurMetier(
            "validation_error", "Tri inconnu.", champs={"sort": [f"Valeurs : {', '.join(TRIS)}"]}
        )
    avant = params.get("available_before")
    if avant:
        try:
            avant = datetime.date.fromisoformat(str(avant))
        except ValueError as erreur:
            raise ErreurMetier(
                "validation_error", "Date invalide.", champs={"available_before": ["AAAA-MM-JJ"]}
            ) from erreur
    loyer_min = _entier(params.get("rent_min"), "rent_min")
    loyer_max = _entier(params.get("rent_max"), "rent_max")
    if loyer_min is not None and loyer_max is not None and loyer_min > loyer_max:
        raise ErreurMetier(
            "validation_error",
            "Le loyer minimum dépasse le maximum.",
            champs={"rent_min": ["Supérieur au loyer maximum"]},
        )
    return {
        "q": q,
        "districts": _liste(params.get("district")),
        "types": _liste(params.get("type"), TypeChambre.values, "type"),
        "rent_min": loyer_min,
        "rent_max": loyer_max,
        "bathroom": _booleen(params.get("bathroom"), "bathroom"),
        "water": _liste(params.get("water"), Eau.values, "water"),
        "meter": _liste(params.get("meter"), Compteur.values, "meter"),
        "fenced": _booleen(params.get("fenced"), "fenced"),
        "available_before": avant or None,
        "max_distance_m": _entier(params.get("max_distance_m"), "max_distance_m"),
        "sort": tri,
        "cursor": params.get("cursor") or None,
        "limit": _entier(params.get("limit"), "limit", 1, LIMITE_MAX) or LIMITE_DEFAUT,
    }


def a_des_criteres(filtres: dict) -> bool:
    """Vrai si au moins un critère de recherche (hors tri et pagination) est posé."""
    return any(
        filtres.get(cle) not in (None, "", [])
        for cle in (
            "q", "districts", "types", "rent_min", "rent_max", "bathroom", "water", "meter",
            "fenced", "available_before", "max_distance_m",
        )
    )  # fmt: skip
