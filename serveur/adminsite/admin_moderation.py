"""Administration : annonces (modération après coup), signalements, sanctions, lecture journalisée (CDC §7.9, EF-MOD)."""

from django import forms
from django.contrib import admin, messages
from django.contrib.admin import helpers
from django.core.exceptions import PermissionDenied
from django.db.models import F
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils.html import format_html, format_html_join

from apps.accounts.models import User
from apps.audit import services as audit
from apps.chat.models import Conversation, Message
from apps.core.errors import ErreurMetier
from apps.listings import selectors as listing_selectors
from apps.listings.enums import StatutTypeChambre
from apps.listings.models import Listing, RoomType
from apps.listings.services import annonces, contenu
from apps.listings.services import types as types_chambre
from apps.moderation import services
from apps.moderation.models import ModerationAction, Report


def _exiger_admin(request) -> None:
    if not (request.user.is_active and request.user.role == "admin"):
        raise PermissionDenied


def _exiger_personnel(request) -> None:
    if not (request.user.is_active and request.user.role in ("moderator", "admin")):
        raise PermissionDenied


def _personne_visee(rapport: Report) -> User | None:
    """Compte visé par le signalement, quelle que soit la cible : le compte, l'auteur du message, le gérant de
    l'annonce, ou l'autre participant de la conversation."""
    if rapport.target_type == "user":
        return User.objects.filter(pk=rapport.target_id).first()
    if rapport.target_type == "message":
        message = Message.objects.select_related("sender").filter(pk=rapport.target_id).first()
        return message.sender if message else None
    if rapport.target_type == "listing":
        annonce = (
            Listing.objects.select_related("gerant__user").filter(pk=rapport.target_id).first()
        )
        return (
            annonce.gerant.user if annonce else None
        )  # `gerant` est le profil, le compte est dessous
    if rapport.target_type == "conversation":
        c = (
            Conversation.objects.select_related("client", "gerant")
            .filter(pk=rapport.target_id)
            .first()
        )
        if c is None:
            return None
        return c.gerant if rapport.reporter_id == c.client_id else c.client
    return None


def _compte(utilisateur: User | None):
    """Nom (lien vers la fiche du compte) et nom d'utilisateur, sur deux lignes."""
    if utilisateur is None:
        return "—"
    return format_html(
        '<a href="{}"><strong>{}</strong></a><br><span class="lg-discret">{}</span>',
        reverse("admin:accounts_user_change", args=[utilisateur.pk]),
        utilisateur.full_name or "Sans nom",
        f"@{utilisateur.username}" if utilisateur.username else (utilisateur.email or ""),
    )


def _signaler_erreur(modeladmin, request, erreur: ErreurMetier) -> None:
    modeladmin.message_user(request, erreur.message, level=messages.ERROR)


class AnnonceEquipeForm(forms.ModelForm):
    """Correction d'une annonce par un administrateur : mêmes règles que pour un gérant (pas de coordonnées)."""

    class Meta:
        model = Listing
        fields = ["title", "rent_amount", "landmark_text", "available_from", "district"]

    def clean(self):
        donnees = super().clean()
        try:
            contenu.refuser_si_coordonnees(
                title=str(donnees.get("title") or ""), landmark_text=str(donnees.get("landmark_text") or "")
            )
        except ErreurMetier as erreur:
            raise forms.ValidationError(erreur.message) from erreur
        return donnees


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
    list_filter = (("published_at", admin.DateFieldListFilter), "status", "hidden_reason", "district")
    search_fields = ("title", "slug", "gerant__full_name")
    # Les dernières mises en ligne d'abord (les brouillons, sans date, à la fin).
    ordering = (F("published_at").desc(nulls_last=True), "-created_at")
    actions = [
        "masquer_annonces", "retirer_annonces", "remettre_en_ligne", "retablir_retiree",
        "marquer_louee_equipe", "supprimer_annonces", "approuver", "refuser",
    ]  # fmt: skip

    def has_add_permission(self, request):
        return False

    # Un administrateur corrige le titre, le loyer, le repère, la date ou le quartier ; le reste se décide par les actions.
    CHAMPS_MODIFIABLES = ("title", "rent_amount", "landmark_text", "available_from", "district")

    def has_change_permission(self, request, obj=None):
        return request.user.is_active and request.user.role == "admin"

    def has_delete_permission(self, request, obj=None):
        return False  # une annonce ne s'efface pas : elle se retire ou se supprime (archivage) par les actions

    def get_form(self, request, obj=None, **kwargs):
        kwargs["form"] = AnnonceEquipeForm
        kwargs["fields"] = list(self.CHAMPS_MODIFIABLES)
        return super().get_form(request, obj, **kwargs)

    def save_model(self, request, obj, form, change):
        _exiger_admin(request)
        obj.save(update_fields=[*form.changed_data, "updated_at"])
        listing_selectors.invalider_fil()
        audit.enregistrer(
            "listing.modifiee_par_equipe", acteur=request.user, cible=obj,
            metadata={"champs": sorted(form.changed_data)},
        )  # fmt: skip

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("gerant", "district")

    def get_fields(self, request, obj=None):
        # L'adresse précise et la description brute ne sont pas des champs d'examen : on les masque ici.
        return [
            "title", "status", "hidden_reason", "gerant", "district", "type_de_logement", "rent_amount",
            "landmark_text", "available_from", "published_at", "last_confirmed_at", "rented_at", "created_at",
        ]  # fmt: skip

    def get_readonly_fields(self, request, obj=None):
        champs = self.get_fields(request, obj)
        if request.user.is_active and request.user.role == "admin":
            return [c for c in champs if c not in self.CHAMPS_MODIFIABLES]
        return champs

    @admin.display(description="Type de logement")
    def type_de_logement(self, obj):
        return types_chambre.libelle(obj.room_type)

    def _decider(self, request, queryset, *, action, titre, explication, etats, defaut):
        """Page de confirmation avec le motif (obligatoire, vu par le gérant), puis une décision par annonce."""
        from django.template.response import TemplateResponse

        _exiger_personnel(request)
        if request.POST.get("confirmer") != "oui":
            return TemplateResponse(
                request,
                "admin/decision-annonce.html",
                {
                    **self.admin_site.each_context(request),
                    "title": titre,
                    "opts": self.model._meta,
                    "annonces": list(queryset),
                    "action": action,
                    "explication": explication,
                    "motif_min": services.MOTIF_MIN,
                    "ids": request.POST.getlist(helpers.ACTION_CHECKBOX_NAME),
                    "motif": "",
                },
            )
        motif = request.POST.get("motif", "")
        faites = 0
        for annonce in queryset:
            if annonce.status not in etats:
                self.message_user(
                    request,
                    f"« {annonce.title} » : état « {annonce.get_status_display()} », action impossible.",
                    level=messages.WARNING,
                )
                continue
            try:
                services.appliquer(request.user, defaut, motif=motif, annonce_id=annonce.pk)
                faites += 1
            except ErreurMetier as erreur:
                self.message_user(
                    request, f"« {annonce.title} » : {erreur.message}", level=messages.ERROR
                )
                if erreur.code == "validation_error":  # motif trop court : inutile d'insister annonce par annonce
                    break
        if faites:
            self.message_user(request, f"{faites} annonce(s) traitée(s) ; le gérant est prévenu avec le motif.")
        return None

    @admin.action(description="Masquer (modération) : l'annonce quitte le site, le gérant peut la corriger")
    def masquer_annonces(self, request, queryset):
        return self._decider(
            request,
            queryset,
            action="masquer_annonces",
            titre="Masquer des annonces",
            explication="Les annonces disparaissent du site. Le gérant est prévenu avec votre motif et peut les corriger ; "
            "vous pouvez les remettre en ligne ensuite.",
            etats=("published", "processing"),
            defaut="listing_hidden",
        )

    @admin.action(description="Retirer (modération) : définitif, le gérant ne peut pas la remettre en ligne")
    def retirer_annonces(self, request, queryset):
        return self._decider(
            request,
            queryset,
            action="retirer_annonces",
            titre="Retirer des annonces",
            explication="Retrait définitif (fausse annonce, arnaque, contenu interdit) : l'annonce disparaît et le gérant ne "
            "peut ni la modifier ni la remettre en ligne. Le gérant est prévenu avec votre motif.",
            etats=("published", "processing", "hidden"),
            defaut="listing_removed",
        )

    @admin.action(description="Remettre en ligne (annonce masquée par la modération)")
    def remettre_en_ligne(self, request, queryset):
        _exiger_personnel(request)
        faites = 0
        for annonce in queryset:
            try:
                annonces.remettre_en_ligne_apres_moderation(annonce, acteur=request.user)
                faites += 1
            except ErreurMetier as erreur:
                self.message_user(
                    request, f"« {annonce.title} » : {erreur.message}", level=messages.WARNING
                )
        if faites:
            self.message_user(request, f"{faites} annonce(s) remise(s) en ligne.")

    def _action_admin(self, request, queryset, *, action, titre, explication, bouton, appliquer):
        """Action réservée aux administrateurs, avec confirmation, journal et message par annonce refusée."""
        from .admin import confirmer_action

        _exiger_admin(request)
        reponse = confirmer_action(
            self, request, queryset, action=action, titre=titre, explication=explication, bouton=bouton
        )
        if reponse is not None:
            return reponse
        faites = 0
        for annonce in queryset:
            try:
                appliquer(annonce)
                audit.enregistrer(
                    "listing.action_equipe", acteur=request.user, cible=annonce, metadata={"action": action}
                )
                faites += 1
            except ErreurMetier as erreur:
                self.message_user(
                    request, f"« {annonce.title} » : {erreur.message}", level=messages.WARNING
                )
        if faites:
            self.message_user(request, f"{faites} annonce(s) traitée(s).")
        return None

    @admin.action(description="Rétablir une annonce retirée (elle repasse en masquée)")
    def retablir_retiree(self, request, queryset):
        return self._action_admin(
            request, queryset, action="retablir_retiree", titre="Rétablir des annonces retirées",
            explication="Les annonces retirées redeviennent masquées : le gérant peut les corriger et les republier.",
            bouton="Oui, rétablir",
            appliquer=lambda a: annonces.retablir_apres_retrait(a, acteur=request.user),
        )  # fmt: skip

    @admin.action(description="Marquer louée (au nom du gérant) : photos et vidéo supprimées")
    def marquer_louee_equipe(self, request, queryset):
        return self._action_admin(
            request, queryset, action="marquer_louee_equipe", titre="Marquer des annonces louées",
            explication="Les photos et la vidéo sont supprimées aussitôt et l'annonce est archivée. Irréversible pour les médias.",
            bouton="Oui, elles sont louées",
            appliquer=lambda a: annonces.marquer_louee(a.gerant, a.pk),
        )  # fmt: skip

    @admin.action(description="Supprimer (archive l'annonce et la retire de l'espace du gérant)")
    def supprimer_annonces(self, request, queryset):
        return self._action_admin(
            request, queryset, action="supprimer_annonces", titre="Supprimer des annonces",
            explication="Les annonces sont archivées et disparaissent de l'espace du gérant ; leurs médias sont purgés.",
            bouton="Oui, supprimer",
            appliquer=lambda a: annonces.supprimer(a.gerant, a.pk),
        )  # fmt: skip

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


class RattachementForm(forms.Form):
    cible = forms.ModelChoiceField(
        label="Rattacher à",
        queryset=RoomType.objects.filter(status=StatutTypeChambre.APPROVED),
        help_text="Les annonces et les alertes qui portent ce type passent sur le type choisi ; la proposition disparaît.",
    )


class NouveauTypeForm(forms.ModelForm):
    """Ajout d'un type de logement par un administrateur : refuse un nom déjà pris ou contenant des coordonnées."""

    class Meta:
        model = RoomType
        fields = ["label", "sort_order"]

    def clean_label(self):
        try:
            return types_chambre.verifier_libelle_libre(self.cleaned_data["label"])
        except ErreurMetier as erreur:
            raise forms.ValidationError(erreur.message) from erreur


@admin.register(RoomType)
class RoomTypeAdmin(admin.ModelAdmin):
    """Types de logement (décision V1) : les propositions des gérants se valident ou se rattachent à un type validé."""

    list_display = ("label", "slug", "status", "annonces", "proposed_by", "created_at")
    list_filter = ("status",)
    search_fields = ("label", "slug")
    ordering = ("-status", "sort_order", "label")  # « pending » d'abord
    actions = ["valider"]
    fields = (
        "label",
        "slug",
        "status",
        "sort_order",
        "proposed_by",
        "reviewed_by",
        "reviewed_at",
        "created_at",
    )
    readonly_fields = ("slug", "status", "proposed_by", "reviewed_by", "reviewed_at", "created_at")

    def has_add_permission(self, request):
        return request.user.is_active and request.user.role == "admin"  # un type validé, ajouté directement

    def has_delete_permission(self, request, obj=None):
        # Un administrateur supprime un type que plus rien n'utilise (page du type) ; sinon « Rattacher ».
        return request.user.is_active and request.user.role == "admin"

    def get_actions(self, request):
        actions = super().get_actions(request)
        actions.pop("delete_selected", None)  # jamais en masse : chaque suppression vérifie l'usage du type
        return actions

    def get_form(self, request, obj=None, **kwargs):
        if obj is None:  # ajout : libellé et ordre seulement, le reste est calculé
            kwargs["form"] = NouveauTypeForm
            kwargs["fields"] = ["label", "sort_order"]
        return super().get_form(request, obj, **kwargs)

    def get_fields(self, request, obj=None):
        return ("label", "sort_order") if obj is None else self.fields

    def get_readonly_fields(self, request, obj=None):
        return () if obj is None else self.readonly_fields

    def delete_model(self, request, obj):
        try:
            types_chambre.supprimer(obj, acteur=request.user)
        except ErreurMetier as erreur:
            self.message_user(request, erreur.message, level=messages.ERROR)


    @admin.display(description="Annonces")
    def annonces(self, obj):
        return Listing.objects.filter(room_type=obj.slug, deleted_at__isnull=True).count()

    def save_model(self, request, obj, form, change):
        _exiger_personnel(request)  # seuls le libellé et l'ordre sont modifiables ici
        if not change:
            nouveau = types_chambre.creer_officiel(
                form.cleaned_data["label"], acteur=request.user, ordre=form.cleaned_data["sort_order"]
            )
            obj.pk, obj.slug, obj.status = nouveau.pk, nouveau.slug, nouveau.status
            obj.label, obj.sort_order = nouveau.label, nouveau.sort_order
            return
        super().save_model(request, obj, form, change)
        types_chambre.vider_cache()

    @admin.action(description="Valider (visible dans les filtres et les alertes)")
    def valider(self, request, queryset):
        _exiger_personnel(request)
        faits = 0
        for t in queryset.filter(status=StatutTypeChambre.PENDING):
            types_chambre.valider(t, acteur=request.user)
            faits += 1
        self.message_user(request, f"{faits} type(s) validé(s).")

    def get_urls(self):
        return [
            path(
                "<int:type_id>/rattacher/",
                self.admin_site.admin_view(self.rattacher),
                name="listings_roomtype_rattacher",
            ),
            *super().get_urls(),
        ]

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = {
            **(extra_context or {}),
            "lien_rattacher": reverse("admin:listings_roomtype_rattacher", args=[object_id]),
        }
        return super().change_view(request, object_id, form_url, extra_context)

    def rattacher(self, request, type_id):
        _exiger_personnel(request)
        t = RoomType.objects.filter(pk=type_id).first()
        if t is None:
            raise PermissionDenied
        formulaire = RattachementForm(request.POST or None)
        formulaire.fields["cible"].queryset = RoomType.objects.filter(
            status=StatutTypeChambre.APPROVED
        ).exclude(pk=t.pk)
        if request.method == "POST" and formulaire.is_valid():
            try:
                n = types_chambre.rattacher(
                    t, formulaire.cleaned_data["cible"], acteur=request.user
                )
            except ErreurMetier as erreur:
                formulaire.add_error(None, erreur.message)
            else:
                cible = formulaire.cleaned_data["cible"]
                self.message_user(
                    request, f"« {t.label} » rattaché à « {cible.label} » ({n} annonce(s))."
                )
                return redirect("admin:listings_roomtype_changelist")
        contexte = {
            **self.admin_site.each_context(request),
            "title": f"Rattacher « {t.label} »",
            "form": formulaire,
            "type_chambre": t,
            "annonces": Listing.objects.filter(room_type=t.slug, deleted_at__isnull=True).count(),
            "opts": self.model._meta,
        }
        return render(request, "admin/rattacher-type.html", contexte)


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
        "reason_code",
        "personne_visee",
        "status",
    )  # « signalé par » : dans la fiche
    list_select_related = ("reporter", "assigned_to")
    list_filter = ("status", "reason_code", "source", "target_type")
    ordering = ("created_at",)
    actions = ["prendre", "classer_traite", "classer", "ecrire_au_plaignant", "ecrire_a_la_personne_visee"]

    @admin.action(description="Écrire à la personne qui a signalé")
    def ecrire_au_plaignant(self, request, queryset):
        from .admin_equipe import rediriger_vers_ecriture

        rapport = queryset.select_related("reporter").first()
        if rapport is None:
            return None
        return rediriger_vers_ecriture(
            self, request, rapport.reporter, contexte=f"signalement:{rapport.pk}",
            objet="À propos de ton signalement",
        )  # fmt: skip

    @admin.action(description="Écrire à la personne visée par le signalement")
    def ecrire_a_la_personne_visee(self, request, queryset):
        from .admin_equipe import rediriger_vers_ecriture

        rapport = queryset.first()
        if rapport is None:
            return None
        return rediriger_vers_ecriture(
            self, request, _personne_visee(rapport), contexte=f"signalement:{rapport.pk}",
            objet="À propos d'un signalement te concernant",
        )  # fmt: skip
    readonly_fields = [
        "personne_visee", "acces_rapide", "reason_code", "details", "status", "signale_par",
        "target_type", "target_id", "listing", "assigned_to", "resolved_by", "resolved_at", "resolution_note",
        "created_at", "id",
    ]  # fmt: skip
    fields = readonly_fields  # ordre d'affichage : qui est visé et quoi faire d'abord, le technique en dernier

    @admin.display(description="Personne visée")
    def personne_visee(self, obj):
        return _compte(_personne_visee(obj))

    @admin.display(description="Signalé par")
    def signale_par(self, obj):
        return _compte(obj.reporter) if obj.reporter_id else "Détection automatique"

    @admin.display(description="Accès rapide")
    def acces_rapide(self, obj):
        """Liens vers tout ce qu'il faut pour trancher : compte, annonce, conversation, décision pré-remplie."""
        liens = []
        visee = _personne_visee(obj)
        if visee is not None:
            liens.append((reverse("admin:accounts_user_change", args=[visee.pk]), "Compte visé"))
        annonce_id = obj.listing_id or (obj.target_id if obj.target_type == "listing" else None)
        if annonce_id:
            liens.append((reverse("admin:listings_listing_change", args=[annonce_id]), "Annonce"))
        if obj.target_type in ("conversation", "message"):
            liens.append(
                (
                    reverse("admin:moderation_report_conversation", args=[obj.pk]),
                    "Lire la conversation",
                )
            )
        decision = reverse("admin:moderation_moderationaction_add") + f"?report={obj.pk}"
        if visee is not None:
            decision += f"&target_user={visee.pk}"
        if annonce_id:
            decision += f"&target_listing={annonce_id}"
        liens.append((decision, "Prendre une décision"))
        return format_html(
            '<span class="lg-liens">{}</span>',
            format_html_join("", '<a class="lg-lien-action" href="{}">{}</a>', liens),
        )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_active and request.user.role == "admin"

    def delete_model(self, request, obj):
        audit.enregistrer(
            "avis.supprime_par_equipe", acteur=request.user, cible=obj.listing,
            metadata={"avis": str(obj.pk), "note": obj.rating},
        )  # fmt: skip
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        for avis in queryset:
            audit.enregistrer(
                "avis.supprime_par_equipe", acteur=request.user, cible=avis.listing,
                metadata={"avis": str(avis.pk), "note": avis.rating},
            )  # fmt: skip
        super().delete_queryset(request, queryset)

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

    @admin.action(description="Classer comme traité")
    def classer_traite(self, request, queryset):
        _exiger_personnel(request)
        for rapport in queryset:
            try:
                services.classer_traite(request.user, rapport, "Situation traitée par l'équipe.")
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


# --------------------------------------------------------------- avis des locataires (plan v3, G3 et J4)
from apps.listings.models import Review  # noqa: E402
from apps.listings.services import avis as service_avis  # noqa: E402


@admin.register(Review)
class AvisAdmin(admin.ModelAdmin):
    """Avis publiés tout de suite ; l'équipe les relit ici et masque ceux qui posent problème (l'auteur garde son avis,
    il disparaît seulement du public)."""

    list_display = (
        "created_at",
        "note_etoiles",
        "commentaire_court",
        "annonce",
        "auteur",
        "visible",
    )
    list_filter = ("is_hidden", "rating")
    search_fields = ("comment", "listing__title")
    readonly_fields = (
        "listing", "author", "rating", "comment", "owner_reply", "owner_replied_at", "created_at", "updated_at",
    )  # fmt: skip
    fields = (
        "listing",
        "author",
        "rating",
        "comment",
        "owner_reply",
        "owner_replied_at",
        "is_hidden",
        "hidden_reason",
        "created_at",
        "updated_at",
    )
    ordering = ("-created_at",)
    actions = ("masquer", "reafficher", "ecrire_a_l_auteur", "ecrire_au_gerant")
    list_select_related = ("listing", "author")

    @admin.action(description="Écrire à l'auteur de l'avis")
    def ecrire_a_l_auteur(self, request, queryset):
        from .admin_equipe import rediriger_vers_ecriture

        avis = queryset.select_related("listing", "author").first()
        if avis is None:
            return None
        return rediriger_vers_ecriture(
            self, request, avis.author, contexte=f"avis:{avis.pk}",
            objet=f"À propos de ton avis sur « {avis.listing.title[:60]} »",
        )  # fmt: skip

    @admin.action(description="Écrire au gérant concerné par l'avis")
    def ecrire_au_gerant(self, request, queryset):
        from .admin_equipe import rediriger_vers_ecriture

        avis = queryset.select_related("listing", "listing__gerant__user").first()
        if avis is None:
            return None
        return rediriger_vers_ecriture(
            self, request, avis.listing.gerant.user, contexte=f"avis:{avis.pk}",
            objet=f"À propos d'un avis reçu sur « {avis.listing.title[:60]} »",
        )  # fmt: skip

    @admin.display(description="Note", ordering="rating")
    def note_etoiles(self, obj):
        return f"{obj.rating}/5"

    @admin.display(description="Commentaire")
    def commentaire_court(self, obj):
        return (obj.comment[:80] + "…") if len(obj.comment) > 80 else (obj.comment or "—")

    @admin.display(description="Annonce", ordering="listing__title")
    def annonce(self, obj):
        return obj.listing.title

    @admin.display(description="Auteur")
    def auteur(self, obj):
        return obj.author.full_name or "Sans nom"

    @admin.display(description="Visible", boolean=True, ordering="is_hidden")
    def visible(self, obj):
        return not obj.is_hidden

    @admin.action(description="Masquer les avis sélectionnés")
    def masquer(self, request, queryset):
        for r in queryset:
            service_avis.masquer(r.pk, acteur=request.user, raison="Masqué par la modération")
        messages.success(request, f"{queryset.count()} avis masqué(s).")

    @admin.action(description="Réafficher les avis sélectionnés")
    def reafficher(self, request, queryset):
        for r in queryset:
            service_avis.reafficher(r.pk, acteur=request.user)
        messages.success(request, f"{queryset.count()} avis réaffiché(s).")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
