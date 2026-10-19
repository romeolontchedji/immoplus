"""Régression : les services du site et de l'API tournent avec le rôle `app`, qui ne modifie que certaines
colonnes de `users` (pas `email`, `role`, `created_at`). Un `save()` complet y est refusé par PostgreSQL."""

from contextlib import contextmanager

import pytest
from django.db import connection

from apps.accounts.models import Statut, User
from apps.accounts.services import compte, inscription, mots_de_passe
from apps.accounts.tests.fabriques import MOT_DE_PASSE, ClientFactory

from .test_api_comptes import E164, FORT, api, obtenir_jeton_otp

pytestmark = [pytest.mark.api, pytest.mark.pg, pytest.mark.django_db]


@pytest.fixture(autouse=True)
def code_otp_fixe(settings):
    settings.OTP_DEBUG_CODE = "424242"


@contextmanager
def _en_tant_que_app():
    with connection.cursor() as c:
        c.execute("SET LOCAL ROLE app")
    try:
        yield
    finally:
        with connection.cursor() as c:
            c.execute("RESET ROLE")


def test_mot_de_passe_oublie_avec_le_role_app(django_capture_on_commit_callbacks):
    ClientFactory(phone_e164=E164)
    jeton = obtenir_jeton_otp(api(), "reset_password", capture=django_capture_on_commit_callbacks)
    with _en_tant_que_app():
        inscription.reinitialiser_mot_de_passe(jeton, FORT)
    assert mots_de_passe.verifier(User.objects.get(phone_e164=E164), FORT)


def test_suppression_du_compte_avec_le_role_app():
    u = ClientFactory()
    with _en_tant_que_app():
        compte.supprimer(User.objects.get(pk=u.pk), MOT_DE_PASSE)
    assert User.objects.get(pk=u.pk).status == Statut.DELETED
