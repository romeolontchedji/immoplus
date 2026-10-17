"""Administration : référentiels gérés par l'équipe (quartiers de Parakou)."""

from django.contrib import admin
from django.db.models import Count, Q

from apps.listings.models import District


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    """Quartiers proposés dans la recherche, les alertes et la publication. Un quartier utilisé ne se supprime pas :
    on le désactive (il disparaît des listes, les annonces existantes restent)."""

    list_display = ("name", "slug", "is_active", "sort_order", "annonces_en_ligne")
    list_editable = ("is_active", "sort_order")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    ordering = ("sort_order", "name")
    prepopulated_fields = {"slug": ("name",)}
    fields = ("name", "slug", "latitude", "longitude", "sort_order", "is_active")

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(
                _en_ligne=Count(
                    "listings",
                    filter=Q(listings__status="published", listings__deleted_at__isnull=True),
                )
            )
        )

    @admin.display(description="Annonces en ligne", ordering="_en_ligne")
    def annonces_en_ligne(self, obj):
        return obj._en_ligne

    def has_delete_permission(self, request, obj=None):
        return False
