"""Site d'administration : connexion par e-mail et mot de passe, titres en français."""

from django import forms
from django.contrib.admin import AdminSite
from django.contrib.auth.forms import AuthenticationForm
from django.db import models
from django.utils import timezone


class FormulaireConnexion(AuthenticationForm):
    """Adresse e-mail et mot de passe."""

    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": "Adresse e-mail ou mot de passe incorrect.",
    }

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request, *args, **kwargs)
        self.fields["username"] = forms.CharField(
            label="Adresse e-mail",
            max_length=254,
            widget=forms.TextInput(attrs={"autofocus": True, "autocomplete": "username"}),
        )


# Menu de l'administration : rubriques par fréquence d'usage (et non par ordre alphabétique), icône par rubrique.
ORDRE_RUBRIQUES = ["moderation", "accounts", "listings", "axes", "audit", "core", "billing"]
ORDRE_PAGES = {
    "moderation": ["Report", "ModerationAction"],
    "accounts": ["GerantProfile", "User"],
    "listings": ["Listing", "Review", "RoomType", "District"],
    "axes": ["AccessAttempt", "AccessFailureLog", "AccessLog"],
}
ICONES_RUBRIQUES = {
    "moderation": "flag",
    "accounts": "users",
    "listings": "house",
    "axes": "shield",
    "audit": "file",
    "core": "settings",
    "billing": "card",
}


class AdminLogeo(AdminSite):
    site_header = "Logeo — administration"
    site_title = "Logeo"
    index_title = "Tableau de bord"
    login_form = FormulaireConnexion

    def get_urls(self):
        from django.urls import path

        return [
            path("verification/", self.verification, name="verification"),
            path("erreurs/", self.admin_view(self.erreurs), name="erreurs"),
            path(
                "connexions-echouees/",
                self.admin_view(self.connexions_echouees),
                name="connexions-echouees",
            ),
            *super().get_urls(),
        ]

    def connexions_echouees(self, request):
        """Échecs de connexion des locataires et gérants (site et application) : axes ne voit que l'administration."""
        from django.core.exceptions import PermissionDenied
        from django.shortcuts import render

        from apps.audit.models import AuditLog

        if request.user.role != "admin":
            raise PermissionDenied
        lignes = AuditLog.objects.filter(
            action__in=["auth.connexion_echouee", "auth.compte_verrouille"]
        ).order_by("-created_at")[:300]
        contexte = {**self.each_context(request), "title": "Connexions échouées (site et application)",
                    "lignes": lignes}  # fmt: skip
        return render(request, "admin/connexions-echouees.html", contexte)

    def erreurs(self, request):
        """Suivi des erreurs (apps/core/erreurs.py) : liste regroupée, détail, « corrigée ». Administrateurs seulement."""
        from django.core.exceptions import PermissionDenied
        from django.shortcuts import redirect, render

        from apps.audit import services as audit
        from apps.core import erreurs

        if request.user.role != "admin":
            raise PermissionDenied
        if request.method == "POST" and request.POST.get("resoudre"):
            erreurs.resoudre(request.POST["resoudre"])
            audit.enregistrer("admin.erreur_resolue", acteur=request.user, cible_type="erreur")
            return redirect("/erreurs/")
        contexte = {
            **self.each_context(request),
            "title": "Erreurs",
            "erreurs": erreurs.liste(),
        }
        return render(request, "admin/erreurs.html", contexte)

    def verification(self, request):
        """Second temps de la connexion : le code reçu par courriel (adminsite/double_auth.py)."""
        from django.shortcuts import redirect, render
        from django.utils.http import url_has_allowed_host_and_scheme

        from . import double_auth

        suite = request.POST.get("next") or request.GET.get("next") or "/"
        if not url_has_allowed_host_and_scheme(suite, allowed_hosts={request.get_host()}):
            suite = "/"
        if not request.user.is_authenticated:
            return redirect("/login/")
        if not double_auth.en_attente(request):
            return redirect(suite)
        message, niveau = None, "info"
        if request.method == "POST":
            if "renvoyer" in request.POST:
                resultat = double_auth.renvoyer(request)
                message = {
                    "envoye": "Un nouveau code vient de partir.",
                    "attendre": "Patiente une minute avant de demander un nouveau code.",
                    "plafond": "Trop de renvois : reconnecte-toi pour recevoir un nouveau code.",
                }[resultat]
            else:
                resultat = double_auth.verifier(request, request.POST.get("code", ""))
                if resultat == "ok":
                    return redirect(suite)
                if resultat in ("bloque", "expire"):
                    return redirect("/login/?double_auth=" + resultat)
                message, niveau = "Code incorrect. Vérifie le dernier courriel reçu.", "erreur"
        contexte = {
            **self.each_context(request),
            "title": "Vérification en deux étapes",
            "courriel": double_auth.masquer_courriel(request.user.email),
            "message": message,
            "niveau": niveau,
            "next": suite,
        }
        return render(request, "admin/verification.html", contexte)

    def login(self, request, extra_context=None):
        """Explique pourquoi on revient à la connexion après un code bloqué ou expiré."""
        from django.contrib import messages

        textes = {
            "bloque": "Trop de codes incorrects : reconnecte-toi pour en recevoir un nouveau.",
            "expire": "Le code a expiré : reconnecte-toi pour en recevoir un nouveau.",
        }
        raison = request.GET.get("double_auth")
        if request.method == "GET" and raison in textes:
            messages.warning(request, textes[raison])
        return super().login(request, extra_context=extra_context)

    def get_app_list(self, request, app_label=None):
        rubriques = super().get_app_list(request, app_label)
        rang = {nom: i for i, nom in enumerate(ORDRE_RUBRIQUES)}
        rubriques.sort(key=lambda r: rang.get(r["app_label"], len(rang)))
        for r in rubriques:
            r["icone"] = ICONES_RUBRIQUES.get(r["app_label"], "tag")
            ordre = ORDRE_PAGES.get(r["app_label"])
            if ordre:
                r["models"].sort(
                    key=lambda m, o=ordre: (
                        o.index(m["object_name"]) if m["object_name"] in o else len(o)
                    )
                )
        return rubriques

    def index(self, request, extra_context=None):
        contexte = extra_context or {}
        if request.user.is_active and request.user.role in ("admin", "moderator"):
            contexte["vue_ensemble"] = _vue_ensemble(request.user)
        if request.user.is_active and request.user.role == "admin":
            from apps.core import erreurs

            contexte["erreurs_recentes"] = erreurs.liste(limite=5)
        return super().index(request, extra_context=contexte)


def _vue_ensemble(utilisateur) -> dict:
    """Indicateurs du tableau de bord d'administration, issus des données réelles."""
    from django.db.models import Count

    from apps.accounts.models import User
    from apps.audit.models import AuditLog
    from apps.core import stats
    from apps.listings.models import Listing
    from apps.moderation import services as moderation
    from apps.moderation.models import ModerationAction, Report

    tableau_moderation = moderation.tableau()
    ouvertes = Report.objects.filter(status__in=moderation.ETATS_OUVERTS)
    sanction_active = ModerationAction.objects.filter(
        revoked_at__isnull=True, ends_at__isnull=False, ends_at__gt=timezone.now()
    )
    uniquement_admin = utilisateur.role == "admin"
    return {
        "role": utilisateur.role,
        "moderation": tableau_moderation,
        "signalements_ouverts_par_motif": dict(
            ouvertes.values_list("reason_code").annotate(n=Count("id")).values_list(
                "reason_code", "n"
            )
        ),
        "sanctions_actives": sanction_active.count(),
        "annonces_publiees": Listing.objects.filter(status="published").count(),
        "taux_reponse": _taux_reponse_moyen(),
        "compteurs_jour": _compteurs_jour(stats),
        "audit_aujourdhui": (
            AuditLog.objects.filter(created_at__date=timezone.localdate()).count()
            if uniquement_admin
            else None
        ),
        "comptes_total": User.objects.filter(status="active").count(),
        "locataires_total": User.objects.filter(status="active", role="client").count(),
        "trafic": _trafic(),
        **_a_traiter(),
    }  # fmt: skip


def _a_traiter() -> dict:
    """Files de travail de l'équipe, en tête du tableau de bord."""
    from apps.accounts.models import GerantProfile
    from apps.core import parametres
    from apps.listings.models import Listing, RoomType

    return {
        "gerants_a_verifier": GerantProfile.complets.filter(
            verification_status__in=["pending", "interview"]
        ).count(),
        "gerants_total": GerantProfile.complets.count(),
        "types_proposes": RoomType.objects.filter(status="pending").count(),
        "annonces_en_relecture": Listing.objects.filter(status="processing").count(),
        "maintenance": bool(parametres.lire("MAINTENANCE_ENABLED")),
        "parametres_provisoires": bool(parametres.lire("LEGAL_PROVISIONAL")),
    }


JOURS_TRAFIC = 14
HAUTEUR_GRAPHE = 120  # unités du viewBox SVG


def _trafic() -> dict:
    """Provenance de l'audience : vues de fiches du site et de l'application (14 jours), appareils mobiles actifs."""
    import datetime

    from django.db.models import Count

    from apps.accounts.models import Device
    from apps.core import stats

    aujourdhui = timezone.localdate()
    depuis = aujourdhui - datetime.timedelta(days=JOURS_TRAFIC - 1)
    web = stats.serie(["views"], "canal:web", depuis=depuis)
    app = stats.serie(["views"], "canal:app", depuis=depuis)
    jours = []
    for i in range(JOURS_TRAFIC):
        jour = depuis + datetime.timedelta(days=i)
        jours.append(
            {
                "jour": jour,
                "web": web.get(jour, {}).get("views", 0),
                "app": app.get(jour, {}).get("views", 0),
            }
        )
    plus_haut = max((j["web"] + j["app"] for j in jours), default=0) or 1
    largeur = 100 / JOURS_TRAFIC
    for i, j in enumerate(jours):  # barres empilées : application en bas, site au-dessus
        h_app = round(j["app"] * HAUTEUR_GRAPHE / plus_haut, 1)
        h_web = round(j["web"] * HAUTEUR_GRAPHE / plus_haut, 1)
        j.update(
            x=round(i * largeur + largeur * 0.15, 2),
            largeur=round(largeur * 0.7, 2),
            y_app=round(HAUTEUR_GRAPHE - h_app, 1),
            h_app=h_app,
            y_web=round(HAUTEUR_GRAPHE - h_app - h_web, 1),
            h_web=h_web,
        )
    semaine = jours[-7:]
    total_web = sum(j["web"] for j in semaine)
    total_app = sum(j["app"] for j in semaine)
    total = total_web + total_app
    actifs = dict(
        Device.objects.filter(
            revoked_at__isnull=True,
            last_seen_at__gte=timezone.now() - datetime.timedelta(days=7),
        )
        .values_list("platform")
        .annotate(n=Count("id"))
        .values_list("platform", "n")
    )
    return {
        "jours": jours,
        "hauteur": HAUTEUR_GRAPHE,
        "jours_avec_vues": sum(1 for j in jours if j["web"] or j["app"]),
        "web_7j": total_web,
        "app_7j": total_app,
        "part_app": round(total_app * 100 / total) if total else None,
        "android": actifs.get("android", 0),
        "ios": actifs.get("ios", 0),
    }


def _taux_reponse_moyen():
    from apps.accounts.models import GerantProfile

    moy = GerantProfile.objects.filter(response_rate_30d__isnull=False).aggregate(
        m=models.Avg("response_rate_30d")
    )["m"]
    return round(moy) if moy is not None else None


def _compteurs_jour(stats):
    clefs = ["conversations_started", "messages", "reports_created"]
    return {c: stats.lire(c) for c in clefs}
