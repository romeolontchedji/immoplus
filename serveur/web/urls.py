"""Routes du site. Complétées phase par phase (CDC §10.9)."""

from django.conf import settings
from django.urls import path

from . import views
from . import views_auth as a
from . import views_equipe as equipe_vue
from . import views_paiement as paiement
from . import views_pro as p
from . import views_suppression as suppression
from . import views_public as pub

urlpatterns = [
    path("", views.accueil, name="accueil"),
    path("conditions", views.conditions, name="conditions"),
    path("confidentialite", views.confidentialite, name="confidentialite"),
    path("annonces", pub.annonces, name="annonces"),
    path("annonces/<slug:slug>", pub.fiche, name="fiche"),
    path("annonces/<slug:slug>/apercu.jpg", pub.apercu_partage, name="apercu-partage"),
    path("annonces/<slug:slug>/contacter", pub.contacter, name="contacter"),
    path("annonces/<slug:slug>/favori", pub.basculer_favori, name="favori"),
    path("annonces/<slug:slug>/signaler", pub.signaler, name="signaler"),
    path("annonces/<slug:slug>/avis", pub.donner_avis, name="avis"),
    path("gerants/<uuid:gerant_id>", pub.profil_gerant, name="profil-gerant"),
    path("quartiers/<slug:slug>", pub.quartier, name="quartier"),
    path("pres-de-l-universite", pub.pres_universite, name="pres-universite"),
    path("compte/favoris", pub.mes_favoris, name="favoris"),
    path("compte/alertes", pub.mes_alertes, name="alertes"),
    path("compte/messages", pub.mes_conversations, name="messages"),
    path("compte/messages/<str:conversation_id>", pub.conversation, name="conversation"),
    path("compte/notifications", pub.mes_notifications, name="notifications"),
    path("compte/notifications/<str:notification_id>/ouvrir", pub.ouvrir_notification, name="notification_ouvrir"),
    path("compte/equipe", equipe_vue.fil_equipe, name="equipe"),
    path("robots.txt", pub.robots, name="robots"),
    path("sitemap.xml", pub.sitemap, name="sitemap"),
    path("connexion", a.connexion, name="connexion"),
    path("deconnexion", a.deconnexion, name="deconnexion"),
    path("inscription", a.inscription_page, name="inscription"),
    path("mot-de-passe-oublie", a.oubli, name="oubli"),
    path("mot-de-passe-oublie/cle", a.oubli_cle, name="oubli-cle"),
    path("mot-de-passe/nouveau/<str:jeton>", a.nouveau_mot_de_passe, name="mot-de-passe-nouveau"),
    path("activer/<str:jeton>", a.activer_gerant, name="activer-gerant"),
    path("compte/cle-de-secours", a.cle_de_secours, name="cle-de-secours"),
    path("compte/email/confirmer/<str:jeton>", a.confirmer_email, name="email-confirmer"),
    path("compte", a.espace_compte, name="compte"),
    path("compte/profil", a.mon_profil, name="profil"),
    path("compte/supprimer", suppression.supprimer_mon_compte, name="compte-supprimer"),
    path("compte/preferences", a.mes_preferences, name="preferences"),
    path("compte/appareils", a.mes_appareils, name="appareils"),
    path(
        "compte/appareils/<uuid:appareil_id>/revoquer",
        a.revoquer_appareil,
        name="appareil-revoquer",
    ),
    path("paiement/preparer", paiement.preparer, name="paiement-preparer"),
    path("paiement/confirmer", paiement.confirmer, name="paiement-confirmer"),
    path("paiement/webhook/kkiapay", paiement.webhook, name="paiement-webhook-kkiapay"),
    path("compte/abonnement", paiement.abonnement, name="abonnement"),
    path("pro/abonnement", paiement.abonnement, name="pro-abonnement"),
    path("pro/dashboard", p.tableau_de_bord, name="pro-dashboard"),
    path("pro/avis", p.avis_recus, name="pro-avis"),
    path("pro/annonces", p.liste, name="pro-annonces"),
    path("pro/annonces/nouvelle", p.editeur, name="pro-annonce-nouvelle"),
    path("pro/annonces/<uuid:annonce_id>", p.editeur, name="pro-annonce"),
]

if settings.DEBUG and getattr(settings, "DEV_INBOX_ENABLED", False):
    urlpatterns.append(path("dev/boite", views.boite_dev, name="boite-dev"))

if getattr(settings, "STYLEGUIDE_ENABLED", False):
    urlpatterns.append(path("styleguide", views.styleguide, name="styleguide"))
