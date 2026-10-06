"""Permissions de base : tout refus est la réponse initiale (CDC §5 « sûr par défaut »)."""

from rest_framework.permissions import BasePermission


class RefusParDefaut(BasePermission):
    """Un endpoint sans règle d'accès explicite répond toujours par un refus."""

    def has_permission(self, request, view):
        return False
