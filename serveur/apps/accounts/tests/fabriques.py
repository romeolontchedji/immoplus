"""Fabriques de données de test pour les comptes."""

import factory
from django.contrib.auth.hashers import make_password
from django.utils import timezone

from apps.accounts.models import Device, GerantProfile, Role, User

MOT_DE_PASSE = "motdepasse-solide-1"


class ClientFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"locataire{n}")
    first_name = "Locataire"
    last_name = factory.Sequence(lambda n: f"N{n}")
    full_name = factory.Sequence(lambda n: f"Locataire {n}")
    role = Role.CLIENT
    terms_version = "1"
    terms_accepted_at = factory.LazyFunction(timezone.now)
    password = factory.LazyFunction(lambda: make_password(MOT_DE_PASSE))


class GerantFactory(ClientFactory):
    role = Role.GERANT
    username = factory.Sequence(lambda n: f"gerant{n}")
    first_name = "Gérant"
    full_name = factory.Sequence(lambda n: f"Gérant {n}")


class PersonnelFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"personnel{n}@immoplus.test")
    full_name = factory.Sequence(lambda n: f"Personnel {n}")
    role = Role.MODERATOR
    password = factory.LazyFunction(lambda: make_password(MOT_DE_PASSE))


class AdminFactory(PersonnelFactory):
    role = Role.ADMIN
    email = factory.Sequence(lambda n: f"admin{n}@immoplus.test")


class GerantProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GerantProfile

    user = factory.SubFactory(GerantFactory)
    zone = "Banikanni"
    created_by = factory.SubFactory(AdminFactory)


class DeviceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Device

    user = factory.SubFactory(ClientFactory)
    installation_id = factory.Sequence(lambda n: f"install-{n:08d}")
    platform = "android"
    refresh_expires_at = factory.LazyFunction(lambda: timezone.now() + timezone.timedelta(days=30))
