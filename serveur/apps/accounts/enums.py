"""Énumérations des comptes, importables par les adaptateurs (API, site) sans toucher aux modèles."""

from django.db import models


class Role(models.TextChoices):
    CLIENT = "client", "Locataire"
    GERANT = "gerant", "Gérant"
    MODERATOR = "moderator", "Modérateur"
    ADMIN = "admin", "Administrateur"


class Statut(models.TextChoices):
    ACTIVE = "active", "Actif"
    SUSPENDED = "suspended", "Suspendu"
    BANNED = "banned", "Banni"
    DELETED = "deleted", "Supprimé"


class Occupation(models.TextChoices):
    """« Tu es » à l'inscription (décision V2) : facultatif, sert aux statistiques et au ton des messages."""

    STUDENT_UP = "student_up", "Étudiant(e) à l'UP"
    STUDENT_OTHER = "student_other", "Étudiant(e) ailleurs"
    EMPLOYEE = "employee", "Salarié(e)"
    SELF_EMPLOYED = "self_employed", "Indépendant(e)"
    OTHER = "other", "Autre"


class Plateforme(models.TextChoices):
    ANDROID = "android", "Android"
    IOS = "ios", "iOS"
    WEB = "web", "Web"


class FournisseurPush(models.TextChoices):
    EXPO = "expo", "Expo"
    FCM = "fcm", "FCM"
    WEBPUSH = "webpush", "Web Push"


class StatutVerification(models.TextChoices):
    PENDING = "pending", "En attente"
    INTERVIEW = "interview", "Entretien"
    VERIFIED = "verified", "Vérifié"
    REJECTED = "rejected", "Refusé"


class TypePiece(models.TextChoices):
    ID_CARD = "id_card", "Carte d'identité"
    PASSPORT = "passport", "Passeport"
    OTHER = "other", "Autre"


ROLES_CLIENTELE = (Role.CLIENT, Role.GERANT)
ROLES_PERSONNEL = (Role.MODERATOR, Role.ADMIN)
