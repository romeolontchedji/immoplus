"""Partage d'une annonce : image d'aperçu des liens (WhatsApp, Facebook, TikTok…) et résumé des caractéristiques.

Les photos sont stockées en WebP, que plusieurs messageries n'affichent pas en aperçu : l'image est convertie en JPEG
1200 × 630 (format recommandé par Open Graph), à la demande, puis gardée en cache. Aucun fichier en plus sur le disque.
"""

import io

from django.core.cache import cache
from PIL import Image, ImageOps

from apps.media import stockage

from .. import selectors

LARGEUR, HAUTEUR = 1200, 630
DELAI_CACHE_S = 7 * 24 * 3600


def image_apercu(ident) -> bytes | None:
    """JPEG d'aperçu d'une annonce visible ; `None` si elle n'a ni photo ni vidéo prête."""
    cle = selectors.cle_image_partage(ident)
    if cle is None:
        return None
    cle_cache = f"partage:apercu:{cle}"
    image = cache.get(cle_cache)
    if image is None:
        image = _convertir(stockage.lire(cle))
        if image is None:
            return None
        cache.set(cle_cache, image, DELAI_CACHE_S)
    return image


def _convertir(contenu: bytes | None) -> bytes | None:
    if not contenu:
        return None
    try:
        with Image.open(io.BytesIO(contenu)) as source:
            cadree = ImageOps.fit(
                source.convert("RGB"), (LARGEUR, HAUTEUR), Image.Resampling.LANCZOS
            )
    except (OSError, ValueError, Image.DecompressionBombError):
        return None
    sortie = io.BytesIO()
    cadree.save(sortie, "JPEG", quality=82, optimize=True, progressive=True)
    return sortie.getvalue()


def resume(f: dict) -> str:
    """Caractéristiques principales en une phrase : aperçu du lien et description pour les moteurs de recherche."""
    morceaux = [f.get("room_type_label") or "", f"{f['district']['name']}, Parakou"]
    if f.get("distance_m") is not None:
        morceaux.append(f"à {f['distance_m']} m de l'UP")
    loyer = f"{f['rent_amount']:,}".replace(",", " ") + " F/mois"
    morceaux.append(loyer + (" (à débattre)" if f.get("rent_negotiable") else ""))
    equipements = [
        "douche intérieure" if f.get("has_private_bathroom") else "",
        f"électricité : {f['electricity_label'].lower()}" if f.get("electricity_label") else "",
        (f.get("water_label") or "").lower(),
        (f.get("kitchen_label") or "").lower(),
        "cour clôturée" if f.get("is_fenced") else "",
    ]
    morceaux.extend(e for e in equipements if e)
    morceaux.append("visite en vidéo")
    if (f.get("gerant") or {}).get("verified"):
        morceaux.append("gérant vérifié")
    return " · ".join(m for m in morceaux if m) + "."
