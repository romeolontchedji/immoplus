"""Fournisseurs de stockage des médias publics (CDC §6, palier 2) : interface, disque local, Cloudinary, squelette S3.

Le code métier ne connaît que des **clés** (`listings/<annonce>/<média>/<fichier>`, déjà enregistrées en base) et ces
quatre opérations : où écrire pendant le traitement, publier, donner l'URL publique, supprimer. Passer du disque à un
stockage objet ne change ni le code métier, ni la base, ni l'application mobile.

Les originaux en cours d'envoi (`MEDIA_TMP_ROOT`) restent un espace de travail local : ffmpeg lit un fichier, et
l'original est effacé 24 h après un traitement réussi.

Cloudinary (ADR 0010) s'active depuis l'administration et cohabite avec le disque : une clé envoyée chez Cloudinary
porte le préfixe `cloudinary:`, si bien que chaque média reste lisible là où il a été rangé, quel que soit le réglage.
"""

import base64
import hashlib
import json
import posixpath
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from abc import ABC, abstractmethod
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

LECTURE_MAX_OCTETS = 15 * 1024 * 1024
PREFIXE_CLOUDINARY = "cloudinary:"


class ErreurStockageDistant(Exception):
    """Le stockage distant a refusé ou n'a pas répondu (réessayer plus tard)."""


def _lire_https(url: str | None) -> bytes | None:
    """Contenu d'une URL publique https (aperçu des liens partagés), taille plafonnée ; `None` en cas d'échec."""
    if not url or not url.startswith("https://"):
        return None
    try:
        with urllib.request.urlopen(url, timeout=5) as reponse:  # noqa: S310  # nosec B310 - https vérifié
            return reponse.read(LECTURE_MAX_OCTETS)
    except (OSError, ValueError):
        return None


class StorageProvider(ABC):
    @abstractmethod
    def dossier_de_travail(self, prefixe: str) -> Path:
        """Dossier local où le traitement écrit les dérivés d'un média (créé s'il manque)."""

    @abstractmethod
    def publier(self, prefixe: str, dossier: Path) -> None:
        """Rend publics les fichiers de `dossier` sous `prefixe` (après un traitement réussi)."""

    @abstractmethod
    def url_publique(self, cle: str | None) -> str | None:
        """URL de lecture d'un fichier publié ; `None` si la clé est vide."""

    @abstractmethod
    def supprimer(self, prefixe: str) -> None:
        """Supprime tout ce qui est publié (ou en cours de traitement) sous `prefixe`. Sans erreur si absent."""

    @abstractmethod
    def espace_suffisant(self) -> bool:
        """Faux quand il faut refuser les nouveaux envois (disque plein, quota atteint)."""

    def lire(self, cle: str) -> bytes | None:
        """Contenu d'un fichier publié (image d'aperçu des liens partagés) ; `None` s'il est absent."""
        return None

    @staticmethod
    def cle(prefixe: str, nom_fichier: str) -> str:
        return posixpath.join(prefixe, nom_fichier)


class LocalStorageProvider(StorageProvider):
    """Disque du serveur (`MEDIA_ROOT`), servi directement par Caddy sous `MEDIA_URL` avec cache longue durée."""

    def __init__(self):
        self.racine = Path(settings.MEDIA_ROOT)

    def _chemin(self, prefixe: str) -> Path:
        chemin = (self.racine / prefixe).resolve()
        if (
            self.racine.resolve() not in chemin.parents
        ):  # une clé ne sort jamais de la racine des médias
            raise ValueError(f"Clé de stockage hors de la racine : {prefixe}")
        return chemin

    def dossier_de_travail(self, prefixe):
        dossier = self._chemin(prefixe)
        dossier.mkdir(parents=True, exist_ok=True)
        return dossier

    def publier(self, prefixe, dossier):
        return None  # le traitement a déjà écrit au bon endroit

    def url_publique(self, cle):
        return f"{settings.MEDIA_URL}{cle}" if cle else None

    def lire(self, cle):
        try:
            return self._chemin(cle).read_bytes()
        except (OSError, ValueError):
            return None

    def supprimer(self, prefixe):
        shutil.rmtree(self._chemin(prefixe), ignore_errors=True)

    def espace_suffisant(self):
        self.racine.mkdir(parents=True, exist_ok=True)
        usage = shutil.disk_usage(self.racine)
        return usage.used / usage.total * 100 < settings.MEDIA_DISK_REFUS_POURCENT


class S3StorageProvider(StorageProvider):
    """Squelette du stockage objet compatible S3 (Cloudflare R2 recommandé : pas de frais de sortie).

    À compléter au palier 2 : client S3 (dépendance à ajouter avec un ADR), envoi des fichiers de `dossier` sous
    `prefixe` avec `Cache-Control: public, max-age=31536000, immutable`, suppression par préfixe. Réglages prévus :
    S3_ENDPOINT_URL, S3_BUCKET, S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY, MEDIA_PUBLIC_BASE_URL (domaine du CDN).
    """

    def __init__(self):
        self.base_publique = getattr(settings, "MEDIA_PUBLIC_BASE_URL", "")
        self.travail = Path(settings.MEDIA_TMP_ROOT) / "derives"

    def dossier_de_travail(self, prefixe):
        dossier = self.travail / prefixe
        dossier.mkdir(parents=True, exist_ok=True)
        return dossier

    def publier(self, prefixe, dossier):
        raise NotImplementedError(
            "Stockage S3 : ajouter le client (ADR), envoyer les fichiers du dossier puis le supprimer."
        )

    def url_publique(self, cle):
        return f"{self.base_publique.rstrip('/')}/{cle}" if cle else None

    def lire(self, cle):
        return _lire_https(self.url_publique(cle))  # par le CDN : aucune dépendance

    def supprimer(self, prefixe):
        shutil.rmtree(self.travail / prefixe, ignore_errors=True)
        raise NotImplementedError("Stockage S3 : supprimer les objets sous le préfixe.")

    def espace_suffisant(self):
        return (
            True  # quota surveillé côté fournisseur ; le disque de travail est contrôlé par /readyz
        )


class CloudinaryStorageProvider(StorageProvider):
    """Cloudinary (ADR 0010) : dérivés préparés sur le disque, envoyés par l'API HTTP, servis par son CDN.

    Seul le `worker` (accès Internet et clés) envoie et supprime ; `worker-media` reste sans Internet. Les autres
    processus n'ont besoin que du nom du compte pour construire les URL. Les fichiers vivent sous
    `<CLOUDINARY_FOLDER>/listings/<annonce>/<média>/` ; leur URL ne change jamais (cache longue durée).
    """

    API = "https://api.cloudinary.com/v1_1"
    LIVRAISON = "https://res.cloudinary.com"
    IMAGES = {".webp", ".jpg", ".jpeg", ".png", ".avif"}
    VIDEOS = {".mp4", ".webm", ".mov"}

    def __init__(self):
        self.compte = settings.CLOUDINARY_CLOUD_NAME
        self.cle_api = settings.CLOUDINARY_API_KEY
        self.secret = settings.CLOUDINARY_API_SECRET
        self.dossier = settings.CLOUDINARY_FOLDER.strip("/")
        self.local = LocalStorageProvider()

    @staticmethod
    def configure() -> bool:
        """Vrai quand le nom du compte est renseigné (les clés d'envoi ne sont données qu'au worker)."""
        return bool(getattr(settings, "CLOUDINARY_CLOUD_NAME", ""))

    @staticmethod
    def sans_prefixe(cle: str) -> str:
        return cle.removeprefix(PREFIXE_CLOUDINARY)

    @classmethod
    def type_de(cls, nom: str) -> str:
        extension = posixpath.splitext(nom)[1].lower()
        return "image" if extension in cls.IMAGES else "video" if extension in cls.VIDEOS else "raw"

    def _identifiant(self, chemin: str) -> tuple[str, str]:
        """(type, public_id) : sans extension pour les images et vidéos, que Cloudinary range à part."""
        nature = self.type_de(chemin)
        base = posixpath.join(self.dossier, chemin)
        return nature, base if nature == "raw" else posixpath.splitext(base)[0]

    def signature(self, parametres: dict[str, str]) -> str:
        """Signature d'un envoi : paramètres triés `a=1&b=2` suivis du secret, en SHA-1 (documentation Cloudinary)."""
        chaine = "&".join(f"{k}={parametres[k]}" for k in sorted(parametres))
        return hashlib.sha1((chaine + self.secret).encode(), usedforsecurity=False).hexdigest()

    def _requete(
        self, methode: str, url: str, corps: bytes | None = None, entetes: dict | None = None
    ) -> dict:
        requete = urllib.request.Request(url, data=corps, method=methode, headers=entetes or {})  # noqa: S310
        try:
            with urllib.request.urlopen(requete, timeout=60) as reponse:  # noqa: S310  # nosec B310 - https fixe
                return json.loads(reponse.read() or b"{}")
        except (OSError, ValueError) as erreur:
            raise ErreurStockageDistant(f"Cloudinary : {erreur}") from erreur

    def _envoyer(self, chemin: str, fichier: Path) -> None:
        if not (self.compte and self.cle_api and self.secret):
            raise ErreurStockageDistant(
                "Cloudinary : CLOUDINARY_API_KEY ou CLOUDINARY_API_SECRET absent du worker."
            )
        nature, public_id = self._identifiant(chemin)
        signes = {"overwrite": "true", "public_id": public_id, "timestamp": str(int(time.time()))}
        champs = {**signes, "api_key": self.cle_api, "signature": self.signature(signes)}
        limite = uuid.uuid4().hex
        morceaux = [
            f'--{limite}\r\nContent-Disposition: form-data; name="{nom}"\r\n\r\n{valeur}\r\n'.encode()
            for nom, valeur in champs.items()
        ]
        morceaux.append(
            f'--{limite}\r\nContent-Disposition: form-data; name="file"; filename="{fichier.name}"\r\n'
            "Content-Type: application/octet-stream\r\n\r\n".encode()
            + fichier.read_bytes()
            + f"\r\n--{limite}--\r\n".encode()
        )
        self._requete(
            "POST",
            f"{self.API}/{self.compte}/{nature}/upload",
            b"".join(morceaux),
            {"Content-Type": f"multipart/form-data; boundary={limite}"},
        )

    def dossier_de_travail(self, prefixe):
        return self.local.dossier_de_travail(
            prefixe
        )  # préparés sur le disque, envoyés ensuite par le worker

    def publier(self, prefixe, dossier):
        for fichier in sorted(Path(dossier).iterdir()):
            if fichier.is_file():
                self._envoyer(posixpath.join(prefixe, fichier.name), fichier)

    def url_publique(self, cle):
        if not cle:
            return None
        chemin = self.sans_prefixe(cle)
        nature, public_id = self._identifiant(chemin)
        extension = "" if nature == "raw" else posixpath.splitext(chemin)[1]
        return f"{self.LIVRAISON}/{self.compte}/{nature}/upload/{urllib.parse.quote(public_id)}{extension}"

    def lire(self, cle):
        return _lire_https(self.url_publique(cle))

    def supprimer(self, prefixe):
        """Supprime la copie locale éventuelle puis tout ce que Cloudinary range sous le préfixe."""
        self.local.supprimer(self.sans_prefixe(prefixe))
        self.supprimer_distant(prefixe)

    def supprimer_distant(self, prefixe: str) -> None:
        """Supprime chez Cloudinary seulement (la copie locale, s'il y en a une, reste)."""
        jeton = base64.b64encode(f"{self.cle_api}:{self.secret}".encode()).decode()
        cible = urllib.parse.quote(posixpath.join(self.dossier, self.sans_prefixe(prefixe)) + "/")
        for nature in ("image", "video", "raw"):
            self._requete(
                "DELETE",
                f"{self.API}/{self.compte}/resources/{nature}/upload?prefix={cible}",
                entetes={"Authorization": f"Basic {jeton}"},
            )

    def telecharger(self, cle: str, destination: Path) -> None:
        """Rapatrie un fichier publié sur le disque (retour au stockage local)."""
        url = self.url_publique(cle)
        try:
            with urllib.request.urlopen(url, timeout=60) as reponse:  # noqa: S310  # nosec B310 - https fixe
                destination.write_bytes(reponse.read())
        except (OSError, ValueError) as erreur:
            raise ErreurStockageDistant(f"Cloudinary : {erreur}") from erreur

    def espace_suffisant(self):
        return self.local.espace_suffisant()  # le disque sert encore de zone de préparation


FOURNISSEURS: dict[str, type[StorageProvider]] = {
    "local": LocalStorageProvider,
    "s3": S3StorageProvider,
}


def fournisseur() -> StorageProvider:
    """Fournisseur des clés sans préfixe (réglage `STORAGE_PROVIDER`, le disque par défaut)."""
    nom = getattr(settings, "STORAGE_PROVIDER", "local")
    try:
        return FOURNISSEURS[nom]()
    except KeyError:
        raise ImproperlyConfigured(f"Fournisseur de stockage inconnu : {nom}") from None


def est_distant(cle: str | None) -> bool:
    return bool(cle) and cle.startswith(PREFIXE_CLOUDINARY)


def pour_cle(cle: str | None) -> StorageProvider:
    """Fournisseur qui détient `cle` : Cloudinary pour une clé préfixée, sinon le fournisseur par défaut."""
    return CloudinaryStorageProvider() if est_distant(cle) else fournisseur()
