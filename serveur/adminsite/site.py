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
    "listings": ["Listing", "RoomType", "District"],
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
