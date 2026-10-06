"""Application Celery : une seule instance de `beat`, files `default`, `notifications`, `media`."""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

app = Celery("logeo")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
