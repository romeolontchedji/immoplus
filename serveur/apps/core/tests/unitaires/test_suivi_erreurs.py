"""Suivi des erreurs : regroupement, masquage, courriel limité à un par heure et par erreur."""

import logging

import pytest
from django.core import mail

from apps.core import erreurs, redis_file

pytestmark = [pytest.mark.pg, pytest.mark.django_db]


@pytest.fixture(autouse=True)
def redis_vide():
    redis_file.reinitialiser()
    client = redis_file.client()
    client.flushall()
    yield
    client.flushall()


def _planter(numero="97123456"):
    try:
        raise ValueError(f"échec pour le numéro {numero}")
    except ValueError:
        logging.getLogger("apps.essai").exception("Traitement impossible pour %s", numero)


def test_erreurs_identiques_regroupees_et_masquees(settings):
    settings.ERREURS_DESTINATAIRES = ["equipe@immoplus.bj"]
    _planter()
    _planter("96000000")
    [e] = erreurs.liste()
    assert e["type"] == "ValueError" and e["nombre"] == 2
    assert "test_suivi_erreurs.py" in e["lieu"]
    assert "97123456" not in e["detail"] and "96000000" not in e["message"]  # numéros masqués
    assert len(mail.outbox) == 1  # un seul courriel pour deux occurrences dans l'heure
    assert "ValueError" in mail.outbox[0].subject and mail.outbox[0].to == ["equipe@immoplus.bj"]


def test_sans_destinataire_aucun_courriel(settings):
    settings.ERREURS_DESTINATAIRES = []
    _planter()
    assert erreurs.liste() and mail.outbox == []


def test_corrigee_puis_revenue(settings):
    settings.ERREURS_DESTINATAIRES = ["equipe@immoplus.bj"]
    _planter()
    erreurs.resoudre(erreurs.liste()[0]["id"])
    assert erreurs.liste() == []
    _planter()
    assert erreurs.liste()[0]["nombre"] == 1 and len(mail.outbox) == 2


def test_redis_absent_ne_casse_rien(monkeypatch):
    def panne():
        raise ConnectionError("redis absent")

    monkeypatch.setattr(redis_file, "client", panne)
    _planter()  # aucune exception ne remonte
