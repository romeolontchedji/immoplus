"""Sessions de l'administration : table distincte de celle du site, illisible pour le rôle PostgreSQL `app`."""

from django.contrib.sessions.base_session import AbstractBaseSession
from django.db import models


class AdminSession(AbstractBaseSession):
    session_key = models.CharField(max_length=40, primary_key=True)

    class Meta:
        db_table = "admin_sessions"

    @classmethod
    def get_session_store_class(cls):
        from .stockage_sessions import SessionStore

        return SessionStore
