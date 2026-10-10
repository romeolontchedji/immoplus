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


class DailyStat(models.Model):
    """Compteurs agrégés par jour (CDC §9.10). Les compteurs par annonce viennent de Redis (UPSERT toutes les 5 min)."""

    pk = models.CompositePrimaryKey("day", "metric", "subject")
    day = models.DateField()
    metric = models.CharField(max_length=32)
    subject = models.CharField(max_length=40, default="global", db_default="global")
    value = models.IntegerField(default=0, db_default=0)

    class Meta:
        db_table = "daily_stats"
        indexes = [models.Index(fields=["subject", "day"], name="daily_stats_sujet_idx")]
