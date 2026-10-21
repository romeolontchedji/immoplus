import pytest
from rest_framework.test import APIRequestFactory

from apps.core.api.permissions import RefusParDefaut
from config import env

pytestmark = pytest.mark.unitaire


def test_refus_par_defaut():
    requete = APIRequestFactory().get("/")
    assert RefusParDefaut().has_permission(requete, None) is False


@pytest.mark.parametrize(
    ("valeur", "attendu"),
    [("1", True), ("oui", True), ("TRUE", True), ("0", False), ("non", False), ("", False)],
)
def test_booleen(monkeypatch, valeur, attendu):
    monkeypatch.setenv("IMMOPLUS_X", valeur)
    assert env.booleen("IMMOPLUS_X") is attendu


def test_booleen_absent_utilise_le_defaut(monkeypatch):
    monkeypatch.delenv("IMMOPLUS_X", raising=False)
    assert env.booleen("IMMOPLUS_X", True) is True


def test_entier_et_liste(monkeypatch):
    monkeypatch.setenv("IMMOPLUS_N", "42")
    monkeypatch.setenv("IMMOPLUS_L", "a, b ,, c")
    assert env.entier("IMMOPLUS_N") == 42
    assert env.entier("IMMOPLUS_ABSENT", 7) == 7
    assert env.liste("IMMOPLUS_L") == ["a", "b", "c"]
    assert env.liste("IMMOPLUS_ABSENT") == []


def test_application_celery_routes_par_file(settings):
    from config.celery import app

    assert app.conf.task_default_queue == "default"
    assert app.conf.task_routes["apps.media.*"] == {"queue": "media"}
    assert app.conf.task_routes["apps.notifications.*"] == {"queue": "notifications"}
