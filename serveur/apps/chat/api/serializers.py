from rest_framework import serializers


class ConversationOuvertureIn(serializers.Serializer):
    listing_id = serializers.UUIDField()
    body = serializers.CharField(max_length=2000, trim_whitespace=False)
    client_msg_id = serializers.UUIDField()


class DemarrageIn(serializers.Serializer):
    listing_id = serializers.UUIDField()


class MessageIn(serializers.Serializer):
    body = serializers.CharField(max_length=2000, trim_whitespace=False)
    client_msg_id = serializers.UUIDField()


class LectureIn(serializers.Serializer):
    up_to_seq = serializers.IntegerField(min_value=0)


class SilenceIn(serializers.Serializer):
    muted_until = serializers.DateTimeField(allow_null=True)


class MessageOut(serializers.Serializer):
    id = serializers.UUIDField()
    seq = serializers.IntegerField()
    sender_id = serializers.UUIDField(allow_null=True)
    client_msg_id = serializers.UUIDField()
    kind = serializers.CharField()
    body = serializers.CharField()
    moderation_status = serializers.CharField()
    flag_reason = serializers.CharField(allow_null=True)
    created_at = serializers.DateTimeField()


class EnvoiOut(serializers.Serializer):
    message = MessageOut()
    warning = serializers.CharField(allow_null=True)


class AnnonceResumeOut(serializers.Serializer):
    id = serializers.UUIDField(allow_null=True)
    slug = serializers.CharField(allow_null=True)
    title = serializers.CharField(allow_null=True)
    status = serializers.CharField(allow_null=True)


class InterlocuteurOut(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField(allow_null=True)


class ConversationOut(serializers.Serializer):
    id = serializers.UUIDField()
    listing = AnnonceResumeOut()
    other = InterlocuteurOut()
    status = serializers.CharField()
    blocked_by_me = serializers.BooleanField()
    last_message_preview = serializers.CharField()
    last_message_at = serializers.DateTimeField(allow_null=True)
    unread_count = serializers.IntegerField()
    muted = serializers.BooleanField()


class ListeConversationsOut(serializers.Serializer):
    items = ConversationOut(many=True)
    next_cursor = serializers.CharField(allow_null=True)
    unread_total = serializers.IntegerField()


class ConversationDetailOut(ConversationOut):
    address_private = serializers.CharField(allow_null=True)
    my_read_seq = serializers.IntegerField()
    other_read_seq = serializers.IntegerField()
    last_seq = serializers.IntegerField()


class OuvertureOut(EnvoiOut):
    conversation = ConversationOut()


class HistoriqueOut(serializers.Serializer):
    items = MessageOut(many=True)
    has_more = serializers.BooleanField()
    last_seq = serializers.IntegerField()


class TicketOut(serializers.Serializer):
    ticket = serializers.CharField()
    expires_in = serializers.IntegerField()
