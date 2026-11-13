"""Recherche : saisie comprise (quartiers reconnus malgré les fautes, remplissage ignoré), « ou » à défaut de « et »."""

import pytest
from django.core.cache import cache
from django.test import Client

from apps.listings.services import annonces, fil, recherche_texte

from .fabriques import DistrictFactory, ListingFactory

QUARTIERS = [
    ("zongo", "Zongo"),
    ("banikanni", "Banikanni"),
    ("zone-industrielle", "Zone Industrielle"),
    ("guema", "Guéma"),
]


class TestAnalyse:
    def test_un_quartier_mal_ecrit_est_reconnu(self):
        a = recherche_texte.analyser("zogo", QUARTIERS)
        assert a.districts == ["zongo"] and a.mots == []
        assert a.reconnus == [{"saisi": "zogo", "nom": "Zongo", "slug": "zongo", "corrige": True}]

    def test_accents_et_majuscules_ne_comptent_pas(self):
        assert recherche_texte.analyser("GUEMA", QUARTIERS).districts == ["guema"]
        assert recherche_texte.analyser("guéma", QUARTIERS).reconnus[0]["corrige"] is False

    def test_un_debut_de_nom_n_est_pas_une_faute(self):
        a = recherche_texte.analyser("bani", QUARTIERS)
        assert a.districts == ["banikanni"] and a.reconnus[0]["corrige"] is False

    def test_un_nom_en_deux_mots(self):
        a = recherche_texte.analyser("zone industriel", QUARTIERS)
        assert a.districts == ["zone-industrielle"] and a.mots == []

    def test_une_phrase_garde_le_quartier_et_les_mots_utiles(self):
        a = recherche_texte.analyser(
            "je cherche une chambre pas chère à zogo avec forage", QUARTIERS
        )
        assert a.districts == ["zongo"]
        assert a.mots == ["forage"]
        assert {"je", "cherche", "une", "chambre", "pas", "chère", "à", "avec"} <= set(a.ignores)

    def test_un_budget_en_chiffres_est_ignore_dans_une_phrase(self):
        a = recherche_texte.analyser("chambre 30000 banikanni", QUARTIERS)
        assert a.districts == ["banikanni"] and a.mots == [] and "30000" in a.ignores

    def test_un_seul_mot_est_garde_tel_quel(self):
        for mot in ("a", "chambre", "forage"):
            assert recherche_texte.analyser(mot, QUARTIERS).mots == [mot]

    def test_un_mot_qui_ne_ressemble_a_aucun_quartier_n_en_devient_pas_un(self):
        a = recherche_texte.analyser("studio cuisine douche", QUARTIERS)
        assert a.districts == [] and a.mots == ["studio", "cuisine", "douche"]

    def test_un_quartier_deja_choisi_dans_les_filtres_prime(self):
        a = recherche_texte.analyser("zogo forage", QUARTIERS, chercher_quartiers=False)
        assert a.districts == [] and a.mots == ["zogo", "forage"]

    def test_la_saisie_est_bornee(self):
        longue = " ".join(f"mot{i}" for i in range(50))
        assert len(recherche_texte.analyser(longue, QUARTIERS).mots) == recherche_texte.MAX_MOTS


@pytest.mark.pg
@pytest.mark.django_db
class TestRechercheDansLeFil:
    @pytest.fixture(autouse=True)
    def _cache(self):
        cache.clear()
        yield
        cache.clear()

    @staticmethod
    def _indexee(**champs):
        annonce = ListingFactory(**champs)
        annonces._vecteur_de_recherche(annonce)
        return annonce

    def test_zogo_trouve_les_chambres_de_zongo(self):
        zongo = DistrictFactory(name="Zongo", slug="zongo-t")
        ailleurs = DistrictFactory(name="Madina", slug="madina-t")
        ici = self._indexee(district=zongo, title="Chambre propre")
        self._indexee(district=ailleurs, title="Chambre ailleurs")
        r = fil.rechercher({"q": "zogo"})
        assert [i["id"] for i in r["items"]] == [ici.pk]
        assert r["interpretation"]["reconnus"][0]["nom"] == "Zongo"
        assert r["interpretation"]["reconnus"][0]["corrige"] is True

    def test_une_phrase_longue_trouve_la_chambre(self):
        zongo = DistrictFactory(name="Zongo", slug="zongo-p")
        voulue = self._indexee(
            district=zongo, title="Chambre avec forage", water_sources=["borehole"]
        )
        self._indexee(district=zongo, title="Chambre simple", water_sources=["running"])
        r = fil.rechercher({"q": "je cherche une chambre pas chère à zogo avec forage"})
        assert voulue.pk in [i["id"] for i in r["items"]]
        assert r["interpretation"]["mode"] == "et"

    def test_ou_quand_aucune_annonce_ne_contient_tous_les_mots(self):
        studio = self._indexee(
            title="Studio moderne", landmark_text="Derrière la pharmacie", water_sources=["running"]
        )
        forage = self._indexee(
            title="Chambre calme",
            landmark_text="Près du forage communautaire",
            water_sources=["running"],
        )
        r = fil.rechercher({"q": "studio forage"})
        ids = {i["id"] for i in r["items"]}
        assert ids == {studio.pk, forage.pk}
        assert r["interpretation"]["mode"] == "ou"

    def test_et_reste_prefere_quand_une_annonce_contient_tous_les_mots(self):
        les_deux = self._indexee(title="Studio avec forage", water_sources=["borehole"])
        self._indexee(title="Studio simple", water_sources=["running"])
        r = fil.rechercher({"q": "studio forage"})
        assert [i["id"] for i in r["items"]] == [les_deux.pk]
        assert r["interpretation"]["mode"] == "et"

    def test_la_page_chambres_explique_ce_qu_elle_a_compris(self):
        DistrictFactory(name="Zongo", slug="zongo-w")
        page = Client().get("/annonces", {"q": "zogo"}).content.decode()
        assert "Quartier compris" in page and "Zongo" in page and "tu as écrit" in page
        assert (
            "Aucune chambre à Zongo pour l&#x27;instant." in page
            or "Aucune chambre à Zongo" in page
        )

    def test_la_page_chambres_dit_pourquoi_elle_montre_des_resultats_partiels(self):
        self._indexee(title="Studio moderne", water_sources=["running"])
        self._indexee(title="Chambre calme avec forage", water_sources=["borehole"])
        page = Client().get("/annonces", {"q": "studio forage"}).content.decode()
        assert "Aucune chambre ne contient tous tes mots" in page

    def test_sans_mot_precis_la_page_le_dit(self):
        self._indexee(title="Chambre calme")
        page = Client().get("/annonces", {"q": "je cherche une chambre"}).content.decode()
        assert "Aucun quartier ni mot précis" in page

    def test_page_vide_propose_des_quartiers_et_la_saisie(self):
        zongo = DistrictFactory(name="Zongo", slug="zongo-s")
        ListingFactory(district=zongo)
        page = Client().get("/annonces", {"q": "introuvablezz"}).content.decode()
        assert "Aucune chambre pour" in page and "introuvablezz" in page
        assert "/quartiers/zongo-s" in page
