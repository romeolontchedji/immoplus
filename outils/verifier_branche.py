#!/usr/bin/env python3
"""Valide le nom d'une branche (courante par défaut, ou celles passées en arguments)."""

import re
import subprocess
import sys

MOTIF = re.compile(
    r"^(main|(feat|fix|refactor|perf|test|docs|style|build|ci|chore|sec)/[a-z0-9]+(-[a-z0-9]+)*)$"
)


def erreur(nom):
    """Retourne un message d'erreur en français, ou None si le nom est valide."""
    if len(nom) > 60:
        return f"Branche « {nom} » trop longue ({len(nom)} caractères, 60 au plus)."
    if not MOTIF.match(nom):
        return (
            f"Nom de branche « {nom} » invalide.\n"
            "    Format : type/mots-en-minuscules-separes-par-des-tirets (sans majuscule, accent ni underscore).\n"
            "    Exemple : feat/messagerie-envoi-message"
        )
    return None


def main(argv):
    if not argv:
        # symbolic-ref fonctionne aussi sur une branche sans commit ; échoue en HEAD détaché (rien à contrôler).
        r = subprocess.run(
            ["git", "symbolic-ref", "--short", "HEAD"], capture_output=True, text=True
        )
        argv = [r.stdout.strip()] if r.returncode == 0 else []
    noms = argv
    echec = False
    for nom in noms:
        if nom == "HEAD":
            continue
        message = erreur(nom)
        if message:
            sys.stderr.write(f"\n✗ {message}\n\n")
            echec = True
    return 1 if echec else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
