"""Conversations et messages (CDC §9.13, §9.14)."""

import uuid

from django.db import models
from django.db.models.functions import Now
from django.utils import timezone

STATUTS_CONVERSATION = ["open", "read_only", "blocked"]
STATUTS_MODERATION = ["visible", "masked", "hidden", "deleted"]


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey("listings.Listing", on_delete=models.PROTECT, related_name="+")
    client = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="+")
    gerant = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="+")
    status = models.CharField(max_length=10, default="open", db_default="open")
    blocked_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    last_seq = models.BigIntegerField(default=0, db_default=0)
    last_message_at = models.DateTimeField(null=True, blank=True)
    last_sender = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    last_message_preview = models.CharField(max_length=80, default="", blank=True)
    client_read_seq = models.BigIntegerField(default=0, db_default=0)
    gerant_read_seq = models.BigIntegerField(default=0, db_default=0)
    client_muted_until = models.DateTimeField(null=True, blank=True)
    gerant_muted_until = models.DateTimeField(null=True, blank=True)
    first_reply_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_default=Now())
    updated_at = models.DateTimeField(auto_now=True, db_default=Now())

    class Meta:
        db_table = "conversations"
        constraints = [
            models.UniqueConstraint(
                fields=["listing", "client"], name="conversations_un_par_couple"
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=STATUTS_CONVERSATION),
                name="conversations_statut_valide",
            ),
            models.CheckConstraint(
                condition=~models.Q(client=models.F("gerant")), name="conversations_deux_personnes"
            ),
        ]
        indexes = [
            models.Index(fields=["client", "-last_message_at"], name="conv_client_activite_idx"),
            models.Index(fields=["gerant", "-last_message_at"], name="conv_gerant_activite_idx"),
            models.Index(fields=["listing"], name="conv_annonce_idx"),
        ]


class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    seq = models.BigIntegerField()
    sender = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    client_msg_id = models.UUIDField()
    kind = models.CharField(max_length=8, default="text", db_default="text")
    body = models.TextField()
    # Texte montré au destinataire quand des coordonnées ont été masquées (mode `mask`) ; `body` reste l'original.
    body_masked = models.TextField(null=True, blank=True)
    flag_reason = models.CharField(max_length=24, null=True, blank=True)
    moderation_status = models.CharField(max_length=12, default="visible", db_default="visible")
    notified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_default=Now())

    class Meta:
        db_table = "messages"
        constraints = [
            models.UniqueConstraint(fields=["conversation", "seq"], name="messages_seq_unique"),
            models.UniqueConstraint(
                fields=["conversation", "sender", "client_msg_id"], name="messages_idempotence"
            ),
            models.CheckConstraint(
                condition=models.Q(kind__in=["text", "system"]), name="messages_type_valide"
            ),
            models.CheckConstraint(
                condition=models.Q(moderation_status__in=STATUTS_MODERATION),
                name="messages_moderation_valide",
            ),
        ]
        indexes = [
            models.Index(
                fields=["created_at"],
                condition=models.Q(notified_at__isnull=True),
                name="messages_non_notifies_idx",
            ),
        ]
