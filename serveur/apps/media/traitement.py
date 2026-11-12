"""Traitement des médias : validation, dérivés WebP des photos, MP4 720p et affiche des vidéos (CDC §11.2).

Version simple : une seule variante vidéo MP4 (le HLS multi-qualité viendra ensuite). Fonctions pures :
aucun accès à la base ; elles lèvent `ErreurTraitement` avec un code affichable.
"""

import hashlib
import json
import logging
import os
import subprocess  # nosec B404
from pathlib import Path

import pillow_heif
from PIL import Image, ImageOps, UnidentifiedImageError

pillow_heif.register_heif_opener()
journal = logging.getLogger(__name__)

TAILLES_PHOTO = (480, 960, 1600)
PIXELS_MAX = 50_000_000
DUREE_MIN_S, DUREE_MAX_S, HAUTEUR_MIN = 10, 60, 480
DELAI_FFMPEG_S = 600
CONTENEURS_VIDEO = ("mov", "mp4", "webm", "matroska")
# Réglages du transcodage (VPS partagé : le temps de calcul est la ressource rare, voir docs/capacite.md).
HAUTEUR_MAX = 720
FPS_MAX = 30
DEBIT_MAX_K = 2500  # kb/s : plafond du flux vidéo, pour que les vidéos restent légères sur les forfaits mobiles
THREADS_FFMPEG = max(1, int(os.environ.get("FFMPEG_THREADS", "2") or 2))


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
    audio = next((s for s in infos.get("streams", []) if s.get("codec_type") == "audio"), None)
    return {
        "width": int(flux["width"]),
        "height": int(flux["height"]),
        "duration_s": round(duree, 2),
        "mime": "video/mp4",
        # Pour choisir entre simple copie et réencodage (voir `commande_conversion`).
        "codec": flux.get("codec_name"),
        "pix_fmt": flux.get("pix_fmt"),
        "fps": _images_par_seconde(flux.get("avg_frame_rate") or flux.get("r_frame_rate")),
        "debit_k": int(float(flux.get("bit_rate") or 0) // 1000),
        "audio": audio.get("codec_name") if audio else None,
        "conteneur": formats,
        "pivote": _est_pivotee(flux),
    }


def _images_par_seconde(valeur) -> float:
    try:
        num, _, den = str(valeur or "0/1").partition("/")
        return float(num) / float(den or 1) if float(den or 1) else 0.0
    except ValueError:
        return 0.0


def _est_pivotee(flux: dict) -> bool:
    """Vidéo de téléphone tournée par une métadonnée de rotation : seul un réencodage la redresse proprement."""
    tournee = (flux.get("tags") or {}).get("rotate")
    cotes = flux.get("side_data_list") or []
    return bool(
        (tournee and str(tournee) not in ("0", "")) or any(c.get("rotation") for c in cotes)
    )


def copie_suffisante(meta: dict) -> bool:
    """Vrai si la vidéo est déjà au format de lecture visé (H.264 720p, 30 images/s, flux léger) : une simple
    copie du flux (quelques secondes) remplace le réencodage (dizaines de secondes)."""
    return (
        meta.get("codec") == "h264"
        and meta.get("pix_fmt") == "yuv420p"
        and meta["height"] <= HAUTEUR_MAX
        and 0 < meta.get("fps", 0) <= FPS_MAX + 1
        and 0 < meta.get("debit_k", 0) <= DEBIT_MAX_K
        and meta.get("audio") in (None, "aac")
        and any(c in ("mp4", "mov") for c in meta.get("conteneur", []))
        and not meta.get("pivote")
    )


def commande_conversion(
    source: Path, sortie: Path, meta: dict, *, copier: bool | None = None
) -> list[str]:
    """Commande ffmpeg : copie du flux si la vidéo est déjà au bon format, sinon H.264 720p léger et rapide.
    `copier` force l'un ou l'autre (reprise par réencodage quand la copie échoue)."""
    base = [
        "ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-protocol_whitelist", "file",
        "-threads", str(THREADS_FFMPEG), "-i", str(source), "-t", str(DUREE_MAX_S),
        "-map", "0:v:0", "-map", "0:a:0?", "-sn", "-dn",
    ]  # fmt: skip
    if copie_suffisante(meta) if copier is None else copier:
        return [*base, "-c", "copy", "-movflags", "+faststart", str(sortie)]
    filtres = [f"scale=-2:'min({HAUTEUR_MAX},ih)'"]
    if meta.get("fps", 0) > FPS_MAX + 1:
        filtres.insert(0, f"fps={FPS_MAX}")
    return [
        *base, "-vf", ",".join(filtres), "-c:v", "libx264", "-preset", "superfast", "-crf", "28",
        "-maxrate", f"{DEBIT_MAX_K}k", "-bufsize", f"{2 * DEBIT_MAX_K}k", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "96k", "-ac", "2", "-movflags", "+faststart", str(sortie),
    ]  # fmt: skip


def traiter_video(source: Path, destination: Path) -> dict:
    """MP4 H.264 720p maximum, affiche WebP. Entrée limitée au protocole `file`, avec délai maximal.

    Une vidéo déjà au bon format est simplement copiée ; les autres sont réencodées vite (préréglage `superfast`,
    30 images/s, débit plafonné, nombre de fils borné pour ne pas saturer le serveur)."""
    meta = sonder_video(source)
    sortie = destination / "video.mp4"
    try:
        r = _executer(commande_conversion(source, sortie, meta))
        if (r.returncode != 0 or not sortie.exists()) and copie_suffisante(meta):
            # La copie du flux a échoué (conteneur atypique) : on réessaie en réencodant.
            journal.warning(
                "Copie du flux vidéo impossible, réencodage : %s", (r.stderr or "")[-300:]
            )
            r = _executer(commande_conversion(source, sortie, meta, copier=False))
        if r.returncode != 0 or not sortie.exists():
            journal.error("ffmpeg a échoué (code %s) : %s", r.returncode, (r.stderr or "")[-500:])
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
