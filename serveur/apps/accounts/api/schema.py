"""Déclare le schéma de sécurité `Bearer` de l'API dans le contrat OpenAPI."""

from drf_spectacular.extensions import OpenApiAuthenticationExtension


class AuthJwtSchema(OpenApiAuthenticationExtension):
    target_class = "apps.accounts.api.authentication.AuthJwt"
    name = "BearerJwt"

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Jeton d'accès de 15 minutes (`aud` = client ou gerant), obtenu par /auth/login.",
        }
