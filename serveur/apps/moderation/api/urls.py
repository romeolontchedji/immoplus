from django.urls import path

from . import views as v

urlpatterns = [
    path("reports", v.Signaler.as_view(), name="reports"),
    path(
        "listings/<uuid:annonce_id>/report-rented",
        v.SignalerDejaLouee.as_view(),
        name="report-rented",
    ),
]
