from django.urls import path

from . import views as v
from . import views_media as m
from . import views_publics as p
from . import views_tableau as t

urlpatterns = [
    path("districts", v.Quartiers.as_view(), name="districts"),
    path("room-types", v.TypesChambre.as_view(), name="room-types"),
    path("pro/room-types", v.TypesChambrePro.as_view(), name="pro-room-types"),
    path("pro/dashboard", t.Tableau.as_view(), name="pro-dashboard"),
    path("listings", p.Fil.as_view(), name="listings"),
    path("listings/<str:ident>", p.Fiche.as_view(), name="listing"),
    path("listings/<str:ident>/views", p.Vue.as_view(), name="listing-views"),
    path("me/favorites", p.Favoris.as_view(), name="favorites"),
    path("me/favorites/<uuid:annonce_id>", p.FavoriDetail.as_view(), name="favorite"),
    path("alert-options", p.OptionsAlerte.as_view(), name="alert-options"),
    path("me/alerts", p.Alertes.as_view(), name="alerts"),
    path("me/alerts/<str:alerte_id>", p.AlerteDetail.as_view(), name="alert"),
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
        "pro/listings/<uuid:annonce_id>/readiness",
        v.PreparationAnnonce.as_view(),
        name="pro-listing-readiness",
    ),
    path(
        "pro/listings/<uuid:annonce_id>/stats",
        v.StatistiquesAnnonce.as_view(),
        name="pro-listing-stats",
    ),
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
