from rest_framework import serializers

from ..enums import Methode


class PlanOut(serializers.Serializer):
    code = serializers.CharField()
    label = serializers.CharField()
    price = serializers.IntegerField(allow_null=True)
    period_months = serializers.IntegerField()
    max_active_listings = serializers.IntegerField(allow_null=True)


class AbonnementOut(serializers.Serializer):
    id = serializers.UUIDField()
    plan_code = serializers.CharField()
    status = serializers.CharField()
    current_period_start = serializers.DateTimeField()
    current_period_end = serializers.DateTimeField()
    cancel_at_period_end = serializers.BooleanField()


class PaiementIn(serializers.Serializer):
    plan_code = serializers.CharField(max_length=32)
    method = serializers.ChoiceField(choices=Methode.values)
    phone = serializers.CharField(max_length=16)
    idempotency_key = serializers.CharField(max_length=64)


class PaiementOut(serializers.Serializer):
    id = serializers.UUIDField()
    plan_code = serializers.CharField()
    amount = serializers.IntegerField()
    status = serializers.CharField()
    provider = serializers.CharField()
    created_at = serializers.DateTimeField()
