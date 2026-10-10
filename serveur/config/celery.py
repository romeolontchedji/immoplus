"""Application Celery : une seule instance de `beat`, files `default`, `notifications`, `media`."""

import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

app = Celery("logeo")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Planning des tâches (une seule instance de `beat`). Heures du fuseau de l'application (Africa/Porto-Novo).
app.conf.beat_schedule = {
    "vues-vers-statistiques": {
        "task": "apps.listings.vider_vues",
        "schedule": crontab(minute="*/5"),
    },
    "rattrapage-notifications-messages": {
        "task": "apps.notifications.sweep_unnotified_messages",
        "schedule": crontab(minute="*"),
    },
    "rappel-gerants-sans-reponse": {
        "task": "apps.notifications.remind_unanswered_messages",
        "schedule": crontab(minute="*/30"),
    },
    "nettoyage-envois": {"task": "apps.media.nettoyer_envois", "schedule": crontab(minute=10)},
    "purge-medias": {"task": "apps.media.purger", "schedule": crontab(minute=20)},
    "fraicheur-annonces": {
        "task": "apps.listings.fraicheur",
        "schedule": crontab(minute=0, hour="*/6"),
    },
    "fin-des-suspensions": {
        "task": "apps.moderation.expirer_sanctions",
        "schedule": crontab(minute=5),
    },
    "conversations-lecture-seule": {
        "task": "apps.chat.lecture_seule",
        "schedule": crontab(minute=30, hour=2),
    },
    "archivage-annonces-louees": {
        "task": "apps.listings.archiver_louees",
        "schedule": crontab(minute=45, hour=2),
    },
    "indicateurs-gerants": {
        "task": "apps.accounts.indicateurs_gerants",
        "schedule": crontab(minute=0, hour=3),
    },
    "purge-otp": {"task": "apps.accounts.purger_otp", "schedule": crontab(minute=15, hour=3)},
    "retention-audit": {"task": "apps.audit.purger", "schedule": crontab(minute=30, hour=3)},
}
