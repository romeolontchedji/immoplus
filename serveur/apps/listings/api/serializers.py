from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from ..enums import Compteur, Cuisine, Eau, StatutAnnonce, StatutTypeChambre
from ..services import types


class DistrictOut(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    slug = serializers.CharField()
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()


class AnnonceIn(serializers.Serializer):
    title = serializers.CharField(max_length=120)
    room_type = serializers.CharField(
        max_length=40, help_text="Slug d'un type de `GET /v1/pro/room-types` (validé ou proposé)."
    )
    district = serializers.UUIDField()
    landmark_text = serializers.CharField(max_length=160)
    address_private = serializers.CharField(max_length=255, required=False, allow_blank=True)
    latitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        required=False,
        allow_null=True,
        help_text="Facultatif : GPS du téléphone. Absent, la chambre est placée au centre du quartier.",
    )
    longitude = serializers.DecimalField(
        max_digits=9, decimal_places=6, required=False, allow_null=True
    )
    rent_amount = serializers.IntegerField(min_value=1)
    deposit_months = serializers.IntegerField(min_value=0, max_value=12)
    advance_months = serializers.IntegerField(min_value=0, max_value=12)
    agent_fee_amount = serializers.IntegerField(min_value=0, required=False)
    available_from = serializers.DateField()
    has_private_bathroom = serializers.BooleanField()
    is_fenced = serializers.BooleanField()
    water_source = serializers.ChoiceField(choices=[e.value for e in Eau])
    electricity_meter = serializers.ChoiceField(choices=[c.value for c in Compteur])
    kitchen = serializers.ChoiceField(
        choices=[c.value for c in Cuisine], required=False, allow_blank=True,
        help_text="private (interne), shared (commune), none (aucune) ; vide = non précisé.",
    )  # fmt: skip
    rent_negotiable = serializers.BooleanField(required=False, help_text="Loyer à débattre.")
    description_md = serializers.CharField(
        max_length=6000, required=False, allow_blank=True,
        help_text="Autres détails, en texte simple (la mise en forme est retirée).",
    )  # fmt: skip


class AnnonceProOut(serializers.Serializer):
    id = serializers.UUIDField()
    slug = serializers.CharField()
    title = serializers.CharField()
    room_type = serializers.CharField()
    room_type_label = serializers.SerializerMethodField()
    district = serializers.UUIDField(source="district_id")
    district_name = serializers.CharField(source="district.name")
    landmark_text = serializers.CharField()
    address_private = serializers.CharField()
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    distance_to_campus_m = serializers.IntegerField()
    rent_amount = serializers.IntegerField()
    deposit_months = serializers.IntegerField()
    advance_months = serializers.IntegerField()
    agent_fee_amount = serializers.IntegerField()
    available_from = serializers.DateField()
    has_private_bathroom = serializers.BooleanField()
    is_fenced = serializers.BooleanField()
    water_source = serializers.CharField()
    electricity_meter = serializers.CharField()
    kitchen = serializers.CharField()
    rent_negotiable = serializers.BooleanField()
    views_total = serializers.SerializerMethodField(
        help_text="Vues de l'annonce depuis sa publication (vues du jour comprises)."
    )
    description_md = serializers.CharField()
    status = serializers.ChoiceField(choices=[s.value for s in StatutAnnonce])
    hidden_reason = serializers.CharField(allow_null=True)
    published_at = serializers.DateTimeField(allow_null=True)
    last_confirmed_at = serializers.DateTimeField(allow_null=True)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()

    @extend_schema_field(OpenApiTypes.INT)
    def get_views_total(self, annonce) -> int:
        from .. import selectors

        stats = self.context.get("stats")
        if stats is None:
            stats = selectors.stats_par_annonce([annonce.pk])
        return stats.get(annonce.pk, {}).get("views_total", 0)

    @extend_schema_field(OpenApiTypes.STR)
    def get_room_type_label(self, annonce) -> str:
        return types.libelle(annonce.room_type) or annonce.room_type


class ApercuIn(serializers.Serializer):
    markdown = serializers.CharField(max_length=6000, allow_blank=True)


class ApercuOut(serializers.Serializer):
    markdown = serializers.CharField()
    html = serializers.CharField()


class MediaIn(serializers.Serializer):
    kind = serializers.ChoiceField(choices=["video", "photo"])
    size_bytes = serializers.IntegerField(min_value=1)


class MediaOut(serializers.Serializer):
    id = serializers.UUIDField()
    kind = serializers.CharField()
    status = serializers.CharField()
    position = serializers.IntegerField()
    is_cover = serializers.BooleanField()
    declared_size_bytes = serializers.IntegerField()
    received_bytes = serializers.IntegerField()
    width = serializers.IntegerField(allow_null=True)
    height = serializers.IntegerField(allow_null=True)
    duration_s = serializers.FloatField(allow_null=True)
    playback_url = serializers.CharField(allow_null=True)
    poster_url = serializers.CharField(allow_null=True)
    error_code = serializers.CharField(allow_null=True)
    error_detail = serializers.CharField(allow_null=True)
    upload_url = serializers.CharField(allow_null=True)


class OrdreMediasIn(serializers.Serializer):
    order = serializers.ListField(child=serializers.UUIDField(), allow_empty=False, max_length=20)
    cover = serializers.UUIDField(required=False, allow_null=True)


class TypeChambreOut(serializers.Serializer):
    slug = serializers.CharField()
    label = serializers.CharField()
    count = serializers.IntegerField(help_text="Annonces publiées de ce type.")


class TypeChambreProOut(serializers.Serializer):
    slug = serializers.CharField()
    label = serializers.CharField()
    status = serializers.ChoiceField(
        choices=StatutTypeChambre.values,
        help_text="`pending` : utilisable par toi tout de suite, visible dans les filtres après validation.",
    )


class PropositionTypeIn(serializers.Serializer):
    label = serializers.CharField(max_length=40, help_text="Nom du type, 3 à 40 caractères.")


class ManqueOut(serializers.Serializer):
    code = serializers.CharField()
    label = serializers.CharField()


class PreparationOut(serializers.Serializer):
    publishable = serializers.BooleanField()
    missing = ManqueOut(many=True)


class StatJourOut(serializers.Serializer):
    day = serializers.DateField()
    views = serializers.IntegerField()
    favorites = serializers.IntegerField()
    contacts = serializers.IntegerField()


class StatistiquesOut(serializers.Serializer):
    days = serializers.IntegerField()
    views = serializers.IntegerField()
    favorites = serializers.IntegerField()
    contacts = serializers.IntegerField()
    daily = StatJourOut(many=True)
