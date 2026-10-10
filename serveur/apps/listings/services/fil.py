"""Fil public et recherche : lecture + mesure des recherches sans résultat (CDC §7.4, §9.10)."""

from apps.core import stats

from .. import selectors
from . import filtres as f


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
    }
