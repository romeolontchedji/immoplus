"""Signalements et actions de modération (CDC §9.16, §9.17)."""

import uuid

from django.db import models
from django.db.models.functions import Now
from django.utils import timezone

from .enums import (  # noqa: F401
    ACTIONS,
    CIBLES,
    ETATS,
    ETATS_OUVERTS,
    LIBELLES_ACTIONS,
    LIBELLES_CIBLES,
    LIBELLES_ETATS,
    LIBELLES_MOTIFS,
    LIBELLES_SOURCES,
    MOTIFS,
)


class Report(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reporter = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="signalé par",
    )
    source = models.CharField(
        max_length=10,
        default="user",
        db_default="user",
        verbose_name="origine",
        choices=list(LIBELLES_SOURCES.items()),
    )
    target_type = models.CharField(
        max_length=12, verbose_name="type de cible", choices=list(LIBELLES_CIBLES.items())
    )
    target_id = models.UUIDField(verbose_name="cible")
    listing = models.ForeignKey(
        "listings.Listing",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="annonce",
    )
    reason_code = models.CharField(
        max_length=24, verbose_name="motif", choices=list(LIBELLES_MOTIFS.items())
    )
    details = models.CharField(max_length=500, default="", blank=True, verbose_name="détails")
    status = models.CharField(
        max_length=18,
        default="open",
        db_default="open",
        verbose_name="statut",
        choices=list(LIBELLES_ETATS.items()),
    )
    assigned_to = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="assigné à",
    )
    resolved_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="traité par",
    )
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name="traité le")
    resolution_note = models.CharField(
        max_length=500, default="", blank=True, verbose_name="note de traitement"
    )
    created_at = models.DateTimeField(
        default=timezone.now, db_default=Now(), verbose_name="créé le"
    )

    def __str__(self) -> str:
        return f"{self.get_reason_code_display()} · {self.created_at:%d/%m/%Y}"

    class Meta:
        db_table = "reports"
        verbose_name = "signalement"
        verbose_name_plural = "signalements"
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
    actor = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="+", verbose_name="auteur"
    )
    report = models.ForeignKey(
        Report,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="actions",
        verbose_name="signalement",
    )
    action = models.CharField(
        max_length=20, verbose_name="action", choices=list(LIBELLES_ACTIONS.items())
    )
    target_user = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="compte visé",
    )
    target_listing = models.ForeignKey(
        "listings.Listing",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="annonce visée",
    )
    target_message = models.ForeignKey(
        "chat.Message",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="message visé",
    )
    ends_at = models.DateTimeField(null=True, blank=True, verbose_name="jusqu'au")
    revoked_at = models.DateTimeField(null=True, blank=True, verbose_name="levée le")
    revoked_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    reason = models.TextField(verbose_name="motif")
    created_at = models.DateTimeField(
        default=timezone.now, db_default=Now(), verbose_name="créé le"
    )

    def __str__(self) -> str:
        return f"{self.get_action_display()} · {self.created_at:%d/%m/%Y}"

    class Meta:
        db_table = "moderation_actions"
        verbose_name = "décision de modération"
        verbose_name_plural = "décisions de modération"
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
