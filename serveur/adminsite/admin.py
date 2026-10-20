"""Enregistrements de l'administration : comptes, gérants, paramètres, journal (CDC §7, EF-ADM)."""

from django import forms
from django.contrib import admin, messages
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied

from apps.accounts.models import GerantProfile, User
from apps.accounts.services import administration
from apps.audit import services as audit
from apps.audit.models import AuditLog
from apps.core import parametres
from apps.core.errors import ErreurMetier
from apps.core.models import AppSetting


class LectureSeule(admin.ModelAdmin):
    """Aucune création, modification ni suppression depuis l'administration."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AuditLog)
class AuditLogAdmin(LectureSeule):
    list_display = ("created_at", "action", "actor", "actor_role", "target_type", "ip")
    list_filter = ("action", "actor_role")
    search_fields = ("action", "target_id")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)

    def has_view_permission(self, request, obj=None):
        return request.user.is_active and request.user.role == "admin"


class NouveauGerantForm(forms.Form):
    """Sans mot de passe (ADR 0009) : le gérant choisit ses identifiants par le lien d'activation."""

    first_name = forms.CharField(label="Prénom", max_length=60)
    last_name = forms.CharField(label="Nom", max_length=60)
    phone = forms.CharField(label="Numéro de téléphone", max_length=40)
    display_name = forms.CharField(label="Nom affiché", max_length=120, required=False)
    zone = forms.CharField(label="Zone d'activité", max_length=160)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("full_name", "username", "role", "status", "phone_e164", "email", "created_at")
    list_filter = ("role", "status")
    search_fields = ("username", "full_name", "first_name", "last_name", "phone_e164", "email")
    ordering = ("-created_at",)
    readonly_fields = (
        "id", "username", "full_name", "phone_e164", "email", "email_verified_at", "recovery_key_created_at", "role",
        "token_version", "terms_version", "terms_accepted_at", "last_seen_at", "deleted_at", "created_at",
        "updated_at", "avatar_path", "liens_compte",
    )  # fmt: skip
    fields = (
        "id", "username", "first_name", "last_name", "full_name", "liens_compte", "role", "status",
        "suspended_until", "phone_e164", "email", "email_verified_at", "recovery_key_created_at", "token_version",
        "terms_version", "terms_accepted_at", "last_seen_at", "deleted_at", "created_at", "updated_at",
        "avatar_path",
    )  # fmt: skip

    @admin.display(description="Accès au compte")
    def liens_compte(self, obj):
        """Lien d'activation (gérant pas encore activé) ou de réinitialisation (mot de passe oublié, ADR 0009)."""
        from django.urls import reverse
        from django.utils.html import format_html

        if obj is None or obj.role not in ("client", "gerant"):
            return "—"
        if obj.role == "gerant" and not obj.has_usable_password():
            url, texte = (
                reverse("admin:accounts_user_lien", args=[obj.pk, "activation"]),
                "Générer un lien d'activation",
            )
        else:
            url, texte = (
                reverse("admin:accounts_user_lien", args=[obj.pk, "reinitialisation"]),
                "Générer un lien de réinitialisation (après vérification de l'identité)",
            )
        return format_html('<a class="button" href="{}">{}</a>', url, texte)

    actions = ["suspendre", "reactiver", "bannir"]

    def has_add_permission(self, request):
        return False  # les comptes se créent par l'API (locataires), « Nouveau gérant » ou la commande (personnel)

    def get_urls(self):
        from django.urls import path

        return [path("nouveau-gerant/", self.admin_site.admin_view(self.nouveau_gerant), name="accounts_user_nouveau_gerant"),
                path("<uuid:user_id>/lien/<str:objet>/", self.admin_site.admin_view(self.lien), name="accounts_user_lien"),
                *super().get_urls()]  # fmt: skip

    def _page_lien(self, request, compte, objet: str, url: str):
        from urllib.parse import quote

        from django.shortcuts import render

        activation = objet == "activation"
        texte = (
            f"Bonjour {compte.first_name}, voici le lien pour activer ton compte gérant Immo+ "
            f"(valable 72 heures, une seule fois) : {url}"
            if activation
            else f"Bonjour {compte.first_name}, voici le lien pour choisir un nouveau mot de passe Immo+ "
            f"(valable 24 heures, une seule fois) : {url}"
        )
        numero = (compte.phone_e164 or "").lstrip("+")
        contexte = {
            **self.admin_site.each_context(request),
            "title": "Lien d'activation" if activation else "Lien de réinitialisation",
            "compte": compte, "url": url, "activation": activation, "opts": self.model._meta,
            "whatsapp": f"https://wa.me/{numero}?text={quote(texte)}" if numero.isdigit() else None,
        }  # fmt: skip
        return render(request, "admin/lien-compte.html", contexte)

    def lien(self, request, user_id, objet):
        """Génère et affiche un lien d'activation ou de réinitialisation, à transmettre par WhatsApp ou e-mail."""
        from django.http import Http404

        if not (request.user.is_active and request.user.role == "admin"):
            raise PermissionDenied
        compte = User.objects.filter(pk=user_id, deleted_at__isnull=True).first()
        if compte is None or objet not in ("activation", "reinitialisation"):
            raise Http404
        try:
            url = (
                administration.lien_activation(acteur=request.user, gerant=compte)
                if objet == "activation"
                else administration.lien_reinitialisation(acteur=request.user, cible=compte)
            )
        except ErreurMetier as erreur:
            self.message_user(request, erreur.message, level=messages.ERROR)
            from django.shortcuts import redirect

            return redirect("admin:accounts_user_change", compte.pk)
        return self._page_lien(request, compte, objet, url)

    def nouveau_gerant(self, request):
        """Crée un compte gérant sans mot de passe, puis affiche son lien d'activation (ADR 0009)."""
        from django.shortcuts import render

        if not (request.user.is_active and request.user.role == "admin"):
            raise PermissionDenied
        formulaire = NouveauGerantForm(request.POST or None)
        if request.method == "POST" and formulaire.is_valid():
            d = formulaire.cleaned_data
            try:
                gerant = administration.creer_gerant(
                    acteur=request.user,
                    telephone=d["phone"],
                    prenom=d["first_name"],
                    nom=d["last_name"],
                    zone=d["zone"],
                    nom_affiche=d["display_name"],
                )
            except ErreurMetier as erreur:
                for champ, messages_champ in erreur.champs.items():
                    for m in messages_champ:
                        formulaire.add_error(champ if champ in formulaire.fields else None, m)
                if not erreur.champs:
                    formulaire.add_error(None, erreur.message)
            else:
                url = administration.lien_activation(acteur=request.user, gerant=gerant)
                return self._page_lien(request, gerant, "activation", url)
        contexte = {
            **self.admin_site.each_context(request),
            "title": "Nouveau gérant",
            "form": formulaire,
            "opts": self.model._meta,
        }
        return render(request, "admin/nouveau-gerant.html", contexte)

    def has_delete_permission(self, request, obj=None):
        return False  # un compte s'anonymise, il ne se supprime pas

    def has_change_permission(self, request, obj=None):
        return request.user.is_active and request.user.role == "admin"

    def has_view_permission(self, request, obj=None):
        return request.user.is_active and request.user.role == "admin"

    def save_model(self, request, obj, form, change):
        if "status" in form.changed_data or "suspended_until" in form.changed_data:
            administration.changer_statut(
                acteur=request.user,
                cible=obj,
                statut=obj.status,
                jusqu_a=obj.suspended_until,
                motif="administration",
            )
        else:
            obj.save()
            audit.enregistrer(
                "compte.modifie",
                acteur=request.user,
                cible=obj,
                metadata={"champs": form.changed_data},
            )

    def _appliquer(self, request, queryset, statut):
        faits = 0
        for cible in queryset:
            try:
                administration.changer_statut(
                    acteur=request.user, cible=cible, statut=statut, motif="action groupée"
                )
                faits += 1
            except ErreurMetier as erreur:
                self.message_user(request, f"{cible} : {erreur.message}", messages.ERROR)
        self.message_user(request, f"{faits} compte(s) mis à jour.")

    @admin.action(description="Suspendre (jusqu'à levée manuelle)")
    def suspendre(self, request, queryset):
        from django.utils import timezone

        for cible in queryset:
            try:
                administration.changer_statut(
                    acteur=request.user, cible=cible, statut="suspended",
                    jusqu_a=timezone.now() + timezone.timedelta(days=7), motif="action groupée",
                )  # fmt: skip
            except ErreurMetier as erreur:
                self.message_user(request, f"{cible} : {erreur.message}", messages.ERROR)
        self.message_user(request, "Suspension de 7 jours appliquée.")

    @admin.action(description="Réactiver")
    def reactiver(self, request, queryset):
        self._appliquer(request, queryset, "active")

    @admin.action(description="Bannir")
    def bannir(self, request, queryset):
        self._appliquer(request, queryset, "banned")


@admin.register(GerantProfile)
class GerantProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "zone", "verification_status", "verified_at", "created_at")
    list_filter = ("verification_status",)
    search_fields = ("user__full_name", "zone", "display_name")
    readonly_fields = (
        "user",
        "verified_at",
        "verified_by",
        "created_by",
        "created_at",
        "updated_at",
    )

    def get_queryset(self, request):
        return GerantProfile.complets.select_related(
            "user"
        )  # l'administration lit toutes les colonnes

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_fields(self, request, obj=None):
        champs = [
            "user",
            "display_name",
            "zone",
            "verification_status",
            "verified_at",
            "verified_by",
            "created_by",
        ]
        if request.user.role == "admin":  # pièces et notes : administrateurs seulement
            champs += [
                "interview_notes",
                "id_doc_type",
                "id_doc_path",
                "extra_doc_path",
                "docs_retain_until",
            ]
        return champs

    def has_change_permission(self, request, obj=None):
        return request.user.is_active and request.user.role == "admin"

    def save_model(self, request, obj, form, change):
        if "verification_status" in form.changed_data:
            administration.definir_verification(
                acteur=request.user, profil=obj, statut=obj.verification_status
            )
        else:
            obj.save()
            audit.enregistrer(
                "gerant.modifie",
                acteur=request.user,
                cible=obj.user,
                metadata={"champs": form.changed_data},
            )


@admin.register(AppSetting)
class AppSettingAdmin(admin.ModelAdmin):
    list_display = ("key", "value", "description", "updated_at")
    readonly_fields = ("key", "description", "updated_by", "updated_at")
    fields = ("key", "value", "description", "updated_by", "updated_at")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_urls(self):
        from django.urls import path

        return [
            path(
                "",
                self.admin_site.admin_view(self.page_parametres),
                name="core_appsetting_changelist",
            ),
            *super().get_urls(),
        ]

    def page_parametres(self, request):
        """Réglages rangés par thème (adminsite/parametres_page.py) ; une section s'enregistre à la fois."""
        from django.shortcuts import redirect, render

        from .parametres_page import SectionForm, sections

        if not self.has_view_permission(request):
            raise PermissionDenied
        modifiable = self.has_change_permission(request)
        cible = request.POST.get("section") if request.method == "POST" else None
        blocs = []
        for code, titre, aide, cles in sections():
            form = SectionForm(cles, request.POST if code == cible else None, prefix=code)
            if code == cible and modifiable and form.is_valid():
                changements = form.changements()
                for cle, (avant, apres) in changements.items():
                    parametres.definir(cle, apres, par=request.user)
                    audit.enregistrer(
                        "parametre.modifie", acteur=request.user, cible_type="parametre",
                        metadata={"cle": cle, "avant": avant, "apres": apres},
                    )  # fmt: skip
                self.message_user(
                    request,
                    f"{titre} : {len(changements)} réglage(s) enregistré(s)."
                    if changements
                    else f"{titre} : aucun changement.",
                )
                return redirect(f"{request.path}#{code}")
            blocs.append({"code": code, "titre": titre, "aide": aide, "form": form})
        contexte = {
            **self.admin_site.each_context(request),
            "title": "Paramètres",
            "blocs": blocs,
            "modifiable": modifiable,
            "opts": self.model._meta,
        }
        return render(request, "admin/parametres.html", contexte)

    def save_model(self, request, obj, form, change):
        if obj.key not in parametres.DEFAUTS:
            raise PermissionDenied
        parametres.definir(obj.key, obj.value, par=request.user)
        audit.enregistrer(
            "parametre.modifie",
            acteur=request.user,
            cible_type="parametre",
            metadata={"cle": obj.key},
        )


from apps.billing.models import Payment, Subscription  # noqa: E402


@admin.register(Subscription)
class SubscriptionAdmin(LectureSeule):
    """Abonnements (inactifs en V1 : plan Gratuit V1 pour chaque gérant vérifié)."""

    list_display = ("gerant", "plan_code", "status", "current_period_end", "cancel_at_period_end")
    list_filter = ("status", "plan_code")


@admin.register(Payment)
class PaymentAdmin(LectureSeule):
    list_display = ("created_at", "gerant", "plan_code", "amount", "provider", "status")
    list_filter = ("status", "provider")
    exclude = ("payer_phone_e164",)  # numéro du payeur jamais affiché en liste ni en détail


from . import admin_moderation, admin_referentiels  # noqa: E402,F401  (modération, quartiers)

# Les droits du personnel viennent du rôle (apps/accounts/permissions_personnel.py) : les groupes ne servent à rien.
if admin.site.is_registered(Group):
    admin.site.unregister(Group)

# Connexions réussies : axes enregistre l'identifiant interne du compte ; on affiche le nom et l'e-mail à la place.
try:
    from axes.admin import AccessLogAdmin as _AccessLogAdmin
    from axes.models import AccessLog
except ImportError:  # pragma: no cover - axes absent (site public)
    AccessLog = None

if AccessLog is not None and admin.site.is_registered(AccessLog):
    admin.site.unregister(AccessLog)

    @admin.register(AccessLog)
    class AccessLogAdmin(_AccessLogAdmin):
        list_display = ("attempt_time", "compte", "ip_address", "logout_time", "user_agent")

        @admin.display(description="Compte", ordering="username")
        def compte(self, obj):
            utilisateur = (
                User.objects.filter(pk=obj.username).first() if _uuid(obj.username) else None
            )
            if utilisateur is None:
                return obj.username
            return f"{utilisateur.full_name or 'Sans nom'} · {utilisateur.email or utilisateur.phone_e164}"


def _uuid(valeur) -> bool:
    import uuid

    try:
        uuid.UUID(str(valeur))
    except ValueError:
        return False
    return True
