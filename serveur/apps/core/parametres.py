"""Paramètres modifiables sans redéploiement (table `app_settings`) avec valeurs par défaut (CDC annexe A).

Lecture : base (cache de 30 s) puis valeur par défaut. Une clé inconnue est une erreur de programmation.
Écriture : réservée à l'administration (`definir`), toujours journalisée par l'appelant.
"""

from django.core.cache import cache

from .models import AppSetting

DEFAUTS: dict[str, tuple[object, str]] = {
    # Nom historique : sert aujourd'hui à valider les numéros de téléphone (plus aucun code SMS, ADR 0009).
    "OTP_ALLOWED_COUNTRIES": (["BJ"], "Pays autorisés pour les numéros de téléphone (codes ISO)."),
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
    "CONTACT_LEAK_MODE": (
        "off",
        "Coordonnées dans la messagerie : off (échange libre), mask, flag ou block.",
    ),
    "SUBSCRIPTION_ENABLED": (False, "Abonnement des gérants (désactivé au lancement)."),
    "PLANS": (
        [
            {
                "code": "free_v1",
                "label": "Gratuit V1",
                "price": 0,
                "period_months": 1,
                "max_active_listings": None,
                "active": True,
            },
            {
                "code": "standard",
                "label": "Standard",
                "price": None,
                "period_months": 1,
                "max_active_listings": None,
                "active": False,
            },
        ],
        "Plans d'abonnement des gérants (CDC §9.19) ; prix à fixer avant activation (décision V11).",
    ),
    "SUBSCRIPTION_GRACE_DAYS": (7, "Jours de grâce d'un abonnement impayé avant expiration."),
    "PAID_ALERTS_ENABLED": (
        False,
        "Alerte prioritaire payante des locataires (SMS en plus du push) : désactivée en V1.",
    ),
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
    "STALE_HIDE_DAYS": (
        0,
        "Jours sans confirmation avant le masquage automatique d'une annonce. 0 = jamais (réglage par défaut "
        "depuis le 19/10/2026 : le gérant retire lui-même une chambre louée ou indisponible).",
    ),
    "STALE_REMINDER_DAYS": (
        [7, 10],
        "Jours sans confirmation avant chaque relance au gérant (utilisé seulement si le masquage est actif).",
    ),
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
        "Numéro de l'équipe Immo+ (appel et WhatsApp), format international.",
    ),
    # Identité de l'éditeur dans les textes légaux : VALEURS FICTIVES PROVISOIRES (décision du 2026-10-17),
    # à remplacer par les vraies avant l'ouverture au public, puis passer LEGAL_PROVISIONAL à faux.
    "LEGAL_PROVISIONAL": (True, "Textes légaux provisoires (identité fictive) : bandeau affiché."),
    "LEGAL_COMPANY": ("IMMOPLUS SARL", "Raison sociale de l'éditeur."),
    "LEGAL_RCCM": ("RB/PKO/26 B 00001", "Numéro RCCM de l'éditeur."),
    "LEGAL_IFU": ("3202600000001", "Numéro IFU de l'éditeur."),
    "LEGAL_ADDRESS": ("Banikanni, Parakou, République du Bénin", "Siège social de l'éditeur."),
    "LEGAL_EMAIL": ("contact@immoplus.bj", "Contact pour les questions légales et les données."),
    "LEGAL_UPDATED_AT": ("2026-10-17", "Date de mise à jour des textes légaux (AAAA-MM-JJ)."),
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
