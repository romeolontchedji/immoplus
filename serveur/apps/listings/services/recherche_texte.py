"""Compréhension de la saisie de recherche : mots de remplissage ignorés, quartiers reconnus même avec une faute.

« je cherche une chambre pas chère à zogo avec forage » devient : quartier Zongo (corrigé) + mot « forage ».
Fonctions pures, sans accès à la base : les quartiers sont donnés par l'appelant.
"""

import difflib
import re
import unicodedata
from dataclasses import dataclass, field

# Au-delà, le reste de la phrase est ignoré (la requête SQL reste bornée).
MAX_MOTS = 12
# Un nom saisi doit ressembler à au moins 80 % du nom du quartier (« zogo » → « zongo » : 89 %).
SEUIL_PROXIMITE = 0.8
# En dessous de 4 lettres, seule l'égalité exacte reconnaît un quartier : trop de bruit sinon.
LONGUEUR_MIN_APPROXIMATION = 4

# Mots qui n'aident pas à trouver une chambre : ils n'apparaissent pas dans les annonces ou apparaissent partout.
# Sans accents, en minuscules. « zone » n'y figure pas : « Zone industrielle » est un quartier.
MOTS_VIDES = frozenset(
    """
    je j tu il elle on nous vous ils elles me m moi te t se s ce c ca cela ceci qui que qu quoi dont ou et ni mais
    donc car si le la les l un une des d du de au aux a en dans sur sous pour par avec sans chez vers entre
    mon ma mes ton ta tes son sa ses notre nos votre vos leur leurs y est sont ete etre ai as avons avez ont
    fait faire peut pouvoir
    cherche cherches chercher cherchons recherche rechercher voudrais voudrait veux veut souhaite souhaiterais
    besoin trouver trouve louer location loue disponible disponibles svp stp plait merci bonjour bonsoir salut
    pas trop tres plus moins bien bon bonne petit petite grand grande beau belle cher chere chers cheres
    pres proche proches environ autour alentours coin quartier quartiers ville parakou
    chambre chambres piece pieces logement logements
    fcfa cfa f francs franc xof
    """.split()
)


def sans_accents(texte: str) -> str:
    """Minuscules sans accents ni ligatures (« Cœur » → « coeur »)."""
    decompose = unicodedata.normalize("NFKD", texte.lower().replace("œ", "oe").replace("æ", "ae"))
    return "".join(c for c in decompose if not unicodedata.combining(c))


def _compact(texte: str) -> str:
    return re.sub(r"[^a-z0-9]", "", sans_accents(texte))


def _proximite(saisi: str, nom: str) -> tuple[float, bool]:
    """(ressemblance de 0 à 1, vrai si c'est une faute et non un début de nom). 0 : ça ne ressemble pas assez."""
    if saisi == nom:
        return 1.0, False
    if len(saisi) < LONGUEUR_MIN_APPROXIMATION:
        return 0.0, False
    if nom.startswith(saisi):  # « bani » pendant la frappe de « Banikanni »
        return 0.95, False
    rapport = difflib.SequenceMatcher(None, saisi, nom).ratio()
    return (rapport, True) if rapport >= SEUIL_PROXIMITE else (0.0, False)


@dataclass
class Analyse:
    mots: list[str] = field(default_factory=list)  # à chercher dans le texte des annonces
    districts: list[str] = field(default_factory=list)  # slugs des quartiers reconnus
    reconnus: list[dict] = field(default_factory=list)  # {"saisi", "nom", "slug", "corrige"}
    ignores: list[str] = field(default_factory=list)  # remplissage et nombres, écartés


def analyser(
    saisie: str, quartiers: list[tuple[str, str]], *, chercher_quartiers: bool = True
) -> Analyse:
    """Sépare la saisie en quartiers reconnus, mots utiles et mots ignorés. `quartiers` : [(slug, nom)]."""
    mots = re.findall(r"[^\W_]+", saisie or "")[:MAX_MOTS]
    normes = [sans_accents(m) for m in mots]
    pris = [False] * len(mots)
    analyse = Analyse()

    if chercher_quartiers and quartiers:
        comparables = [(slug, nom, _compact(nom)) for slug, nom in quartiers if _compact(nom)]
        for taille in (3, 2, 1):  # « zone industrielle » avant « zone »
            for debut in range(len(mots) - taille + 1):
                fin = debut + taille
                if any(pris[debut:fin]):
                    continue
                if normes[debut] in MOTS_VIDES or normes[fin - 1] in MOTS_VIDES:
                    continue  # un nom ne commence ni ne finit par « à », « de »… (« à zogo » : seul « zogo » compte)
                candidat = "".join(normes[debut:fin])
                meilleur = (0.0, False, "", "")
                for slug, nom, compact in comparables:
                    note, faute = _proximite(candidat, compact)
                    if note > meilleur[0]:
                        meilleur = (note, faute, slug, nom)
                if meilleur[0] > 0:
                    pris[debut:fin] = [True] * taille
                    if meilleur[2] not in analyse.districts:
                        analyse.districts.append(meilleur[2])
                        analyse.reconnus.append(
                            {
                                "saisi": " ".join(mots[debut:fin]),
                                "nom": meilleur[3],
                                "slug": meilleur[2],
                                "corrige": meilleur[1],
                            }
                        )

    # Un seul mot : on le garde tel quel (frappe en cours, « a », « b »…), le remplissage ne s'applique qu'aux phrases.
    phrase = len(mots) >= 2
    for i, mot in enumerate(mots):
        if pris[i]:
            continue
        if phrase and (normes[i] in MOTS_VIDES or (normes[i].isdigit() and len(normes[i]) >= 4)):
            analyse.ignores.append(mot)  # « 30000 » : le budget se règle avec le filtre de loyer
        else:
            analyse.mots.append(mot)
    return analyse
