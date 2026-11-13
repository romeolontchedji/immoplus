"""Compréhension de la saisie de recherche : remplissage ignoré, quartiers, types de chambre et équipements reconnus,
même avec une faute (« zogo » → Zongo, « foraje » → forage).

« je cherche une chambre sanitaire à zogo avec forage et douche » devient : type Chambre sanitaire + quartier Zongo +
eau forage + douche interne. Fonctions pures, sans accès à la base : quartiers et types sont donnés par l'appelant.
"""

import difflib
import re
import unicodedata
from dataclasses import dataclass, field

# Au-delà, le reste de la phrase est ignoré (la requête SQL reste bornée).
MAX_MOTS = 12
# Un nom saisi doit ressembler à au moins 80 % du nom cherché (« zogo » → « zongo » : 89 %).
SEUIL_PROXIMITE = 0.8
# En dessous de 4 lettres, seule l'égalité exacte reconnaît un nom : trop de bruit sinon.
LONGUEUR_MIN_APPROXIMATION = 4
# Un type ou un quartier s'écrit sur 1 à 4 mots (« entrée couché semi sanitaire »).
MOTS_MAX_D_UN_NOM = 4

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

# Équipements : suite de mots (chacun avec ses variantes) → critère du fil. Les règles les plus longues passent d'abord.
# (genre affiché, libellé affiché, critère, valeur, mots)
_EQUIPEMENTS = [
    ("Eau", "compteur d'eau personnel", "water", "individual", [("compteur",), ("eau",), ("personnel", "individuel", "prive")]),
    ("Eau", "décompteur", "water", "sub_meter", [("decompteur",), ("eau",)]),
    ("Eau", "eau courante partagée", "water", "running", [("eau",), ("courante", "partagee", "commune")]),
    ("Eau", "forage", "water", "borehole", [("forage",)]),
    ("Eau", "puits", "water", "well", [("puits",)]),
    ("Électricité", "compteur personnel", "meter", "individual", [("compteur", "electricite"), ("personnel", "individuel", "prive", "personnelle", "individuelle")]),
    ("Électricité", "compteur partagé", "meter", "shared", [("compteur", "electricite"), ("partage", "commun", "partagee", "commune")]),
    ("Cuisine", "cuisine interne", "kitchen", "private", [("cuisine",), ("interne", "privee", "individuelle", "personnelle")]),
    ("Cuisine", "cuisine commune", "kitchen", "shared", [("cuisine",), ("commune", "partagee", "collective")]),
    ("Douche", "douche interne", "bathroom", True, [("douche",), ("interne", "privee", "personnelle")]),
    ("Douche", "douche interne", "bathroom", True, [("douche",)]),
    ("Clôture", "clôturée", "fenced", True, [("cloture", "cloturee", "cloturees")]),
]  # fmt: skip
_EQUIPEMENTS.sort(key=lambda r: -len(r[4]))
GENRES_LISTES = {"water", "meter", "kitchen"}


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
    if abs(len(saisi) - len(nom)) > max(1, round(len(nom) * 0.2)):
        return (
            0.0,
            False,
        )  # pas la même longueur : une phrase contenant le nom n'est pas une faute de frappe du nom
    rapport = difflib.SequenceMatcher(None, saisi, nom).ratio()
    return (rapport, True) if rapport >= SEUIL_PROXIMITE else (0.0, False)


def _mot_ressemble(saisi: str, variantes: tuple[str, ...]) -> tuple[bool, bool]:
    """(ressemble, avec faute) d'un mot saisi à l'une des variantes d'un mot attendu."""
    for variante in variantes:
        note, faute = _proximite(saisi, variante)
        if note >= SEUIL_PROXIMITE:
            return True, faute
    return False, False


@dataclass
class Analyse:
    mots: list[str] = field(default_factory=list)  # à chercher dans le texte des annonces
    districts: list[str] = field(default_factory=list)  # slugs des quartiers reconnus
    types: list[str] = field(default_factory=list)  # slugs des types de chambre reconnus
    filtres: dict = field(
        default_factory=dict
    )  # équipements : water, meter, kitchen (listes), bathroom, fenced
    reconnus: list[dict] = field(
        default_factory=list
    )  # quartiers : {"saisi", "nom", "slug", "corrige"}
    comprises: list[dict] = field(
        default_factory=list
    )  # tout ce qui est compris : genre, libellé, saisi, faute
    ignores: list[str] = field(default_factory=list)  # remplissage et nombres, écartés


def _noms(taille_max: int, normes: list[str], pris: list[bool], candidats, *, bords_libres: bool):
    """Cherche des suites de mots qui ressemblent à un nom. `candidats` : [(identifiant, libellé, forme compacte)].
    Produit (début, fin, [(identifiant, libellé)], faute). Un nom ne finit jamais par un mot de remplissage ; il peut
    commencer par l'un d'eux (« chambre sanitaire ») si `bords_libres`, sinon non (« à zogo » : seul « zogo » compte)."""
    trouves = []
    mots_des_noms = {
        sans_accents(m) for _, libelle, _ in candidats for m in re.findall(r"[^\W_]+", libelle)
    }
    for taille in range(min(taille_max, len(normes)), 0, -1):
        for debut in range(len(normes) - taille + 1):
            fin = debut + taille
            if any(pris[debut:fin]):
                continue
            if taille == 1 and normes[debut] in MOTS_VIDES:
                continue
            if normes[fin - 1] in MOTS_VIDES:
                continue  # un nom ne finit jamais par « à », « de »…
            if normes[debut] in MOTS_VIDES and not (
                bords_libres and normes[debut] in mots_des_noms
            ):
                continue  # …et ne commence par un mot de remplissage que si c'est un mot des noms (« chambre »)
            candidat = "".join(normes[debut:fin])
            notes = [
                (_proximite(candidat, compact), ident, libelle, compact)
                for ident, libelle, compact in candidats
            ]
            notes = [n for n in notes if n[0][0] > 0]
            if not notes:
                continue
            meilleur = max(n[0][0] for n in notes)
            retenus = [
                (ident, libelle)
                for (note, _), ident, libelle, compact in notes
                # le meilleur, et les variantes qui continuent le nom saisi (« studio » : Studio et Studio meublé)
                if note == meilleur or (len(candidat) >= 5 and compact.startswith(candidat))
            ]
            faute = next(f for (n, f), *_ in notes if n == meilleur)
            for i in range(debut, fin):
                pris[i] = True
            trouves.append((debut, fin, retenus, faute))
    return trouves


def analyser(
    saisie: str,
    quartiers: list[tuple[str, str]],
    types: list[tuple[str, str]] | None = None,
    *,
    deja: frozenset[str] = frozenset(),
) -> Analyse:
    """Sépare la saisie en types, équipements, quartiers, mots utiles et mots ignorés.

    `quartiers` et `types` : [(slug, nom)]. `deja` : critères déjà posés dans les filtres de la page
    (`districts`, `types`, `water`, `meter`, `kitchen`, `bathroom`, `fenced`) : la saisie ne les remplace pas."""
    mots = re.findall(r"[^\W_]+", saisie or "")[:MAX_MOTS]
    normes = [sans_accents(m) for m in mots]
    pris = [False] * len(mots)
    analyse = Analyse()

    def ajouter(genre: str, libelle: str, debut: int, fin: int, faute: bool) -> None:
        analyse.comprises.append(
            {
                "genre": genre,
                "libelle": libelle,
                "saisi": " ".join(mots[debut:fin]),
                "corrige": faute,
            }
        )

    # 1. Types de chambre (« chambre sanitaire » avant que « chambre » ne soit pris pour du remplissage).
    if types and "types" not in deja:
        candidats = [(slug, nom, _compact(nom)) for slug, nom in types if _compact(nom)]
        for debut, fin, retenus, faute in _noms(
            MOTS_MAX_D_UN_NOM, normes, pris, candidats, bords_libres=True
        ):
            for slug, _ in retenus:
                if slug not in analyse.types:
                    analyse.types.append(slug)
            ajouter("Type", " ou ".join(nom for _, nom in retenus), debut, fin, faute)

    # 2. Équipements : eau, électricité, cuisine, douche, clôture.
    for genre, libelle, cle, valeur, motifs in _EQUIPEMENTS:
        if cle in deja or (cle in analyse.filtres and cle not in GENRES_LISTES):
            continue
        for debut in range(len(mots) - len(motifs) + 1):
            fin = debut + len(motifs)
            if any(pris[debut:fin]):
                continue
            ressemblances = [
                _mot_ressemble(normes[debut + k], motif) for k, motif in enumerate(motifs)
            ]
            if not all(ok for ok, _ in ressemblances):
                continue
            for i in range(debut, fin):
                pris[i] = True
            if cle in GENRES_LISTES:
                if valeur not in analyse.filtres.setdefault(cle, []):
                    analyse.filtres[cle].append(valeur)
            else:
                analyse.filtres[cle] = valeur
            ajouter(genre, libelle, debut, fin, any(f for _, f in ressemblances))
            break

    # 3. Quartiers.
    if quartiers and "districts" not in deja:
        candidats = [(slug, nom, _compact(nom)) for slug, nom in quartiers if _compact(nom)]
        for debut, fin, retenus, faute in _noms(
            MOTS_MAX_D_UN_NOM - 1, normes, pris, candidats, bords_libres=False
        ):
            slug, nom = retenus[0]
            if slug not in analyse.districts:
                analyse.districts.append(slug)
                analyse.reconnus.append(
                    {"saisi": " ".join(mots[debut:fin]), "nom": nom, "slug": slug, "corrige": faute}
                )
                ajouter("Quartier", nom, debut, fin, faute)

    # 4. Le reste. Un seul mot est gardé tel quel (frappe en cours : « a », « b »…) ; le remplissage ne s'applique
    # qu'aux phrases.
    phrase = len(mots) >= 2
    for i, mot in enumerate(mots):
        if pris[i]:
            continue
        if phrase and (normes[i] in MOTS_VIDES or (normes[i].isdigit() and len(normes[i]) >= 4)):
            analyse.ignores.append(mot)  # « 30000 » : le budget se règle avec le filtre de loyer
        else:
            analyse.mots.append(mot)
    return analyse
