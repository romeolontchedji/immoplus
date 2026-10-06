#!/usr/bin/env python3
"""Refuse gros fichiers, traces de débogage, secrets, fichiers .env réels et sauvegardes."""

import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import depot  # noqa: E402

TAILLE_MAX = 1024 * 1024
EXCEPTIONS_TAILLE = (
    "serveur/web/static/vendor/",
    "docs/api/openapi.json",
    "docs/api/logeo.postman_collection.json",
)
CODE = (".py", ".js")
DEBOGAGE = [
    (re.compile(r"(?<![\w.])print\("), "appel à l'instruction d'affichage (utilise le journal)"),
    (re.compile(r"\bbreakpoint\(\)"), "point d'arrêt de débogage"),
    (re.compile(r"\bimport pdb\b|\bpdb\.set_trace"), "débogueur pdb"),
    (re.compile(r"\bconsole\.log\b"), "trace de console du navigateur"),
]
SECRETS = [
    (re.compile(r"AKIA[0-9A-Z]{16}"), "clé d'accès AWS"),
    (re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |)PRIVATE KEY-----"), "clé privée"),
    (re.compile(r"\b(?:sk|pk|ghp|gho|xox[bp])[-_][A-Za-z0-9_-]{20,}"), "jeton d'API"),
    (
        re.compile(
            r"(?i)\b(?:secret|password|passwd|token|api_?key)\w*\s*[:=]\s*['\"][^'\"\s$<{]{12,}['\"]"
        ),
        "secret en clair",
    ),
    (re.compile(r"[a-z][a-z0-9+.-]*://[^/\s:@'\"]+:[^/\s@'\"$<{]{3,}@"), "URL avec identifiants"),
]
# Référence du projet : contient des URL de développement factices (ex. utilisateur:utilisateur@hôte).
SANS_CONTROLE_SECRETS = ("docs/cahier-des-charges.md",)
SAUVEGARDES = re.compile(r"(\.bak|\.dump|\.sql\.gz|\.sqlite3|~|\.orig|\.rej)$")


def est_env_reel(nom):
    return nom == ".env" or (nom.startswith(".env.") and nom != ".env.example")


def erreurs_fichier(chemin, indexe, exempt_secrets=SANS_CONTROLE_SECRETS):
    nom = chemin.split("/")[-1]
    erreurs = []
    if est_env_reel(nom):
        erreurs.append(
            f"{chemin} : fichier d'environnement réel interdit (garde seulement .env.example)."
        )
    if SAUVEGARDES.search(nom):
        erreurs.append(f"{chemin} : sauvegarde ou fichier temporaire interdit.")
    brut = depot.contenu(chemin, indexe)
    if brut is not None and len(brut) > TAILLE_MAX and not chemin.startswith(EXCEPTIONS_TAILLE):
        erreurs.append(f"{chemin} : fichier de plus de 1 Mo ({len(brut) // 1024} Ko).")
    texte = depot.texte(chemin, indexe)
    if texte is None:
        return erreurs
    if chemin.endswith(CODE) and not chemin.startswith("serveur/web/static/vendor/"):
        for numero, ligne in enumerate(texte.splitlines(), start=1):
            for motif, libelle in DEBOGAGE:
                if motif.search(ligne):
                    erreurs.append(f"{chemin}:{numero} : {libelle}.")
    if chemin not in exempt_secrets:
        for numero, ligne in enumerate(texte.splitlines(), start=1):
            for motif, libelle in SECRETS:
                if motif.search(ligne):
                    erreurs.append(
                        f"{chemin}:{numero} : {libelle} détecté. Les secrets vont dans l'environnement, jamais dans le dépôt."
                    )
    return erreurs


def main(argv):
    indexe = "--indexe" in argv
    liste = depot.fichiers(indexe)
    erreurs = []
    for chemin in liste:
        erreurs += erreurs_fichier(chemin, indexe)
    if shutil.which("gitleaks") and not indexe:
        r = subprocess.run(
            ["gitleaks", "detect", "--no-banner", "--redact"], capture_output=True, text=True
        )
        if r.returncode != 0:
            erreurs.append("gitleaks a détecté un secret :\n" + r.stdout + r.stderr)
    if erreurs:
        sys.stderr.write("\n✗ Contrôle d'hygiène : refusé\n")
        for e in erreurs:
            sys.stderr.write(f"  - {e}\n")
        sys.stderr.write("\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
