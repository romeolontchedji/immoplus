"""Fil public et recherche : lecture + mesure des recherches sans résultat (CDC §7.4, §9.10)."""

from apps.core import stats

from .. import selectors
from . import filtres as f

# Un quartier qui donne moins de résultats que ce seuil déclenche la proposition des quartiers voisins.
SEUIL_VOISINS = 3
VOISINS_MAX = 6


def _voisins(criteres: dict, deja: int) -> dict | None:
    """Mêmes critères dans les quartiers proches, proposés à part (jamais mélangés aux résultats demandés)."""
    if not criteres["districts"] or criteres["cursor"] or deja >= SEUIL_VOISINS:
        return None
    proches = selectors.quartiers_voisins(criteres["districts"])
    if not proches:
        return None
    resultat = selectors.fil(
        {**criteres, "districts": [q.slug for q in proches], "limit": VOISINS_MAX, "cursor": None}
    )
    if not resultat["items"]:
        return None
    noms = {item["district"]["name"] for item in resultat["items"]}
    return {
        "districts": [{"name": q.name, "slug": q.slug} for q in proches if q.name in noms],
        "items": resultat["items"],
    }


def rechercher(params) -> dict:
    criteres = f.normaliser(params)
    resultat = selectors.fil(criteres)
    if criteres["q"] and not criteres["cursor"] and not resultat["items"]:
        stats.incrementer("search_empty")
    return {
        **resultat,
        "filtres": criteres,
        "vide": not resultat["items"],
        "alerte_proposee": f.a_des_criteres(criteres),
        "voisins": _voisins(criteres, len(resultat["items"])),
    }
