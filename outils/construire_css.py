#!/usr/bin/env python3
"""Assemble, minifie et empreinte le CSS du site (bibliothèque standard uniquement).

Couches, dans l'ordre : tokens, base, layout, components/*.css, utilities.
Sortie : serveur/web/static/css/dist/immoplus.<empreinte>.css et manifest.json.
"""

import hashlib
import json
import os
import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
SOURCES = Path(
    os.environ.get("IMMOPLUS_CSS_SOURCES", RACINE / "serveur" / "web" / "static" / "css")
)
DIST = SOURCES / "dist"
COUCHES = ["tokens", "base", "layout", "components", "utilities"]


def minifier(css: str) -> str:
    """Retire commentaires et espaces superflus (sans toucher aux chaînes ni aux `calc`)."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = re.sub(r"\s+", " ", css)
    css = re.sub(r"\s*([{};,>])\s*", r"\1", css)
    css = re.sub(r":\s+", ":", css)
    css = css.replace(";}", "}")
    return css.strip()


def lire_couche(nom: str) -> str:
    if nom == "components":
        fichiers = sorted((SOURCES / "components").glob("*.css"))
        return "\n".join(f.read_text(encoding="utf-8") for f in fichiers)
    return (SOURCES / f"{nom}.css").read_text(encoding="utf-8")


def assembler() -> str:
    blocs = [f"@layer {', '.join(COUCHES)};"]
    for nom in COUCHES:
        blocs.append(f"@layer {nom}{{{minifier(lire_couche(nom))}}}")
    return "".join(blocs)


def construire() -> Path:
    css = assembler()
    empreinte = hashlib.sha256(css.encode("utf-8")).hexdigest()[:10]
    DIST.mkdir(parents=True, exist_ok=True)
    for ancien in DIST.glob("immoplus.*.css"):
        ancien.unlink()
    sortie = DIST / f"immoplus.{empreinte}.css"
    sortie.write_text(css, encoding="utf-8")
    (DIST / "manifest.json").write_text(
        json.dumps({"immoplus.css": f"css/dist/{sortie.name}"}, indent=2) + "\n", encoding="utf-8"
    )
    return sortie


if __name__ == "__main__":
    chemin = construire()
    try:
        nom = chemin.relative_to(RACINE)
    except ValueError:
        nom = chemin
    sys.stdout.write(f"CSS construit : {nom} ({chemin.stat().st_size} octets)\n")
    sys.exit(0)
