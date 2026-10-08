from django.urls import path

from . import views as v
from . import views_media as m

urlpatterns = [
    path("districts", v.Quartiers.as_view(), name="districts"),
    path("pro/listings", v.AnnoncesPro.as_view(), name="pro-listings"),
    path("pro/listings/<uuid:annonce_id>", v.AnnonceProDetail.as_view(), name="pro-listing"),
    path(
        "pro/listings/<uuid:annonce_id>/publish",
        v.Publication.as_view(),
        name="pro-listing-publish",
    ),
    path(
        "pro/listings/<uuid:annonce_id>/confirm",
        v.Confirmation.as_view(),
        name="pro-listing-confirm",
    ),
    path("pro/listings/<uuid:annonce_id>/hide", v.Masquage.as_view(), name="pro-listing-hide"),
    path(
        "pro/listings/<uuid:annonce_id>/mark-rented",
        v.MarquerLouee.as_view(),
        name="pro-listing-rented",
    ),
    path(
        "pro/listings/<uuid:annonce_id>/undo-rented",
        v.AnnulerLouee.as_view(),
        name="pro-listing-undo-rented",
    ),
    path("pro/listings/<uuid:annonce_id>/media", m.MediasAnnonce.as_view(), name="pro-media"),
    path(
        "pro/listings/<uuid:annonce_id>/media/order",
        m.OrdreMedias.as_view(),
        name="pro-media-order",
    ),
    path(
        "pro/listings/<uuid:annonce_id>/media/<uuid:media_id>",
        m.MediaDetail.as_view(),
        name="pro-media-detail",
    ),
    path("pro/markdown/preview", v.ApercuMarkdown.as_view(), name="pro-markdown-preview"),
]
