"""Paramètres modifiables sans redéploiement (table `app_settings`) avec valeurs par défaut (CDC annexe A).

Lecture : base (cache de 30 s) puis valeur par défaut. Une clé inconnue est une erreur de programmation.
Écriture : réservée à l'administration (`definir`), toujours journalisée par l'appelant.
"""

from django.core.cache import cache

from .models import AppSetting

DEFAUTS: dict[str, tuple[object, str]] = {
    "OTP_ALLOWED_COUNTRIES": (["BJ"], "Pays autorisés pour les OTP (codes ISO)."),
    "OTP_DAILY_BUDGET": (
        {"signup": 150, "reset_password": 80, "change_phone": 40},  # nosec B105
        "Budget quotidien d'envois d'OTP par usage (300 au total).",
    ),
    "OTP_PHONE_PER_HOUR": (3, "Demandes d'OTP par heure et par numéro."),
    "OTP_INSTALLATION_PER_DAY": (10, "Demandes d'OTP par jour et par appareil."),
    "OTP_IP24_PER_DAY": (60, "Demandes d'OTP par jour et par plage d'adresses /24."),
    "OTP_RESEND_DELAY_S": (60, "Délai avant renvoi d'un OTP, en secondes."),
    "LOGIN_LOCK_THRESHOLD": (5, "Échecs de connexion avant verrouillage."),
    "LOGIN_LOCK_MINUTES": (15, "Durée du premier verrouillage (doublée à chaque récidive)."),
    "LOGIN_FAILS_PER_HOUR_PER_PHONE": (
        30,
        "Échecs par heure et par numéro, tous appareils confondus.",
    ),
    "ADMIN_LOCK_THRESHOLD": (
        5,
        "Échecs de connexion à l'administration avant verrouillage du compte.",
    ),
    "ADMIN_SESSION_IDLE_MIN": (
        30,
        "Inactivité maximale d'une session d'administration, en minutes.",
    ),
    "ADMIN_SESSION_MAX_H": (8, "Durée maximale d'une session d'administration, en heures."),
    "TURNSTILE_ENABLED": (True, "Défi anti-robot du site."),
    "TERMS_VERSION": ("1", "Version courante des CGU et de la politique de confidentialité."),
    "CAMPUS_REFERENCE": (
        {"latitude": 9.337, "longitude": 2.6303},
        "Point de référence du campus (Université de Parakou) : coordonnées à relever.",
    ),
    "CONTACT_LEAK_MODE": ("mask", "Détection des coordonnées : mask, flag ou block."),
    "SUBSCRIPTION_ENABLED": (False, "Abonnement des gérants (désactivé au lancement)."),
    "ALERTS_MAX_PER_USER": (5, "Alertes actives par locataire."),
    "MESSAGE_PER_MINUTE": (30, "Messages par minute et par utilisateur."),
    "NEW_CONVERSATIONS_PER_DAY": (20, "Nouvelles conversations par jour et par locataire."),
    "READONLY_AFTER_RENT_DAYS": (
        30,
        "Jours après la location avant la lecture seule des conversations.",
    ),
    "ARCHIVE_AFTER_RENT_DAYS": (90, "Jours après la location avant l'archivage de l'annonce."),
    "RENTED_VIDEO_DELETE_DAYS": (7, "Jours après la location avant la suppression de la vidéo."),
    "UNANSWERED_REMINDER_H": (2, "Heures avant le rappel au gérant pour un message non lu."),
    "SMS_FALLBACK_ENABLED": (False, "SMS de repli au gérant (désactivé par défaut)."),
    "LISTING_PREMODERATION": (
        False,
        "Pré-modération de toutes les annonces (désactivée par défaut).",
    ),
    "STAFF_READS_ALERT_THRESHOLD": (
        20,
        "Lectures de conversation par jour avant alerte, par compte du personnel.",
    ),
    "MODERATOR_MAX_SUSPENSION_DAYS": (
        30,
        "Durée maximale d'une suspension prononcée par un modérateur.",
    ),
    "RENTED_REPORTS_THRESHOLD": (3, "Signalements « déjà louée » distincts avant dossier."),
    "STALE_HIDE_DAYS": (14, "Jours sans confirmation avant le masquage d'une annonce."),
    "STALE_REMINDER_DAYS": ([7, 10], "Jours sans confirmation avant chaque relance."),
    "MIN_SUPPORTED_VERSION": (
        "1.0.0",
        "Version minimale de l'application mobile (en dessous : mise à jour).",
    ),
    "MAINTENANCE_ENABLED": (False, "Maintenance annoncée à l'application mobile."),
    "MAINTENANCE_MESSAGE": (
        "",
        "Message affiché pendant la maintenance (vide : texte par défaut).",
    ),
    "APP_NOTICE": ("", "Avis court affiché dans l'application (vide : aucun)."),
    "TEAM_PHONE": (
        "+2290156201400",
        "Numéro de l'équipe Logeo (appel et WhatsApp), format international.",
    ),
}

_DELAI_CACHE_S = 30
_ABSENT = object()


def _cle_cache(cle: str) -> str:
    return f"parametre:{cle}"


def lire(cle: str):
    """Valeur courante du paramètre `cle`."""
    if cle not in DEFAUTS:
        raise KeyError(f"paramètre inconnu : {cle}")
    en_cache = cache.get(_cle_cache(cle), _ABSENT)
    if en_cache is not _ABSENT:
        return en_cache
    ligne = AppSetting.objects.filter(key=cle).values_list("value", flat=True).first()
    valeur = DEFAUTS[cle][0] if ligne is None else ligne
    cache.set(_cle_cache(cle), valeur, _DELAI_CACHE_S)
    return valeur


def definir(cle: str, valeur, *, par=None) -> None:
    """Enregistre une valeur (administration). Le cache est invalidé immédiatement."""
    if cle not in DEFAUTS:
        raise KeyError(f"paramètre inconnu : {cle}")
    AppSetting.objects.update_or_create(
        key=cle, defaults={"value": valeur, "description": DEFAUTS[cle][1], "updated_by": par}
    )
    cache.delete(_cle_cache(cle))
