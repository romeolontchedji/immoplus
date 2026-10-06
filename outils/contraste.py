#!/usr/bin/env python3
"""Vérifie les contrastes WCAG AA des jetons de `tokens.css` (clair et sombre). Échoue en CI."""

import re
import sys
from pathlib import Path

TOKENS = (
    Path(__file__).resolve().parent.parent / "serveur" / "web" / "static" / "css" / "tokens.css"
)

# (premier plan, arrière-plan, seuil, description) : 4,5 pour le texte, 3 pour les éléments d'interface.
PAIRES = [
    ("--text", "--bg", 4.5, "texte sur fond"),
    ("--text", "--surface", 4.5, "texte sur surface"),
    ("--text", "--surface-sunken", 4.5, "texte sur surface en creux"),
    ("--text-muted", "--bg", 4.5, "texte atténué sur fond"),
    ("--text-muted", "--surface", 4.5, "texte atténué sur surface"),
    ("--text-muted", "--surface-sunken", 4.5, "texte atténué sur surface en creux"),
    ("--on-primary", "--primary", 4.5, "texte du bouton primaire"),
    ("--on-primary", "--primary-hover", 4.5, "texte du bouton primaire survolé"),
    ("--on-primary-soft", "--primary-soft", 4.5, "texte de puce de marque"),
    ("--on-accent-soft", "--accent-soft", 4.5, "texte d'accent doux"),
    ("--link", "--bg", 4.5, "lien sur fond"),
    ("--link", "--surface", 4.5, "lien sur surface"),
    ("--focus", "--bg", 3.0, "anneau de focus sur fond"),
    ("--focus", "--surface", 3.0, "anneau de focus sur surface"),
    ("--primary", "--bg", 3.0, "bordure de contrôle actif"),
    ("--succes-text", "--succes-bg", 4.5, "texte de succès"),
    ("--avertissement-text", "--avertissement-bg", 4.5, "texte d'avertissement"),
    ("--danger-text", "--danger-bg", 4.5, "texte de danger"),
    ("--information-text", "--information-bg", 4.5, "texte d'information"),
]


def _declarations(bloc: str) -> dict[str, str]:
    return dict(re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", bloc))


def _bloc(css: str, debut: str) -> str:
    """Retourne le contenu du premier bloc `{...}` (équilibré) qui suit `debut`."""
    i = css.index(debut)
    i = css.index("{", i) + 1
    profondeur, j = 1, i
    while profondeur:
        profondeur += {"{": 1, "}": -1}.get(css[j], 0)
        j += 1
    return css[i : j - 1]


def charger() -> dict[str, dict[str, str]]:
    css = re.sub(r"/\*.*?\*/", "", TOKENS.read_text(encoding="utf-8"), flags=re.S)
    clair = _declarations(_bloc(css, ":root {"))
    media = _bloc(css, "@media (prefers-color-scheme: dark)")
    sombre_media = _declarations(_bloc(media, ':root:not([data-theme="light"])'))
    sombre_attr = _declarations(_bloc(css, ':root[data-theme="dark"]'))
    return {
        "clair": clair,
        "sombre": {**clair, **sombre_attr},
        "sombre_media": {**clair, **sombre_media},
    }


def resoudre(theme: dict[str, str], nom: str, profondeur: int = 0) -> str:
    valeur = theme[nom].strip()
    m = re.fullmatch(r"var\((--[\w-]+)\)", valeur)
    if m and profondeur < 10:
        return resoudre(theme, m.group(1), profondeur + 1)
    return valeur


def luminance(hexa: str) -> float:
    hexa = hexa.lstrip("#")
    r, g, b = (int(hexa[i : i + 2], 16) / 255 for i in (0, 2, 4))
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in (r, g, b)]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def rapport(a: str, b: str) -> float:
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def verifier() -> list[str]:
    """Retourne la liste des échecs (vide si tout est conforme)."""
    themes = charger()
    erreurs = []
    if themes["sombre"] != themes["sombre_media"]:
        erreurs.append("Le thème sombre « media » et le thème sombre « attribut » diffèrent.")
    for nom_theme in ("clair", "sombre"):
        theme = themes[nom_theme]
        for avant, arriere, seuil, description in PAIRES:
            try:
                r = rapport(resoudre(theme, avant), resoudre(theme, arriere))
            except (KeyError, ValueError) as e:
                erreurs.append(f"[{nom_theme}] {description} : jeton introuvable ({e}).")
                continue
            if r < seuil:
                erreurs.append(
                    f"[{nom_theme}] {description} : {avant} sur {arriere} = {r:.2f}:1 (minimum {seuil}:1)."
                )
    return erreurs


if __name__ == "__main__":
    echecs = verifier()
    if echecs:
        sys.stderr.write("✗ Contrastes insuffisants :\n  - " + "\n  - ".join(echecs) + "\n")
        sys.exit(1)
    sys.stdout.write(f"✔ Contrastes conformes ({len(PAIRES)} paires × 2 thèmes).\n")
