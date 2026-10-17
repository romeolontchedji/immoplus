"""Valeurs fixes des signalements et des actions de modération."""

MOTIFS = [
    "fake_listing",
    "already_rented",
    "price_mismatch",
    "contact_leak",
    "harassment",
    "scam",
    "other",
]
CIBLES = ["listing", "message", "user", "conversation"]
ETATS_OUVERTS = ["open", "in_review"]
ETATS = [*ETATS_OUVERTS, "resolved_actioned", "resolved_dismissed"]
ACTIONS = [
    "message_masked", "message_deleted", "listing_hidden", "listing_removed",
    "warning", "suspension", "ban", "reinstatement",
]  # fmt: skip

# Libellés affichés dans l'administration (les valeurs stockées ne changent pas).
LIBELLES_MOTIFS = {
    "fake_listing": "Fausse annonce",
    "already_rented": "Déjà louée",
    "price_mismatch": "Prix différent",
    "contact_leak": "Coordonnées partagées",
    "harassment": "Harcèlement",
    "scam": "Arnaque",
    "other": "Autre",
}
LIBELLES_CIBLES = {
    "listing": "Annonce",
    "message": "Message",
    "user": "Compte",
    "conversation": "Conversation",
}
LIBELLES_ETATS = {
    "open": "Ouvert",
    "in_review": "En cours d'examen",
    "resolved_actioned": "Traité : sanction",
    "resolved_dismissed": "Classé sans suite",
}
LIBELLES_ACTIONS = {
    "message_masked": "Message masqué",
    "message_deleted": "Message supprimé",
    "listing_hidden": "Annonce masquée",
    "listing_removed": "Annonce retirée",
    "warning": "Avertissement",
    "suspension": "Suspension",
    "ban": "Bannissement",
    "reinstatement": "Réhabilitation",
}
LIBELLES_SOURCES = {"user": "Utilisateur", "system": "Détection automatique"}
