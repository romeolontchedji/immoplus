from rest_framework import serializers

from ..enums import CIBLES, MOTIFS


class SignalementIn(serializers.Serializer):
    target_type = serializers.ChoiceField(choices=CIBLES)
    target_id = serializers.UUIDField()
    reason_code = serializers.ChoiceField(choices=MOTIFS)
    details = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")


class SignalementOut(serializers.Serializer):
    id = serializers.UUIDField()
    status = serializers.CharField()
    created = serializers.BooleanField()
