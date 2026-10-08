"""Texte enrichi des annonces : Markdown restreint, assaini (CDC §11.8) ; détection des coordonnées (CDC §11.7)."""

import re
from dataclasses import dataclass, field

import nh3
from markdown_it import MarkdownIt

from apps.core.errors import ErreurMetier

LONGUEUR_MAX = 4000
LIGNES_LISTE_MAX = 40
_BALISES = {"p", "strong", "em", "s", "h3", "ul", "ol", "li", "br"}
_MD = MarkdownIt("zero").enable(
    ["paragraph", "emphasis", "strikethrough", "list", "heading", "newline", "text"]
)


def _nettoyer_source(texte: str) -> str:
    """Retire ce que le sous-ensemble interdit : HTML, images, liens (on garde le texte), code, citations."""
    texte = nh3.clean(texte, tags=set())  # balises HTML brutes supprimées
    texte = texte.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    texte = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", texte)
    texte = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", texte)
    texte = texte.replace("`", "")
    texte = re.sub(r"(?m)^\s*>+\s?", "", texte)
    texte = re.sub(r"(?m)^\s{0,3}#{1,6}\s+", "### ", texte)  # un seul niveau de titre
    return texte.strip()


def rendre(markdown: str) -> tuple[str, str]:
    """Retourne (markdown nettoyé, HTML assaini). Lève `ErreurMetier` si le texte est trop long."""
    nettoye = _nettoyer_source(markdown or "")
    if len(nettoye) > LONGUEUR_MAX:
        raise ErreurMetier(
            "validation_error",
            f"La description est trop longue ({LONGUEUR_MAX} caractères au plus).",
            champs={"description_md": ["Trop longue"]},
        )
    lignes_liste = sum(
        1 for ligne in nettoye.splitlines() if re.match(r"^\s*(?:[-*+]|\d+\.)\s", ligne)
    )
    if lignes_liste > LIGNES_LISTE_MAX:
        raise ErreurMetier(
            "validation_error",
            f"Une liste ne peut pas dépasser {LIGNES_LISTE_MAX} lignes.",
            champs={"description_md": ["Liste trop longue"]},
        )
    html = nh3.clean(_MD.render(nettoye), tags=_BALISES, attributes={}, link_rel=None)
    return nettoye, html


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
