"""Régression : les services du site et de l'API tournent avec le rôle `app`, qui ne modifie que certaines
colonnes de `users` (jamais `role` ni `created_at`). Un `save()` complet y est refusé par PostgreSQL. Chaque
écriture faite sans code SMS (ADR 0009) est vérifiée ici sous ce rôle."""

from contextlib import contextmanager

import pytest
from django.db import connection

from apps.accounts.models import Statut, User
from apps.accounts.services import administration, compte, identifiants, inscription, mots_de_passe
from apps.accounts.tests.fabriques import MOT_DE_PASSE, AdminFactory, ClientFactory

from .test_api_comptes import FORT

pytestmark = [pytest.mark.api, pytest.mark.pg, pytest.mark.django_db]


@contextmanager
def _en_tant_que_app():
    with connection.cursor() as c:
        c.execute("SET LOCAL ROLE app")
    try:
        yield
    finally:
        with connection.cursor() as c:
            c.execute("RESET ROLE")


def test_inscription_avec_le_role_app():
    with _en_tant_que_app():
        u, cle = inscription.inscrire_client(
            nom_utilisateur="role.app", prenom="Rôle", nom="App",
            mot_de_passe=FORT, cgu_acceptees=True,
        )  # fmt: skip
    assert identifiants.cle_correcte(User.objects.get(pk=u.pk), cle)


def test_cle_de_secours_avec_le_role_app():
    u = ClientFactory(username="role.cle")
    cle = identifiants.nouvelle_cle_de_secours(u)
    u.save()
    with _en_tant_que_app():
        inscription.reinitialiser_par_cle("role.cle", cle, FORT, client="installation-test")
        compte.regenerer_cle_de_secours(User.objects.get(pk=u.pk), FORT)
    assert mots_de_passe.verifier(User.objects.get(pk=u.pk), FORT)


def test_lien_de_l_equipe_avec_le_role_app():
    u = ClientFactory()
    url = administration.lien_reinitialisation(acteur=AdminFactory(), cible=u)
    with _en_tant_que_app():
        inscription.reinitialiser_par_lien(url.rsplit("/", 1)[1], FORT)
    assert mots_de_passe.verifier(User.objects.get(pk=u.pk), FORT)


def test_profil_et_email_avec_le_role_app():
    u = ClientFactory()
    with _en_tant_que_app():
        moi = User.objects.get(pk=u.pk)
        compte.modifier_profil(moi, prenom="Aïcha", nom="Sanni")
        compte.confirmer_email(identifiants.creer_jeton(moi, "email", a="aicha@exemple.bj"))
    moi = User.objects.get(pk=u.pk)
    assert (moi.full_name, moi.email) == ("Aïcha Sanni", "aicha@exemple.bj")


def test_activation_d_un_gerant_avec_le_role_app():
    gerant = administration.creer_gerant(
        acteur=AdminFactory(), prenom="Kofi", nom="Gérant", zone="Zongo"
    )
    url = administration.lien_activation(acteur=AdminFactory(), gerant=gerant)
    with _en_tant_que_app():
        administration.activer_gerant(
            url.rsplit("/", 1)[1], nom_utilisateur="kofi.gerant", mot_de_passe=FORT
        )
    assert User.objects.get(pk=gerant.pk).username == "kofi.gerant"


def test_suppression_du_compte_avec_le_role_app():
    u = ClientFactory()
    with _en_tant_que_app():
        compte.supprimer(User.objects.get(pk=u.pk), MOT_DE_PASSE)
    assert User.objects.get(pk=u.pk).status == Statut.DELETED
