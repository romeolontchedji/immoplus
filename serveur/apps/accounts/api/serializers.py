"""Schémas d'entrée et de sortie de l'API de comptes (le contrat OpenAPI en est tiré)."""

from rest_framework import serializers

from apps.accounts.enums import Occupation, Plateforme


class AppareilIn(serializers.Serializer):
    platform = serializers.ChoiceField(choices=[p.value for p in Plateforme])
    label = serializers.CharField(max_length=120, required=False, allow_blank=True)


class InscriptionIn(AppareilIn):
    username = serializers.CharField(
        max_length=40,
        help_text="3 à 30 caractères : lettres, chiffres, point, tiret bas (ADR 0009).",
    )
    first_name = serializers.CharField(max_length=60)
    last_name = serializers.CharField(max_length=60)
    password = serializers.CharField(max_length=128, trim_whitespace=False)
    terms_accepted = serializers.BooleanField()
    occupation = serializers.ChoiceField(
        choices=Occupation.values,
        required=False,
        allow_null=True,
        help_text="« Tu es » (facultatif).",
    )


class ConnexionIn(AppareilIn):
    username = serializers.CharField(
        max_length=40,
        help_text="Nom d'utilisateur (ou, jusqu'au 20/11/2026, numéro d'un ancien compte).",
    )
    password = serializers.CharField(max_length=128, trim_whitespace=False, allow_blank=True)


class RafraichissementIn(serializers.Serializer):
    refresh_token = serializers.CharField(max_length=200)


class LienParEmailIn(serializers.Serializer):
    identifier = serializers.CharField(
        max_length=254, help_text="Nom d'utilisateur ou e-mail confirmé."
    )


class CleDeSecoursIn(serializers.Serializer):
    username = serializers.CharField(max_length=40)
    recovery_key = serializers.CharField(max_length=40, help_text="Ex. K7QM-2XPA-9RTD-H4WN.")
    new_password = serializers.CharField(max_length=128, trim_whitespace=False)


class CleDeSecoursOut(serializers.Serializer):
    recovery_key = serializers.CharField(help_text="Nouvelle clé : à montrer une seule fois.")


class DisponibiliteOut(serializers.Serializer):
    available = serializers.BooleanField()
    message = serializers.CharField(allow_blank=True)
    suggestions = serializers.ListField(child=serializers.CharField())


class ChangementMotDePasseIn(serializers.Serializer):
    current_password = serializers.CharField(max_length=128, trim_whitespace=False)
    new_password = serializers.CharField(max_length=128, trim_whitespace=False)


class EmailIn(serializers.Serializer):
    email = serializers.CharField(max_length=254)


class MotDePasseIn(serializers.Serializer):
    password = serializers.CharField(max_length=128, trim_whitespace=False)


class SuppressionIn(serializers.Serializer):
    password = serializers.CharField(max_length=128, trim_whitespace=False)


class ProfilIn(serializers.Serializer):
    first_name = serializers.CharField(max_length=60, required=False)
    last_name = serializers.CharField(max_length=60, required=False)
    occupation = serializers.ChoiceField(
        choices=Occupation.values,
        required=False,
        allow_null=True,
        help_text="`null` efface la réponse.",
    )


class JetonsOut(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    expires_in = serializers.IntegerField()


class UtilisateurOut(serializers.Serializer):
    id = serializers.UUIDField()
    username = serializers.CharField(allow_null=True)
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    full_name = serializers.CharField()
    email = serializers.CharField(allow_null=True, help_text="Seulement s'il est confirmé.")
    recovery_key_created_at = serializers.DateTimeField(allow_null=True)
    occupation = serializers.ChoiceField(choices=Occupation.values, allow_null=True)
    role = serializers.ChoiceField(choices=["client", "gerant"])
    terms_version = serializers.CharField(allow_null=True)
    created_at = serializers.DateTimeField()


class SessionOut(serializers.Serializer):
    user = UtilisateurOut()
    tokens = JetonsOut()
    device_id = serializers.UUIDField()


class InscriptionOut(SessionOut):
    recovery_key = serializers.CharField(
        help_text="Clé de secours : à montrer une seule fois (ADR 0009)."
    )


class AppareilOut(serializers.Serializer):
    id = serializers.UUIDField()
    label = serializers.CharField(allow_null=True)
    platform = serializers.CharField()
    app_version = serializers.CharField(allow_null=True)
    last_seen_at = serializers.DateTimeField(allow_null=True)
    created_at = serializers.DateTimeField()
    current = serializers.BooleanField()


class JetonPushIn(serializers.Serializer):
    provider = serializers.CharField(max_length=8)
    token = serializers.CharField(max_length=4096)


class ReglageNotification(serializers.Serializer):
    push = serializers.BooleanField(
        required=False, help_text="Faux : aucune notification push (absent = activé)."
    )
    apercu = serializers.BooleanField(
        required=False, help_text="Messages : faux = « Nouveau message » sans le texte."
    )


class PreferencesSchema(serializers.Serializer):
    """Forme documentée de `PreferencesIO` (OpenAPI) : seules les catégories envoyées changent."""

    messages = ReglageNotification(required=False)
    alertes = ReglageNotification(required=False)
    rappels = ReglageNotification(required=False)
    silence = serializers.ListField(
        child=serializers.CharField(max_length=64),
        required=False,
        help_text="Conversations en sourdine.",
    )


class PreferencesIO(serializers.Serializer):
    """Objet libre {catégorie: {push, apercu}, silence: [...]}, validé par le service."""

    def to_internal_value(self, data):
        return data

    def to_representation(self, instance):
        return instance
