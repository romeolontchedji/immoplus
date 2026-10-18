"""Page « Paramètres » de l'administration : réglages rangés par thème, champ adapté à chaque type de valeur.

Remplace l'édition ligne par ligne en JSON brut. Chaque enregistrement passe par `parametres.definir` (cache vidé) et
est journalisé avec l'ancienne et la nouvelle valeur.
"""

import json

from django import forms

from apps.core import parametres

SECTIONS = [
    ("application", "Application et maintenance", "Ce que voient les applications au démarrage.",
     ["MAINTENANCE_ENABLED", "MAINTENANCE_MESSAGE", "APP_NOTICE", "MIN_SUPPORTED_VERSION"]),
    ("contact", "Contact et identité légale", "Affichés sur le site, dans l'app et dans les textes légaux.",
     ["TEAM_PHONE", "LEGAL_PROVISIONAL", "LEGAL_COMPANY", "LEGAL_RCCM", "LEGAL_IFU", "LEGAL_ADDRESS", "LEGAL_EMAIL",
      "LEGAL_UPDATED_AT", "TERMS_VERSION"]),
    ("annonces", "Annonces", "Publication, fraîcheur et cycle de vie des chambres.",
     ["LISTING_PREMODERATION", "STALE_REMINDER_DAYS", "STALE_HIDE_DAYS", "RENTED_REPORTS_THRESHOLD",
      "RENTED_VIDEO_DELETE_DAYS", "READONLY_AFTER_RENT_DAYS", "ARCHIVE_AFTER_RENT_DAYS", "CAMPUS_REFERENCE"]),
    ("messagerie", "Messagerie, alertes et notifications", "Limites d'envoi et protection des coordonnées.",
     ["CONTACT_LEAK_MODE", "MESSAGE_PER_MINUTE", "NEW_CONVERSATIONS_PER_DAY", "ALERTS_MAX_PER_USER",
      "UNANSWERED_REMINDER_H", "SMS_FALLBACK_ENABLED"]),
    ("securite", "Sécurité et codes SMS", "Budget des SMS, verrouillages et défi anti-robot.",
     ["OTP_DAILY_BUDGET", "OTP_PHONE_PER_HOUR", "OTP_INSTALLATION_PER_DAY", "OTP_IP24_PER_DAY", "OTP_RESEND_DELAY_S",
      "OTP_ALLOWED_COUNTRIES", "LOGIN_LOCK_THRESHOLD", "LOGIN_LOCK_MINUTES", "LOGIN_FAILS_PER_HOUR_PER_PHONE",
      "TURNSTILE_ENABLED", "ADMIN_LOCK_THRESHOLD", "ADMIN_SESSION_IDLE_MIN", "ADMIN_SESSION_MAX_H"]),
    ("moderation", "Modération", "Garde-fous du personnel.",
     ["STAFF_READS_ALERT_THRESHOLD", "MODERATOR_MAX_SUSPENSION_DAYS"]),
    ("abonnement", "Abonnement (désactivé en V1)", "Prêt côté serveur ; aucun écran de paiement tant que c'est désactivé.",
     ["SUBSCRIPTION_ENABLED", "SUBSCRIPTION_GRACE_DAYS", "PLANS", "PAID_ALERTS_ENABLED"]),
]  # fmt: skip

CHOIX = {
    "CONTACT_LEAK_MODE": [
        ("off", "Aucun filtrage : numéros et liens s'échangent librement"),
        ("mask", "Masquer les coordonnées"),
        ("flag", "Signaler à la modération"),
        ("block", "Bloquer le message"),
    ]
}
LONGS = {"MAINTENANCE_MESSAGE", "APP_NOTICE", "LEGAL_ADDRESS"}


def sections() -> list[tuple[str, str, str, list[str]]]:
    """Sections avec, en dernier, les paramètres connus qui ne sont rangés nulle part (aucun n'est oublié)."""
    ranges = {cle for *_, cles in SECTIONS for cle in cles}
    autres = [cle for cle in parametres.DEFAUTS if cle not in ranges]
    return SECTIONS + ([("autres", "Autres", "", autres)] if autres else [])


def _champ(cle: str) -> forms.Field:
    defaut, description = parametres.DEFAUTS[cle]
    commun = {"label": description, "help_text": cle, "required": False}
    if cle in CHOIX:
        return forms.ChoiceField(choices=CHOIX[cle], **commun)
    if isinstance(defaut, bool):
        return forms.BooleanField(**commun)
    if isinstance(defaut, int):
        return forms.IntegerField(min_value=0, **{**commun, "required": True})
    if isinstance(defaut, (list, dict)):
        return forms.JSONField(
            widget=forms.Textarea(attrs={"rows": 4, "class": "lg-json"}),
            **{**commun, "required": True},
        )
    attrs = {"rows": 3} if cle in LONGS else {}
    return forms.CharField(
        widget=forms.Textarea(attrs=attrs) if cle in LONGS else forms.TextInput(), **commun
    )


class SectionForm(forms.Form):
    def __init__(self, cles: list[str], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cles = cles
        for cle in cles:
            self.fields[cle] = _champ(cle)
            self.initial[cle] = parametres.lire(cle)

    def changements(self) -> dict:
        """{clé: (avant, après)} pour les seules valeurs modifiées."""
        sortie = {}
        for cle in self.cles:
            avant, apres = parametres.lire(cle), self.cleaned_data.get(cle)
            if isinstance(parametres.DEFAUTS[cle][0], str) and apres is None:
                apres = ""
            if json.dumps(avant, sort_keys=True, default=str) != json.dumps(
                apres, sort_keys=True, default=str
            ):
                sortie[cle] = (avant, apres)
        return sortie
