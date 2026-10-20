"""Mots de passe : Argon2id, longueur minimale, mots de passe courants refusés (CDC EF-AUT-03)."""

import secrets

from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from apps.core.errors import ErreurMetier

_HACHAGE_FACTICE: str | None = None


def valider(mot_de_passe: str, champ: str = "password", utilisateur=None) -> None:
    """Lève `ErreurMetier(validation_error)` si le mot de passe est trop court, trop courant ou trop proche du nom
    d'utilisateur, du prénom ou du nom (`utilisateur`, même pas encore enregistré)."""
    try:
        validate_password(mot_de_passe, user=utilisateur)
    except ValidationError as erreur:
        raise ErreurMetier(
            "validation_error",
            "Le mot de passe est trop faible.",
            champs={champ: list(erreur.messages)},
        ) from erreur


def hacher(mot_de_passe: str) -> str:
    return make_password(mot_de_passe)


def _hachage_factice() -> str:
    global _HACHAGE_FACTICE
    if _HACHAGE_FACTICE is None:
        _HACHAGE_FACTICE = make_password(secrets.token_urlsafe(24))
    return _HACHAGE_FACTICE


def verifier(utilisateur, mot_de_passe: str) -> bool:
    """Compare en temps constant ; si `utilisateur` est None (numéro inconnu), fait le même travail à vide."""
    if utilisateur is None or not utilisateur.has_usable_password():
        check_password(mot_de_passe, _hachage_factice())
        return False
    return check_password(mot_de_passe, utilisateur.password)
