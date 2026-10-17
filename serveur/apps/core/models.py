"""Paramètres modifiables sans redéploiement (CDC §9.19)."""

from django.db import models
from django.db.models.functions import Now
from django.utils import timezone


class AppSetting(models.Model):
    key = models.CharField(max_length=64, primary_key=True, verbose_name="clé")
    value = models.JSONField(verbose_name="valeur")
    description = models.CharField(max_length=255, verbose_name="description")
    updated_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        db_column="updated_by",
        verbose_name="modifié par",
    )
    updated_at = models.DateTimeField(
        default=timezone.now, db_default=Now(), verbose_name="modifié le"
    )

    def __str__(self) -> str:
        return self.key

    class Meta:
        db_table = "app_settings"
        verbose_name = "paramètre"
        verbose_name_plural = "paramètres"


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
