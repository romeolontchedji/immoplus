"""Référencement : page « près de l'université », canoniques et noindex des listes, vidéo des aperçus, accueil."""

import pytest
from django.test import Client

from apps.listings.models import ListingMedia
from apps.listings.tests.fabriques import DistrictFactory, ListingFactory

from .test_partage import html, json_ld, meta

pytestmark = [pytest.mark.integration, pytest.mark.pg, pytest.mark.django_db]


class TestPresDeLUniversite:
    def test_seules_les_chambres_proches_du_campus_de_la_plus_proche_a_la_plus_loin(self):
        ListingFactory(title="Chambre à 900 m", distance_to_campus_m=900)
        ListingFactory(title="Chambre à 200 m", distance_to_campus_m=200)
        ListingFactory(title="Chambre à 4 km", distance_to_campus_m=4000)
        page = html(Client().get("/pres-de-l-universite"))
        assert (
            "<title>Chambres à louer près de l&#x27;Université de Parakou (UP) — Immo+</title>"
            in page
        )
        assert "Chambres à louer près de l&#x27;Université de Parakou</h1>" in page
        assert page.index("Chambre à 200 m") < page.index("Chambre à 900 m")
        assert "Chambre à 4 km" not in page
        assert '<link rel="canonical" href="http://testserver/pres-de-l-universite">' in page
        assert 'name="robots"' not in page  # la page nue est indexée

    def test_un_filtre_ajoute_reste_sur_la_page_et_n_est_pas_indexe(self):
        ListingFactory(title="Studio proche", room_type="studio", distance_to_campus_m=300)
        ListingFactory(title="Chambre proche", room_type="single", distance_to_campus_m=300)
        page = html(Client().get("/pres-de-l-universite?type=studio"))
        assert "Studio proche" in page and "Chambre proche" not in page
        assert '<meta name="robots" content="noindex, follow">' in page
        assert '<link rel="canonical" href="http://testserver/pres-de-l-universite">' in page

    def test_dans_le_plan_du_site_et_le_pied_de_page(self):
        assert "/pres-de-l-universite</loc>" in html(Client().get("/sitemap.xml"))
        assert 'href="/pres-de-l-universite"' in html(Client().get("/"))


class TestListes:
    def test_catalogue_et_quartier_ont_leur_canonique_et_leurs_mots_cles(self):
        d = DistrictFactory(name="Albarika", slug="albarika")
        page = html(Client().get("/annonces"))
        assert (
            "<title>Chambres à louer à Parakou — loyers, quartiers, visite vidéo — Immo+</title>"
            in page
        )
        assert "près de l&#x27;Université de Parakou" in meta(page, "description")
        assert '<link rel="canonical" href="http://testserver/annonces">' in page
        quartier = html(Client().get(f"/quartiers/{d.slug}"))
        assert "<title>Chambres à louer à Albarika, Parakou — Immo+</title>" in quartier
        assert '<link rel="canonical" href="http://testserver/quartiers/albarika">' in quartier

    def test_une_liste_filtree_ou_paginee_n_est_pas_indexee(self):
        page = html(Client().get("/annonces?rent_max=20000"))
        assert '<meta name="robots" content="noindex, follow">' in page
        assert '<link rel="canonical" href="http://testserver/annonces">' in page

    def test_le_pied_de_page_mene_aux_pages_de_quartier(self):
        page = html(Client().get("/"))
        assert 'href="/quartiers/banikanni"' in page and "/annonces?district=" not in page


class TestApercuAvecVideo:
    def test_la_visite_en_video_accompagne_l_image_dans_l_aperçu(self):
        a = ListingFactory(title="Chambre filmée")
        ListingMedia.objects.create(
            listing=a, kind="video", status="ready", declared_size_bytes=1, width=720, height=1280,
            playback_path=f"listings/{a.pk}/v1/lecture.mp4", poster_path=f"listings/{a.pk}/v1/affiche.webp",
        )  # fmt: skip
        page = html(Client().get(f"/annonces/{a.slug}"))
        url = f"http://testserver/media/listings/{a.pk}/v1/lecture.mp4"
        assert meta(page, "og:video") == url and meta(page, "og:video:type") == "video/mp4"
        assert meta(page, "og:image").endswith(
            f"/annonces/{a.slug}/apercu.jpg"
        )  # l'image reste en tête
        assert "à louer à" in page.split("<title>")[1].split("</title>")[0]

    def test_sans_video_pas_de_balise_video(self):
        a = ListingFactory()
        assert "og:video" not in html(Client().get(f"/annonces/{a.slug}"))


class TestAccueilEtRobots:
    def test_l_accueil_se_presente_aux_moteurs(self):
        page = html(Client().get("/"))
        assert '<link rel="canonical" href="http://testserver/">' in page
        assert "Université de Parakou" in meta(page, "description")
        types = {bloc["@type"] for bloc in json_ld(page)}
        assert types == {"WebSite", "Organization"}

    def test_les_pages_de_compte_et_de_lien_ne_sont_pas_explorees(self):
        robots = html(Client().get("/robots.txt"))
        for chemin in (
            "/compte",
            "/pro",
            "/connexion",
            "/inscription",
            "/mot-de-passe",
            "/activer",
        ):
            assert f"Disallow: {chemin}\n" in robots
