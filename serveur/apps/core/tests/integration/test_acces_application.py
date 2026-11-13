"""Mise à jour obligatoire (426) et maintenance (503) : API et site, jamais l'administration ni app-config."""

import pytest
from django.test import Client
from rest_framework.test import APIClient

from apps.core import parametres
from apps.core.acces_application import est_inferieure

pytestmark = [pytest.mark.integration, pytest.mark.pg, pytest.mark.django_db]


@pytest.mark.parametrize(
    "installee,minimale,attendu",
    [("1.0.0", "1.0.1", True), ("1.10.0", "1.9.0", False), ("1.0", "1.0.0", False), ("2", "1.9.9", False),
     ("abc", "1.0.0", False), ("1.0.0", "1.0.0", False)],
)  # fmt: skip
def test_comparaison_des_versions(installee, minimale, attendu):
    assert est_inferieure(installee, minimale) is attendu


def test_version_trop_ancienne_426():
    parametres.definir("MIN_SUPPORTED_VERSION", "2.0.0")
    c = APIClient(HTTP_X_APP_VERSION="1.4.0")
    r = c.get("/v1/listings")
    assert r.status_code == 426 and r.json()["error"]["code"] == "upgrade_required"
    assert c.get("/v1/app-config").status_code == 200  # l'app doit pouvoir lire la version minimale
    assert APIClient(HTTP_X_APP_VERSION="2.0.0").get("/v1/listings").status_code == 200
    assert (
        APIClient().get("/v1/listings").status_code == 200
    )  # sans en-tête (site, outils) : pas de blocage


def test_maintenance_de_l_application_coupe_l_api_et_pas_le_site():
    parametres.definir("MAINTENANCE_ENABLED", True)
    parametres.definir("MAINTENANCE_MESSAGE", "Mise à jour des serveurs jusqu'à 14 h.")
    try:
        r = APIClient().get("/v1/listings")
        assert (
            r.status_code == 503
            and r.json()["error"]["code"] == "maintenance"
            and r["Retry-After"] == "300"
        )
        assert APIClient().get("/v1/app-config").json()["maintenance"]["active"] is True
        assert APIClient().get("/v1/legal/conditions").status_code == 200
        assert Client().get("/").status_code == 200  # le site web reste ouvert
    finally:
        parametres.definir("MAINTENANCE_ENABLED", False)


def test_maintenance_du_site_coupe_le_site_et_pas_l_application():
    parametres.definir("SITE_MAINTENANCE_ENABLED", True)
    parametres.definir("MAINTENANCE_MESSAGE", "Mise à jour des serveurs jusqu'à 14 h.")
    try:
        page = Client().get("/")
        assert page.status_code == 503 and "jusqu&#x27;à 14 h" in page.content.decode()
        assert page["Retry-After"] == "300"
        assert Client().get("/conditions").status_code == 503
        assert Client().get("/annonces").status_code == 503
        # toujours ouverts : santé, fichiers, paiement reçu de KKiaPay, textes légaux de l'API
        assert Client().get("/healthz").status_code == 200
        webhook = Client().post("/paiement/webhook/kkiapay")
        assert "revient tout de suite" not in webhook.content.decode()  # pas la page de maintenance
        assert APIClient().get("/v1/legal/conditions").status_code == 200
        # l'application mobile continue de fonctionner
        assert APIClient().get("/v1/listings").status_code == 200
        assert APIClient().get("/v1/app-config").json()["maintenance"]["active"] is False
    finally:
        parametres.definir("SITE_MAINTENANCE_ENABLED", False)
