"""Routes du site. Complétées phase par phase (CDC §10.9)."""

from django.conf import settings
from django.urls import path

from . import views
from . import views_auth as a
from . import views_pro as p

urlpatterns = [
    path("", views.accueil, name="accueil"),
    path("connexion", a.connexion, name="connexion"),
    path("deconnexion", a.deconnexion, name="deconnexion"),
    path("inscription", a.inscription_telephone, name="inscription"),
    path("inscription/code", a.inscription_code, name="inscription-code"),
    path("inscription/profil", a.inscription_profil, name="inscription-profil"),
    path("mot-de-passe-oublie", a.oubli_telephone, name="oubli"),
    path("mot-de-passe-oublie/code", a.oubli_code, name="oubli-code"),
    path("mot-de-passe-oublie/nouveau", a.oubli_nouveau, name="oubli-nouveau"),
    path("compte", a.espace_compte, name="compte"),
    path("pro/annonces", p.liste, name="pro-annonces"),
    path("pro/annonces/nouvelle", p.editeur, name="pro-annonce-nouvelle"),
    path("pro/annonces/<uuid:annonce_id>", p.editeur, name="pro-annonce"),
]

if getattr(settings, "STYLEGUIDE_ENABLED", False):
    urlpatterns.append(path("styleguide", views.styleguide, name="styleguide"))
