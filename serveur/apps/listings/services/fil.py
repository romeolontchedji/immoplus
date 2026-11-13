"""Fil public et recherche : lecture + mesure des recherches sans résultat (CDC §7.4, §9.10)."""

from apps.core import stats

from .. import selectors
from . import filtres as f
from . import recherche_texte

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


def _mode_de_recherche(effectifs: dict, analyse) -> str:
    """« et » : toutes les annonces contiennent tous les mots. S'il n'y en a aucune et que la saisie compte plusieurs
    mots, « ou » : au moins un mot suffit. Décidé à chaque page (le curseur ne dit pas quel mode a servi)."""
    if len(analyse.mots) < 2:
        return "et"
    premiere = selectors.fil({**effectifs, "q_mode": "et", "cursor": None, "limit": 1})
    return "et" if premiere["items"] else "ou"


def rechercher(params) -> dict:
    criteres = f.normaliser(params)
    # La saisie est comprise avant d'être cherchée : quartier reconnu (même avec une faute), remplissage écarté.
    analyse = recherche_texte.analyser(
        criteres["q"],
        [(d.slug, d.name) for d in selectors.quartiers_actifs()],
        chercher_quartiers=not criteres[
            "districts"
        ],  # un quartier déjà choisi dans les filtres prime
    )
    effectifs = {
        **criteres,
        "q": " ".join(analyse.mots),
        "districts": criteres["districts"] or analyse.districts,
    }
    mode = _mode_de_recherche(effectifs, analyse)
    resultat = selectors.fil({**effectifs, "q_mode": mode})
    vide = not resultat["items"]
    if criteres["q"] and not criteres["cursor"] and vide:
        stats.incrementer("search_empty")
    return {
        **resultat,
        "filtres": criteres,
        "vide": vide,
        "alerte_proposee": f.a_des_criteres(effectifs),
        "voisins": _voisins({**effectifs, "q_mode": mode}, len(resultat["items"])),
        # Ce que la recherche a compris : le site l'explique à la personne (page Chambres seulement).
        "interpretation": {
            "saisie": criteres["q"],
            "mots": analyse.mots,
            "ignores": analyse.ignores,
            "reconnus": analyse.reconnus,
            "mode": mode,
            "sans_critere": bool(criteres["q"] and not analyse.mots and not analyse.reconnus),
        },
        "suggestions": selectors.quartiers_avec_chambres(6) if vide and criteres["q"] else [],
    }
