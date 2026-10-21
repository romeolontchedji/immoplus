"""Centre de notifications, suivi de livraison et unicité (CDC §9.15)."""

import uuid

from django.db import models
from django.db.models.functions import Now
from django.utils import timezone


class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="+")
    kind = models.CharField(max_length=40)
    title = models.CharField(max_length=120)
    body = models.CharField(max_length=255)
    data = models.JSONField(default=dict, db_default={})
    dedupe_key = models.CharField(max_length=120, null=True, blank=True, unique=True)
    collapse_key = models.CharField(max_length=80, null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    delivery_status = models.CharField(max_length=10, default="pending", db_default="pending")
    delivery_attempts = models.SmallIntegerField(default=0, db_default=0)
    last_error = models.CharField(max_length=255, null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_default=Now())

    class Meta:
        db_table = "notifications"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    delivery_status__in=["pending", "sent", "partial", "failed", "skipped"]
                ),
                name="notifications_livraison_valide",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "-created_at"], name="notifications_liste_idx"),
            models.Index(
                fields=["user"],
                condition=models.Q(read_at__isnull=True),
                name="notifications_non_lues_idx",
            ),
        ]
