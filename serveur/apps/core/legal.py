"""Textes légaux (CDC §8.4) : une source Markdown versionnée par document, l'identité de l'éditeur dans les paramètres
(`LEGAL_*`), un seul rendu partagé par le site (HTML) et l'application (blocs de texte simples).
"""

from functools import lru_cache
from pathlib import Path

from markdown_it import MarkdownIt

from . import configuration, parametres
from .errors import ErreurMetier

DOSSIER = Path(__file__).parent / "textes_legaux"
DOCUMENTS = {"conditions": "conditions.md", "confidentialite": "confidentialite.md"}
_md = MarkdownIt("commonmark", {"html": False})  # source interne, HTML brut interdit malgré tout


@lru_cache(maxsize=len(DOCUMENTS))
def _source(slug: str) -> str:
    return (DOSSIER / DOCUMENTS[slug]).read_text(encoding="utf-8")


def editeur() -> dict:
    return {
        "company": parametres.lire("LEGAL_COMPANY"),
        "rccm": parametres.lire("LEGAL_RCCM"),
        "ifu": parametres.lire("LEGAL_IFU"),
        "address": parametres.lire("LEGAL_ADDRESS"),
        "email": parametres.lire("LEGAL_EMAIL"),
        "phone": configuration.contact_equipe()["phone_display"],
    }


def _remplir(texte: str, e: dict) -> str:
    for cle, valeur in {
        "raison_sociale": e["company"], "rccm": e["rccm"], "ifu": e["ifu"],
        "adresse": e["address"], "email": e["email"], "telephone": e["phone"],
    }.items():  # fmt: skip
        texte = texte.replace(f"[[{cle}]]", str(valeur))
    return texte


def _texte_en_ligne(jeton) -> tuple[str | None, str]:
    """(libellé en gras de tête, texte) d'un élément en ligne : « **Compte :** numéro… » → ("Compte", "numéro…")."""
    enfants = [e for e in (jeton.children or []) if not (e.type == "text" and e.content == "")]
    libelle, morceaux, dans_gras_initial = None, [], False
    for i, e in enumerate(enfants):
        if e.type == "strong_open" and i == 0:
            dans_gras_initial, libelle = True, ""
        elif e.type == "strong_close" and dans_gras_initial:
            dans_gras_initial = False
        elif e.type == "text":
            if dans_gras_initial:
                libelle += e.content
            else:
                morceaux.append(e.content)
        elif e.type in ("softbreak", "hardbreak"):
            morceaux.append("\n")
        elif e.type == "code_inline":
            morceaux.append(e.content)
    if libelle is not None:
        libelle = libelle.strip().rstrip(":").strip()
    return libelle, "".join(morceaux).strip()


def document(slug: str) -> dict:
    if slug not in DOCUMENTS:
        raise ErreurMetier("not_found", "Document introuvable.", statut=404)
    e = editeur()
    source = _remplir(_source(slug), e)
    jetons = _md.parse(source)
    titre, resume, sections = "", "", []
    type_bloc = None
    for i, j in enumerate(jetons):
        if j.type == "heading_open":
            contenu = jetons[i + 1].content
            if j.tag == "h1":
                titre = contenu
            else:
                sections.append({"title": contenu, "blocks": [], "_debut": i})
        elif j.type in ("paragraph_open", "list_item_open") and type_bloc is None:
            type_bloc = "li" if j.type == "list_item_open" else "p"
        elif j.type == "inline" and type_bloc and jetons[i - 1].type == "paragraph_open":
            libelle, texte = _texte_en_ligne(j)
            if not sections:
                resume = resume or texte
            else:
                bloc = {"type": type_bloc, "text": texte}
                if libelle:
                    bloc["label"] = libelle
                sections[-1]["blocks"].append(bloc)
        elif j.type in ("paragraph_close", "list_item_close"):
            if j.type == "list_item_close" or type_bloc == "p":
                type_bloc = None
    # HTML de chaque section, pour le site (même source, même découpage).
    fins = [s["_debut"] for s in sections[1:]] + [len(jetons)]
    for s, fin in zip(sections, fins, strict=True):
        s["html"] = _md.renderer.render(jetons[s.pop("_debut") + 3 : fin], _md.options, {})
    return {
        "slug": slug,
        "title": titre,
        "summary": resume,
        "version": str(parametres.lire("TERMS_VERSION")),
        "updated_at": parametres.lire("LEGAL_UPDATED_AT"),
        "provisional": bool(parametres.lire("LEGAL_PROVISIONAL")),
        "editor": e,
        "sections": sections,
    }
