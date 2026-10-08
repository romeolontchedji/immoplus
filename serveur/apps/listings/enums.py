"""Énumérations des annonces, importables par les adaptateurs sans toucher aux modèles."""

from django.db import models


class TypeChambre(models.TextChoices):
    SINGLE = "single", "Chambre simple"
    ENTREE_COUCHER = "entree_coucher", "Entrée-coucher"
    CHAMBRE_SALON = "chambre_salon", "Chambre-salon"
    STUDIO = "studio", "Studio"


class StatutAnnonce(models.TextChoices):
    DRAFT = "draft", "Brouillon"
    PROCESSING = "processing", "En traitement"
    PUBLISHED = "published", "Publiée"
    HIDDEN = "hidden", "Masquée"
    RENTED = "rented", "Louée"
    ARCHIVED = "archived", "Archivée"
    REMOVED = "removed", "Retirée"


class RaisonMasquage(models.TextChoices):
    STALE = "stale", "Sans confirmation"
    MODERATION = "moderation", "Modération"
    OWNER = "owner", "Gérant"
    GERANT_SUSPENDED = "gerant_suspended", "Gérant suspendu"


class Eau(models.TextChoices):
    RUNNING = "running", "Eau courante"
    WELL = "well", "Puits"
    BOREHOLE = "borehole", "Forage"


class Compteur(models.TextChoices):
    INDIVIDUAL = "individual", "Individuel"
    SHARED = "shared", "Partagé"


class TypeMedia(models.TextChoices):
    VIDEO = "video", "Vidéo"
    PHOTO = "photo", "Photo"


class StatutMedia(models.TextChoices):
    UPLOADING = "uploading", "Envoi en cours"
    UPLOADED = "uploaded", "Envoyé"
    PROCESSING = "processing", "Traitement"
    READY = "ready", "Prêt"
    FAILED = "failed", "Échec"
    DELETED = "deleted", "Supprimé"
