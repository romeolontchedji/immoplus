#!/usr/bin/env python3
"""Valide un message de commit au format Logeo (Conventional Commits en français)."""

import re
import sys

TYPES = (
    "feat",
    "fix",
    "refactor",
    "perf",
    "test",
    "docs",
    "style",
    "build",
    "ci",
    "chore",
    "revert",
    "sec",
)
PORTEES = (
    "serveur",
    "web",
    "admin",
    "api",
    "ws",
    "media",
    "auth",
    "annonces",
    "messagerie",
    "notifications",
    "moderation",
    "abonnement",
    "audit",
    "infra",
    "docs",
    "deps",
    "design",
    "i18n",
    "outils",
    "mobile",
)
ENTETE = re.compile(r"^(?P<type>[a-z]+)\((?P<portee>[a-z]+)\)(?P<casse>!)?: (?P<sujet>.+)$")
REFS = re.compile(
    r"^Refs: (?:n/a|(?:(?:EF|ENF)-[A-Z0-9]+(?:-[A-Z0-9]+)*)(?:, (?:EF|ENF)-[A-Z0-9]+(?:-[A-Z0-9]+)*)*)$",
    re.M,
)
EXEMPLE = "feat(messagerie): ajouter l'envoi de message\n\n    Refs: EF-MSG-03"


def _lignes_utiles(texte):
    return [ligne for ligne in texte.splitlines() if not ligne.startswith("#")]


def verifier(message, push=False):
    """Retourne la liste des erreurs (vide si le message est valide)."""
    lignes = _lignes_utiles(message)
    entete = lignes[0].strip() if lignes else ""
    if entete.startswith(("Merge ", 'Revert "')):
        return []
    if entete.startswith(("fixup!", "squash!")):
        return (
            [
                "Commit « fixup!/squash! » refusé au push : réécris l'historique (git rebase -i --autosquash)."
            ]
            if push
            else []
        )
    if re.match(r"(?i)^wip\b", entete):
        return ["Commit « WIP » refusé : termine le travail et nomme-le correctement."]
    erreurs = []
    m = ENTETE.match(entete)
    if not m:
        return [
            f"En-tête invalide : « {entete} ».\n    Format attendu : type(portée): sujet\n    Exemple :\n    {EXEMPLE}"
        ]
    if m["type"] not in TYPES:
        erreurs.append(f"Type « {m['type']} » inconnu. Types : {', '.join(TYPES)}.")
    if m["portee"] not in PORTEES:
        erreurs.append(f"Portée « {m['portee']} » inconnue. Portées : {', '.join(PORTEES)}.")
    sujet = m["sujet"]
    if len(entete) > 72:
        erreurs.append(f"Première ligne trop longue ({len(entete)} caractères, 72 au plus).")
    if len(sujet) < 5:
        erreurs.append("Le sujet doit faire au moins 5 caractères.")
    if sujet[:1] != sujet[:1].lower():
        erreurs.append("Le sujet doit commencer par une minuscule.")
    if sujet.endswith("."):
        erreurs.append("Le sujet ne doit pas se terminer par un point.")
    if len(lignes) > 1 and lignes[1].strip():
        erreurs.append("Laisse une ligne vide entre l'en-tête et le corps.")
    corps = lignes[1:]
    for i, ligne in enumerate(corps, start=2):
        if len(ligne) > 100:
            erreurs.append(
                f"Ligne {i} du corps trop longue ({len(ligne)} caractères, 100 au plus)."
            )
    if m["casse"] and not [
        ligne for ligne in corps if ligne.strip() and not ligne.startswith("Refs:")
    ]:
        erreurs.append("Un changement cassant (« ! ») exige un corps expliquant la migration.")
    if m["type"] in ("feat", "fix") and not REFS.search("\n".join(corps)):
        erreurs.append(
            "Les commits feat/fix exigent une ligne « Refs: EF-XXX-NN[, ENF-XXX-NN] » ou « Refs: n/a »."
        )
    return erreurs


def main(argv):
    push = "--push" in argv
    args = [a for a in argv if not a.startswith("--")]
    if len(args) != 1:
        sys.stderr.write("Usage : verifier_commit.py [--push] <fichier-message>\n")
        return 2
    with open(args[0], encoding="utf-8") as f:
        erreurs = verifier(f.read(), push=push)
    if erreurs:
        sys.stderr.write("\n✗ Message de commit refusé :\n")
        for e in erreurs:
            sys.stderr.write(f"  - {e}\n")
        sys.stderr.write(f"\n  Exemple valide :\n    {EXEMPLE}\n\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
