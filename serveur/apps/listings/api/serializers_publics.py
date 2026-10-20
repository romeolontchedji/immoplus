"""Schémas de l'API publique : fil, fiche, favoris, alertes (CDC §10.3)."""

from rest_framework import serializers


class QuartierRefOut(serializers.Serializer):
    name = serializers.CharField()
    slug = serializers.CharField()


class GerantCarteOut(serializers.Serializer):
    name = serializers.CharField(allow_null=True)
    verified = serializers.BooleanField()


class CarteOut(serializers.Serializer):
    id = serializers.UUIDField()
    slug = serializers.CharField()
    title = serializers.CharField()
    room_type = serializers.CharField()
    room_type_label = serializers.CharField(
        help_text="Libellé à afficher (types gérés par l'équipe)."
    )
    district = QuartierRefOut()
    landmark_text = serializers.CharField()
    rent_amount = serializers.IntegerField()
    rent_negotiable = serializers.BooleanField(help_text="Loyer à débattre avec le gérant.")
    deposit_months = serializers.IntegerField()
    advance_months = serializers.IntegerField()
    distance_m = serializers.IntegerField()
    has_private_bathroom = serializers.BooleanField()
    is_fenced = serializers.BooleanField()
    available_from = serializers.DateField()
    status = serializers.CharField()
    published_at = serializers.DateTimeField(allow_null=True)
    cover_url = serializers.CharField(allow_null=True)
    video_poster_url = serializers.CharField(allow_null=True)
    has_video = serializers.BooleanField()
    gerant = GerantCarteOut()


class VoisinsOut(serializers.Serializer):
    districts = QuartierRefOut(many=True)
    items = CarteOut(many=True)


class FilOut(serializers.Serializer):
    items = CarteOut(many=True)
    next_cursor = serializers.CharField(allow_null=True)
    voisins = VoisinsOut(
        allow_null=True,
        help_text="Quartier demandé presque vide : mêmes critères dans les quartiers proches (à part).",
    )


class MediaPublicOut(serializers.Serializer):
    id = serializers.UUIDField()
    kind = serializers.CharField()
    playback_url = serializers.CharField(required=False)
    poster_url = serializers.CharField(required=False, allow_null=True)
    duration_s = serializers.FloatField(required=False, allow_null=True)
    url = serializers.CharField(required=False, allow_null=True)
    thumb_url = serializers.CharField(required=False, allow_null=True)
    is_cover = serializers.BooleanField(required=False)
    width = serializers.IntegerField(allow_null=True)
    height = serializers.IntegerField(allow_null=True)


class GerantFicheOut(serializers.Serializer):
    id = serializers.UUIDField(help_text="Pour ouvrir son profil public (`GET /v1/gerants/{id}`).")
    name = serializers.CharField(allow_null=True)
    verified = serializers.BooleanField()
    median_response_min = serializers.IntegerField(allow_null=True)


class ResumeAvisOut(serializers.Serializer):
    average = serializers.FloatField(allow_null=True, help_text="Note moyenne sur 5, une décimale.")
    count = serializers.IntegerField()


class AvisOut(serializers.Serializer):
    id = serializers.UUIDField()
    rating = serializers.IntegerField()
    comment = serializers.CharField()
    author_name = serializers.CharField(help_text="Prénom et initiale du nom.")
    listing_title = serializers.CharField()
    listing_slug = serializers.CharField()
    created_at = serializers.DateTimeField()


class AvisListeOut(serializers.Serializer):
    summary = ResumeAvisOut()
    items = AvisOut(many=True)
    can_review = serializers.BooleanField(
        help_text="Le locataire connecté peut donner (ou modifier) son avis."
    )
    my_review = serializers.DictField(allow_null=True)


class AvisIn(serializers.Serializer):
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(max_length=600, required=False, allow_blank=True)


class GerantPublicOut(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField(allow_null=True)
    verified = serializers.BooleanField()
    median_response_min = serializers.IntegerField(allow_null=True)
    member_since = serializers.DateField()
    listings = CarteOut(many=True)
    reviews = ResumeAvisOut()


class FicheOut(serializers.Serializer):
    id = serializers.UUIDField()
    slug = serializers.CharField()
    title = serializers.CharField()
    room_type = serializers.CharField()
    room_type_label = serializers.CharField(
        help_text="Libellé à afficher (types gérés par l'équipe)."
    )
    district = QuartierRefOut()
    landmark_text = serializers.CharField()
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    distance_m = serializers.IntegerField()
    rent_amount = serializers.IntegerField()
    deposit_months = serializers.IntegerField()
    advance_months = serializers.IntegerField()
    agent_fee_amount = serializers.IntegerField()
    water_deposit_amount = serializers.IntegerField(help_text="Caution eau en F (0 = aucune).")
    electricity_deposit_amount = serializers.IntegerField(
        help_text="Caution électricité en F (0 = aucune)."
    )
    available_from = serializers.DateField()
    has_private_bathroom = serializers.BooleanField()
    is_fenced = serializers.BooleanField()
    water_sources = serializers.ListField(child=serializers.CharField())
    water_labels = serializers.ListField(child=serializers.CharField())
    water_label = serializers.CharField(
        help_text="Sources d'eau en une phrase (« Forage, Puits »)."
    )
    electricity_meter = serializers.CharField()
    electricity_label = serializers.CharField()
    kitchen = serializers.CharField(help_text="Vide = non précisé.")
    kitchen_label = serializers.CharField()
    rent_negotiable = serializers.BooleanField()
    description_md = serializers.CharField(help_text="Autres détails, texte simple.")
    description_html = serializers.CharField()
    status = serializers.CharField()
    published_at = serializers.DateTimeField(allow_null=True)
    last_confirmed_at = serializers.DateTimeField(allow_null=True)
    media = MediaPublicOut(many=True)
    reviews = ResumeAvisOut()
    gerant = GerantFicheOut()
    is_favorite = serializers.BooleanField()


class VueOut(serializers.Serializer):
    counted = serializers.BooleanField()


class AlerteIn(serializers.Serializer):
    label = serializers.CharField(max_length=80, required=False, allow_blank=True)
    district_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, max_length=30
    )
    room_types = serializers.ListField(
        child=serializers.CharField(max_length=40),
        required=False,
        max_length=10,
        help_text="Slugs de `GET /v1/room-types` (types validés).",
    )
    max_rent = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    private_bathroom_required = serializers.BooleanField(required=False)
    max_distance_m = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    water_sources = serializers.ListField(
        child=serializers.CharField(max_length=10), required=False, max_length=10,
        help_text="Eau souhaitée (au moins une) : individual, sub_meter, running, borehole, well. Vide = peu importe.",
    )  # fmt: skip
    electricity_meters = serializers.ListField(
        child=serializers.CharField(max_length=10), required=False, max_length=10,
        help_text="Électricité souhaitée : individual, sub_meter, shared. Vide = peu importe.",
    )  # fmt: skip
    kitchens = serializers.ListField(
        child=serializers.CharField(max_length=10), required=False, max_length=10,
        help_text="Cuisine souhaitée : private, shared. Vide = peu importe.",
    )  # fmt: skip
    fenced_required = serializers.BooleanField(required=False, help_text="Cour clôturée exigée.")
    is_active = serializers.BooleanField(required=False)


class AlerteOut(serializers.Serializer):
    id = serializers.UUIDField()
    label = serializers.CharField()
    district_ids = serializers.ListField(child=serializers.UUIDField())
    room_types = serializers.ListField(child=serializers.CharField())
    max_rent = serializers.IntegerField(allow_null=True)
    private_bathroom_required = serializers.BooleanField()
    max_distance_m = serializers.IntegerField(allow_null=True)
    water_sources = serializers.ListField(child=serializers.CharField())
    electricity_meters = serializers.ListField(child=serializers.CharField())
    kitchens = serializers.ListField(child=serializers.CharField())
    fenced_required = serializers.BooleanField()
    is_active = serializers.BooleanField()
    created_at = serializers.DateTimeField()


class QuartierFrequenceOut(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    slug = serializers.CharField()
    alerts = serializers.IntegerField(help_text="Alertes actives qui citent ce quartier.")
    listings = serializers.IntegerField(help_text="Annonces publiées dans ce quartier.")


class OptionsAlerteOut(serializers.Serializer):
    districts = QuartierFrequenceOut(many=True, help_text="Les plus demandés d'abord.")
    budgets = serializers.ListField(
        child=serializers.IntegerField(), help_text="Plafonds proposés, en F."
    )
