"""Retours du 20/10 : alertes (critères d'équipement, refus d'une alerte vide), recherche au fil de la frappe,
cautions des compteurs, fiche sans bloc gérant, minimum de 5 photos."""

import re

import pytest
from django.test import Client

from apps.accounts.tests.fabriques import ClientFactory
from apps.core.errors import ErreurMetier
from apps.listings import selectors
from apps.listings.enums import PHOTOS_MIN
from apps.listings.models import Alert, ListingMedia
from apps.listings.services import alertes, annonces
from apps.listings.tests.fabriques import (
    DistrictFactory,
    ListingFactory,
    gerant_verifie,
    medias_prets,
)

pytestmark = [pytest.mark.integration, pytest.mark.pg, pytest.mark.django_db]


def connecte(utilisateur) -> Client:
    c = Client()
    c.force_login(utilisateur, backend="django.contrib.auth.backends.ModelBackend")
    session = c.session
    session["tv"] = utilisateur.token_version
    session.save()
    return c


def titres(q: str) -> set[str]:
    page = Client().get("/annonces", {"q": q}).content.decode()
    return {t for t in ("Studio Banikanni", "Chambre Zongo", "Entrée Albarika") if t in page}


class TestAlertes:
    def test_une_alerte_sans_option_est_refusee(self):
        u = ClientFactory()
        with pytest.raises(ErreurMetier) as e:
            alertes.creer(u, {"label": "Rien"})
        assert e.value.code == "alert_empty"
        page = (
            connecte(u)
            .post("/compte/alertes", {"action": "creer", "label": "Rien"})
            .content.decode()
        )
        assert (
            "Choisis d'abord au moins une option" in page
            and not Alert.objects.filter(user=u).exists()
        )

    def test_plusieurs_choix_et_equipements(self):
        u, a, b = ClientFactory(), DistrictFactory(), DistrictFactory()
        connecte(u).post(
            "/compte/alertes",
            {"action": "creer", "district_ids": [str(a.pk), str(b.pk)], "water_sources": ["borehole", "well"],
             "electricity_meters": ["individual"], "indispensables": ["cloture"]},
        )  # fmt: skip
        alerte = Alert.objects.get(user=u)
        assert set(alerte.district_ids) == {a.pk, b.pk}
        assert alerte.water_sources == ["borehole", "well"] and alerte.fenced_required

    def test_correspondance_par_equipements(self):
        u = ClientFactory()
        alerte = alertes.creer(u, {"water_sources": ["borehole"], "fenced_required": True})
        bonne = ListingFactory(water_sources=["running", "borehole"], is_fenced=True)
        sans_forage = ListingFactory(water_sources=["running"], is_fenced=True)
        ouverte = ListingFactory(water_sources=["borehole"], is_fenced=False)
        assert (alerte.pk, u.pk) in selectors.alertes_correspondantes(bonne.pk)
        for autre in (sans_forage, ouverte):
            assert not selectors.alertes_correspondantes(autre.pk)
        assert selectors.nombre_pour_alerte(alerte) == 1

    def test_seules_les_alertes_actives_en_tete_et_formulaire_replie(self):
        u = ClientFactory()
        Alert.objects.create(user=u, label="Active", max_rent=20000)
        Alert.objects.create(user=u, label="Dormante", max_rent=20000, is_active=False)
        page = connecte(u).get("/compte/alertes").content.decode()
        assert "Alertes actives (1)" in page and "Alertes en pause (1)" in page
        assert '<details class="alertes-nouvelle">' in page  # replié tant qu'on n'a pas cliqué


class TestRecherche:
    @pytest.fixture(autouse=True)
    def annonces(self):
        ListingFactory(title="Studio Banikanni", room_type="studio", water_sources=["borehole"])
        ListingFactory(title="Chambre Zongo", room_type="single", kitchen="private")
        ListingFactory(title="Entrée Albarika", room_type="entree_coucher")

    def test_chaque_lettre_affine(self):
        for annonce in ListingFactory._meta.model.objects.all():
            annonces._vecteur_de_recherche(annonce)
        assert titres("B") == {"Studio Banikanni"}
        assert titres("Ba") == {"Studio Banikanni"}
        assert titres("Zon") == {"Chambre Zongo"}

    def test_les_caracteristiques_comptent(self):
        for annonce in ListingFactory._meta.model.objects.all():
            annonces._vecteur_de_recherche(annonce)
        assert titres("fora") == {"Studio Banikanni"}  # forage, une source d'eau
        assert titres("cuisine int") == {"Chambre Zongo"}
        assert titres("entrée-couché") == {"Entrée Albarika"}  # le type de chambre


class TestFicheEtPublication:
    def test_cautions_distinctes_et_pas_de_bloc_gerant(self):
        a = ListingFactory(
            deposit_months=2, water_deposit_amount=5000, electricity_deposit_amount=10000
        )
        page = Client().get(f"/annonces/{a.slug}").content.decode()
        assert (
            "Caution du loyer" in page and "Caution eau" in page and "Caution électricité" in page
        )
        assert re.search(r"5\W000 F", page) and re.search(r"10\W000 F", page)
        assert "fiche-gerant-entete" not in page and "Contacter le gérant" in page

    def test_cinq_photos_pour_publier(self):
        a = ListingFactory(status="draft")
        medias_prets(a, photos=PHOTOS_MIN - 1)
        assert "trois_photos_pretes" in annonces.manques_a_la_publication(a)
        ListingMedia.objects.create(
            listing=a, kind="photo", status="ready", declared_size_bytes=1, position=9
        )
        assert "trois_photos_pretes" not in annonces.manques_a_la_publication(a)


class TestVideoFacultative:
    def test_publier_sans_video(self):
        a = ListingFactory(status="draft", gerant=gerant_verifie())
        medias_prets(a, photos=PHOTOS_MIN, video=False)
        assert annonces.manques_a_la_publication(a) == []

    def test_retirer_la_video_d_une_annonce_en_ligne(self):
        from apps.listings.services import medias

        a = ListingFactory()
        medias_prets(a, photos=PHOTOS_MIN, video=True)
        video = ListingMedia.objects.get(listing=a, kind="video")
        medias.supprimer(a.gerant, a.pk, video.pk)
        video.refresh_from_db()
        assert video.status == "deleted"

    def test_fiche_sans_video(self):
        a = ListingFactory()
        medias_prets(a, photos=PHOTOS_MIN, video=False)
        page = Client().get(f"/annonces/{a.slug}").content.decode()
        assert "data-galerie" in page and "<video" not in page
