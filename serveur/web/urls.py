"""Routes du site. Complétées phase par phase (CDC §10.9)."""

from django.conf import settings
from django.urls import path

from . import views
from . import views_auth as a
from . import views_pro as p
from . import views_public as pub

urlpatterns = [
    path("", views.accueil, name="accueil"),
    path("conditions", views.conditions, name="conditions"),
    path("confidentialite", views.confidentialite, name="confidentialite"),
    path("annonces", pub.annonces, name="annonces"),
    path("annonces/<slug:slug>", pub.fiche, name="fiche"),
    path("annonces/<slug:slug>/contacter", pub.contacter, name="contacter"),
    path("annonces/<slug:slug>/favori", pub.basculer_favori, name="favori"),
    path("annonces/<slug:slug>/signaler", pub.signaler, name="signaler"),
    path("quartiers/<slug:slug>", pub.quartier, name="quartier"),
    path("compte/favoris", pub.mes_favoris, name="favoris"),
    path("compte/alertes", pub.mes_alertes, name="alertes"),
    path("compte/messages", pub.mes_conversations, name="messages"),
    path("compte/messages/<str:conversation_id>", pub.conversation, name="conversation"),
    path("compte/notifications", pub.mes_notifications, name="notifications"),
    path("robots.txt", pub.robots, name="robots"),
    path("sitemap.xml", pub.sitemap, name="sitemap"),
    path("connexion", a.connexion, name="connexion"),
    path("deconnexion", a.deconnexion, name="deconnexion"),
    path("inscription", a.inscription_telephone, name="inscription"),
    path("inscription/code", a.inscription_code, name="inscription-code"),
    path("inscription/profil", a.inscription_profil, name="inscription-profil"),
    path("mot-de-passe-oublie", a.oubli_telephone, name="oubli"),
    path("mot-de-passe-oublie/code", a.oubli_code, name="oubli-code"),
    path("mot-de-passe-oublie/nouveau", a.oubli_nouveau, name="oubli-nouveau"),
    path("compte", a.espace_compte, name="compte"),
    path("compte/preferences", a.mes_preferences, name="preferences"),
    path("compte/appareils", a.mes_appareils, name="appareils"),
    path(
        "compte/appareils/<uuid:appareil_id>/revoquer",
        a.revoquer_appareil,
        name="appareil-revoquer",
    ),
    path("compte/numero", a.changement_numero_telephone, name="numero"),
    path("compte/numero/code", a.changement_numero_code, name="numero-code"),
    path("pro/dashboard", p.tableau_de_bord, name="pro-dashboard"),
    path("pro/annonces", p.liste, name="pro-annonces"),
    path("pro/annonces/nouvelle", p.editeur, name="pro-annonce-nouvelle"),
    path("pro/annonces/<uuid:annonce_id>", p.editeur, name="pro-annonce"),
]

if getattr(settings, "STYLEGUIDE_ENABLED", False):
    urlpatterns.append(path("styleguide", views.styleguide, name="styleguide"))
