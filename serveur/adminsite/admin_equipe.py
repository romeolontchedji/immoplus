"""Administration : messages entre l'équipe et les utilisateurs (réponse à une question, à un avis, suite à une
décision de modération). Administrateurs et modérateurs."""

import uuid
from urllib.parse import urlencode

from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render
from django.urls import path, reverse
from django.utils.html import format_html

from apps.accounts.models import User
from apps.core.errors import ErreurMetier
from apps.moderation import messages_equipe as equipe
from apps.moderation.models import MessageEquipe


def _exiger_personnel(request) -> None:
    if not (request.user.is_active and request.user.role in ("moderator", "admin")):
        raise PermissionDenied


def lien_ecriture(utilisateur, *, objet: str = "", contexte: str = "") -> str:
    """Adresse de la page d'écriture à une personne, avec un objet et un contexte pré-remplis."""
    base = reverse("admin:moderation_messageequipe_ecrire", args=[utilisateur.pk])
    parametres = {k: v for k, v in (("objet", objet), ("contexte", contexte)) if v}
    return f"{base}?{urlencode(parametres)}" if parametres else base


def rediriger_vers_ecriture(modeladmin, request, utilisateur, *, objet="", contexte=""):
    """Action de liste : ouvre la page d'écriture pour la première personne concernée."""
    _exiger_personnel(request)
    if (
        utilisateur is None
        or utilisateur.role not in ("client", "gerant")
        or utilisateur.deleted_at
    ):
        modeladmin.message_user(request, "Cette personne n'est pas joignable.", messages.WARNING)
        return None
    return HttpResponseRedirect(lien_ecriture(utilisateur, objet=objet, contexte=contexte))


@admin.register(MessageEquipe)
class MessageEquipeAdmin(admin.ModelAdmin):
    """Boîte de l'équipe : les questions des utilisateurs (à traiter) et les messages envoyés."""

    list_display = ("created_at", "sens", "personne", "objet", "extrait", "etat")
    list_filter = ("vers_utilisateur", ("traite_le", admin.EmptyFieldListFilter), "contexte_type")
    search_fields = ("corps", "objet", "utilisateur__full_name", "utilisateur__username")
    ordering = ("-created_at",)
    actions = ["repondre", "classer"]
    list_select_related = ("utilisateur", "auteur")

    def has_add_permission(self, request):
        return False  # on écrit depuis la fiche d'une personne, d'un avis ou d'un signalement

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return request.user.is_active and request.user.role in ("moderator", "admin")

    @admin.display(description="Sens", ordering="vers_utilisateur")
    def sens(self, obj):
        return "Équipe → personne" if obj.vers_utilisateur else "Personne → équipe"

    @admin.display(description="Personne")
    def personne(self, obj):
        u = obj.utilisateur
        return format_html(
            '<a href="{}">{}</a>', lien_ecriture(u), u.full_name or u.username or "Sans nom"
        )

    @admin.display(description="Message")
    def extrait(self, obj):
        return (obj.corps[:90] + "…") if len(obj.corps) > 90 else obj.corps

    @admin.display(description="État")
    def etat(self, obj):
        if obj.vers_utilisateur:
            return "Lu" if obj.lu_le else "Non lu"
        return "Traité" if obj.traite_le else "À traiter"

    @admin.action(description="Répondre à cette personne")
    def repondre(self, request, queryset):
        premier = queryset.select_related("utilisateur").first()
        return rediriger_vers_ecriture(
            self, request, premier.utilisateur if premier else None, contexte="question"
        )

    @admin.action(description="Classer sans répondre")
    def classer(self, request, queryset):
        _exiger_personnel(request)
        nombre = equipe.classer_sans_repondre(request.user, queryset.values_list("pk", flat=True))
        if nombre:
            self.message_user(
                request, f"{nombre} message(s) classé(s) sans réponse.", messages.SUCCESS
            )
        else:
            self.message_user(
                request, "Aucun message à classer : ils sont déjà traités.", messages.WARNING
            )

    def get_urls(self):
        return [
            path(
                "ecrire/<uuid:user_id>/",
                self.admin_site.admin_view(self.ecrire),
                name="moderation_messageequipe_ecrire",
            ),
            *super().get_urls(),
        ]

    def ecrire(self, request, user_id):
        """Le fil avec une personne et le formulaire pour lui écrire."""
        _exiger_personnel(request)
        personne = User.objects.filter(pk=user_id).first()
        if personne is None or personne.role not in ("client", "gerant"):
            raise Http404
        contexte = request.POST.get("contexte") or request.GET.get("contexte", "")
        type_, _, ref = contexte.partition(":")
        try:
            ref_uuid = uuid.UUID(ref) if ref else None
        except ValueError:
            ref_uuid = None
        objet = request.POST.get("objet") or request.GET.get("objet", "")
        erreur = None
        if request.method == "POST":
            try:
                equipe.ecrire_a(
                    request.user, personne, request.POST.get("corps", ""),
                    objet=objet, contexte_type=type_, contexte_id=ref_uuid,
                )  # fmt: skip
            except ErreurMetier as e:
                erreur = e.message
            else:
                self.message_user(request, "Message envoyé : la personne est prévenue.")
                return HttpResponseRedirect(
                    reverse("admin:moderation_messageequipe_ecrire", args=[personne.pk])
                )
        contexte_page = {
            **self.admin_site.each_context(request),
            "title": f"Écrire à {personne.full_name or personne.username}",
            "opts": self.model._meta,
            "personne": personne,
            "fil": equipe.fil(personne.pk),
            "objet": objet,
            "contexte": contexte,
            "erreur": erreur,
            "corps": request.POST.get("corps", ""),
            "corps_max": equipe.CORPS_MAX,
        }
        return render(request, "admin/ecrire-equipe.html", contexte_page)
