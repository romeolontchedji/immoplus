"""Textes légaux (CDC §8.4) : une source Markdown versionnée par document, l'identité de l'éditeur dans les paramètres
(`LEGAL_*`), un seul rendu partagé par le site (HTML) et l'application (blocs de texte simples).
"""

import re
from functools import lru_cache
from pathlib import Path

from markdown_it import MarkdownIt

from . import configuration, parametres
from .errors import ErreurMetier

DOSSIER = Path(__file__).parent / "textes_legaux"
DOCUMENTS = {"conditions": "conditions.md", "confidentialite": "confidentialite.md"}
_md = MarkdownIt("commonmark", {"html": False})  # source interne, HTML brut interdit malgré tout


@lru_cache(maxsize=len(DOCUMENTS))
def source_d_origine(slug: str) -> str:
    """Texte fourni avec l'application (celui qui sert tant que l'administration n'a rien enregistré)."""
    return (DOSSIER / DOCUMENTS[slug]).read_text(encoding="utf-8")


def _source(slug: str) -> str:
    """Texte en vigueur : celui de l'administration s'il existe, sinon le texte d'origine."""
    from .models import LegalDocument

    modifie = LegalDocument.objects.filter(pk=slug).values_list("body_md", flat=True).first()
    return modifie if modifie else source_d_origine(slug)


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
    return _construire(slug, _source(slug))


def _construire(slug: str, texte: str) -> dict:
    """Découpe un texte Markdown en titre, résumé et sections (blocs pour l'application, HTML pour le site)."""
    e = editeur()
    source = _remplir(texte, e)
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


# --------------------------------------------------------------- modification depuis l'administration
TEXTE_MAX = 60_000
VARIABLES = ("raison_sociale", "rccm", "ifu", "adresse", "email", "telephone")


def valider(texte: str) -> str:
    """Texte prêt à enregistrer, ou `ErreurMetier` expliquant ce qui ne va pas."""
    texte = (texte or "").replace("\r\n", "\n").strip()
    if not texte:
        raise ErreurMetier("validation_error", "Le texte est vide.")
    if len(texte) > TEXTE_MAX:
        raise ErreurMetier(
            "validation_error", f"Le texte est trop long ({TEXTE_MAX} caractères au plus)."
        )
    if not texte.startswith("# "):
        raise ErreurMetier(
            "validation_error",
            "Le texte commence par le titre du document, sur une ligne « # Titre ».",
        )
    if not any(ligne.startswith("## ") for ligne in texte.splitlines()):
        raise ErreurMetier(
            "validation_error",
            "Ajoute au moins une section, sur une ligne « ## 1. Titre de la section ».",
        )
    inconnues = sorted(set(re.findall(r"\[\[([^\]]*)\]\]", texte)) - set(VARIABLES))
    if inconnues:
        raise ErreurMetier(
            "validation_error",
            f"Variable inconnue : [[{inconnues[0]}]]. Variables permises : "
            + ", ".join(f"[[{v}]]" for v in VARIABLES)
            + ".",
        )
    return texte


def apercu(texte: str) -> dict:
    """Rendu d'un texte en cours d'écriture (titre, résumé, sections HTML), sans l'enregistrer."""
    doc = _construire("apercu", valider(texte))
    return {
        "title": doc["title"],
        "summary": doc["summary"],
        "sections": [s["html"] for s in doc["sections"]],
    }


def enregistrer(slug: str, texte: str, *, acteur, nouvelle_acceptation: bool = False) -> None:
    """Enregistre le texte d'un document (administrateur), date la mise à jour et, si demandé, fait accepter de
    nouveau à chacun la nouvelle version."""
    import datetime

    from django.db import transaction

    from apps.audit import services as audit

    if slug not in DOCUMENTS:
        raise ErreurMetier("not_found", "Document introuvable.", statut=404)
    if getattr(acteur, "role", None) != "admin" or not acteur.is_active:
        raise ErreurMetier("forbidden", "Réservé aux administrateurs.", statut=403)
    texte = valider(texte)
    from .models import LegalDocument

    with transaction.atomic():
        LegalDocument.objects.update_or_create(
            slug=slug, defaults={"body_md": texte, "updated_by": acteur}
        )
        parametres.definir("LEGAL_UPDATED_AT", datetime.date.today().isoformat(), par=acteur)
        if nouvelle_acceptation:
            courante = str(parametres.lire("TERMS_VERSION"))
            suivante = str(int(courante) + 1) if courante.isdigit() else "2"
            parametres.definir("TERMS_VERSION", suivante, par=acteur)
        audit.enregistrer(
            "legal.modifie",
            acteur=acteur,
            metadata={"document": slug, "nouvelle_acceptation": nouvelle_acceptation},
        )


def retablir(slug: str, *, acteur) -> None:
    """Revient au texte d'origine fourni avec l'application."""
    from apps.audit import services as audit

    from .models import LegalDocument

    if slug not in DOCUMENTS:
        raise ErreurMetier("not_found", "Document introuvable.", statut=404)
    if getattr(acteur, "role", None) != "admin" or not acteur.is_active:
        raise ErreurMetier("forbidden", "Réservé aux administrateurs.", statut=403)
    LegalDocument.objects.filter(pk=slug).delete()
    audit.enregistrer("legal.retabli", acteur=acteur, metadata={"document": slug})
