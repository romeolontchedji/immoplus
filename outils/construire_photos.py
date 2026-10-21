"""Convertit les photos d'ambiance de photos-brutes/ en WebP recadrés (ADR 0006, plan d'actions v2 §8).

    python outils/construire_photos.py

Site : serveur/web/static/design/photos/<nom>-<largeur>.webp (480, 960, 1600 ; jamais agrandie au-delà de
l'original). Application : mobile/assets/photos/<nom>.webp (960). Le recadrage (proportion, point d'intérêt) est
fixé ici pour chaque photo : on remplace l'original dans photos-brutes/ sous le même nom puis on relance.
Les originaux ne sont pas versionnés ; les WebP produits le sont.
"""

import sys
from pathlib import Path

from PIL import Image, ImageOps

RACINE = Path(__file__).resolve().parent.parent
BRUTES = RACINE / "photos-brutes"
SITE = RACINE / "serveur/web/static/design/photos"
MOBILE = RACINE / "mobile/assets/photos"
LARGEURS_SITE = (480, 960, 1600)
LARGEUR_MOBILE = 960
QUALITE = 70
# Photos très détaillées (vue aérienne) : sous le voile sombre, une qualité plus basse ne se voit pas.
QUALITE_PAR_PHOTO = {"accueil-1": 55}

# nom : (destination, proportion largeur/hauteur, point d'intérêt x, y entre 0 et 1)
RECETTES = {
    "accueil-1": ("site", 16 / 9, 0.5, 0.32),
    "accueil-2": ("site", 16 / 9, 0.5, 0.4),
    "accueil-3": ("site", 16 / 9, 0.5, 0.5),
    "gerant": ("site", 3 / 2, 0.7, 0.4),
    "onboarding-1": ("mobile", 6 / 5, 0.47, 0.5),
    "onboarding-2": ("mobile", 6 / 5, 0.5, 0.47),
    "onboarding-3": ("mobile", 6 / 5, 0.53, 0.45),
    "onboarding-4": ("mobile", 6 / 5, 0.42, 0.5),
    "bienvenue": ("mobile", 1.0, 0.5, 0.5),
}


def recadrer(image: Image.Image, proportion: float, x: float, y: float) -> Image.Image:
    """Plus grande zone à la proportion voulue, centrée au plus près du point d'intérêt."""
    largeur, hauteur = image.size
    if largeur / hauteur > proportion:
        lc, hc = round(hauteur * proportion), hauteur
    else:
        lc, hc = largeur, round(largeur / proportion)
    gauche = min(max(round(x * largeur - lc / 2), 0), largeur - lc)
    haut = min(max(round(y * hauteur - hc / 2), 0), hauteur - hc)
    return image.crop((gauche, haut, gauche + lc, haut + hc))


def reduire(image: Image.Image, largeur: int) -> Image.Image:
    if image.width <= largeur:
        return image
    return image.resize(
        (largeur, round(image.height * largeur / image.width)), Image.Resampling.LANCZOS
    )


def original(nom: str) -> Path | None:
    return next((p for p in sorted(BRUTES.glob(f"{nom}.*")) if p.suffix.lower() != ".txt"), None)


def main() -> int:
    manquantes = []
    for nom, (destination, proportion, x, y) in RECETTES.items():
        chemin = original(nom)
        if chemin is None:
            manquantes.append(nom)
            continue
        image = recadrer(
            ImageOps.exif_transpose(Image.open(chemin)).convert("RGB"), proportion, x, y
        )
        if destination == "site":
            SITE.mkdir(parents=True, exist_ok=True)
            for cible in LARGEURS_SITE:  # jamais agrandie : sous la cible, la taille d'origine
                sortie = SITE / f"{nom}-{cible}.webp"
                qualite = QUALITE_PAR_PHOTO.get(nom, QUALITE)
                reduire(image, cible).save(sortie, "WEBP", quality=qualite, method=6)
        else:
            MOBILE.mkdir(parents=True, exist_ok=True)
            reduire(image, LARGEUR_MOBILE).save(
                MOBILE / f"{nom}.webp", "WEBP", quality=QUALITE, method=6
            )
        sys.stdout.write(f"{nom} : {chemin.name} → {image.width}×{image.height} recadrée\n")
    if manquantes:
        sys.stderr.write(f"Absentes de photos-brutes/ : {', '.join(manquantes)}\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
