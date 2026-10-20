"""Partage d'une chambre : bouton, aperçu des liens (Open Graph), données structurées et image JPEG d'aperçu."""

import io
import json
import re

import pytest
from django.test import Client
from PIL import Image

from apps.accounts.tests.fabriques import MOT_DE_PASSE
from apps.core.providers.stockage import LocalStorageProvider
from apps.listings.models import ListingMedia
from apps.listings.services import vues
from apps.listings.tests.fabriques import ListingFactory

pytestmark = [pytest.mark.integration, pytest.mark.pg, pytest.mark.django_db]


def html(reponse) -> str:
    return reponse.content.decode()


def meta(page: str, propriete: str) -> str:
    trouve = re.search(
        rf'<meta (?:property|name)="{re.escape(propriete)}"\s+content="([^"]*)"', page
    )
    assert trouve, propriete
    return trouve.group(1)


def json_ld(page: str) -> list:
    bloc = re.search(r'<script type="application/ld\+json">(.*?)</script>', page, re.S)
    assert bloc
    return json.loads(bloc.group(1))


def photo_sur_disque(annonce, racine, couleur="red"):
    media = ListingMedia.objects.create(
        listing=annonce,
        kind="photo",
        status="ready",
        declared_size_bytes=1,
        position=0,
        is_cover=True,
    )
    dossier = f"listings/{annonce.pk}/{media.pk}"
    media.poster_path = f"{dossier}/w480.webp"
    media.variants = {"480": "w480.webp", "1280": "w1280.webp"}
    media.save(update_fields=["poster_path", "variants"])
    chemin = racine / dossier
    chemin.mkdir(parents=True)
    Image.new("RGB", (1600, 1200), couleur).save(chemin / "w1280.webp", "WEBP")
    return media


class TestApercuDuLien:
    def test_la_fiche_decrit_la_chambre_pour_les_aperçus(self):
        a = ListingFactory(
            title="Chambre-salon lumineuse",
            rent_amount=35000,
            rent_negotiable=True,
            has_private_bathroom=True,
            electricity_meter="individual",
            kitchen="private",
        )
        page = html(Client().get(f"/annonces/{a.slug}"))
        url = f"http://testserver/annonces/{a.slug}"
        assert f'<link rel="canonical" href="{url}">' in page
        assert meta(page, "og:url") == url
        assert meta(page, "og:image") == f"{url}/apercu.jpg"
        assert meta(page, "twitter:card") == "summary_large_image"
        titre = meta(page, "og:title")
        assert (
            "Chambre-salon lumineuse" in titre
            and "35 000 F/mois" in titre
            and a.district.name in titre
        )
        description = meta(page, "og:description")
        for attendu in (
            "à débattre",
            "douche intérieure",
            "électricité : compteur personnel",
            "cuisine interne",
        ):
            assert attendu in description
        assert meta(page, "description") == description

    def test_donnees_structurees_sans_adresse_privee(self):
        a = ListingFactory(rent_amount=30000, address_private="Maison bleue derrière la pharmacie")
        page = html(Client().get(f"/annonces/{a.slug}"))
        annonce, fil = json_ld(page)
        assert annonce["@type"] == "RealEstateListing"
        assert annonce["offers"]["price"] == 30000 and annonce["offers"]["priceCurrency"] == "XOF"
        assert annonce["about"]["address"]["addressLocality"] == "Parakou"
        assert annonce["about"]["address"]["streetAddress"] == a.district.name
        assert fil["@type"] == "BreadcrumbList" and len(fil["itemListElement"]) == 3
        assert "pharmacie" not in page

    def test_le_texte_de_l_annonce_ne_casse_pas_le_json_ld(self):
        a = ListingFactory(title="Chambre </script><b>&")
        annonce, _ = json_ld(html(Client().get(f"/annonces/{a.slug}")))
        assert annonce["name"] == "Chambre </script><b>&"

    def test_les_autres_pages_ont_un_aperçu_par_defaut(self):
        page = html(Client().get("/annonces"))
        assert meta(page, "og:image").endswith(".jpg") and "/static/" in meta(page, "og:image")
        assert meta(page, "og:site_name") == "Immo+"

    def test_le_robot_de_whatsapp_ne_compte_pas_de_vue(self):
        assert vues.est_robot("WhatsApp/2.24.1 A")


class TestBoutonPartager:
    def test_bouton_sur_la_fiche_avec_whatsapp_facebook_et_lien(self):
        a = ListingFactory()
        page = html(Client().get(f"/annonces/{a.slug}"))
        assert "Partager" in page and "js/partage" in page
        assert "https://wa.me/?text=" in page
        assert (
            "https://www.facebook.com/sharer/sharer.php?u=http%3A%2F%2Ftestserver%2Fannonces%2F"
            in page
        )
        assert f'value="http://testserver/annonces/{a.slug}"' in page

    def test_le_gerant_partage_ses_annonces_en_ligne_seulement(self):
        en_ligne = ListingFactory()
        brouillon = ListingFactory(gerant=en_ligne.gerant, status="draft")
        c = Client()
        c.force_login(en_ligne.gerant.user, backend="django.contrib.auth.backends.ModelBackend")
        session = c.session
        session["tv"] = en_ligne.gerant.user.token_version
        session.save()
        page = html(c.get("/pro/annonces"))
        assert f"/annonces/{en_ligne.slug}" in page and "lien-" in page
        assert f'value="http://testserver/annonces/{brouillon.slug}"' not in page
        assert MOT_DE_PASSE


class TestImageApercu:
    def test_jpeg_1200_x_630_tire_de_la_couverture(self, settings, tmp_path):
        settings.MEDIA_ROOT = tmp_path
        a = ListingFactory()
        photo_sur_disque(a, tmp_path)
        r = Client().get(f"/annonces/{a.slug}/apercu.jpg")
        assert r.status_code == 200 and r["Content-Type"] == "image/jpeg"
        assert "max-age" in r["Cache-Control"]
        image = Image.open(io.BytesIO(r.content))
        assert image.format == "JPEG" and image.size == (1200, 630)

    def test_sans_photo_image_par_defaut(self):
        a = ListingFactory()
        r = Client().get(f"/annonces/{a.slug}/apercu.jpg")
        assert r.status_code == 302 and r["Location"].endswith(".jpg")

    def test_annonce_masquee_jamais_exposee(self, settings, tmp_path):
        settings.MEDIA_ROOT = tmp_path
        a = ListingFactory(status="hidden")
        photo_sur_disque(a, tmp_path)
        r = Client().get(f"/annonces/{a.slug}/apercu.jpg")
        assert r.status_code == 302


class TestLectureDuStockage:
    pytestmark = [pytest.mark.unitaire]

    def test_lecture_bornee_a_la_racine(self, settings, tmp_path):
        settings.MEDIA_ROOT = tmp_path / "medias"
        (tmp_path / "medias").mkdir()
        (tmp_path / "secret.txt").write_text("non")
        (tmp_path / "medias" / "a.txt").write_text("oui")
        fournisseur = LocalStorageProvider()
        assert fournisseur.lire("a.txt") == b"oui"
        assert fournisseur.lire("../secret.txt") is None
        assert fournisseur.lire("absent.webp") is None
