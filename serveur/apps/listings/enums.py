"""Énumérations des annonces, importables par les adaptateurs sans toucher aux modèles."""

from django.db import models


class StatutTypeChambre(models.TextChoices):
    APPROVED = "approved", "Validé"
    PENDING = "pending", "Proposé, à valider"


class TypeChambre(models.TextChoices):
    """Types officiels de départ (décision V1) : la liste vivante est la table `room_types`."""

    SINGLE = "single", "Chambre simple"
    ENTREE_COUCHER = "entree_coucher", "Entrée-couché simple"
    CHAMBRE_SALON = "chambre_salon", "Chambre-salon simple"
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
    """Source et comptage de l'eau (ordre d'affichage des listes)."""

    INDIVIDUAL = "individual", "Compteur d'eau personnel"
    SUB_METER = "sub_meter", "Décompteur"
    RUNNING = "running", "Eau courante partagée"
    BOREHOLE = "borehole", "Forage"
    WELL = "well", "Puits"


class Compteur(models.TextChoices):
    """Comptage de l'électricité (SBEE)."""

    INDIVIDUAL = "individual", "Compteur personnel"
    SUB_METER = "sub_meter", "Décompteur"
    SHARED = "shared", "Compteur partagé"


class Cuisine(models.TextChoices):
    PRIVATE = "private", "Cuisine interne"
    SHARED = "shared", "Cuisine commune"
    NONE = "none", "Pas de cuisine"


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
