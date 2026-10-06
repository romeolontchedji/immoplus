import fakeredis
import pytest

from apps.core.verrou import VerrouRedis

pytestmark = pytest.mark.unitaire


@pytest.fixture
def client():
    return fakeredis.FakeRedis()


def test_un_seul_detenteur(client):
    a, b = VerrouRedis(client, "k"), VerrouRedis(client, "k")
    assert a.acquerir() is True
    assert b.acquerir() is False


def test_renouvellement_reserve_au_detenteur(client):
    a, b = VerrouRedis(client, "k"), VerrouRedis(client, "k")
    a.acquerir()
    assert a.renouveler() is True
    assert b.renouveler() is False


def test_liberation_reserve_au_detenteur(client):
    a, b = VerrouRedis(client, "k"), VerrouRedis(client, "k")
    a.acquerir()
    assert b.liberer() is False
    assert a.liberer() is True
    assert b.acquerir() is True


def test_le_verrou_expire(client):
    a, b = VerrouRedis(client, "k", duree_s=1), VerrouRedis(client, "k")
    a.acquerir()
    client.expire("k", 0)
    assert a.renouveler() is False
    assert b.acquerir() is True


def test_ancien_detenteur_ne_reprend_pas_la_main(client):
    a, b = VerrouRedis(client, "k"), VerrouRedis(client, "k")
    a.acquerir()
    client.delete("k")
    b.acquerir()
    assert a.renouveler() is False
    assert a.liberer() is False
