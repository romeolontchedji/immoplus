"""Paramètres modifiables sans redéploiement (table `app_settings`) avec valeurs par défaut (CDC annexe A).

Lecture : base (cache de 30 s) puis valeur par défaut. Une clé inconnue est une erreur de programmation.
Écriture : réservée à l'administration (`definir`), toujours journalisée par l'appelant.
"""

from django.core.cache import cache

from .models import AppSetting

DEFAUTS: dict[str, tuple[object, str]] = {
    "OTP_ALLOWED_COUNTRIES": (["BJ"], "Pays autorisés pour les OTP (codes ISO)."),
    "OTP_DAILY_BUDGET": (
        {"signup": 150, "reset_password": 80, "change_phone": 40, "gerant_activation": 30},  # nosec B105
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
    "SUBSCRIPTION_ENABLED": (False, "Abonnement des gérants (désactivé au lancement)."),
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
