"""Fournisseurs de stockage des médias publics (CDC §6, palier 2) : interface, disque local, squelette S3/R2.

Le code métier ne connaît que des **clés** (`listings/<annonce>/<média>/<fichier>`, déjà enregistrées en base) et ces
quatre opérations : où écrire pendant le traitement, publier, donner l'URL publique, supprimer. Passer du disque à un
stockage objet ne change ni le code métier, ni la base, ni l'application mobile.

Les originaux en cours d'envoi (`MEDIA_TMP_ROOT`) restent un espace de travail local : ffmpeg lit un fichier, et
l'original est effacé 24 h après un traitement réussi.
"""

import posixpath
import shutil
import urllib.request
from abc import ABC, abstractmethod
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

LECTURE_MAX_OCTETS = 15 * 1024 * 1024


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
        # Lecture par l'URL publique du CDN (https seulement) : aucune dépendance, taille plafonnée.
        url = self.url_publique(cle)
        if not url or not url.startswith("https://"):
            return None
        try:
            with urllib.request.urlopen(url, timeout=5) as reponse:  # noqa: S310  # nosec B310 - https vérifié
                return reponse.read(LECTURE_MAX_OCTETS)
        except (OSError, ValueError):
            return None

    def supprimer(self, prefixe):
        shutil.rmtree(self.travail / prefixe, ignore_errors=True)
        raise NotImplementedError("Stockage S3 : supprimer les objets sous le préfixe.")

    def espace_suffisant(self):
        return (
            True  # quota surveillé côté fournisseur ; le disque de travail est contrôlé par /readyz
        )


FOURNISSEURS: dict[str, type[StorageProvider]] = {
    "local": LocalStorageProvider,
    "s3": S3StorageProvider,
}


def fournisseur() -> StorageProvider:
    nom = getattr(settings, "STORAGE_PROVIDER", "local")
    try:
        return FOURNISSEURS[nom]()
    except KeyError:
        raise ImproperlyConfigured(f"Fournisseur de stockage inconnu : {nom}") from None
