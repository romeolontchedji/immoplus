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
