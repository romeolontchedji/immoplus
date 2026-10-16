#!/usr/bin/env python3
"""Refuse les chemins et contenus qui violent les conventions de nommage de Logeo."""

import os
import re
import sys
import tomllib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import depot  # noqa: E402

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEBAB = r"[a-z0-9]+(?:[.-][a-z0-9]+)*"
SEGMENT_SOUPLE = re.compile(r"^[a-z0-9_.-]+$")
SEGMENTS_IMPOSES = {"ISSUE_TEMPLATE", "LC_MESSAGES"}
# Arborescences dont les noms suivent une convention externe : maquettes Design (majuscules et
# espaces), gabarits imposés par l'admin Django (ex. change_list.html) et Expo / React Native
# (composants en PascalCase, groupes (…), segments [id] et fichiers +not-found).
ARBRES_SANS_CONVENTION = (
    "docs/design/",
    "logeo-design-pack/",
    "serveur/adminsite/templates/admin/",
    "mobile/",
)
PAR_EXTENSION = {
    ".py": re.compile(r"^[a-z0-9_]+\.py$"),
    ".html": re.compile(rf"^{KEBAB}\.html$"),
    ".css": re.compile(rf"^{KEBAB}\.css$"),
    ".js": re.compile(rf"^{KEBAB}\.js$"),
    ".md": re.compile(rf"^{KEBAB}\.md$"),
}


def configuration():
    with open(os.path.join(RACINE, "outils", "mots-interdits.toml"), "rb") as f:
        return tomllib.load(f)


def erreurs_chemin(chemin, conf):
    erreurs = []
    motifs = re.compile("|".join(re.escape(m) for m in conf["motifs"]), re.I)
    if motifs.search(chemin):
        erreurs.append(
            f"{chemin} : le chemin contient un mot interdit (« backend »). Le dossier s'appelle « serveur/ »."
        )
    if chemin.startswith(ARBRES_SANS_CONVENTION):
        return erreurs
    segments = chemin.split("/")
    nom = segments[-1]
    for seg in segments[:-1]:
        if seg.startswith(".") or seg in SEGMENTS_IMPOSES:
            continue
        if not SEGMENT_SOUPLE.match(seg):
            erreurs.append(
                f"{chemin} : dossier « {seg} » hors convention (minuscules, chiffres, - et _)."
            )
    radical = nom.split(".")[0]
    if (
        nom in conf["noms_imposes"]
        or radical in conf["noms_majuscules"]
        or nom in {"base_site.html", "swagger_ui.html", "logeo_admin.css"}
        or nom.startswith((".", "_"))
    ):
        return erreurs
    motif = PAR_EXTENSION.get(os.path.splitext(nom)[1])
    if motif is not None:
        if not motif.match(nom):
            regle = "snake_case" if nom.endswith(".py") else "kebab-case"
            erreurs.append(f"{chemin} : nom de fichier hors convention ({regle} attendu).")
    elif not SEGMENT_SOUPLE.match(nom):
        erreurs.append(
            f"{chemin} : nom de fichier hors convention (minuscules, chiffres, - _ et .)."
        )
    return erreurs


def erreurs_contenu(chemin, texte, conf):
    if any(
        chemin == f or (f.endswith("/") and chemin.startswith(f)) for f in conf["fichiers_exemptes"]
    ):
        return []
    motifs = re.compile("|".join(re.escape(m) for m in conf["motifs"]), re.I)
    erreurs = []
    for numero, ligne in enumerate(texte.splitlines(), start=1):
        if motifs.search(ligne) and not any(j in ligne for j in conf["exceptions_jetons"]):
            erreurs.append(
                f"{chemin}:{numero} : mot interdit (« backend »). Exceptions : outils/mots-interdits.toml."
            )
    return erreurs


def main(argv):
    indexe = "--indexe" in argv
    conf = configuration()
    erreurs = []
    for chemin in depot.fichiers(indexe):
        erreurs += erreurs_chemin(chemin, conf)
        t = depot.texte(chemin, indexe)
        if t is not None:
            erreurs += erreurs_contenu(chemin, t, conf)
    if erreurs:
        sys.stderr.write("\n✗ Contrôle des noms : refusé\n")
        for e in erreurs:
            sys.stderr.write(f"  - {e}\n")
        sys.stderr.write("\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
