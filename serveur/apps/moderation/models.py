"""Signalements et actions de modération (CDC §9.16, §9.17)."""

import uuid

from django.db import models
from django.db.models.functions import Now
from django.utils import timezone

from .enums import ACTIONS, CIBLES, ETATS, ETATS_OUVERTS, MOTIFS  # noqa: F401


class Report(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reporter = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    source = models.CharField(max_length=10, default="user", db_default="user")
    target_type = models.CharField(max_length=12)
    target_id = models.UUIDField()
    listing = models.ForeignKey(
        "listings.Listing", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    reason_code = models.CharField(max_length=24)
    details = models.CharField(max_length=500, default="", blank=True)
    status = models.CharField(max_length=18, default="open", db_default="open")
    assigned_to = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    resolved_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_note = models.CharField(max_length=500, default="", blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_default=Now())

    class Meta:
        db_table = "reports"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(source__in=["user", "system"]), name="reports_source_valide"
            ),
            models.CheckConstraint(
                condition=models.Q(target_type__in=CIBLES), name="reports_cible_valide"
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=ETATS), name="reports_etat_valide"
            ),
            models.UniqueConstraint(
                fields=["reporter", "target_type", "target_id"],
                condition=models.Q(status__in=ETATS_OUVERTS, reporter__isnull=False),
                name="reports_un_ouvert_par_auteur_et_cible",
            ),
            models.UniqueConstraint(
                fields=["target_type", "target_id", "reason_code"],
                condition=models.Q(status__in=ETATS_OUVERTS, source="system"),
                name="reports_un_automatique_ouvert",
            ),
        ]
        indexes = [models.Index(fields=["status", "created_at"], name="reports_file_idx")]


class ModerationAction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="+")
    report = models.ForeignKey(
        Report, on_delete=models.SET_NULL, null=True, blank=True, related_name="actions"
    )
    action = models.CharField(max_length=20)
    target_user = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    target_listing = models.ForeignKey(
        "listings.Listing", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    target_message = models.ForeignKey(
        "chat.Message", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    ends_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    reason = models.TextField()
    created_at = models.DateTimeField(default=timezone.now, db_default=Now())

    class Meta:
        db_table = "moderation_actions"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(action__in=ACTIONS), name="moderation_action_valide"
            ),
            models.CheckConstraint(
                condition=models.Q(target_user__isnull=False)
                | models.Q(target_listing__isnull=False)
                | models.Q(target_message__isnull=False),
                name="moderation_au_moins_une_cible",
            ),
        ]
        indexes = [
            models.Index(fields=["target_user", "-created_at"], name="moderation_utilisateur_idx")
        ]
