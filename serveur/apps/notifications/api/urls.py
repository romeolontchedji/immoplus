from django.urls import path

from . import views as v

urlpatterns = [
    path("notifications", v.Liste.as_view(), name="notifications"),
    path("notifications/unread-count", v.Compteur.as_view(), name="notifications-unread-count"),
    path("notifications/read-all", v.ToutLu.as_view(), name="notifications-read-all"),
    path("notifications/<uuid:notification_id>/read", v.Lue.as_view(), name="notification-read"),
]
