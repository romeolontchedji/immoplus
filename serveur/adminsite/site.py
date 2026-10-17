"""Site d'administration : connexion par e-mail et mot de passe, titres en français."""

from django import forms
from django.contrib.admin import AdminSite
from django.contrib.auth.forms import AuthenticationForm
from django.db import models
from django.utils import timezone


class FormulaireConnexion(AuthenticationForm):
    """Adresse e-mail et mot de passe."""

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request, *args, **kwargs)
        self.fields["username"] = forms.CharField(
            label="Adresse e-mail",
            max_length=254,
            widget=forms.TextInput(attrs={"autofocus": True, "autocomplete": "username"}),
        )


class AdminLogeo(AdminSite):
    site_header = "Logeo — administration"
    site_title = "Logeo"
    index_title = "Tableau de bord"
    login_form = FormulaireConnexion

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


def _taux_reponse_moyen():
    from apps.accounts.models import GerantProfile

    moy = GerantProfile.objects.filter(response_rate_30d__isnull=False).aggregate(
        m=models.Avg("response_rate_30d")
    )["m"]
    return round(moy) if moy is not None else None


def _compteurs_jour(stats):
    clefs = ["conversations_started", "messages", "reports_created"]
    return {c: stats.lire(c) for c in clefs}
