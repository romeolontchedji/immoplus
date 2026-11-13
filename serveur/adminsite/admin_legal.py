"""Administration : modifier les conditions d'utilisation et la politique de confidentialité (administrateurs).

Le texte est du Markdown, écrit avec une barre d'outils (gras, italique, titre de section, liste, lien) et un aperçu en
direct rendu par le serveur, avec le même moteur que le site et l'application."""

from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponseNotAllowed, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.response import TemplateResponse
from django.urls import path, reverse

from apps.audit import services as audit
from apps.core import legal, parametres
from apps.core.errors import ErreurMetier
from apps.core.models import LegalDocument

TITRES = {
    "conditions": "Conditions d'utilisation",
    "confidentialite": "Politique de confidentialité",
}


def _exiger_admin(request) -> None:
    if not (request.user.is_active and request.user.role == "admin"):
        raise PermissionDenied


@admin.register(LegalDocument)
class LegalDocumentAdmin(admin.ModelAdmin):
    """Les deux documents légaux : modifiables (administrateurs), jamais créés ni supprimés ici."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return request.user.is_active and request.user.role == "admin"

    def changelist_view(self, request, extra_context=None):
        _exiger_admin(request)
        modifies = dict(LegalDocument.objects.values_list("slug", "updated_at"))
        documents = [
            {
                "slug": slug,
                "titre": titre,
                "modifie_le": modifies.get(slug),
                "lien": reverse("admin:core_legaldocument_modifier", args=[slug]),
            }
            for slug, titre in TITRES.items()
        ]
        contexte = {
            **self.admin_site.each_context(request),
            "title": "Textes légaux",
            "documents": documents,
            "version": parametres.lire("TERMS_VERSION"),
            "mise_a_jour": parametres.lire("LEGAL_UPDATED_AT"),
            "opts": self.model._meta,
        }
        return TemplateResponse(request, "admin/legal-liste.html", contexte)

    def get_urls(self):
        return [
            path(
                "<slug:slug>/modifier/",
                self.admin_site.admin_view(self.modifier),
                name="core_legaldocument_modifier",
            ),
            path(
                "<slug:slug>/apercu/",
                self.admin_site.admin_view(self.apercu),
                name="core_legaldocument_apercu",
            ),
            *super().get_urls(),
        ]

    def modifier(self, request, slug):
        _exiger_admin(request)
        if slug not in TITRES:
            raise Http404
        erreur = None
        texte = legal._source(slug)
        if request.method == "POST":
            texte = request.POST.get("texte", "")
            try:
                if "retablir" in request.POST:
                    legal.retablir(slug, acteur=request.user)
                    audit.enregistrer(
                        "legal.retabli", acteur=request.user, metadata={"document": slug}
                    )
                    self.message_user(request, "Texte d'origine rétabli.")
                else:
                    nouvelle = bool(request.POST.get("nouvelle_acceptation"))
                    legal.enregistrer(
                        slug, texte, acteur=request.user, nouvelle_acceptation=nouvelle
                    )
                    audit.enregistrer(
                        "legal.modifie",
                        acteur=request.user,
                        metadata={"document": slug, "nouvelle_acceptation": nouvelle},
                    )
                    self.message_user(request, "Texte enregistré. Il est en ligne tout de suite.")
                return HttpResponseRedirect(request.path)
            except ErreurMetier as e:
                erreur = e.message
        contexte = {
            **self.admin_site.each_context(request),
            "title": TITRES[slug],
            "slug": slug,
            "texte": texte,
            "erreur": erreur,
            "personnalise": LegalDocument.objects.filter(pk=slug).exists(),
            "variables": legal.VARIABLES,
            "lien_apercu": reverse("admin:core_legaldocument_apercu", args=[slug]),
            "lien_liste": reverse("admin:core_legaldocument_changelist"),
            "version": parametres.lire("TERMS_VERSION"),
            "opts": self.model._meta,
        }
        return render(request, "admin/legal-edition.html", contexte)

    def apercu(self, request, slug):
        if request.method != "POST":
            return HttpResponseNotAllowed(["POST"])
        _exiger_admin(request)
        if slug not in TITRES:
            raise Http404
        try:
            return JsonResponse(legal.apercu(request.POST.get("texte", "")))
        except ErreurMetier as e:
            return JsonResponse({"erreur": e.message}, status=400)
