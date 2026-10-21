from rest_framework import serializers


class NotificationOut(serializers.Serializer):
    id = serializers.UUIDField()
    kind = serializers.CharField()
    title = serializers.CharField()
    body = serializers.CharField()
    data = serializers.DictField()
    read_at = serializers.DateTimeField(allow_null=True)
    created_at = serializers.DateTimeField()


class ListeNotificationsOut(serializers.Serializer):
    items = NotificationOut(many=True)
    next_cursor = serializers.CharField(allow_null=True)
    unread_count = serializers.IntegerField()


class CompteurOut(serializers.Serializer):
    unread_count = serializers.IntegerField()


class ToutLuOut(serializers.Serializer):
    updated = serializers.IntegerField()
