"""Fabriques de données de test pour les comptes."""

import itertools

import factory
from django.contrib.auth.hashers import make_password
from django.utils import timezone

from apps.accounts.models import Device, GerantProfile, Role, User

_compteur = itertools.count(1)
MOT_DE_PASSE = "motdepasse-solide-1"


def _numero(n: int) -> str:
    # Mobiles béninois valides : +22901 puis 8 chiffres commençant par 97.
    return f"+2290197{n:06d}"


class ClientFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    phone_e164 = factory.LazyFunction(lambda: _numero(next(_compteur)))
    full_name = factory.Sequence(lambda n: f"Locataire {n}")
    role = Role.CLIENT
    phone_verified_at = factory.LazyFunction(timezone.now)
    terms_version = "1"
    terms_accepted_at = factory.LazyFunction(timezone.now)
    password = factory.LazyFunction(lambda: make_password(MOT_DE_PASSE))


class GerantFactory(ClientFactory):
    role = Role.GERANT
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
