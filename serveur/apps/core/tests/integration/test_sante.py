import pytest
from django.test import Client

pytestmark = [pytest.mark.integration, pytest.mark.pg]


@pytest.mark.django_db
def test_healthz_repond_ok():
    reponse = Client().get("/healthz")
    assert reponse.status_code == 200
    assert reponse.json() == {"status": "ok"}
    assert reponse["Cache-Control"] == "no-store"


@pytest.mark.django_db
def test_readyz_ok_quand_tout_repond(settings):
    reponse = Client().get("/readyz")
    assert reponse.status_code == 200, reponse.content
    assert reponse.json()["controles"] == {
        "base": True,
        "cache": True,
        "file": True,
        "disque": True,
    }


@pytest.mark.django_db
def test_readyz_503_si_redis_injoignable(settings):
    settings.REDIS_QUEUE_URL = "redis://127.0.0.1:1/0"
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
