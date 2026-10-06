import pytest

from apps.core import requete

pytestmark = pytest.mark.unitaire


def test_reprend_un_identifiant_sain():
    assert requete.nouvel_identifiant("abcd1234-ef56") == "abcd1234-ef56"


@pytest.mark.parametrize(
    "mauvais", [None, "", "court", "a b c d e f g h", "x" * 65, "<script>alert(1)</script>"]
)
def test_remplace_un_identifiant_douteux(mauvais):
    nouveau = requete.nouvel_identifiant(mauvais)
    assert nouveau != mauvais
    assert len(nouveau) == 32
