import pytest
from django.test import Client

pytestmark = [pytest.mark.integration, pytest.mark.securite]


def test_csp_sans_script_ni_style_en_ligne():
    reponse = Client().get("/healthz")
    csp = reponse["Content-Security-Policy"]
    assert "'unsafe-inline'" not in csp
    assert "'unsafe-eval'" not in csp
    assert "script-src 'self' https://challenges.cloudflare.com" in csp
    assert "frame-ancestors 'none'" in csp
    assert "object-src 'none'" in csp


def test_identifiant_de_requete_propage():
    reponse = Client().get("/healthz", headers={"X-Request-ID": "abcdef12-3456"})
    assert reponse["X-Request-ID"] == "abcdef12-3456"


def test_identifiant_de_requete_genere():
    reponse = Client().get("/healthz")
    assert len(reponse["X-Request-ID"]) == 32


def test_autres_en_tetes_de_securite():
    reponse = Client().get("/healthz")
    assert reponse["X-Content-Type-Options"] == "nosniff"
    assert reponse["Referrer-Policy"] == "same-origin"
    assert reponse["X-Frame-Options"] == "DENY"
    assert "camera=()" in reponse["Permissions-Policy"]
