"""Schémas OpenAPI de la configuration distante (lecture seule)."""

from rest_framework import serializers


class MaintenanceOut(serializers.Serializer):
    active = serializers.BooleanField()
    message = serializers.CharField(allow_blank=True)


class LimitesOut(serializers.Serializer):
    message_max_length = serializers.IntegerField()
    messages_per_minute = serializers.IntegerField()
    alerts_max = serializers.IntegerField()
    favorites_max = serializers.IntegerField()
    photos_max = serializers.IntegerField()
    photo_max_bytes = serializers.IntegerField()
    video_max_bytes = serializers.IntegerField()
    upload_chunk_max_bytes = serializers.IntegerField()
    page_size_default = serializers.IntegerField()
    page_size_max = serializers.IntegerField()


class TempsReelOut(serializers.Serializer):
    path = serializers.CharField()
    ticket_ttl_s = serializers.IntegerField()
    ping_interval_s = serializers.IntegerField()
    inactivity_close_s = serializers.IntegerField()
    max_connections = serializers.IntegerField()


class ContactOut(serializers.Serializer):
    phone = serializers.CharField()
    whatsapp_url = serializers.URLField()


class AppConfigOut(serializers.Serializer):
    min_supported_version = serializers.CharField()
    maintenance = MaintenanceOut()
    notice = serializers.CharField(allow_blank=True)
    flags = serializers.DictField(child=serializers.BooleanField())
    limits = LimitesOut()
    realtime = TempsReelOut()
    contact = ContactOut()
