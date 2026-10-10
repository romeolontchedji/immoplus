"""Administration : annonces (relecture), signalements, sanctions, lecture journalisée (CDC §7.9, EF-MOD)."""

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.urls import path, reverse

from apps.core.errors import ErreurMetier
from apps.listings.models import Listing
from apps.listings.services import annonces
from apps.moderation import services
from apps.moderation.models import ModerationAction, Report


def _exiger_personnel(request) -> None:
    if not (request.user.is_active and request.user.role in ("moderator", "admin")):
        raise PermissionDenied


def _signaler_erreur(modeladmin, request, erreur: ErreurMetier) -> None:
    modeladmin.message_user(request, erreur.message, level=messages.ERROR)


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "gerant",
        "status",
        "hidden_reason",
        "rent_amount",
        "district",
        "published_at",
    )
    list_filter = ("status", "hidden_reason", "district")
    search_fields = ("title", "slug", "gerant__full_name")
    ordering = ("-created_at",)
    actions = ["approuver", "refuser"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        # Les annonces en attente de relecture sont les premières de la liste.
        return super().get_queryset(request).select_related("gerant", "district")

    def get_fields(self, request, obj=None):
        # L'adresse précise et la description brute ne sont pas des champs d'examen : on les masque ici.
        return [
            "title", "status", "hidden_reason", "gerant", "district", "room_type", "rent_amount",
            "landmark_text", "available_from", "published_at", "last_confirmed_at", "rented_at", "created_at",
        ]  # fmt: skip

    def get_readonly_fields(self, request, obj=None):
        return self.get_fields(request, obj)

    @admin.action(description="Approuver et publier (première annonce)")
    def approuver(self, request, queryset):
        _exiger_personnel(request)
        faites = 0
        for annonce in queryset:
            try:
                annonces.approuver_premiere(annonce, acteur=request.user)
                faites += 1
            except ErreurMetier as erreur:
                self.message_user(
                    request, f"« {annonce.title} » : {erreur.message}", level=messages.WARNING
                )
        if faites:
            self.message_user(request, f"{faites} annonce(s) publiée(s).")

    @admin.action(description="Refuser (masquer par la modération)")
    def refuser(self, request, queryset):
        _exiger_personnel(request)
        faites = 0
        for annonce in queryset:
            try:
                annonces.refuser(annonce, acteur=request.user)
                faites += 1
            except ErreurMetier as erreur:
                self.message_user(
                    request, f"« {annonce.title} » : {erreur.message}", level=messages.WARNING
                )
        if faites:
            self.message_user(request, f"{faites} annonce(s) refusée(s).")


class LectureConversationForm(forms.Form):
    reason = forms.CharField(
        label="Motif de la lecture",
        min_length=services.MOTIF_MIN,
        max_length=200,
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Obligatoire avant l'ouverture ; conservé dans le journal d'activité.",
    )


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "source",
        "target_type",
        "reason_code",
        "status",
        "listing",
        "assigned_to",
    )
    list_filter = ("status", "reason_code", "source", "target_type")
    ordering = ("created_at",)
    actions = ["prendre", "classer"]
    readonly_fields = [
        "id", "reporter", "source", "target_type", "target_id", "listing", "reason_code", "details", "status",
        "assigned_to", "resolved_by", "resolved_at", "resolution_note", "created_at",
    ]  # fmt: skip

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        t = services.tableau()
        self.message_user(
            request,
            f"Dossiers ouverts : {t['ouverts']} (hors délai de 24 h : {t['hors_delai']}) · "
            f"délai médian de traitement sur 30 jours : "
            f"{'—' if t['delai_median_h'] is None else str(t['delai_median_h']) + ' h'}",
        )
        return super().changelist_view(request, extra_context)

    @admin.action(description="Prendre en charge")
    def prendre(self, request, queryset):
        _exiger_personnel(request)
        for rapport in queryset:
            try:
                services.prendre_en_charge(request.user, rapport)
            except ErreurMetier as erreur:
                _signaler_erreur(self, request, erreur)

    @admin.action(description="Classer sans suite")
    def classer(self, request, queryset):
        _exiger_personnel(request)
        for rapport in queryset:
            try:
                services.classer_sans_suite(
                    request.user, rapport, "Classé sans suite après examen du dossier."
                )
            except ErreurMetier as erreur:
                _signaler_erreur(self, request, erreur)

    def get_urls(self):
        return [
            path(
                "<uuid:rapport_id>/conversation/",
                self.admin_site.admin_view(self.lire_conversation),
                name="moderation_report_conversation",
            ),
            *super().get_urls(),
        ]

    def lire_conversation(self, request, rapport_id):
        """Ouvre la conversation liée au signalement, après saisie du motif (EF-MOD-03)."""
        _exiger_personnel(request)
        rapport = Report.objects.filter(pk=rapport_id).first()
        if rapport is None or rapport.target_type not in ("conversation", "message"):
            raise PermissionDenied
        conversation_id = rapport.target_id
        if rapport.target_type == "message":
            from apps.chat import selectors

            message = selectors.message_par_id(rapport.target_id)
            if message is None:
                raise PermissionDenied
            conversation_id = message.conversation_id
        formulaire = LectureConversationForm(request.POST or None)
        lecture = None
        if request.method == "POST" and formulaire.is_valid():
            try:
                lecture = services.lire_conversation(
                    request.user, conversation_id, formulaire.cleaned_data["reason"]
                )
            except ErreurMetier as erreur:
                formulaire.add_error(None, erreur.message)
        contexte = {
            **self.admin_site.each_context(request),
            "title": "Lecture d'une conversation",
            "form": formulaire,
            "messages_conversation": lecture["messages"] if lecture else None,
            "opts": self.model._meta,
        }
        return render(request, "admin/lecture-conversation.html", contexte)


class DecisionForm(forms.ModelForm):
    class Meta:
        model = ModerationAction
        fields = (
            "action",
            "report",
            "target_user",
            "target_listing",
            "target_message",
            "ends_at",
            "reason",
        )

    def clean(self):
        donnees = super().clean()
        return donnees


@admin.register(ModerationAction)
class ModerationActionAdmin(admin.ModelAdmin):
    """Le formulaire d'ajout EST l'outil de décision : il applique l'action, puis la journalise (EF-MOD-04)."""

    form = DecisionForm
    list_display = (
        "created_at",
        "action",
        "target_user",
        "target_listing",
        "actor",
        "ends_at",
        "revoked_at",
    )
    list_filter = ("action",)
    ordering = ("-created_at",)
    raw_id_fields = ("report", "target_user", "target_listing", "target_message")

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        _exiger_personnel(request)
        d = form.cleaned_data
        try:
            services.appliquer(
                request.user,
                d["action"],
                motif=d["reason"],
                rapport=d.get("report"),
                utilisateur=d.get("target_user"),
                annonce_id=d["target_listing"].pk if d.get("target_listing") else None,
                message_id=d["target_message"].pk if d.get("target_message") else None,
                jusqua=d.get("ends_at"),
            )
        except ErreurMetier as erreur:
            request._decision_refusee = True
            detail = " ".join(m for liste in erreur.champs.values() for m in liste)
            self.message_user(request, f"{erreur.message} {detail}".strip(), level=messages.ERROR)

    def log_addition(self, request, obj, message):
        if not getattr(request, "_decision_refusee", False):
            super().log_addition(request, obj, message)

    def response_add(self, request, obj, post_url_continue=None):
        if getattr(request, "_decision_refusee", False):
            return redirect(reverse("admin:moderation_moderationaction_add"))
        return super().response_add(request, obj, post_url_continue)
