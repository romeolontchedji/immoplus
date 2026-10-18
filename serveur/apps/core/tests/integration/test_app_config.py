"""GET /v1/app-config (CDC §10) et contact de l'équipe servi au site."""

import pytest
from django.test import Client

from apps.core import configuration, parametres

pytestmark = [pytest.mark.integration, pytest.mark.pg, pytest.mark.django_db]


def test_app_config_publique_et_complete():
    r = Client().get("/v1/app-config")
    assert r.status_code == 200, r.content
    corps = r.json()
    assert corps["min_supported_version"] == "1.0.0"
    assert corps["maintenance"] == {"active": False, "message": ""}
    assert corps["flags"]["subscription"] is False  # paiement débranché en V1
    # Alertes payantes des locataires : désactivées en V1.
    assert corps["flags"]["paid_alerts"] is False
    assert corps["limits"]["photos_max"] == 10 and corps["limits"]["message_max_length"] == 2000
    assert corps["realtime"]["path"] == "/ws/v1/"
    assert corps["contact"] == {
        "phone": "+2290156201400",
        "whatsapp_url": "https://wa.me/2290156201400",
    }


def test_maintenance_pilotee_par_parametre():
    parametres.definir("MAINTENANCE_ENABLED", True)
    parametres.definir("MAINTENANCE_MESSAGE", "Retour à 14 h.")
    corps = Client().get("/v1/app-config").json()
    assert corps["maintenance"] == {"active": True, "message": "Retour à 14 h."}


def test_abonnement_reste_faux_meme_si_le_parametre_est_vrai():
    parametres.definir("SUBSCRIPTION_ENABLED", True)
    assert Client().get("/v1/app-config").json()["flags"]["subscription"] is False


def test_contact_equipe_formate():
    assert configuration.contact_equipe() == {
        "phone": "+2290156201400",
        "phone_display": "+229 01 56 20 14 00",
        "tel_url": "tel:+2290156201400",
        "whatsapp_url": "https://wa.me/2290156201400",
    }


def test_pied_de_page_utilise_le_bon_numero():
    html = Client().get("/").content.decode()
    assert 'href="https://wa.me/2290156201400"' in html
    assert "22901562014000" not in html  # ancien lien avec un 0 de trop


def test_alertes_payantes_restent_cachees_meme_si_le_parametre_est_active():
    from apps.core import parametres

    parametres.definir("PAID_ALERTS_ENABLED", True)
    try:
        assert Client().get("/v1/app-config").json()["flags"]["paid_alerts"] is False
    finally:
        parametres.definir("PAID_ALERTS_ENABLED", False)
