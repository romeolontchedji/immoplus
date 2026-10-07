"""Journal d'activité résistant à la modification (CDC §9.18)."""

from django.db import models
from django.db.models.functions import Now
from django.utils import timezone


class AuditLog(models.Model):
    """Lignes jamais modifiées ni supprimées par l'application (droits SQL et déclencheur, voir la migration)."""

    id = models.BigAutoField(primary_key=True)
    actor = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        db_column="actor_id",
    )
    actor_role = models.CharField(max_length=12, null=True, blank=True)
    action = models.CharField(max_length=64)
    target_type = models.CharField(max_length=32, null=True, blank=True)
    target_id = models.UUIDField(null=True, blank=True)
    metadata = models.JSONField(default=dict, db_default={})
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_default=Now())

    class Meta:
        db_table = "audit_logs"
        indexes = [
            models.Index(fields=["created_at"], name="audit_created_idx"),
            models.Index(fields=["actor", "created_at"], name="audit_actor_created_idx"),
            models.Index(fields=["target_type", "target_id"], name="audit_target_idx"),
        ]
