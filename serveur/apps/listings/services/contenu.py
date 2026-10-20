"""« Autres détails » des annonces : texte simple, sans mise en forme (19/10/2026) ; détection des coordonnées (CDC §11.7).

Le gérant écrit du texte brut : les marques de mise en forme (gras, italique, titres) d'anciennes descriptions sont
retirées, les retours à la ligne sont gardés. Le HTML produit ne contient que <p> et <br>, texte échappé.
"""

import html as html_lib
import re
from dataclasses import dataclass, field

import nh3

from apps.core.errors import ErreurMetier

LONGUEUR_MAX = 4000


def texte_simple(texte: str) -> str:
    """Texte brut : HTML, liens, marques de gras, d'italique, de barré et de titre retirés ; trois lignes vides au plus."""
    texte = nh3.clean(texte or "", tags=set())
    texte = texte.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    texte = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", texte)
    texte = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", texte)
    texte = texte.replace("`", "")
    texte = re.sub(r"(?m)^\s*>+\s?", "", texte)
    texte = re.sub(r"(?m)^\s{0,3}#{1,6}\s+", "", texte)
    texte = re.sub(r"(\*\*|__|~~)(.+?)\1", r"\2", texte)
    texte = re.sub(r"(?<![\w*])[*_](?!\s)(.+?)(?<!\s)[*_](?![\w*])", r"\1", texte)
    texte = re.sub(r"(?m)^\s*[*+]\s+", "- ", texte)
    texte = re.sub(r"[ \t]+\n", "\n", texte)
    texte = re.sub(r"\n{3,}", "\n\n", texte)
    return texte.strip()


def rendre(texte: str) -> tuple[str, str]:
    """Retourne (texte simple, HTML : paragraphes et retours à la ligne). Lève `ErreurMetier` si trop long."""
    propre = texte_simple(texte)
    if len(propre) > LONGUEUR_MAX:
        raise ErreurMetier(
            "validation_error",
            f"Les autres détails sont trop longs ({LONGUEUR_MAX} caractères au plus).",
            champs={"description_md": ["Trop long"]},
        )
    paragraphes = [p for p in re.split(r"\n\s*\n", propre) if p.strip()]
    html = "".join(
        "<p>" + "<br>".join(html_lib.escape(ligne) for ligne in p.splitlines()) + "</p>"
        for p in paragraphes
    )
    return propre, html


def texte_brut(html: str) -> str:
    return nh3.clean(html or "", tags=set()).replace("&amp;", "&")


# --------------------------------------------------------------- détection des coordonnées
_CHIFFRES_LETTRES = r"(?:z[ée]ro|un|deux|trois|quatre|cinq|six|sept|huit|neuf)"
_MOTS_CLES = re.compile(
    r"whats?\s*app|watsap|wh?atsapp|telegram|t[ée]l[ée]gram|facebook|messenger|insta(?:gram)?|appelle[\s-]*moi|mon\s+num[ée]ro",
    re.I,
)
_EMAIL = re.compile(r"[\w.+-]+\s*(?:@|\(at\)|\[at\])\s*[\w-]+(?:\.|\s*\(dot\)\s*)[a-z]{2,}", re.I)
_LIEN = re.compile(
    r"https?://|www\.|\b[a-z0-9-]{2,}\.(?:com|net|org|bj|fr|io|me|ly|gl|co|app|info|xyz)\b|\bwa\.me\b|\bt\.me\b|bit\.ly|tinyurl|chat\.whatsapp",
    re.I,
)
_TELEPHONE = re.compile(r"(?<![\w])(?:\+|00)?(?:\d[\s.\-]?){7,}\d(?![\w])")
_EPELE = re.compile(rf"(?:\b{_CHIFFRES_LETTRES}\b[\s,.\-]*){{6,}}", re.I)
_MONTANT_APRES = re.compile(r"^\s*(?:fcfa|cfa|f\b|francs?)", re.I)


@dataclass
class Detection:
    forts: list[str] = field(default_factory=list)
    faibles: list[str] = field(default_factory=list)

    @property
    def fort(self) -> bool:
        return bool(self.forts)


def detecter(texte: str) -> Detection:
    """Repère numéros, e-mails, liens (signaux forts) et mots-clés (signal faible). Les montants en FCFA sont exclus."""
    d = Detection()
    texte = texte or ""
    for m in _TELEPHONE.finditer(texte):
        if len(re.sub(r"\D", "", m.group())) >= 8 and not _MONTANT_APRES.match(
            texte[m.end() : m.end() + 12]
        ):
            d.forts.append("telephone")
            break
    if _EPELE.search(texte):
        d.forts.append("numero_epele")
    if _EMAIL.search(texte):
        d.forts.append("email")
    if _LIEN.search(texte):
        d.forts.append("lien")
    if _MOTS_CLES.search(texte):
        d.faibles.append("mot_cle")
    return d


def refuser_si_coordonnees(**champs: str) -> None:
    """Annonces : enregistrement refusé avec explication quand un signal fort est présent (mode `mask`)."""
    fautes = {nom: ["Les coordonnées (numéro, e-mail, lien) sont interdites : tout passe par la messagerie Logeo."]
              for nom, valeur in champs.items() if detecter(valeur).fort}  # fmt: skip
    if fautes:
        raise ErreurMetier(
            "contact_detected",
            "Retire les numéros, e-mails et liens de ton annonce : les échanges se font dans Logeo.",
            champs=fautes,
        )


def masquer(texte: str) -> str:
    """Remplace par des étoiles les séquences détectées comme coordonnées (mode `mask`, CDC §11.7)."""

    def etoiles(m: re.Match) -> str:
        return "*" * len(m.group())

    def telephone(m: re.Match) -> str:
        suite = texte[m.end() : m.end() + 12]
        if len(re.sub(r"\D", "", m.group())) >= 8 and not _MONTANT_APRES.match(suite):
            return etoiles(m)
        return m.group()

    resultat = _TELEPHONE.sub(telephone, texte)
    for motif in (_EPELE, _EMAIL, _LIEN):
        resultat = motif.sub(etoiles, resultat)
    return resultat
