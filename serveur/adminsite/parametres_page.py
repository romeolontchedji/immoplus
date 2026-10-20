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
      "UNANSWERED_REMINDER_H"]),
    ("securite", "Sécurité", "Verrouillages et défi anti-robot.",
     ["LOGIN_LOCK_THRESHOLD", "LOGIN_LOCK_MINUTES", "LOGIN_FAILS_PER_HOUR_PER_PHONE",
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

# Note affichée sous chaque réglage (plan v3, J1) : à quoi il sert, ce que change une modification, l'unité.
NOTES = {
    "MAINTENANCE_ENABLED": "Coché : l'application mobile affiche un écran de maintenance au lieu de fonctionner. Le site "
    "reste ouvert. À utiliser pendant une mise à jour du serveur.",
    "MAINTENANCE_MESSAGE": "Texte de l'écran de maintenance (ex. « Retour vers 14 h »). Vide : message standard.",
    "APP_NOTICE": "Petit message affiché en haut de l'application pour tous (ex. une nouveauté). Vide : rien n'est affiché.",
    "MIN_SUPPORTED_VERSION": "Les applications plus anciennes que cette version doivent se mettre à jour avant de "
    "continuer. Format 1.2.0. À monter seulement après publication de la nouvelle version sur les magasins.",
    "TEAM_PHONE": "Numéro affiché partout pour joindre l'équipe (appel et WhatsApp). Format international : +229…",
    "LEGAL_PROVISIONAL": "Coché : un bandeau prévient que les mentions légales sont provisoires. À décocher quand "
    "l'entreprise est réellement immatriculée et les champs ci-dessous exacts.",
    "LEGAL_COMPANY": "Nom officiel de la société qui édite Immo+, repris dans les conditions et la confidentialité.",
    "LEGAL_RCCM": "Numéro d'immatriculation au registre du commerce (RCCM).",
    "LEGAL_IFU": "Identifiant fiscal unique (IFU) de la société.",
    "LEGAL_ADDRESS": "Adresse du siège, affichée dans les textes légaux.",
    "LEGAL_EMAIL": "Adresse où écrire pour une question légale ou sur ses données personnelles.",
    "LEGAL_UPDATED_AT": "Date « mise à jour le » des textes légaux. Format AAAA-MM-JJ.",
    "TERMS_VERSION": "Changer ce numéro oblige chaque utilisateur à accepter de nouveau les conditions à sa prochaine "
    "connexion. Ne le modifier que si les conditions ont réellement changé.",
    "LISTING_PREMODERATION": "Coché : chaque annonce attend la validation de l'équipe avant d'être visible. Décoché : "
    "seule la première annonce d'un gérant est relue.",
    "STALE_REMINDER_DAYS": "Liste de jours sans confirmation après lesquels le gérant reçoit un rappel, ex. [7, 10]. "
    "Utilisé seulement si le masquage automatique ci-dessous est actif.",
    "STALE_HIDE_DAYS": "Nombre de jours sans confirmation avant que l'annonce soit masquée automatiquement. 0 = jamais "
    "(recommandé : le gérant marque lui-même une chambre louée).",
    "RENTED_REPORTS_THRESHOLD": "Nombre de locataires différents qui signalent « déjà louée » avant qu'un dossier "
    "s'ouvre dans la modération.",
    "RENTED_VIDEO_DELETE_DAYS": "Après « louée », la vidéo est supprimée au bout de ce nombre de jours (le gérant peut "
    "annuler « louée » d'ici là).",
    "READONLY_AFTER_RENT_DAYS": "Après « louée », les conversations de la chambre passent en lecture seule au bout de "
    "ce nombre de jours.",
    "ARCHIVE_AFTER_RENT_DAYS": "Après « louée », l'annonce est archivée (retirée de l'espace du gérant) au bout de ce "
    "nombre de jours.",
    "CAMPUS_REFERENCE": "Position de l'Université de Parakou qui sert à calculer « à 450 m de l'UP ». Format "
    '{"latitude": 9.337, "longitude": 2.630}.',
    "CONTACT_LEAK_MODE": "Que faire d'un numéro ou d'un lien écrit dans la messagerie : laisser passer, le masquer, "
    "prévenir la modération ou bloquer le message. Les annonces refusent toujours les coordonnées.",
    "MESSAGE_PER_MINUTE": "Nombre maximum de messages qu'une personne peut envoyer par minute (contre les envois en "
    "masse).",
    "NEW_CONVERSATIONS_PER_DAY": "Nombre maximum de nouveaux gérants qu'un locataire peut contacter par jour.",
    "ALERTS_MAX_PER_USER": "Nombre maximum d'alertes actives par locataire.",
    "UNANSWERED_REMINDER_H": "Un gérant qui n'a pas lu un message reçoit un rappel après ce nombre d'heures.",
    "LOGIN_LOCK_THRESHOLD": "Nombre de mauvais mots de passe d'affilée avant de bloquer temporairement la connexion "
    "(site et application).",
    "LOGIN_LOCK_MINUTES": "Durée du premier blocage, en minutes ; elle double à chaque nouveau blocage du même compte.",
    "LOGIN_FAILS_PER_HOUR_PER_PHONE": "Plafond d'échecs par heure pour un même nom d'utilisateur, tous appareils confondus (contre les "
    "attaques réparties).",
    "TURNSTILE_ENABLED": "Coché : le défi anti-robot (Cloudflare Turnstile) protège l'inscription et le mot de passe "
    "oublié sur le site.",
    "ADMIN_LOCK_THRESHOLD": "Nombre de mauvais mots de passe avant le blocage d'un compte de l'administration.",
    "ADMIN_SESSION_IDLE_MIN": "Sans activité pendant ce nombre de minutes, la session de l'administration se ferme.",
    "ADMIN_SESSION_MAX_H": "Une session de l'administration se ferme au bout de ce nombre d'heures, même active.",
    "STAFF_READS_ALERT_THRESHOLD": "Si un membre du personnel ouvre plus de conversations que ce nombre dans la "
    "journée, une alerte est levée (protection de la vie privée).",
    "MODERATOR_MAX_SUSPENSION_DAYS": "Durée maximale d'une suspension décidée par un modérateur ; au-delà, il faut un "
    "administrateur.",
    "SUBSCRIPTION_ENABLED": "Coché : les gérants doivent avoir un abonnement actif pour publier. Désactivé en V1 : "
    "tout est gratuit.",
    "SUBSCRIPTION_GRACE_DAYS": "Jours pendant lesquels un gérant garde ses annonces en ligne après la fin de son "
    "abonnement.",
    "PLANS": "Liste des formules d'abonnement (code, nom, prix en FCFA, durée). Ne sert qu'une fois l'abonnement activé.",
    "PAID_ALERTS_ENABLED": "Coché : les locataires peuvent payer une alerte prioritaire (SMS en plus de la notification). "
    "Désactivé en V1.",
}

LONGS = {"MAINTENANCE_MESSAGE", "APP_NOTICE", "LEGAL_ADDRESS"}


def sections() -> list[tuple[str, str, str, list[str]]]:
    """Sections avec, en dernier, les paramètres connus qui ne sont rangés nulle part (aucun n'est oublié)."""
    ranges = {cle for *_, cles in SECTIONS for cle in cles}
    autres = [cle for cle in parametres.DEFAUTS if cle not in ranges]
    return SECTIONS + ([("autres", "Autres", "", autres)] if autres else [])


def _champ(cle: str) -> forms.Field:
    champ = _champ_brut(cle)
    champ.note = NOTES.get(cle, "")  # lu par admin/parametres.html
    return champ


def _champ_brut(cle: str) -> forms.Field:
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
