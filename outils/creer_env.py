#!/usr/bin/env python3
"""Crée `.env` (secrets générés) puis un fichier d'environnement par service à partir des modèles.

Idempotent : un fichier existant n'est jamais écrasé sans `--force`. Bibliothèque standard seulement.
"""

import argparse
import base64
import re
import secrets
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
MODELE_RACINE = RACINE / ".env.example"
DOSSIER_ENV = RACINE / "infra" / "compose" / "env"
MARQUEUR = re.compile(r"\{\{(\w+)\}\}")

# Secrets générés quand la valeur est vide. `PRIVATE_FILES_KEY` est une clé Fernet (32 octets en base64 URL).
SECRETS_TEXTE = [
    "POSTGRES_PASSWORD", "APP_DB_PASSWORD", "ADMIN_DB_PASSWORD", "MIGRATE_DB_PASSWORD",
    "SITE_SECRET_KEY", "ADMIN_SECRET_KEY", "JWT_SIGNING_KEY", "OTP_HMAC_KEY",
]  # fmt: skip
SECRETS_FERNET = ["PRIVATE_FILES_KEY"]


def lire_valeurs(chemin: Path) -> dict[str, str]:
    valeurs = {}
    for ligne in chemin.read_text(encoding="utf-8").splitlines():
        ligne = ligne.strip()
        if ligne and not ligne.startswith("#") and "=" in ligne:
            nom, _, valeur = ligne.partition("=")
            valeurs[nom.strip()] = valeur.strip()
    return valeurs


def generer(valeurs: dict[str, str]) -> dict[str, str]:
    """Complète les secrets vides ; les valeurs déjà fournies sont conservées."""
    for nom in SECRETS_TEXTE:
        if not valeurs.get(nom):
            valeurs[nom] = secrets.token_urlsafe(48)
    for nom in SECRETS_FERNET:
        if not valeurs.get(nom):
            valeurs[nom] = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
    return valeurs


def ecrire_racine(force: bool) -> dict[str, str]:
    cible = RACINE / ".env"
    if cible.exists() and not force:
        valeurs = generer(lire_valeurs(cible))
        return valeurs
    valeurs = generer(lire_valeurs(MODELE_RACINE))
    lignes = []
    for ligne in MODELE_RACINE.read_text(encoding="utf-8").splitlines():
        nom = ligne.partition("=")[0].strip()
        if "=" in ligne and not ligne.lstrip().startswith("#") and nom in valeurs:
            ligne = f"{nom}={valeurs[nom]}"
        lignes.append(ligne)
    cible.write_text("\n".join(lignes) + "\n", encoding="utf-8")
    cible.chmod(0o600)
    return valeurs


def rendre(modele: str, valeurs: dict[str, str]) -> str:
    def remplacer(m: re.Match) -> str:
        nom = m.group(1)
        if nom not in valeurs:
            raise KeyError(f"variable {nom} absente de .env")
        return valeurs[nom]

    return MARQUEUR.sub(remplacer, modele)


def ecrire_services(valeurs: dict[str, str], force: bool) -> list[Path]:
    crees = []
    for modele in sorted(DOSSIER_ENV.glob("*.env.example")):
        cible = modele.with_name(modele.name.removesuffix(".example"))
        if cible.exists() and not force:
            continue
        cible.write_text(rendre(modele.read_text(encoding="utf-8"), valeurs), encoding="utf-8")
        cible.chmod(0o600)
        crees.append(cible)
    return crees


def main(argv: list[str] | None = None) -> int:
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument("--force", action="store_true", help="écrase les fichiers existants")
    args = parseur.parse_args(argv)
    valeurs = ecrire_racine(args.force)
    crees = ecrire_services(valeurs, args.force)
    sys.stdout.write(
        f"✔ .env prêt ; {len(crees)} fichier(s) de service créé(s) dans infra/compose/env/.\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
