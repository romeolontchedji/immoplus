"""Application installable (PWA) : manifeste, service worker, page hors ligne, invitation après connexion."""

import json
import pathlib
import re

import pytest
from django.conf import settings
from django.test import Client

from apps.accounts.tests.fabriques import ClientFactory
from apps.core import parametres

pytestmark = [pytest.mark.integration, pytest.mark.pg, pytest.mark.django_db]


def connecte(utilisateur) -> Client:
    c = Client()
    c.force_login(utilisateur, backend="django.contrib.auth.backends.ModelBackend")
    session = c.session
    session["tv"] = utilisateur.token_version
    session.save()
    return c


def test_le_manifeste_rend_le_site_installable():
    r = Client().get("/manifest.webmanifest")
    assert r.status_code == 200 and r["Content-Type"].startswith("application/manifest+json")
    m = json.loads(r.content)
    assert m["display"] == "standalone" and m["start_url"].startswith("/") and m["scope"] == "/"
    assert m["short_name"] == "Immo+" and m["lang"] == "fr"
    tailles = {i["sizes"] for i in m["icons"]}
    assert {"192x192", "512x512"} <= tailles
    assert any(i["purpose"] == "maskable" for i in m["icons"])


def test_les_icones_du_manifeste_existent():
    racine = pathlib.Path(settings.BASE_DIR) / "web" / "static" / "design" / "icones"
    for nom in ("icone-192.png", "icone-512.png", "apple-touch-icon.png"):
        assert (racine / nom).is_file(), nom


def test_le_service_worker_est_servi_a_la_racine_sans_cache():
    r = Client().get("/sw.js")
    assert r.status_code == 200 and "javascript" in r["Content-Type"]
    assert r["Cache-Control"] == "no-cache"
    code = r.content.decode()
    assert "/hors-ligne" in code and "addEventListener" in code
    # Aucune page n'est gardée en mémoire (comptes, messages, alertes) : seules les navigations ont un repli.
    assert 'requete.mode === "navigate"' in code and "/static/" in code


def test_la_page_hors_ligne_s_affiche_sans_compte():
    r = Client().get("/hors-ligne")
    assert r.status_code == 200 and "Pas de connexion" in r.content.decode()


def test_la_tete_des_pages_declare_l_application():
    page = Client().get("/").content.decode()
    assert 'rel="manifest" href="/manifest.webmanifest"' in page
    assert 'name="theme-color"' in page and "apple-touch-icon" in page
    assert "js/pwa" in page


def test_l_invitation_a_installer_n_est_montree_qu_apres_connexion():
    visiteur = Client().get("/annonces").content.decode()
    assert "data-installer-action" not in visiteur
    connecte_page = connecte(ClientFactory()).get("/annonces").content.decode()
    assert "data-installer-action" in connecte_page and "Installe Immo+" in connecte_page
    # Cachée jusqu'à ce que le navigateur la propose.
    assert re.search(r"data-installer\s+hidden", connecte_page)


def test_le_manifeste_et_le_service_worker_restent_lisibles_en_maintenance():
    parametres.definir("SITE_MAINTENANCE_ENABLED", True)
    try:
        assert Client().get("/manifest.webmanifest").status_code == 200
        assert Client().get("/sw.js").status_code == 200
        assert Client().get("/annonces").status_code == 503
    finally:
        parametres.definir("SITE_MAINTENANCE_ENABLED", False)
