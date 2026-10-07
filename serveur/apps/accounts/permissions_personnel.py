"""Droits du personnel, déduits du rôle (aucun champ modifiable par le site ou l'API).

Les administrateurs ont tous les droits ; les modérateurs n'ont que la liste explicite ci-dessous.
"""

PERMISSIONS_MODERATEUR = frozenset(
    {
        "moderation.view_report",
        "moderation.change_report",
        "moderation.view_moderationaction",
        "moderation.add_moderationaction",
        "listings.view_listing",
        "listings.change_listing",
        "accounts.view_gerantprofile",
    }
)
MODULES_MODERATEUR = frozenset({"moderation", "listings", "accounts"})


def autorise(utilisateur, perm: str) -> bool:
    if not utilisateur.is_active:
        return False
    if utilisateur.role == "admin":
        return True
    return utilisateur.role == "moderator" and perm in PERMISSIONS_MODERATEUR


def autorise_module(utilisateur, app_label: str) -> bool:
    if not utilisateur.is_active:
        return False
    if utilisateur.role == "admin":
        return True
    return utilisateur.role == "moderator" and app_label in MODULES_MODERATEUR
