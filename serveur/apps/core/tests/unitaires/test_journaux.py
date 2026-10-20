import json
import logging

import pytest

from apps.core.logging import FormateurJson, masquer

pytestmark = pytest.mark.unitaire


@pytest.mark.parametrize(
    "texte",
    [
        "appel du 97 12 34 56",
        "numéro +229 97 12 34 56 reçu",
        "tel 0197123456",
        "00229 97-12-34-56",
        "97.12.34.56",
    ],
)
def test_masque_les_numeros(texte):
    assert "97" not in masquer(texte).replace("[masqué]", "")
    assert "[masqué]" in masquer(texte)


@pytest.mark.parametrize("texte", ["code 123456", "OTP: 654321", "otp=111222"])
def test_masque_les_codes_otp(texte):
    sortie = masquer(texte)
    assert "[masqué]" in sortie
    assert not any(c.isdigit() for c in sortie)


def test_ne_masque_pas_un_prix():
    assert masquer("loyer 25 000 FCFA") == "loyer 25 000 FCFA"


def test_formateur_json_valide():
    enregistrement = logging.LogRecord(
        "immoplus", logging.INFO, __file__, 1, "bonjour %s", ("monde",), None
    )
    donnees = json.loads(FormateurJson().format(enregistrement))
    assert donnees["message"] == "bonjour monde"
    assert {"ts", "niveau", "logger", "id_requete"} <= donnees.keys()
