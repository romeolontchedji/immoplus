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


class Objet(models.TextChoices):
    SIGNUP = "signup", "Inscription"
    RESET_PASSWORD = "reset_password", "Mot de passe oublié"
    CHANGE_PHONE = "change_phone", "Changement de numéro"


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
