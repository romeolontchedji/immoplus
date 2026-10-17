"""Compteurs journaliers (CDC §9.10) : UPSERT dans `daily_stats`, jour au fuseau Africa/Porto-Novo."""

import datetime

from django.db import connection
from django.utils import timezone


def jour_courant() -> datetime.date:
    return timezone.localdate()


def incrementer(
    metrique: str, valeur: int = 1, *, sujet: str = "global", jour: datetime.date | None = None
) -> None:
    """Ajoute `valeur` au compteur (créé si absent). Idempotence : à la charge de l'appelant."""
    if not valeur:
        return
    with connection.cursor() as c:
        c.execute(
            "INSERT INTO daily_stats (day, metric, subject, value) VALUES (%s, %s, %s, %s) "
            "ON CONFLICT (day, metric, subject) DO UPDATE SET value = daily_stats.value + EXCLUDED.value",
            [jour or jour_courant(), metrique[:32], sujet[:40], valeur],
        )


def lire(metrique: str, *, sujet: str = "global", jour: datetime.date | None = None) -> int:
    with connection.cursor() as c:
        c.execute(
            "SELECT value FROM daily_stats WHERE day = %s AND metric = %s AND subject = %s",
            [jour or jour_courant(), metrique, sujet],
        )
        ligne = c.fetchone()
    return ligne[0] if ligne else 0


def somme(metrique: str, sujets: list[str], *, depuis: datetime.date) -> int:
    """Total d'un compteur pour plusieurs sujets depuis une date (tableau de bord du gérant)."""
    if not sujets:
        return 0
    with connection.cursor() as c:
        c.execute(
            "SELECT COALESCE(SUM(value), 0) FROM daily_stats WHERE metric = %s AND subject = ANY(%s) AND day >= %s",
            [metrique, sujets, depuis],
        )
        return int(c.fetchone()[0])


def serie(
    metriques: list[str], sujet: str, *, depuis: datetime.date
) -> dict[datetime.date, dict[str, int]]:
    """Valeurs jour par jour de plusieurs compteurs d'un même sujet (statistiques d'une annonce)."""
    with connection.cursor() as c:
        c.execute(
            "SELECT day, metric, value FROM daily_stats WHERE subject = %s AND metric = ANY(%s) AND day >= %s",
            [sujet, metriques, depuis],
        )
        resultat: dict[datetime.date, dict[str, int]] = {}
        for jour, metrique, valeur in c.fetchall():
            resultat.setdefault(jour, {})[metrique] = int(valeur)
    return resultat
