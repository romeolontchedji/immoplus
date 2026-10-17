from rest_framework import serializers

from ..enums import Compteur, Eau, StatutAnnonce, TypeChambre


class DistrictOut(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    slug = serializers.CharField()
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()


class AnnonceIn(serializers.Serializer):
    title = serializers.CharField(max_length=120)
    room_type = serializers.ChoiceField(choices=[t.value for t in TypeChambre])
    district = serializers.UUIDField()
    landmark_text = serializers.CharField(max_length=160)
    address_private = serializers.CharField(max_length=255, required=False, allow_blank=True)
    latitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        required=False,
        allow_null=True,
        help_text="Facultatif : GPS du téléphone. Absent, la chambre est placée au centre du quartier.",
    )
    longitude = serializers.DecimalField(
        max_digits=9, decimal_places=6, required=False, allow_null=True
    )
    rent_amount = serializers.IntegerField(min_value=1)
    deposit_months = serializers.IntegerField(min_value=0, max_value=12)
    advance_months = serializers.IntegerField(min_value=0, max_value=12)
    agent_fee_amount = serializers.IntegerField(min_value=0, required=False)
    available_from = serializers.DateField()
    has_private_bathroom = serializers.BooleanField()
    is_fenced = serializers.BooleanField()
    water_source = serializers.ChoiceField(choices=[e.value for e in Eau])
    electricity_meter = serializers.ChoiceField(choices=[c.value for c in Compteur])
    description_md = serializers.CharField(max_length=6000, required=False, allow_blank=True)


class AnnonceProOut(serializers.Serializer):
    id = serializers.UUIDField()
    slug = serializers.CharField()
    title = serializers.CharField()
    room_type = serializers.CharField()
    district = serializers.UUIDField(source="district_id")
    district_name = serializers.CharField(source="district.name")
    landmark_text = serializers.CharField()
    address_private = serializers.CharField()
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    distance_to_campus_m = serializers.IntegerField()
    rent_amount = serializers.IntegerField()
    deposit_months = serializers.IntegerField()
    advance_months = serializers.IntegerField()
    agent_fee_amount = serializers.IntegerField()
    available_from = serializers.DateField()
    has_private_bathroom = serializers.BooleanField()
    is_fenced = serializers.BooleanField()
    water_source = serializers.CharField()
    electricity_meter = serializers.CharField()
    description_md = serializers.CharField()
    status = serializers.ChoiceField(choices=[s.value for s in StatutAnnonce])
    hidden_reason = serializers.CharField(allow_null=True)
    published_at = serializers.DateTimeField(allow_null=True)
    last_confirmed_at = serializers.DateTimeField(allow_null=True)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class ApercuIn(serializers.Serializer):
    markdown = serializers.CharField(max_length=6000, allow_blank=True)


class ApercuOut(serializers.Serializer):
    markdown = serializers.CharField()
    html = serializers.CharField()


class MediaIn(serializers.Serializer):
    kind = serializers.ChoiceField(choices=["video", "photo"])
    size_bytes = serializers.IntegerField(min_value=1)


class MediaOut(serializers.Serializer):
    id = serializers.UUIDField()
    kind = serializers.CharField()
    status = serializers.CharField()
    position = serializers.IntegerField()
    is_cover = serializers.BooleanField()
    declared_size_bytes = serializers.IntegerField()
    received_bytes = serializers.IntegerField()
    width = serializers.IntegerField(allow_null=True)
    height = serializers.IntegerField(allow_null=True)
    duration_s = serializers.FloatField(allow_null=True)
    playback_url = serializers.CharField(allow_null=True)
    poster_url = serializers.CharField(allow_null=True)
    error_code = serializers.CharField(allow_null=True)
    error_detail = serializers.CharField(allow_null=True)
    upload_url = serializers.CharField(allow_null=True)


class OrdreMediasIn(serializers.Serializer):
    order = serializers.ListField(child=serializers.UUIDField(), allow_empty=False, max_length=20)
    cover = serializers.UUIDField(required=False, allow_null=True)
