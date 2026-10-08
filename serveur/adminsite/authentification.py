"""Authentification du personnel par adresse e-mail et mot de passe (jamais par numéro de téléphone)."""

from django.contrib.auth.backends import BaseBackend

from apps.accounts.models import ROLES_PERSONNEL, User
from apps.accounts.services import mots_de_passe


class AuthPersonnel(BaseBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        email = (username or "").strip().lower()
        utilisateur = (
            User.objects.filter(email__iexact=email, role__in=ROLES_PERSONNEL).first()
            if email
            else None
        )
        correct = mots_de_passe.verifier(
            utilisateur, password or ""
        )  # travail à vide si le compte n'existe pas
        if correct and utilisateur is not None and utilisateur.is_active:
            return utilisateur
        return None

    def get_user(self, user_id):
        utilisateur = User.objects.filter(pk=user_id, role__in=ROLES_PERSONNEL).first()
        return utilisateur if utilisateur and utilisateur.is_active else None
