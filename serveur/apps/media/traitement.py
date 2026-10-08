"""Traitement des médias : validation, dérivés WebP des photos, MP4 720p et affiche des vidéos (CDC §11.2).

Version simple : une seule variante vidéo MP4 (le HLS multi-qualité viendra ensuite). Fonctions pures :
aucun accès à la base ; elles lèvent `ErreurTraitement` avec un code affichable.
"""

import hashlib
import json
import subprocess  # nosec B404
from pathlib import Path

import pillow_heif
from PIL import Image, ImageOps, UnidentifiedImageError

pillow_heif.register_heif_opener()

TAILLES_PHOTO = (480, 960, 1600)
PIXELS_MAX = 50_000_000
DUREE_MIN_S, DUREE_MAX_S, HAUTEUR_MIN = 10, 60, 480
DELAI_FFMPEG_S = 600
CONTENEURS_VIDEO = ("mov", "mp4", "webm", "matroska")


class ErreurTraitement(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def sha256(chemin: Path) -> str:
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        for bloc in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloc)
    return h.hexdigest()


def traiter_photo(source: Path, destination: Path) -> dict:
    """Décode, retire l'EXIF (orientation appliquée), écrit des variantes WebP. Retourne les métadonnées."""
    try:
        with Image.open(source) as brute:
            if brute.width * brute.height > PIXELS_MAX:
                raise ErreurTraitement("image_trop_grande", "L'image est trop grande.")
            if brute.format not in ("JPEG", "PNG", "WEBP", "HEIF", "MPO"):
                raise ErreurTraitement(
                    "format_non_supporte",
                    "Format d'image non pris en charge (JPEG, PNG, HEIC, WebP).",
                )
            image = ImageOps.exif_transpose(brute).convert(
                "RGB"
            )  # une image neuve : plus aucune métadonnée
            mime = Image.MIME.get(brute.format, "image/jpeg")
    except ErreurTraitement:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as erreur:
        raise ErreurTraitement(
            "fichier_illisible", "Ce fichier n'est pas une image lisible."
        ) from erreur
    largeur, hauteur = image.size
    variantes = {}
    for cible in TAILLES_PHOTO:
        if cible > largeur and variantes:
            break
        copie = image.copy()
        copie.thumbnail((cible, cible * 4))
        nom = f"w{min(cible, largeur)}.webp"
        copie.save(destination / nom, "WEBP", quality=80)
        variantes[str(min(cible, largeur))] = nom
    return {"mime": mime, "width": largeur, "height": hauteur, "variants": variantes}


def _executer(commande: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(  # noqa: S603  # nosec B603
        commande, capture_output=True, text=True, timeout=DELAI_FFMPEG_S, check=False
    )


def sonder_video(source: Path) -> dict:
    try:
        r = _executer(
            [
                "ffprobe",
                "-v",
                "error",
                "-protocol_whitelist",
                "file",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                str(source),
            ]
        )
    except subprocess.TimeoutExpired as erreur:
        raise ErreurTraitement(
            "delai_depasse", "L'analyse de la vidéo a pris trop de temps."
        ) from erreur
    if r.returncode != 0:
        raise ErreurTraitement("fichier_illisible", "Cette vidéo n'est pas lisible.")
    infos = json.loads(r.stdout or "{}")
    flux = next((s for s in infos.get("streams", []) if s.get("codec_type") == "video"), None)
    formats = (infos.get("format", {}).get("format_name") or "").split(",")
    if flux is None or not any(c in formats for c in CONTENEURS_VIDEO):
        raise ErreurTraitement(
            "format_non_supporte", "Format vidéo non pris en charge (MP4, MOV ou WebM)."
        )
    duree = float(infos["format"].get("duration") or flux.get("duration") or 0)
    if not DUREE_MIN_S <= duree <= DUREE_MAX_S:
        raise ErreurTraitement(
            "duree_hors_limites",
            f"La vidéo doit durer entre {DUREE_MIN_S} et {DUREE_MAX_S} secondes.",
        )
    if int(flux.get("height", 0)) < HAUTEUR_MIN:
        raise ErreurTraitement(
            "resolution_trop_basse", f"La vidéo doit faire au moins {HAUTEUR_MIN}p."
        )
    return {
        "width": int(flux["width"]),
        "height": int(flux["height"]),
        "duration_s": round(duree, 2),
        "mime": "video/mp4",
    }


def traiter_video(source: Path, destination: Path) -> dict:
    """MP4 H.264 720p maximum, affiche WebP. Entrée limitée au protocole `file`, avec délai maximal."""
    meta = sonder_video(source)
    sortie = destination / "video.mp4"
    try:
        r = _executer(
            [
                "ffmpeg", "-nostdin", "-y", "-protocol_whitelist", "file", "-i", str(source), "-t", str(DUREE_MAX_S),
                "-vf", "scale=-2:'min(720,ih)'", "-c:v", "libx264", "-preset", "veryfast", "-crf", "27",
                "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", str(sortie),
            ]
        )  # fmt: skip
        if r.returncode != 0 or not sortie.exists():
            raise ErreurTraitement("transcodage_echoue", "La vidéo n'a pas pu être convertie.")
        image_brute = destination / "affiche.png"
        _executer(
            [
                "ffmpeg",
                "-nostdin",
                "-y",
                "-protocol_whitelist",
                "file",
                "-ss",
                "1",
                "-i",
                str(sortie),
                "-frames:v",
                "1",
                str(image_brute),
            ]
        )
    except subprocess.TimeoutExpired as erreur:
        raise ErreurTraitement(
            "delai_depasse", "La conversion de la vidéo a pris trop de temps."
        ) from erreur
    affiche = destination / "affiche.webp"
    if image_brute.exists():
        with Image.open(image_brute) as im:
            im.convert("RGB").save(affiche, "WEBP", quality=75)
        image_brute.unlink()
    meta.update({"playback": sortie.name, "poster": affiche.name if affiche.exists() else None})
    return meta
