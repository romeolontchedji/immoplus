"""Schémas de l'API publique : fil, fiche, favoris, alertes (CDC §10.3)."""

from rest_framework import serializers


class QuartierRefOut(serializers.Serializer):
    name = serializers.CharField()
    slug = serializers.CharField()


class GerantCarteOut(serializers.Serializer):
    name = serializers.CharField(allow_null=True)
    verified = serializers.BooleanField()


class CarteOut(serializers.Serializer):
    id = serializers.UUIDField()
    slug = serializers.CharField()
    title = serializers.CharField()
    room_type = serializers.CharField()
    district = QuartierRefOut()
    landmark_text = serializers.CharField()
    rent_amount = serializers.IntegerField()
    deposit_months = serializers.IntegerField()
    advance_months = serializers.IntegerField()
    distance_m = serializers.IntegerField()
    has_private_bathroom = serializers.BooleanField()
    is_fenced = serializers.BooleanField()
    available_from = serializers.DateField()
    status = serializers.CharField()
    published_at = serializers.DateTimeField(allow_null=True)
    cover_url = serializers.CharField(allow_null=True)
    video_poster_url = serializers.CharField(allow_null=True)
    has_video = serializers.BooleanField()
    gerant = GerantCarteOut()


class FilOut(serializers.Serializer):
    items = CarteOut(many=True)
    next_cursor = serializers.CharField(allow_null=True)


class MediaPublicOut(serializers.Serializer):
    id = serializers.UUIDField()
    kind = serializers.CharField()
    playback_url = serializers.CharField(required=False)
    poster_url = serializers.CharField(required=False, allow_null=True)
    duration_s = serializers.FloatField(required=False, allow_null=True)
    url = serializers.CharField(required=False, allow_null=True)
    thumb_url = serializers.CharField(required=False, allow_null=True)
    is_cover = serializers.BooleanField(required=False)
    width = serializers.IntegerField(allow_null=True)
    height = serializers.IntegerField(allow_null=True)


class GerantFicheOut(serializers.Serializer):
    name = serializers.CharField(allow_null=True)
    verified = serializers.BooleanField()
    median_response_min = serializers.IntegerField(allow_null=True)


class FicheOut(serializers.Serializer):
    id = serializers.UUIDField()
    slug = serializers.CharField()
    title = serializers.CharField()
    room_type = serializers.CharField()
    district = QuartierRefOut()
    landmark_text = serializers.CharField()
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    distance_m = serializers.IntegerField()
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
    description_html = serializers.CharField()
    status = serializers.CharField()
    published_at = serializers.DateTimeField(allow_null=True)
    last_confirmed_at = serializers.DateTimeField(allow_null=True)
    media = MediaPublicOut(many=True)
    gerant = GerantFicheOut()
    is_favorite = serializers.BooleanField()


class VueOut(serializers.Serializer):
    counted = serializers.BooleanField()


class AlerteIn(serializers.Serializer):
    label = serializers.CharField(max_length=80, required=False, allow_blank=True)
    district_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, max_length=30
    )
    room_types = serializers.ListField(
        child=serializers.CharField(max_length=16), required=False, max_length=4
    )
    max_rent = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    private_bathroom_required = serializers.BooleanField(required=False)
    max_distance_m = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    is_active = serializers.BooleanField(required=False)


class AlerteOut(serializers.Serializer):
    id = serializers.UUIDField()
    label = serializers.CharField()
    district_ids = serializers.ListField(child=serializers.UUIDField())
    room_types = serializers.ListField(child=serializers.CharField())
    max_rent = serializers.IntegerField(allow_null=True)
    private_bathroom_required = serializers.BooleanField()
    max_distance_m = serializers.IntegerField(allow_null=True)
    is_active = serializers.BooleanField()
    created_at = serializers.DateTimeField()
