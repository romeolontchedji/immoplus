"""Quartiers, annonces et médias (CDC §9.7 à §9.9)."""

import uuid

from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import models
from django.db.models.functions import Now
from django.utils import timezone

from .enums import (
    Compteur,
    Cuisine,
    Eau,
    RaisonMasquage,
    StatutAnnonce,
    StatutMedia,
    StatutTypeChambre,
    TypeMedia,
)


class District(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=80, verbose_name="nom")
    slug = models.CharField(max_length=80, unique=True, verbose_name="identifiant d'URL")
    city = models.CharField(max_length=40, default="Parakou", db_default="Parakou")
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    sort_order = models.SmallIntegerField(default=0, db_default=0, verbose_name="ordre")
    is_active = models.BooleanField(default=True, db_default=True, verbose_name="actif")

    class Meta:
        db_table = "districts"
        verbose_name = "quartier"
        verbose_name_plural = "quartiers"
        ordering = ["sort_order", "name"]

    def __str__(self) -> str:
        return self.name


class RoomType(models.Model):
    """Type de logement (décision V1) : officiel, ou proposé par un gérant puis validé ou rattaché par la modération.

    `listings.room_type` et `alerts.room_types` portent le `slug` : un rattachement réécrit ces valeurs.
    """

    slug = models.CharField(max_length=40, unique=True, verbose_name="identifiant d'URL")
    label = models.CharField(max_length=40, verbose_name="libellé")
    status = models.CharField(
        max_length=10,
        choices=StatutTypeChambre.choices,
        default=StatutTypeChambre.PENDING,
        db_default="pending",
        verbose_name="statut",
    )
    sort_order = models.SmallIntegerField(default=100, db_default=100, verbose_name="ordre")
    proposed_by = models.ForeignKey(
        "accounts.GerantProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        db_column="proposed_by",
        verbose_name="proposé par",
    )
    reviewed_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        db_column="reviewed_by",
        verbose_name="examiné par",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name="examiné le")
    created_at = models.DateTimeField(
        default=timezone.now, db_default=Now(), verbose_name="créé le"
    )

    class Meta:
        db_table = "room_types"
        ordering = ["sort_order", "label"]
        verbose_name = "type de logement"
        verbose_name_plural = "types de logement"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=[s.value for s in StatutTypeChambre]),
                name="room_types_statut_valide",
            ),
            models.CheckConstraint(
                condition=models.Q(slug__regex=r"^[a-z0-9_]{2,40}$"), name="room_types_slug_valide"
            ),
        ]

    def __str__(self) -> str:
        return self.label


class Listing(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gerant = models.ForeignKey(
        "accounts.GerantProfile",
        on_delete=models.PROTECT,
        related_name="listings",
        db_column="gerant_id",
        verbose_name="gérant",
    )
    slug = models.CharField(max_length=160, unique=True, verbose_name="identifiant d'URL")
    title = models.CharField(max_length=120, verbose_name="titre")
    # Slug d'un `RoomType` (contrôlé par le service).
    room_type = models.CharField(max_length=40, verbose_name="type de logement")
    district = models.ForeignKey(
        District, on_delete=models.PROTECT, related_name="listings", verbose_name="quartier"
    )
    landmark_text = models.CharField(max_length=160, verbose_name="repère")
    address_private = models.CharField(
        max_length=255, blank=True, default="", verbose_name="adresse privée"
    )
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    distance_to_campus_m = models.IntegerField(verbose_name="distance à l'UP (m)")
    rent_amount = models.IntegerField(verbose_name="loyer (F)")
    deposit_months = models.SmallIntegerField(verbose_name="caution (mois)")
    advance_months = models.SmallIntegerField(verbose_name="avance (mois)")
    agent_fee_amount = models.IntegerField(
        default=0, db_default=0, verbose_name="frais de démarcheur (F)"
    )
    available_from = models.DateField(verbose_name="disponible le")
    has_private_bathroom = models.BooleanField(verbose_name="douche interne")
    is_fenced = models.BooleanField(verbose_name="clôturée")
    water_source = models.CharField(max_length=10, choices=Eau.choices, verbose_name="eau")
    electricity_meter = models.CharField(
        max_length=10, choices=Compteur.choices, verbose_name="compteur"
    )
    # Vide = non précisé (annonces publiées avant l'ajout du champ).
    kitchen = models.CharField(
        max_length=10, choices=Cuisine.choices, blank=True, default="", db_default="",
        verbose_name="cuisine",
    )  # fmt: skip
    rent_negotiable = models.BooleanField(
        default=False, db_default=False, verbose_name="loyer à débattre"
    )
    # « Autres détails » : texte simple (plus de mise en forme depuis le 19/10/2026).
    description_md = models.TextField(default="", db_default="", verbose_name="autres détails")
    description_html = models.TextField(default="", db_default="")
    search_vector = SearchVectorField(null=True, blank=True)
    status = models.CharField(
        max_length=12,
        choices=StatutAnnonce.choices,
        default=StatutAnnonce.DRAFT,
        db_default="draft",
        verbose_name="statut",
    )
    hidden_reason = models.CharField(
        max_length=16,
        choices=RaisonMasquage.choices,
        null=True,
        blank=True,
        verbose_name="raison du masquage",
    )
    published_at = models.DateTimeField(null=True, blank=True, verbose_name="publiée le")
    rented_at = models.DateTimeField(null=True, blank=True, verbose_name="louée le")
    last_confirmed_at = models.DateTimeField(null=True, blank=True, verbose_name="confirmée le")
    reminder_stage = models.SmallIntegerField(default=0, db_default=0)
    created_at = models.DateTimeField(
        default=timezone.now, db_default=Now(), verbose_name="créé le"
    )
    updated_at = models.DateTimeField(auto_now=True, db_default=Now(), verbose_name="modifié le")
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="supprimé le")

    def __str__(self) -> str:
        return self.title

    class Meta:
        db_table = "listings"
        verbose_name = "annonce"
        verbose_name_plural = "annonces"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(rent_amount__gt=0), name="listings_loyer_positif"
            ),
            models.CheckConstraint(
                condition=models.Q(deposit_months__gte=0, deposit_months__lte=12),
                name="listings_caution_bornee",
            ),
            models.CheckConstraint(
                condition=models.Q(advance_months__gte=0, advance_months__lte=12),
                name="listings_avance_bornee",
            ),
            models.CheckConstraint(
                condition=models.Q(agent_fee_amount__gte=0), name="listings_frais_positifs"
            ),
            models.CheckConstraint(
                condition=models.Q(title__regex=r"^.{5,}$"), name="listings_titre_5_caracteres"
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=[s.value for s in StatutAnnonce]),
                name="listings_statut_valide",
            ),
            models.CheckConstraint(
                condition=models.Q(water_source__in=[e.value for e in Eau]),
                name="listings_eau_valide",
            ),
            models.CheckConstraint(
                condition=models.Q(electricity_meter__in=[c.value for c in Compteur]),
                name="listings_compteur_valide",
            ),
            models.CheckConstraint(
                condition=models.Q(kitchen__in=["", *[c.value for c in Cuisine]]),
                name="listings_cuisine_valide",
            ),
            models.CheckConstraint(
                condition=models.Q(hidden_reason__isnull=True)
                | models.Q(hidden_reason__in=[r.value for r in RaisonMasquage]),
                name="listings_raison_valide",
            ),
        ]
        indexes = [
            models.Index(fields=["status", "-published_at"], name="listings_fil_idx"),
            models.Index(
                fields=["-published_at", "-id"],
                condition=models.Q(status="published"),
                name="listings_fil_publie_idx",
            ),
            models.Index(
                fields=["district", "rent_amount"],
                condition=models.Q(status="published"),
                name="listings_quartier_loyer_idx",
            ),
            models.Index(
                fields=["last_confirmed_at"],
                condition=models.Q(status="published"),
                name="listings_fraicheur_idx",
            ),
            models.Index(fields=["district", "status"], name="listings_quartier_idx"),
            models.Index(fields=["gerant", "status"], name="listings_gerant_idx"),
            models.Index(fields=["rent_amount"], name="listings_loyer_idx"),
            models.Index(fields=["distance_to_campus_m"], name="listings_distance_idx"),
            GinIndex(fields=["search_vector"], name="listings_recherche_idx"),
        ]


class ListingMedia(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="media")
    kind = models.CharField(max_length=5, choices=TypeMedia.choices)
    position = models.SmallIntegerField(default=0, db_default=0)
    is_cover = models.BooleanField(default=False, db_default=False)
    status = models.CharField(
        max_length=12,
        choices=StatutMedia.choices,
        default=StatutMedia.UPLOADING,
        db_default="uploading",
    )
    declared_size_bytes = models.BigIntegerField()
    received_bytes = models.BigIntegerField(default=0, db_default=0)
    upload_expires_at = models.DateTimeField(null=True, blank=True)
    original_path = models.CharField(max_length=255, null=True, blank=True)
    mime_type = models.CharField(max_length=60, null=True, blank=True)
    size_bytes = models.BigIntegerField(null=True, blank=True)
    sha256 = models.CharField(max_length=64, null=True, blank=True)
    width = models.IntegerField(null=True, blank=True)
    height = models.IntegerField(null=True, blank=True)
    duration_s = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    playback_path = models.CharField(max_length=255, null=True, blank=True)
    poster_path = models.CharField(max_length=255, null=True, blank=True)
    variants = models.JSONField(null=True, blank=True)
    error_code = models.CharField(max_length=40, null=True, blank=True)
    error_detail = models.TextField(null=True, blank=True)
    delete_after = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_default=Now())
    updated_at = models.DateTimeField(auto_now=True, db_default=Now())

    class Meta:
        db_table = "listing_media"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(kind__in=["video", "photo"]), name="media_type_valide"
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=[s.value for s in StatutMedia]),
                name="media_statut_valide",
            ),
            models.UniqueConstraint(
                fields=["listing"],
                condition=models.Q(is_cover=True),
                name="media_une_seule_couverture",
            ),
            models.UniqueConstraint(
                fields=["listing"],
                condition=models.Q(kind="video") & ~models.Q(status__in=["deleted", "failed"]),
                name="media_une_seule_video_active",
            ),
        ]
        indexes = [
            models.Index(fields=["listing", "position"], name="media_ordre_idx"),
            models.Index(fields=["sha256"], name="media_sha256_idx"),
        ]


class Favorite(models.Model):
    """Favori d'un locataire (CDC §9.11)."""

    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="+")
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="favorites")
    created_at = models.DateTimeField(default=timezone.now, db_default=Now())

    class Meta:
        db_table = "favorites"
        constraints = [
            models.UniqueConstraint(fields=["user", "listing"], name="favorites_un_par_couple")
        ]
        indexes = [models.Index(fields=["listing"], name="favorites_annonce_idx")]


class Alert(models.Model):
    """Alerte d'un locataire : critères appliqués à chaque publication (CDC §9.12)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="+")
    label = models.CharField(max_length=80, default="", blank=True)
    district_ids = ArrayField(models.UUIDField(), default=list, db_default=[])
    room_types = ArrayField(models.CharField(max_length=40), default=list, db_default=[])
    max_rent = models.IntegerField(null=True, blank=True)
    private_bathroom_required = models.BooleanField(default=False, db_default=False)
    max_distance_m = models.IntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_default=True)
    created_at = models.DateTimeField(default=timezone.now, db_default=Now())
    updated_at = models.DateTimeField(auto_now=True, db_default=Now())

    class Meta:
        db_table = "alerts"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(max_rent__isnull=True) | models.Q(max_rent__gt=0),
                name="alerts_loyer_positif",
            ),
        ]
        indexes = [
            GinIndex(fields=["district_ids"], name="alerts_quartiers_idx"),
            models.Index(fields=["user", "is_active"], name="alerts_utilisateur_idx"),
        ]


class Review(models.Model):
    """Avis d'un locataire sur une chambre, possible seulement après une vraie discussion avec son gérant.

    Publié tout de suite ; la modération peut le masquer (signalement ou contrôle). Un avis par locataire et par
    chambre, modifiable par son auteur."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(
        Listing, on_delete=models.CASCADE, related_name="reviews", verbose_name="annonce"
    )
    author = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="+", verbose_name="auteur"
    )
    rating = models.SmallIntegerField(verbose_name="note")
    comment = models.TextField(default="", db_default="", blank=True, verbose_name="commentaire")
    is_hidden = models.BooleanField(default=False, db_default=False, verbose_name="masqué")
    hidden_reason = models.CharField(
        max_length=200, default="", db_default="", blank=True, verbose_name="raison du masquage"
    )
    created_at = models.DateTimeField(
        default=timezone.now, db_default=Now(), verbose_name="créé le"
    )
    updated_at = models.DateTimeField(auto_now=True, db_default=Now(), verbose_name="modifié le")

    def __str__(self) -> str:
        return f"{self.rating}/5"

    class Meta:
        db_table = "listing_reviews"
        verbose_name = "avis"
        verbose_name_plural = "avis"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(rating__gte=1, rating__lte=5), name="avis_note_1_a_5"
            ),
            models.UniqueConstraint(fields=["listing", "author"], name="avis_un_par_chambre"),
        ]
        indexes = [
            models.Index(fields=["listing", "is_hidden", "-created_at"], name="avis_annonce_idx"),
        ]
