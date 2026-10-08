"""Paramètres modifiables sans redéploiement (CDC §9.19)."""

from django.db import models
from django.db.models.functions import Now
from django.utils import timezone


class AppSetting(models.Model):
    key = models.CharField(max_length=64, primary_key=True)
    value = models.JSONField()
    description = models.CharField(max_length=255)
    updated_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        db_column="updated_by",
    )
    updated_at = models.DateTimeField(default=timezone.now, db_default=Now())

    class Meta:
        db_table = "app_settings"
