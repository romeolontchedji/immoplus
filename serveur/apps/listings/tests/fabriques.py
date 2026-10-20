import factory
from django.utils import timezone

from apps.accounts.models import StatutVerification
from apps.accounts.tests.fabriques import AdminFactory, GerantFactory, GerantProfileFactory

from ..models import District, Listing, ListingMedia


class DistrictFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = District

    name = factory.Sequence(lambda n: f"Quartier {n}")
    slug = factory.Sequence(lambda n: f"quartier-{n}")
    latitude = 9.34
    longitude = 2.63


def gerant_verifie(**kw):
    p = GerantProfileFactory(**kw)
    p.verification_status = StatutVerification.VERIFIED
    p.verified_at = timezone.now()
    type(p).complets.filter(pk=p.pk).update(
        verification_status="verified", verified_at=p.verified_at
    )
    p.refresh_from_db()
    return p


def donnees_annonce(quartier, **extra):
    return {
        "title": "Chambre propre près du campus",
        "room_type": "single",
        "district": str(quartier.pk),
        "landmark_text": "Derrière la pharmacie du carrefour",
        "address_private": "Rue 12, maison bleue",
        "latitude": "9.340000",
        "longitude": "2.633000",
        "rent_amount": 25000,
        "deposit_months": 2,
        "advance_months": 1,
        "available_from": "2026-11-01",
        "has_private_bathroom": True,
        "is_fenced": True,
        "water_sources": ["running"],
        "electricity_meter": "individual",
        "description_md": "Chambre **calme**, eau courante.\n\n- Douche interne\n- Portail",
        **extra,
    }


def medias_prets(annonce, photos=3, video=True):
    if video:
        ListingMedia.objects.create(
            listing=annonce, kind="video", status="ready", declared_size_bytes=1
        )
    for i in range(photos):
        ListingMedia.objects.create(
            listing=annonce,
            kind="photo",
            status="ready",
            declared_size_bytes=1,
            position=i,
            is_cover=(i == 0),
        )


class ListingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Listing

    gerant = factory.SubFactory(GerantProfileFactory)
    slug = factory.Sequence(lambda n: f"annonce-{n}")
    title = factory.Sequence(lambda n: f"Chambre numéro {n}")
    room_type = "single"
    district = factory.SubFactory(DistrictFactory)
    landmark_text = "Près du marché"
    latitude = 9.34
    longitude = 2.633
    distance_to_campus_m = 500
    rent_amount = 25000
    deposit_months = 2
    advance_months = 1
    available_from = "2026-11-01"
    has_private_bathroom = True
    is_fenced = True
    water_sources = factory.LazyFunction(lambda: ["running"])
    electricity_meter = "individual"
    status = "published"
    published_at = factory.LazyFunction(timezone.now)


__all__ = ["AdminFactory", "GerantFactory"]
