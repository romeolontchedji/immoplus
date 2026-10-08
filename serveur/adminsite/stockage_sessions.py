from django.contrib.sessions.backends.db import SessionStore as SessionStoreBase


class SessionStore(SessionStoreBase):
    @classmethod
    def get_model_class(cls):
        from .models import AdminSession

        return AdminSession
