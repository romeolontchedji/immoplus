"""Configuration distante de l'application mobile (GET /v1/app-config, CDC §10) et contact de l'équipe.

`apps.core` ne connaît pas les autres applications : chacune déclare ses limites au démarrage (`declarer_limites`
dans son `AppConfig.ready`), et ce module les assemble avec les paramètres modifiables (`app_settings`).
"""

from . import parametres

_limites: dict[str, int] = {}
_temps_reel: dict[str, object] = {}


def declarer_limites(**valeurs: int) -> None:
    _limites.update(valeurs)


def declarer_temps_reel(**valeurs) -> None:
    _temps_reel.update(valeurs)


def contact_equipe() -> dict:
    """Numéro de l'équipe (un seul paramètre) décliné pour l'appel, WhatsApp et l'affichage."""
    numero = str(parametres.lire("TEAM_PHONE")).replace(" ", "")
    chiffres = numero.lstrip("+")
    local = chiffres[3:] if chiffres.startswith("229") else chiffres
    affiche = "+229 " + " ".join(local[i : i + 2] for i in range(0, len(local), 2))
    return {
        "phone": numero,
        "phone_display": affiche,
        "tel_url": f"tel:{numero}",
        "whatsapp_url": f"https://wa.me/{chiffres}",
    }


def configuration_app() -> dict:
    return {
        "min_supported_version": parametres.lire("MIN_SUPPORTED_VERSION"),
        "maintenance": {
            "active": bool(parametres.lire("MAINTENANCE_ENABLED")),
            "message": parametres.lire("MAINTENANCE_MESSAGE") or "",
        },
        "notice": parametres.lire("APP_NOTICE") or "",
        "flags": {
            # Décision du porteur (2026-10-17) : aucun écran de paiement en V1, même si le serveur `billing` est prêt ;
            # le drapeau des apps reste faux quelle que soit la valeur du paramètre.
            "subscription": False,
            "paid_alerts": False,  # même décision : rien de payant n'est visible en V1
            "contact_leak_block": parametres.lire("CONTACT_LEAK_MODE") == "block",
        },
        "limits": {
            "messages_per_minute": int(parametres.lire("MESSAGE_PER_MINUTE")),
            "alerts_max": int(parametres.lire("ALERTS_MAX_PER_USER")),
            **_limites,
        },
        "realtime": dict(_temps_reel),
        "contact": {k: v for k, v in contact_equipe().items() if k in ("phone", "whatsapp_url")},
    }
