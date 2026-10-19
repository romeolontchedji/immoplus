import pytest
from django.test import Client

pytestmark = [pytest.mark.integration, pytest.mark.pg]


@pytest.mark.django_db
def test_healthz_repond_ok():
    reponse = Client().get("/healthz")
    assert reponse.status_code == 200
    assert reponse.json() == {"status": "ok"}
    assert reponse["Cache-Control"] == "no-store"


def _disque(monkeypatch, occupe_pourcent: int) -> None:
    """Le contrôle « disque » lit l'occupation réelle : on la fixe pour ne pas dépendre de la machine de test."""
    import shutil
    from collections import namedtuple

    Usage = namedtuple("Usage", "total used free")
    monkeypatch.setattr(
        shutil, "disk_usage", lambda _chemin: Usage(100, occupe_pourcent, 100 - occupe_pourcent)
    )


@pytest.mark.django_db
def test_readyz_ok_quand_tout_repond(settings, monkeypatch):
    _disque(monkeypatch, 40)
    reponse = Client().get("/readyz")
    assert reponse.status_code == 200, reponse.content
    assert reponse.json()["controles"] == {
        "base": True,
        "cache": True,
        "file": True,
        "disque": True,
    }


@pytest.mark.django_db
def test_readyz_503_si_redis_injoignable(settings, monkeypatch):
    import redis

    from apps.core import redis_file

    monkeypatch.setattr(
        redis_file,
        "client",
        lambda: redis.Redis.from_url("redis://127.0.0.1:1/0", socket_timeout=1),
    )
    reponse = Client().get("/readyz")
    assert reponse.status_code == 503
    assert reponse.json()["controles"]["file"] is False
    assert reponse.json()["status"] == "indisponible"


@pytest.mark.django_db
def test_readyz_503_si_disque_plein(settings):
    settings.MEDIA_DISK_REFUS_POURCENT = 0
    reponse = Client().get("/readyz")
    assert reponse.status_code == 503
    assert reponse.json()["controles"]["disque"] is False


def test_healthz_refuse_post():
    assert Client().post("/healthz").status_code == 405


@pytest.mark.django_db
def test_readyz_503_si_le_disque_depasse_85_pour_cent(monkeypatch):
    _disque(monkeypatch, 90)
    reponse = Client().get("/readyz")
    assert reponse.status_code == 503 and reponse.json()["controles"]["disque"] is False
