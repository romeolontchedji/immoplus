"""Schémas d'entrée et de sortie de l'API de comptes (le contrat OpenAPI en est tiré)."""

from rest_framework import serializers

from apps.accounts.models import Objet, Plateforme


class OtpDemandeIn(serializers.Serializer):
    phone = serializers.CharField(max_length=40)
    purpose = serializers.ChoiceField(choices=[o.value for o in Objet])
    attestation_token = serializers.CharField(max_length=4096, required=False, allow_blank=True)


class OtpVerificationIn(serializers.Serializer):
    phone = serializers.CharField(max_length=40)
    purpose = serializers.ChoiceField(choices=[o.value for o in Objet])
    code = serializers.CharField(max_length=12)


class OtpJetonOut(serializers.Serializer):
    otp_token = serializers.CharField()
    expires_in = serializers.IntegerField()


class AppareilIn(serializers.Serializer):
    platform = serializers.ChoiceField(choices=[p.value for p in Plateforme])
    label = serializers.CharField(max_length=120, required=False, allow_blank=True)


class InscriptionIn(AppareilIn):
    otp_token = serializers.CharField(max_length=2048)
    full_name = serializers.CharField(max_length=200)
    password = serializers.CharField(max_length=128, trim_whitespace=False)
    terms_accepted = serializers.BooleanField()


class ActivationIn(AppareilIn):
    otp_token = serializers.CharField(max_length=2048)
    password = serializers.CharField(max_length=128, trim_whitespace=False)
    terms_accepted = serializers.BooleanField()


class ConnexionIn(AppareilIn):
    phone = serializers.CharField(max_length=40)
    password = serializers.CharField(max_length=128, trim_whitespace=False, allow_blank=True)


class RafraichissementIn(serializers.Serializer):
    refresh_token = serializers.CharField(max_length=200)


class MotDePasseOublieIn(serializers.Serializer):
    otp_token = serializers.CharField(max_length=2048)
    new_password = serializers.CharField(max_length=128, trim_whitespace=False)


class ChangementMotDePasseIn(serializers.Serializer):
    current_password = serializers.CharField(max_length=128, trim_whitespace=False)
    new_password = serializers.CharField(max_length=128, trim_whitespace=False)


class ChangementNumeroIn(serializers.Serializer):
    password = serializers.CharField(max_length=128, trim_whitespace=False)
    otp_token = serializers.CharField(max_length=2048)


class SuppressionIn(serializers.Serializer):
    password = serializers.CharField(max_length=128, trim_whitespace=False)


class ProfilIn(serializers.Serializer):
    full_name = serializers.CharField(max_length=200, required=False)


class JetonsOut(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    expires_in = serializers.IntegerField()


class UtilisateurOut(serializers.Serializer):
    id = serializers.UUIDField()
    full_name = serializers.CharField()
    role = serializers.ChoiceField(choices=["client", "gerant"])
    phone = serializers.CharField(allow_null=True)
    terms_version = serializers.CharField(allow_null=True)
    created_at = serializers.DateTimeField()


class SessionOut(serializers.Serializer):
    user = UtilisateurOut()
    tokens = JetonsOut()
    device_id = serializers.UUIDField()


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


class PreferencesIO(serializers.Serializer):
    """Objet libre {catégorie: {push, apercu}, silence: [...]}, validé par le service."""

    def to_internal_value(self, data):
        return data

    def to_representation(self, instance):
        return instance
