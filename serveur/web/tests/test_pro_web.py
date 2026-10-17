import pytest
from django.test import Client

from apps.accounts.tests.fabriques import MOT_DE_PASSE, ClientFactory
from apps.listings.models import Listing
from apps.listings.tests.fabriques import (
    DistrictFactory,
    ListingFactory,
    gerant_verifie,
    medias_prets,
)

pytestmark = [pytest.mark.integration, pytest.mark.pg, pytest.mark.django_db]


@pytest.fixture
def session_gerant():
    g = gerant_verifie()
    c = Client()
    c.post("/connexion", {"phone": g.user.phone_e164[4:], "password": MOT_DE_PASSE})
    return c, g


def formulaire(quartier, **extra):
    return {
        "action": "enregistrer", "title": "Chambre propre près du campus", "room_type": "single", "district": str(quartier.pk),
        "landmark_text": "Derrière la pharmacie", "address_private": "",
        "rent_amount": "25000", "deposit_months": "2", "advance_months": "1", "agent_fee_amount": "0",
        "available_from": "2026-11-01", "has_private_bathroom": "on", "is_fenced": "on", "water_source": "running",
        "electricity_meter": "individual", "description_md": "Chambre **calme**", **extra,
    }  # fmt: skip


def test_creation_puis_edition(session_gerant):
    c, g = session_gerant
    q = DistrictFactory()
    r = c.post("/pro/annonces/nouvelle", formulaire(q))
    assert r.status_code == 302
    a = Listing.objects.get()
    assert a.gerant == g and r["Location"] == f"/pro/annonces/{a.pk}"
    r = c.post(f"/pro/annonces/{a.pk}", formulaire(q, rent_amount="30000"))
    assert r.status_code == 200 and "enregistrée" in r.content.decode()
    a.refresh_from_db()
    assert a.rent_amount == 30000
    assert "Mes annonces" in c.get("/pro/annonces").content.decode()


def test_coordonnees_refusees_dans_le_formulaire(session_gerant):
    c, _ = session_gerant
    r = c.post(
        "/pro/annonces/nouvelle",
        formulaire(DistrictFactory(), description_md="Appelle le 97 12 34 56"),
    )
    assert (
        r.status_code == 200 and "interdites" in r.content.decode() and not Listing.objects.exists()
    )


def test_publication_signale_ce_qui_manque(session_gerant):
    c, g = session_gerant
    q = DistrictFactory()
    c.post("/pro/annonces/nouvelle", formulaire(q))
    a = Listing.objects.get()
    r = c.post(f"/pro/annonces/{a.pk}", {"action": "publier"})
    assert "pas encore prête" in r.content.decode()
    medias_prets(a)
    ListingFactory(gerant=g)
    c.post(f"/pro/annonces/{a.pk}", {"action": "publier"})
    a.refresh_from_db()
    assert a.status == "published"


def test_un_locataire_n_a_pas_d_espace_gerant():
    ClientFactory(phone_e164="+2290197343434")
    c = Client()
    c.post("/connexion", {"phone": "97343434", "password": MOT_DE_PASSE})
    assert c.get("/pro/annonces").status_code == 404
    assert c.get("/pro/dashboard").status_code == 404


def test_tableau_de_bord_affiche_les_indicateurs(session_gerant):
    c, g = session_gerant
    ListingFactory(gerant=g, status="published")
    ListingFactory(gerant=g, status="draft")
    html = c.get("/pro/dashboard").content.decode()
    assert "Tableau de bord" in html
    assert "Publiées" in html and "Brouillons" in html


def test_mes_annonces_montre_les_commandes_du_statut(session_gerant):
    c, g = session_gerant
    brouillon = ListingFactory(gerant=g, status="draft")
    publiee = ListingFactory(gerant=g, status="published")
    html = c.get("/pro/annonces").content.decode()
    assert f"/pro/annonces/{brouillon.pk}" in html
    assert "Supprimer" in html and "Confirmer la disponibilité" in html
    assert publiee.title in html


def test_le_dashboard_d_un_autre_gerant_ne_fuit_pas(session_gerant):
    c, _ = session_gerant
    ListingFactory(status="published", title="Annonce secrete")
    assert "Annonce secrete" not in c.get("/pro/dashboard").content.decode()


def test_anonyme_redirige_vers_la_connexion():
    assert Client().get("/pro/annonces")["Location"].startswith("/connexion")


def test_l_annonce_d_un_autre_gerant_est_introuvable(session_gerant):
    c, _ = session_gerant
    autre = ListingFactory()
    assert c.get(f"/pro/annonces/{autre.pk}").status_code == 404
    assert c.post(f"/pro/annonces/{autre.pk}", {"action": "masquer"}).status_code == 404


def test_gerer_les_medias_couverture_ordre_suppression(session_gerant):
    c, g = session_gerant
    a = ListingFactory(gerant=g, status="draft")
    medias_prets(a, photos=3, video=False)
    page = c.get(f"/pro/annonces/{a.pk}").content.decode()
    assert "Définir en couverture" in page and "Monter" in page and "Descendre" in page
    assert (
        '<details class="confirmation">' in page and 'name="action" value="media-supprimer"' in page
    )

    couv = a.media.get(is_cover=True)
    autre = a.media.filter(is_cover=False).first()
    c.post(f"/pro/annonces/{a.pk}", {"action": "couvrir", "media_id": str(autre.pk)})
    couv.refresh_from_db()
    autre.refresh_from_db()
    assert autre.is_cover and not couv.is_cover

    premier = a.media.order_by("position").first()
    c.post(f"/pro/annonces/{a.pk}", {"action": "descendre", "media_id": str(premier.pk)})
    assert a.media.order_by("position").first().pk != premier.pk

    restant = a.media.exclude(status="deleted").count()
    c.post(f"/pro/annonces/{a.pk}", {"action": "media-supprimer", "media_id": str(premier.pk)})
    assert a.media.exclude(status="deleted").count() == restant - 1


def test_l_editeur_affiche_l_apercu_de_la_carte(session_gerant):
    c, g = session_gerant
    a = ListingFactory(gerant=g, status="draft", title="Chambre apercu")
    medias_prets(a, photos=1, video=False)
    page = c.get(f"/pro/annonces/{a.pk}").content.decode()
    assert "Aperçu" in page and "Chambre apercu" in page and "carte carte--interactive" in page


def test_la_suppression_d_un_brouillon_passe_par_une_confirmation(session_gerant):
    c, g = session_gerant
    ListingFactory(gerant=g, status="draft")
    page = c.get("/pro/annonces").content.decode()
    assert '<details class="confirmation">' in page and 'name="action" value="supprimer"' in page


def test_un_media_d_une_autre_annonce_ne_se_supprime_pas(session_gerant):
    c, g = session_gerant
    mienne = ListingFactory(gerant=g, status="draft")
    autre = ListingFactory(status="draft")
    medias_prets(autre, photos=1, video=False)
    media = autre.media.first()
    r = c.post(
        f"/pro/annonces/{mienne.pk}", {"action": "media-supprimer", "media_id": str(media.pk)}
    )
    assert r.status_code == 200
    media.refresh_from_db()
    assert media.status != "deleted"


def test_la_page_d_edition_charge_le_script_d_envoi_externe(session_gerant):
    c, g = session_gerant
    a = ListingFactory(gerant=g, status="draft")
    html = c.get(f"/pro/annonces/{a.pk}").content.decode()
    assert "js/envoi.js" in html and 'id="envoi-medias"' in html
    assert "<script>" not in html and " onclick=" not in html


def test_envoi_depuis_le_site_avec_session_et_csrf(
    session_gerant, settings, tmp_path, django_capture_on_commit_callbacks
):
    import io

    from PIL import Image

    settings.MEDIA_TMP_ROOT, settings.MEDIA_ROOT = tmp_path / "t", tmp_path / "p"
    c, g = session_gerant
    a = ListingFactory(gerant=g, status="draft")
    c = Client(enforce_csrf_checks=True)
    c.post(
        "/connexion",
        {
            "phone": g.user.phone_e164[4:],
            "password": MOT_DE_PASSE,
            "csrfmiddlewaretoken": _jeton(c),
        },
    )
    jeton = _jeton(c, f"/pro/annonces/{a.pk}")
    tampon = io.BytesIO()
    Image.new("RGB", (300, 200)).save(tampon, "JPEG")
    donnees = tampon.getvalue()
    sans = c.post(
        f"/v1/pro/listings/{a.pk}/media",
        {"kind": "photo", "size_bytes": len(donnees)},
        content_type="application/json",
    )
    assert sans.status_code == 403  # session sans jeton CSRF : refusée
    r = c.post(
        f"/v1/pro/listings/{a.pk}/media",
        {"kind": "photo", "size_bytes": len(donnees)},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=jeton,
    )
    assert r.status_code == 201
    with django_capture_on_commit_callbacks(execute=True):
        p = c.patch(
            r.json()["upload_url"],
            donnees,
            content_type="application/offset+octet-stream",
            HTTP_TUS_RESUMABLE="1.0.0",
            HTTP_UPLOAD_OFFSET="0",
            HTTP_X_CSRFTOKEN=jeton,
        )
    assert p.status_code == 204


def _jeton(client, url="/connexion"):
    import re

    html = client.get(url).content.decode()
    trouve = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', html)
    return (
        trouve.group(1)
        if trouve
        else client.cookies["csrftoken" if "csrftoken" in client.cookies else "lgcsrf"].value
    )


# --------------------------------------------------------------- mise en forme de la description (V6)
def test_l_editeur_propose_la_barre_de_mise_en_forme(session_gerant):
    c, _ = session_gerant
    page = c.get("/pro/annonces/nouvelle").content.decode()
    assert (
        "data-mise-en-forme" in page
        and 'data-format="gras"' in page
        and "js/mise-en-forme.js" in page
    )
    assert "Latitude" not in page and "Longitude" not in page  # décision V7


def test_apercu_depuis_le_site_avec_session_et_csrf():
    g = gerant_verifie()
    connexion = Client()
    connexion.post("/connexion", {"phone": g.user.phone_e164[4:], "password": MOT_DE_PASSE})
    c = Client(enforce_csrf_checks=True)
    c.cookies = connexion.cookies
    jeton = c.get("/pro/annonces/nouvelle").context["csrf_token"]
    r = c.post(
        "/v1/pro/markdown/preview",
        {"markdown": "Chambre **calme**\n- Douche"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=str(jeton),
    )
    assert r.status_code == 200 and "<strong>calme</strong>" in r.json()["html"]
    sans_csrf = c.post(
        "/v1/pro/markdown/preview", {"markdown": "x"}, content_type="application/json"
    )
    assert sans_csrf.status_code == 403


def test_apercu_refuse_a_un_locataire_connecte_sur_le_site():
    ClientFactory(phone_e164="+2290197616161")
    c = Client()
    c.post("/connexion", {"phone": "97616161", "password": MOT_DE_PASSE})
    r = c.post("/v1/pro/markdown/preview", {"markdown": "x"}, content_type="application/json")
    assert r.status_code == 403


def test_interrupteur_encore_disponible(session_gerant):
    """Plan v2, W4 : décocher = louée (retirée du fil), recocher = remise en ligne."""
    c, g = session_gerant
    a = ListingFactory(gerant=g, status="published")
    medias_prets(a)  # sans vidéo prête, une annonce remise en ligne repasse en brouillon
    page = c.get("/pro/dashboard").content.decode()
    assert 'role="switch"' in page and 'aria-checked="true"' in page and a.title in page
    r = c.post(
        "/pro/dashboard", {"action": "disponible", "annonce_id": str(a.pk), "disponible": "0"}
    )
    assert r.status_code == 302
    a.refresh_from_db()
    assert a.status == "rented"
    c.post("/pro/dashboard", {"action": "disponible", "annonce_id": str(a.pk), "disponible": "1"})
    a.refresh_from_db()
    assert a.status == "published"


def test_interrupteur_refuse_l_annonce_d_un_autre(session_gerant):
    c, _ = session_gerant
    autre = ListingFactory(status="published")
    r = c.post(
        "/pro/dashboard", {"action": "disponible", "annonce_id": str(autre.pk), "disponible": "0"}
    )
    assert r.status_code == 200 and "introuvable" in r.content.decode().lower()
    autre.refresh_from_db()
    assert autre.status == "published"
