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
    monkeypatch.setenv("LOGEO_X", valeur)
    assert env.booleen("LOGEO_X") is attendu


def test_booleen_absent_utilise_le_defaut(monkeypatch):
    monkeypatch.delenv("LOGEO_X", raising=False)
    assert env.booleen("LOGEO_X", True) is True


def test_entier_et_liste(monkeypatch):
    monkeypatch.setenv("LOGEO_N", "42")
    monkeypatch.setenv("LOGEO_L", "a, b ,, c")
    assert env.entier("LOGEO_N") == 42
    assert env.entier("LOGEO_ABSENT", 7) == 7
    assert env.liste("LOGEO_L") == ["a", "b", "c"]
    assert env.liste("LOGEO_ABSENT") == []


def test_application_celery_routes_par_file(settings):
    from config.celery import app

    assert app.conf.task_default_queue == "default"
    assert app.conf.task_routes["apps.media.*"] == {"queue": "media"}
    assert app.conf.task_routes["apps.notifications.*"] == {"queue": "notifications"}
